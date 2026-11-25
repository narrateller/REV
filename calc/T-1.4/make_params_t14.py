"""Export a selected drive or an explicitly requested V1 diagnostic."""
import argparse
import json
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location
from math import fsum

import yaml

from drive import HERE, ROOT
from x1_calc import motions

BAND_UPPER_BAR = (20, 50, 100, 150, 200, 250, float("inf"))
SAMPLES = 4000
TAIL_GROUP = "eject_return_close"
TOL_S = 1e-9


def motion_rows(motion, *, group=None, breakpoints_m=None,
                boost=False, boost_pressure_bar=0):
    """Use the maximum pressure over each band as in make_params_t12b.py."""
    boundaries = dict(breakpoints_m or {})
    if motion.marker_m:
        boundaries.setdefault(motion.marker_m, None)
    points_m = sorted(set(boundaries) | {motion.stroke_m * i / SAMPLES for i in range(SAMPLES + 1)})
    bands = []
    for start_m, end_m in zip(points_m, points_m[1:]):
        speed_mm_s = motion.speed_at_m_s((start_m + end_m) / 2) * 1000
        pressure_bar = max(motion.pressure_bar(start_m), motion.pressure_bar(end_m))
        band = next(edge for edge in BAND_UPPER_BAR if pressure_bar <= edge)
        can_boost = boost and pressure_bar <= boost_pressure_bar
        if bands and start_m not in boundaries and bands[-1][:3] == [band, speed_mm_s, can_boost]:
            bands[-1][3:] = [end_m, max(pressure_bar, bands[-1][4])]
        else:
            bands.append([band, speed_mm_s, can_boost, end_m, pressure_bar])
    rows, markers = [], {}
    for _, speed_mm_s, can_boost, end_m, pressure_bar in bands:
        row = dict(name=f"{motion.name} {len(rows) + 1}", actuator=motion.actuator,
                   stroke_mm=end_m * 1000 - fsum(row["stroke_mm"] for row in rows),
                   direction="retract" if motion.mode == "retract" else "extend",
                   pressure_bar=pressure_bar, speed_mm_s="pump", max_speed_mm_s=speed_mm_s,
                   regeneration=motion.mode == "regen", dwell_s=0)
        if rows:
            row["continues"] = True
        if group:
            row["group"] = group
        if can_boost:
            row["use_accumulator"] = True
        rows.append(row)
        if boundaries.get(end_m):
            markers[boundaries[end_m]] = row["name"]
    return rows, markers


def gate_module():
    path = ROOT / "ops/gates/calc_gates.py"
    spec = spec_from_file_location("calc_gates_readonly", path)
    gate = module_from_spec(spec)
    import sys
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = gate
    try:
        spec.loader.exec_module(gate)
    finally:
        sys.path.pop(0)
    return gate


def simulated_tail(gate, params, cycle):
    cylinders = gate.actuators(params)
    positions = {name: [0.] for name in cylinders}
    rows, *_ = gate.evaluate_timed_phases(cycle, cylinders, params["drive"], positions)
    return {row["name"]: row for row in rows}


def make_candidate(params, model, cylinder, settings, drive_projection, charge, feed_s=.64, *, diagnostic=False):
    import copy

    gate = gate_module()
    candidate = copy.deepcopy(params)
    prefix = "T-1.4 round 2 V1 diagnostic; no drive selected." if diagnostic else "T-1.4 round 2 V1."
    candidate["description"] = f"{prefix} D-GK-01, 0.83 kg base, 90 kg/m3 and 0.64 s dosing."
    candidate["main_cylinder"]["p_relief_bar"] = 315
    candidate["drive"].update(drive_projection)
    if charge:
        candidate["drive"]["accumulator"] = charge
    else:
        candidate["drive"].pop("accumulator", None)

    sequence = motions(model, cylinder, 90)
    cycle = []
    for name in ("pre_down", "regen", "press"):
        rows, _ = motion_rows(sequence[name])
        if name == "press":
            rows[-1]["press"] = True
        cycle.extend(rows)
    cycle.extend(dict(name=name, actuator="none", dwell_s=settings.get(key, default))
                 for name, key, default in (("hold", "hold_s", .30), ("unload", "unload_s", .25)))
    cycle.extend(motion_rows(sequence["gate_open"])[0])

    eject_stroke_m = sequence["eject"].stroke_m
    unlock_x_m = settings.get("unlock_x_m", model.main_travel_m)
    unlock_m = min(eject_stroke_m, unlock_x_m - model.press_end_m)
    clear_m = model.overtravel_m + .010
    boost_branches = settings.get("boost_branches", ("return",)) if charge else ()
    low_bar = charge["min_delivery_pressure_bar"] if charge else 0.
    eject, e_marks = motion_rows(sequence["eject"], group=TAIL_GROUP,
                                  breakpoints_m={unlock_m: "unlock"},
                                  boost="eject" in boost_branches, boost_pressure_bar=low_bar)
    stroke_return, r_marks = motion_rows(sequence["return"], group=TAIL_GROUP,
                                         breakpoints_m={clear_m: "close"},
                                         boost="return" in boost_branches, boost_pressure_bar=low_bar)
    pre_up, _ = motion_rows(sequence["pre_up"], group=TAIL_GROUP,
                            boost="pre_up" in boost_branches, boost_pressure_bar=low_bar)

    rows = simulated_tail(gate, candidate, eject)
    pre_up[0]["start_delay_s"] = rows[e_marks["unlock"]]["motion_end_s"] + TOL_S
    rows = simulated_tail(gate, candidate, eject + pre_up)
    stroke_return[0]["start_delay_s"] = rows[eject[-1]["name"]]["motion_end_s"] + TOL_S
    rows = simulated_tail(gate, candidate, eject + stroke_return + pre_up)
    gate_close, _ = motion_rows(sequence["gate_close"], group=TAIL_GROUP,
                                boost="gate_close" in boost_branches, boost_pressure_bar=low_bar)
    gate_close[0]["start_delay_s"] = rows[r_marks["close"]]["motion_end_s"] + TOL_S
    cycle.extend(eject + stroke_return + gate_close + pre_up)
    cycle.append(dict(name="feed", actuator="none", dwell_s=feed_s))
    candidate["cycle"] = cycle
    for motion in ("hold", "unload", "feed"):
        assert "group" not in next(row for row in cycle if row["name"] == motion)
    assert all("group" not in row for row in cycle if row.get("press"))
    gate.validate_params(candidate)
    return candidate


def write_candidate(candidate, path):
    path.write_text(
        "# Generated by calc/T-1.4/make_params_t14.py.\n"
        "# D-GK-01 geometry. Delays are derived from pressure-band travel.\n"
        "# The PLC uses measured positions and confirmations for those transitions.\n"
        + yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")


def main():
    from drive import configuration, get_inputs

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnostic", action="store_true", help="Export V1 for gate comparison only")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    official = ROOT / "design/params.t14.yaml"
    if args.diagnostic:
        if args.out is None or not args.out.resolve().is_relative_to(HERE):
            parser.error("diagnostics require --out inside calc/T-1.4")
        output = args.out
    else:
        result = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
        chosen = result.get("selected_variant")
        if chosen is None:
            parser.error("round 2 has no selected drive; do not overwrite the previous parameter set")
        if chosen == "V2":
            parser.error("schema v1 lacks prefill motion and mechanically linked rapid cylinders")
        if chosen == "V3":
            parser.error("schema v1 lacks a second accumulator and pressure-dependent dispatch")
        output = args.out or official
        if not output.resolve().is_relative_to(HERE) and output.resolve() != official:
            parser.error("output path is outside calc/T-1.4 and design/params.t14.yaml")
    inputs = get_inputs()
    model, cylinder, settings, projection, accumulator = configuration(inputs)
    write_candidate(make_candidate(inputs[1], model, cylinder, settings, projection, accumulator,
                                   diagnostic=args.diagnostic), output)


if __name__ == "__main__":
    main()
