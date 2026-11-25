
"""Validate component ports, phase references and directed hydraulic routes."""
from collections import defaultdict, deque
from pathlib import Path
import re

import yaml

from safety_checks import mutation_suite, safety_checks

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DESIGN = ROOT / "design/hydraulics"
CIRCUIT = DESIGN / "T-1.5_circuit.yaml"
INTERLOCKS = DESIGN / "T-1.5_interlocks.yaml"
ENDPOINT = re.compile(r"([A-Z0-9]+)\.([A-Z0-9]+)")
OPERATORS = {"and", "or", "not", "true", "false"}
BLOCKED = {"closed", "off", "center"}
REQUIRED_FUNCTIONS = {
    "pump_36_kW", "cutoff_relief_unload", "prefill_and_deaeration",
    "regeneration_direct", "hold_decompression", "independent_fault_dump",
    "rapid_drive", "precompaction_local_reliefs", "slide_gate", "tail_priority",
    "lp_accumulator_safety", "external_pilot", "conditioning",
}


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def graph(elements, commands, errors):
    links = defaultdict(list)
    for unit, state in commands.items():
        if unit not in elements or state not in elements[unit]["states"] and state not in BLOCKED:
            errors.append(f"unknown command {unit}={state}")
    for name, item in elements.items():
        state = commands.get(name, item.get("default_state"))
        for flow in item["states"].get(state, []):
            upstream, downstream = flow.split(">")
            links[item["ports"][upstream]].append((item["ports"][downstream], name))
    return links


def net(elements, endpoint):
    unit, port = ENDPOINT.fullmatch(endpoint).groups()
    return elements[unit]["ports"][port]


def find_route(elements, links, endpoints, required=()):
    start, stop = (net(elements, endpoint) for endpoint in endpoints)
    queue = deque([(start, 0, [])])
    visited = {(start, 0)}
    while queue:
        node, matched, path = queue.popleft()
        if node == stop and matched == len(required):
            return path
        for neighbor, unit in links[node]:
            next_matched = matched + (matched < len(required) and unit == required[matched])
            key = neighbor, next_matched
            if key not in visited:
                queue.append((neighbor, next_matched, [*path, unit]))
                visited.add(key)
    return None


def sensor_refs(config):
    for field in (
        "common_conditions", "additional_conditions", "conditions", "entry_conditions",
        "continuation_conditions", "exit_conditions", "sensors", "require_by_deadline",
    ):
        for condition in config.get(field, []):
            yield from (word for word in re.findall(r"[A-Za-z_][A-Za-z_0-9]*", condition)
                        if word not in OPERATORS)


def check(circuit, interlocks, params, sources):
    elements, lines = circuit["elements"], circuit["lines"]
    errors = []
    ratings = []
    unknown_sensors = []
    bad_routes = []
    used_nets = defaultdict(list)
    phase_configs = interlocks["phases"]
    sensor_ids = [item["sensor"] for item in elements.values() if "sensor" in item]
    if len(sensor_ids) != len(set(sensor_ids)):
        errors.append("duplicate sensor tags")
    for unit, item in elements.items():
        if not all(item.get(key) for key in ("size", "series", "manufacturer")):
            ratings.append(f"{unit}: missing designation")
        if item["section"] not in circuit["sections"]:
            errors.append(f"{unit}: unknown section")
        if item["source"] != "project" and item["source"] not in sources["catalogs"]:
            errors.append(f"{unit}: unknown catalogue reference")
        if "catalog_source" in item and item["catalog_source"] not in sources["catalogs"]:
            errors.append(f"{unit}: unknown candidate catalogue reference")
        design, rated = item["p_design_bar"], item["p_rated_bar"]
        if design is not None and (rated is None or rated < design):
            ratings.append(f"{unit}: pressure rating below design")
        catalogue_flow = item.get("catalog_max_L_min", item.get("catalog_flow_at_5bar_L_min"))
        if catalogue_flow is not None and item["Q_L_min"] > catalogue_flow:
            ratings.append(f"{unit}: design flow exceeds selected catalogue flow")
        for port, name in item["ports"].items():
            if name not in lines:
                errors.append(f"{unit}.{port}: undeclared line {name}")
                continue
            used_nets[name].append(f"{unit}.{port}")
            port_design = item.get("port_design_bar", {}).get(port, lines[name]["p_design_bar"])
            port_rating = item.get("port_rated_bar", {}).get(port, rated)
            if port_rating is not None and port_design > port_rating:
                ratings.append(f"{unit}.{port}: pressure rating {port_rating} < {port_design} bar")
        if item["type"] == "proportional_2_2" and item["source"] == "WRC" and item["states"].get("open") != ["B>A"]:
            errors.append(f"{unit}: 150 bar pilot requires the qualified B→A orientation")
        for state, connections in item["states"].items():
            for path in connections:
                if any(port not in item["ports"] for port in path.split(">")):
                    errors.append(f"{unit}.{state}: invalid port pair {path}")
    zsf = elements.get("ZSF", {})
    case = zsf.get("mounting_case")
    flow = sources["catalogs"]["ZSF"].get(f"case_{case}_flow_L_min", 0)
    if case != 2 or zsf.get("Q_L_min", 0) > flow:
        errors.append(f"ZSF: application case {case}, available {flow} L/min; case 2 required")
    for name, line in lines.items():
        if len(used_nets[name]) < 2 and line["kind"] != "gas":
            errors.append(f"{name}: line connects fewer than two ports")
    for name, members in circuit["functions"].items():
        if not members or set(members) - elements.keys():
            errors.append(f"{name}: missing function components")
    if missing := REQUIRED_FUNCTIONS - circuit["functions"].keys():
        errors.append(f"required functions missing: {sorted(missing)}")

    common_commands = interlocks["defaults"]["common_commands"]
    common_routes = interlocks["defaults"]["common_routes"]
    verified = {}

    def test_routes(name, config, commands, extra_routes=()):
        unknown_sensors.extend(f"{name}: {tag}" for tag in sensor_refs(config) if tag not in sensor_ids)
        links = graph(elements, commands, errors)
        verified[name] = []
        declared = config.get("routes", []) + config.get("floating_routes", [])
        for start, stop, *required in [*declared, *extra_routes]:
            try:
                route = find_route(elements, links, (start, stop), required[0] if required else ())
            except (AttributeError, KeyError, ValueError):
                route = None
            if route is None:
                bad_routes.append(f"{name}: {start} → {stop}, {required}")
            else:
                verified[name].append({"from": start, "to": stop, "via": route})
        for start, stop in config.get("forbidden_routes", []):
            if find_route(elements, links, (start, stop)) is not None:
                bad_routes.append(f"{name}: unintended {start} → {stop}")
        # Active proportional stages require external supply and separate drain.
        for unit, state in commands.items():
            item = elements.get(unit, {})
            is_proportional = (item.get("source") == "WRC" and state == "open"
                               or item.get("source") == "WRLE" and state in {"extend", "retract"})
            needs_active_pilot = item.get("source") == "LC2A" and state in {"float", "open"}
            if not (is_proportional or needs_active_pilot):
                continue
            for start, end in [("SAX.A", f"{unit}.X"), (f"{unit}.Y", "T0.D")]:
                if find_route(elements, links, (start, end)) is None:
                    bad_routes.append(f"{name}: missing pilot/drain for {unit}: {start} → {end}")

    by_phase = defaultdict(list)
    unmapped = []
    for step in params["cycle"]:
        name = step["name"]
        matches = [key for key, value in phase_configs.items()
                   if re.fullmatch(value["reference_pattern"], name)]
        if len(matches) == 1:
            by_phase[matches[0]].append(name)
        else:
            unmapped.append(name)
    for name, config in phase_configs.items():
        if not by_phase[name] or not config.get("routes") or not config.get("on_loss"):
            errors.append(f"{name}: missing reference rows, routes, or fault response")
        commands = common_commands | config["commands"]
        test_routes(name, config, commands, common_routes)
        if window := config.get("movement_window"):
            tags = list(sensor_refs(window))
            tags.append(window["position_sensor"])
            unknown_sensors.extend(f"{name}: {tag}" for tag in tags if tag not in sensor_ids)
        if branch := config.get("optional_lp"):
            test_routes(f"{name}/lp", branch, commands | branch["commands"])
    for names in interlocks["permitted_overlaps"]:
        overlap = {}
        all_routes = []
        for name in names:
            config = phase_configs[name]
            for unit, state in config["commands"].items():
                if unit in overlap and overlap[unit] != state:
                    errors.append(f"{names}: conflicting parallel commands for {unit}")
                overlap[unit] = state
            all_routes.extend(config["routes"])
        test_routes("+".join(names), {"routes": all_routes}, common_commands | overlap)
    for name, config in interlocks["operating_branches"].items():
        test_routes(name, config, common_commands | config["commands"])
    for name, config in interlocks.get("switching_windows", {}).items():
        test_routes(name, config, common_commands | config["commands"])
    outputs = interlocks.get("safety_outputs", {})
    for channel, config in outputs.get("channels", {}).items():
        for field in ("feedback", "pressure_feedback"):
            if field in config and config[field] not in sensor_ids:
                unknown_sensors.append(f"safety channel {channel}: {config[field]}")
    for name, config in outputs.items():
        if isinstance(config, dict) and name != "channels":
            unknown_sensors.extend(f"{name}: {tag}" for tag in sensor_refs(config) if tag not in sensor_ids)
    for name, config in interlocks["faults"].items():
        test_routes(name, config, config["commands"])
    for name, conditions in interlocks["guard_library"].items():
        unknown_sensors.extend(f"{name}: {tag}" for tag in sensor_refs({"conditions": conditions})
                               if tag not in sensor_ids)
    phases_without_routes = [row for phase, rows in by_phase.items()
                             if any(error.startswith(f"{phase}:") for error in bad_routes) for row in rows]
    safety_errors, intensification = safety_checks(circuit, interlocks, graph, find_route)
    return {
        "passed": not any((errors, ratings, unknown_sensors, bad_routes, unmapped, safety_errors)),
        "safety_errors": safety_errors, "rod_intensification": intensification,
        "elements": len(elements), "sensors": len(sensor_ids), "lines": len(lines),
        "reference_rows": len(params["cycle"]), "physical_phases": len(phase_configs),
        "phases_without_flow_path": len(unmapped) + len(phases_without_routes),
        "unknown_sensor_interlocks": len(set(unknown_sensors)),
        "elements_without_size_or_underrated": len({entry.split(":")[0].split(".")[0] for entry in ratings}),
        "unmapped_reference_steps": unmapped, "reference_mapping": dict(by_phase),
        "route_errors": bad_routes, "rating_errors": ratings,
        "unknown_sensor_references": sorted(set(unknown_sensors)), "errors": errors,
        "verified_paths": verified,
    }


def evaluate():
    interlocks = read_yaml(INTERLOCKS)
    params = read_yaml(ROOT / interlocks["reference"])
    circuit = read_yaml(CIRCUIT)
    sources = read_yaml(HERE / "sources.yaml")

    def compare(model, logic):
        return check(model, logic, params, sources)

    result = compare(circuit, interlocks)
    mutations = mutation_suite(circuit, interlocks, compare) if result["passed"] else []
    rejected = sum(test["status"] == "FAIL" for test in mutations)
    result["mutations"] = {"total": len(mutations), "rejected": rejected, "cases": mutations}
    result["passed"] = result["passed"] and len(mutations) >= 8 and rejected == len(mutations)
    return result


if __name__ == "__main__":
    import json

    result = evaluate()
    output = HERE / "results.json"
    combined = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    combined["circuit"] = result
    output.write_text(json.dumps(combined, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8", newline="\n")
    print(f"{result['reference_rows']} reference rows; {result['physical_phases']} physical phases")
    print(f"{result['mutations']['rejected']}/{result['mutations']['total']} mutations rejected")
    if not result["passed"]:
        for key in ("safety_errors", "errors", "route_errors", "rating_errors", "unknown_sensor_references",
                    "unmapped_reference_steps"):
            print(key, result[key])
    raise SystemExit(0 if result["passed"] else 1)
