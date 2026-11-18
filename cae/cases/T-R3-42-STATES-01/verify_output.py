#!/usr/bin/env python3
"""Reproduce the R3 case audit, R4 questions and conditional axial checks."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ANALYSIS = ROOT / "verification/r3_force_path/analysis"
sys.path.insert(0, str(ANALYSIS))
import compare
import yaml

TASK = HERE.name
TASK_PATH = f"coordination/tasks/{TASK}"
BASELINE = "baselines/operator-fork-20261118/state_catalog_index.json"
GEOMETRY = "verification/r4_force_geometry/symbolic_20261116"
DRIVE = ROOT / "drives" / f"{TASK}-axial.json"

GEOMETRY_REQUESTS = {
    "datum_motion": "Базы и локальные оси, исходная поза, траектория и подписанные e_y(q), e_z(q), включая промежуточные положения.",
    "cylinder_frame": "Ось цилиндра, монтажные точки и их DOF, способ передачи реакций, геометрия и паспорт выбранного крепления.",
    "rod_grip": "Геометрия захвата штока, контактные стороны для обоих знаков, люфт и ограничения движения.",
    "grip_transfer": "Точки приложения и локальные оси траверсы/портала, плечи, соединение с передачей усилия в обоих направлениях.",
    "transfer_carrier": "Отдельные L_free_rod(q) и L_free_carrier(q), координаты активных опор и закрепления на полном ходе.",
    "carrier_punch": "Сечения перехода и материал, геометрия захвата для обоих знаков, контакты и зазоры в камере.",
    "carrier_guides": "Координаты и направление каждой направляющей, расстояния между опорами в обеих плоскостях, контактные стороны, зазоры, преднатяг.",
    "guides_frame": "Координаты и разрезы креплений направляющих, опорные поверхности, материал и DOF в обеих плоскостях.",
    "material_reaction": "Геометрия контактных поверхностей и удержания материала. Для A указать путь реакции при пустом пуске, для B контакты упора и замка по фазам.",
    "reaction_frame": "Координаты, ориентации и контактные стороны реакционных опор, схема замыкания в раму и сечения связей.",
    "sections_stability": "Раздельные A, I_y/I_z, W_y/W_z и J штока, носителя и звеньев передачи, материалы и обоснованные закрепления по позам.",
    "envelopes_service": "Габариты и траектории по полному ходу, задние/боковые зазоры, зоны подачи, выдачи и демонтажа.",
    "receiver_cycle": "Положение границы выдачи и приёмника, геометрия удержания остатков, возврата и открытия/замыкания упора.",
}

PHASE_LOADS = {
    "startup_empty": "Начальная реакция при отсутствии сформированного столба, давление и ускорение при запуске.",
    "gather_partial": "Профиль поджатия, фактическая масса порции и удержание при частичном ходе.",
    "approach": "Нагрузка по траектории до первого контакта, момент контакта, трение и ускорение.",
    "work_peak": "Фактический профиль и точка приложения рабочей нагрузки, реакция и удержание материала A.",
    "work_peak_closed": "Фактический рабочий профиль, контакт закрытого упора и распределение нагрузки по замку B.",
    "hold_unload": "Остаточная сила и пружинение во времени, порядок разгрузки и удержание.",
    "unlock": "Остаточная сила на замке, его нагрузка по траектории и условия удержания.",
    "stop_open": "Нагрузки движущегося упора, раскрытие контакта и остаточное удержание.",
    "eject": "Сопротивление выдаче, фактическое перемещение до приёмника и сопротивление остатков.",
    "eject_open": "Сопротивление выдаче с открытым упором, фактическое перемещение и приём остатков.",
    "return_full": "Фазовое сопротивление возврату, удержание столба и передача растяжения по захваченной цепи.",
    "return_full_open": "Фазовое сопротивление возврату при открытом упоре, контакты удержания и передача растяжения.",
    "refill": "Масса и свойства новой порции, реакция и сохранение остатков при повторном заполнении.",
    "close_relock_reset": "Нагрузки на закрывающийся упор и замок, подтверждение освобождения траекторий и сброса.",
    "ready": "Остаточные нагрузки и условия удержания при текущем состоянии материала, приёмника и ресурсов.",
    "jam_emergency": "Нагрузки при заклинивании и торможении, остаточное усилие и условия безопасного удержания.",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads((ROOT / path).read_bytes())


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def input_hash(path):
    return {"path": path, "sha256": sha256((ROOT / path).read_bytes())}


def load_calculation_inputs(source_commit):
    paths = [
        "params/registry.yaml", f"{compare.REL}/compare.py", "scripts/repo_support.py",
        "verification/r4_cycle_interfaces/proposal/baseline_bindings.json",
    ]
    data = yaml.safe_load((ROOT / paths[0]).read_bytes())
    bindings = read_json(paths[-1])["rows"]
    for source in sorted({row["source"] for row in bindings}):
        paths.append(source)
        manifest = read_json(source)
        references = {item["id"]: item for item in manifest["inputs"] + manifest["outputs"]}
        for row in (item for item in bindings if item["source"] == source):
            original = references[row["parameter_id"]]
            fields = ("value", "unit", "revision", "engineering_sha256")
            require(all(original[name] == row[name] for name in fields),
                    f"{source}: force-path binding changed for {row['parameter_id']}")
    for path in paths:
        require(input_hash(path)["sha256"] == sha256(git("show", f"{source_commit}:{path}")),
                f"Numerical input or calculation code changed since {source_commit}: {path}")
    return compare.validate_bindings(bindings, compare.flatten(data)), paths


def axial_reference(state, selected):
    """A quasi-static imposed demand in a captured ideal serial load path."""
    reference = state["source_reference"]
    if reference is None:
        return None
    work = reference == "WORK_PEAK"
    require(work or reference == "RETURN_REQUIRED", f"Unknown load reference {reference}")
    bindings = selected[state["scenario"]]
    force = bindings["load.work_peak" if work else "load.return_required"]
    rod = bindings["cylinder.rod_diameter"]
    coeff = compare.coefficients({name: row["value"] for name, row in bindings.items()})
    force_x = force["value"] if work else -force["value"]
    internal_n = coeff["IDEAL_WORK_N" if work else "IDEAL_RETURN_N"]["value"]
    cylinder_reaction, opposing_reaction = -force_x, -internal_n
    axial_residual = cylinder_reaction + opposing_reaction
    rod_stress = coeff["ROD_WORK_STRESS" if work else "ROD_RETURN_STRESS"]["value"]
    require(internal_n == -force_x and axial_residual == 0.0, "Ideal axial balance failed")
    return {
        "status": "CALCULATED_CONDITIONAL",
        "scope": "IMPOSED_AXIAL_DEMAND_ONLY",
        "assumptions": "Квазистатика, идеальная последовательная захваченная цепь с отношением 1:1 и заданной противоположной осевой реакцией.",
        "inputs": [
            {name: row[name] for name in ("parameter_id", "revision", "engineering_sha256", "value", "unit", "source")}
            for row in (force, rod)
        ],
        "applied_force_x_N": force_x,
        "reaction_on_moving_chain_x_N": -force_x,
        "force_on_frame_at_cylinder_x_N": cylinder_reaction,
        "force_on_frame_at_reaction_x_N": opposing_reaction,
        "signed_internal_axial_force_N": internal_n,
        "rod_nominal_area_m2": coeff["ROD_AREA"]["value"],
        "rod_nominal_axial_stress_Pa": rod_stress,
        "ideal_axial_force_balance_residual_N": axial_residual,
        "actual_force_moment_or_support_loads_assessed": False,
    }


def build_outputs():
    claim_input = read_json(f"{TASK_PATH}/input_manifest.json")
    base = claim_input["source_main_sha"]
    for item in claim_input["inputs"]:
        ref = f"{base}:{item['path']}"
        require(git("rev-parse", ref).decode().strip() == item["git_object"], f"Git input: {ref}")
        require(sha256(git("show", ref)) == item["sha256"], f"Hash input: {ref}")
        if item["path"] != f"{TASK_PATH}/task.json":
            require(input_hash(item["path"])["sha256"] == item["sha256"], f"Working input: {ref}")

    catalog = read_json(BASELINE)
    raw_source = git("show", f"{catalog['source_commit']}:{catalog['source_path']}")
    require(sha256(raw_source) == catalog["source_sha256"], "Frozen source catalog hash")
    cases = catalog["cases"]
    case_ids = [item["case_id"] for item in cases]
    require(case_ids == [f"S42-{index:03d}" for index in range(1, 43)], "Exact catalog ID order")
    require([item["source_index"] for item in cases] == list(range(42)), "Exact source indices")
    require([item["source_state"] for item in cases] == json.loads(raw_source), "Exact source states")

    dependencies = read_json(f"{GEOMETRY}/state_dependencies.json")["rows"]
    require([row["source_state"] for row in dependencies] == json.loads(raw_source), "R4 case join")
    interfaces = read_json(f"{GEOMETRY}/interfaces.json")["rows"]
    by_key = {row["row_key"]: row for row in interfaces}
    require(len(interfaces) == len(by_key) == 52, "Exact interface coverage")
    selected, calc_paths = load_calculation_inputs(catalog["source_commit"])

    audit = []
    drive_checks = []
    handoff = {key: [] for key in by_key}
    for item, dependency in zip(cases, dependencies, strict=True):
        state = item["source_state"]
        case = item["case_id"]
        variant = state["variant"]
        keys = dependency["interface_row_keys"]
        require(len(keys) == len(set(keys)) and keys, f"{case}: duplicate/missing keys")
        for key in keys:
            require(by_key[key]["variant"] == variant, f"{case}: mismatched interface {key}")
            handoff[key].append(case)
        conditional = axial_reference(state, selected)
        if conditional:
            drive_checks.append({"case_id": case, **conditional})
        audit.append({
            "case_id": case,
            "source_index": item["source_index"],
            "variant": variant,
            "scenario": state["scenario"],
            "mode": state["mode"],
            "phase": state["state"],
            "source_reference": state["source_reference"],
            "source_at_fork": item["status_at_fork"],
            "units": {"force": "N", "moment": "N*m", "length": "m", "time": "s"},
            "source_frame": "O на задней плоскости камеры и оси пуансона, +x к выходу, +y к стороне цилиндра V2, +z вверх.",
            "sign": "F_x положительна по +x, моменты по правилу правой руки, внутренний N положителен при растяжении.",
            "pose_domain": state["pose_domain"],
            "interface_ids": keys,
            "phase_load": {
                "status": "UNKNOWN", "value": None,
                "missing_input": PHASE_LOADS[state["state"]],
                "required": "F(q,t), место приложения и оси, включая поперечные и переходные нагрузки.",
            },
            "boundary_conditions": {
                "status": "UNKNOWN", "value": None,
                "phase_requirement": dependency["contact_and_load_requirement"],
                "missing_inputs": dependency["missing_arguments"],
            },
            "conditional_check": str(DRIVE.relative_to(ROOT)) if conditional else None,
            "status": "BLOCKED_INPUTS",
            "actual_result": {
                "axial_force_N": None, "moment_Nm": None, "support_reactions_N": None,
                "capacity_margin": None, "execution": "NOT_RUN",
            },
        })
    require(all(handoff.values()), "Every R4 interface must be used")
    require(len(drive_checks) == 8, "Eight named work/return conditional checks required")
    input_paths = (
        f"{TASK_PATH}/input_manifest.json", BASELINE, f"{GEOMETRY}/state_dependencies.json",
        f"{GEOMETRY}/interfaces.json", f"{GEOMETRY}/symbolic_dependencies.json",
        "verification/r3_force_path/analysis/params/registry.yaml",
        str((HERE / "verify_output.py").relative_to(ROOT)),
        *calc_paths,
    )
    inputs = [input_hash(path) for path in dict.fromkeys(input_paths)]
    context = {"task_id": TASK, "author_session": claim_input["author_session"],
               "source_main_sha": base, "source_catalog_commit": catalog["source_commit"],
               "source_catalog_sha256": catalog["source_sha256"]}
    return {
        HERE / "case_audit.json": {
            **context, "scope": "PRE_R4_CASE_AUDIT",
            "inputs": inputs,
            "counts": dict(Counter(row["status"] for row in audit)),
            "cases": audit,
        },
        HERE / "r4_interface_requests.json": {
            **context, "scope": "GEOMETRY_REQUESTS_FOR_R4",
            "interfaces": [
                {"interface_id": key, "case_ids": ids,
                 "geometry_request": GEOMETRY_REQUESTS[key.split("/", 1)[1]],
                 "source_unknowns": by_key[key]["unknown_arguments"],
                 "source_raw_refs": [
                     {"id": ref["source_id"], "revision": ref["revision"], "path": ref["path"]}
                     for ref in by_key[key]["source_references"] if ref["source"] == "RAW"
                 ]}
                for key, ids in handoff.items()
            ],
        },
        DRIVE: {
            **context, "scope": "CONDITIONAL_AXIAL_CHECKS_FOR_NAMED_REFERENCES",
            "formulae": ["N=-F_x", "A=pi*d^2/4", "sigma=N/A", "sum(F_x)=-F_x+F_x"],
            "cases": drive_checks,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write only the generated R3 outputs")
    args = parser.parse_args()
    outputs = {path: (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
               for path, payload in build_outputs().items()}
    outputs[HERE / "output_manifest.json"] = (json.dumps({
        "task_id": TASK,
        "command": f"python {HERE.relative_to(ROOT)}/verify_output.py",
        "outputs": [{"path": str(path.relative_to(ROOT)), "sha256": sha256(raw)}
                    for path, raw in outputs.items()],
    }, indent=2) + "\n").encode()
    for path, raw in outputs.items():
        if args.write:
            path.write_bytes(raw)
        else:
            require(path.read_bytes() == raw, f"Artifact mismatch: {path.relative_to(ROOT)}")
    print("PASS: 42 audited cases, 52 interface requests, 8 conditional axial checks")


if __name__ == "__main__":
    main()
