"""Rebuild or verify the versioned, conditional REV load-case inputs."""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess


PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]
BASE = "b1f0243f86fef672902bd462b8567a3ec7066f59"
R4 = "a56a62e36a1f2a1e7d1d6081d7c9ec7d5e49ab4a"
CATALOG = "baselines/operator-fork-20261118/state_catalog_index.json"
AUDIT = "cae/cases/T-R3-42-STATES-01/case_audit.json"
RECONCILIATION = "cae/cases/T-R3-42-STATES-01/r4_reconciliation.json"
AXIAL = "drives/T-R3-42-STATES-01-axial.json"
GEOMETRY = "cad/source/force_geometry/manifest.json"
SOURCE_PATHS = (CATALOG, AUDIT, RECONCILIATION, AXIAL, GEOMETRY)
VARIANTS = ("A-V1", "A-V2", "B-V1", "B-V2")
OUTPUT = PACKAGE / "envelope.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def dimension(bindings, field):
    entry = bindings[field]
    require(entry["unit"] == "m" and positive(entry["value"]), f"Invalid length: {field}")
    return entry["value"]


def compile_variant(variant, geometry, references, factors):
    bindings = geometry["original_bindings"][variant[0]]
    work, back = references
    fw, fr = work["applied_force_x_N"], back["applied_force_x_N"]
    require(positive(fw) and positive(-fr), f"Invalid source force sign: {variant}")
    require(fw == bindings["load.work_peak"]["value"] and -fr == bindings["load.return_required"]["value"],
            f"Axial references differ from R4 bindings: {variant}")
    length = dimension(bindings, "chamber.length")
    width = dimension(bindings, "chamber.width")
    height = dimension(bindings, "chamber.height")
    diameter = dimension(bindings, "cylinder.rod_diameter")
    require(all(ref["inputs"][1]["value"] == diameter for ref in references), f"Rod diameter mismatch: {variant}")
    approach = dimension(bindings, "stroke.approach")
    work_end = approach + dimension(bindings, "stroke.work")
    forward_end = work_end + dimension(bindings, "stroke.eject")
    require(math.isclose(forward_end, dimension(bindings, "stroke.return"), abs_tol=1e-12),
            f"Stroke closure: {variant}")
    spans = [length * scale for scale in factors["guide_span_over_chamber_length"]]
    require(all(map(positive, spans)), f"Nonpositive guide span: {variant}")
    return {
        "fcstd": str(Path(GEOMETRY).parent / geometry["variants"][variant]["path"]),
        "fcstd_sha256": geometry["variants"][variant]["sha256"],
        "source_reference_case_ids": {"WORK": work["case_id"], "RETURN": back["case_id"]},
        "reference_force_N": {"WORK": fw, "RETURN": fr},
        "reference_dimensions_m": {"chamber_length": length, "chamber_width": width,
                                   "chamber_height": height, "rod_diameter": diameter},
        "relative_pose_m": {"origin": 0, "approach_end": approach, "work_end": work_end, "forward_end": forward_end},
        "assumed_samples_m": {
            "guide_span": spans,
            "actuator_y": [width * scale for scale in factors["actuator_y_over_chamber_width"][variant[2:]]],
            "reaction_y": [width * scale for scale in factors["reaction_y_over_chamber_width"]],
            "reaction_z": [height * scale for scale in factors["reaction_z_over_chamber_height"]],
        },
    }


def compile_case(case_id, state, variant, profile, paths, fractions, interface_ids):
    lo, hi = [variant["relative_pose_m"][bound] for bound in profile["pose"]]
    require(lo <= hi, f"Inverted pose sampling interval: {case_id}")
    poses = list(dict.fromkeys(lo + (hi - lo) * value for value in fractions))
    reference = variant["reference_force_N"]
    forces = {"ZERO": 0, "REVERSE_WORK": -reference["WORK"], **reference}
    loads = []
    for key in profile["force"]:
        load = forces[key]
        if load == 0:
            held = []
        elif load > 0:
            held = profile.get("positive_paths_by_family", {}).get(state["variant"][0], [])
            held = held or profile.get("positive_paths", profile.get("paths", []))
        else:
            held = profile.get("negative_paths", profile.get("paths", []))
        permitted = {"EITHER", "COMPRESSION" if load > 0 else "TENSION"}
        require(load == 0 or (held and all(paths[path]["sign"] in permitted for path in held)),
                f"Missing or incompatible held path: {case_id}/{key}")
        loads.append({"sample": key, "F_x_N": load, "held_axial_paths": held})
    require(len(loads) >= 2 and sum(row["F_x_N"] == 0 for row in loads) == 1,
            f"Expected unloaded control and forced sample: {case_id}")
    return {"variant": state["variant"], "phase": state["state"], "pose_samples_q_m": poses,
            "axial_samples": loads, "r4_interface_ids": interface_ids,
            "envelope_input_status": "READY_ASSUMED", "envelope_execution": "NOT_RUN",
            "physical_input_status": "BLOCKED_INPUTS", "physical_execution": "NOT_RUN"}


def build(check_git):
    sources = {path: (ROOT / path).read_bytes() for path in SOURCE_PATHS}
    if check_git:
        git("merge-base", "--is-ancestor", R4, BASE)
        for path, data in sources.items():
            require(data == git("show", f"{BASE}:{path}"), f"Input differs from pinned Git blob: {path}")
        require(sources[GEOMETRY] == git("show", f"{R4}:{GEOMETRY}"), "R4 manifest differs from source commit")
    catalog, audit, reconciliation, axial, geometry = (json.loads(sources[path]) for path in SOURCE_PATHS)
    require(reconciliation["geometry_sha"] == R4, "R3 reconciliation does not pin expected geometry")
    require(reconciliation["geometry_manifest_sha256"] == sha256(sources[GEOMETRY]).hexdigest(), "R4 manifest hash mismatch")
    require(reconciliation["r3_audit_sha256"] == sha256(sources[AUDIT]).hexdigest(), "R3 audit hash mismatch")
    settings = (PACKAGE / "assumptions.json").read_bytes()
    assumptions = json.loads(settings)
    fractions = assumptions["pose_fraction_samples"]
    require(fractions == sorted(set(fractions)) and fractions[0] == 0 and fractions[-1] == 1,
            "Pose fractions must cover both endpoints")
    require(assumptions["lifecycle"] == assumptions["comparison_material"]["lifecycle"] == "ASSUMED", "Lifecycle mismatch")
    require(all(positive(value) for value in assumptions["buckling_comparisons"].values()), "Nonpositive K")

    catalog_rows = {row["case_id"]: row["source_state"] for row in catalog["cases"]}
    require(len(catalog_rows) == len(catalog["cases"]) == 42, "Expected 42 unique catalog cases")
    require(catalog_rows.keys() == geometry["cases"].keys() == reconciliation["cases"].keys(), "Case set mismatch")
    require(tuple(geometry["variants"]) == VARIANTS, "Expected four CAD variants")
    references = {}
    for row in axial["cases"]:
        state = catalog_rows[row["case_id"]]
        require(row["status"] == "CALCULATED_CONDITIONAL", "Unexpected axial evidence lifecycle")
        phase = state["state"]
        require(phase in {"work_peak", "work_peak_closed", "return_full", "return_full_open"}, "Unexpected reference phase")
        key = (state["variant"], "WORK" if phase.startswith("work_") else "RETURN")
        require(key not in references, f"Duplicate axial reference: {key}")
        references[key] = row
    require(len(references) == len(axial["cases"]) == 8, "Expected eight axial references")
    variants = {}
    for key in VARIANTS:
        variant = compile_variant(key, geometry, (references[key, "WORK"], references[key, "RETURN"]), assumptions["geometry_factors"])
        sha = sha256((ROOT / variant["fcstd"]).read_bytes()).hexdigest()
        require(sha == variant["fcstd_sha256"], f"FCStd content mismatch or LFS pointer: {key}")
        variants[key] = variant

    profiles = assumptions["phase_profiles"]
    require(profiles.keys() == {state["state"] for state in catalog_rows.values()}, "Phase coverage mismatch")
    cases = {}
    for case_id, state in catalog_rows.items():
        cad_case = geometry["cases"][case_id]
        r3_case = reconciliation["cases"][case_id]
        require(r3_case["status"] == cad_case["geometry_for_load_case"] == "BLOCKED_INPUTS"
                and r3_case["execution"] == "NOT_RUN", f"Unexpected physical status: {case_id}")
        require((cad_case["variant"], cad_case["state"]) == (state["variant"], state["state"]), f"CAD case mismatch: {case_id}")
        cases[case_id] = compile_case(case_id, state, variants[state["variant"]], profiles[state["state"]],
                                      assumptions["held_axial_paths"], fractions, cad_case["interface_ids"])
    return {"schema_version": 1, "scope": "ASSUMED_STATIC_SCREENING", "source_main_sha": BASE,
            "r4_source_sha": R4, "source_sha256": {path: sha256(data).hexdigest() for path, data in sources.items()},
            "assumptions_sha256": sha256(settings).hexdigest(), "variants": variants, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--write", action="store_true", help="Regenerate envelope.json")
    args = parser.parse_args()
    try:
        data = json.dumps(build(args.check_git), ensure_ascii=False, indent=2, allow_nan=False).encode() + b"\n"
        if args.write:
            OUTPUT.write_bytes(data)
        else:
            require(OUTPUT.read_bytes() == data, "envelope.json differs from replay")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print("PASS: 42 assumed cases, 16 phase profiles, 8 axial references and 4 FCStd hashes")


if __name__ == "__main__":
    main()
