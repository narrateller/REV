"""Replay the round-2 rear-module assessment, excluding the transferred chamber."""
import argparse
import json
from math import exp, log, pi, radians, sin
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

from scipy.optimize import brentq
import yaml

from mass import ruling_section, study as mass_study
from render_report import render_report
from vdi2230 import study as vdi_study


HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parents[1]
ROOT = Path(os.environ.get("REV_T22_INPUT_ROOT", OUTPUT)).resolve()
LEVELS = (0, 1, 2, 3)
COVER_STEM = "r2_s16_ma8_recessed_taps_t144_r1.2"
CONVERGENCE_LIMIT = .05
BALANCE_LIMIT = .001


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True)+"\n",
                    encoding="utf-8", newline="\n")


def dump_yaml(path, data):
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=105),
                    encoding="utf-8", newline="\n")


def run_solver(levels):
    subprocess.run([sys.executable, "-B", str(HERE/"cap_fea/joint.py"), "--round-2", "--case",
                    "recessed_taps", "--thickness-mm", "144", "--MA-blend-mm", "1.2", *map(str,levels)],
                   cwd=ROOT, check=True)


def gates():
    path = OUTPUT/"gates.t22.json"
    subprocess.run([sys.executable, "-B", "ops/gates/calc_gates.py", "--params", "design/params.t21.yaml",
                    "--criteria", "ops/criteria/design_criteria.yaml", "--out", str(path)],
                   cwd=ROOT, check=True)
    by_id = {row["id"]:row for row in read_json(path)["gates"]}
    return {gate:{key:by_id[gate][key] for key in ("status","unit","value")}
            for gate in ("G-PFACE","G-DOSE","G-CYCLE")}


def gci(coarse, mid, fine, sizes_mm):
    h3, h2, h1 = sizes_mm
    r21, r32 = h2/h1, h3/h2
    e32, e21 = coarse-mid, mid-fine
    pair_changes = [abs(e32/mid),abs(e21/fine)]
    # For equal adjacent values, the log-order formula is indeterminate.
    order = None
    if abs(e21)>1e-12 and e32/e21>0.:
        ratio = e32/e21

        def equation(p):
            return exp(p*log(r21))*(r32**p-1)/(r21**p-1)-ratio

        if equation(1e-5)*equation(30.) < 0.:
            order = brentq(equation,1e-5,30.)
    if order is None:
        conservative_index = 3*pair_changes[-1]/(r21**2-1)
        return dict(values=[coarse,mid,fine], successive_changes_fraction=pair_changes,
                    observed_order=None, GCI21_fraction=None, asymptotic_ratio=None,
                    indicative_2nd_order_index_fraction=conservative_index,
                    order_status="oscillatory_or_indeterminate")
    GCI21 = 1.25*pair_changes[-1]/(r21**order-1)
    GCI32 = 1.25*pair_changes[0]/(r32**order-1)
    return dict(values=[coarse,mid,fine], successive_changes_fraction=pair_changes,
                observed_order=order,GCI21_fraction=GCI21,GCI32_fraction=GCI32,
                asymptotic_ratio=GCI32/(r21**order*GCI21),order_status="observed")


def convergence(rows):
    if len(rows) < 3:
        return dict(levels=[row["mesh_level"] for row in rows], status="NOT_EVALUATED")
    selected = rows[-3:]
    h_mm = [row["mesh_near_mm"] for row in selected]
    point_results = {}
    for point, point_data in selected[-1]["interior_probes"].items():
        for field in point_data:
            if field != "xyz_mm":
                point_results[f"{point}.{field}"] = gci(
                    *(row["interior_probes"][point][field] for row in selected),h_mm)
    useful_fields = ("static_VM_MPa", "fkm_factor", "unclamped_VM_MPa", "stress_range_VM_MPa")
    region_results = {
        f"{region}.{field}":gci(*(row["regions"][region][field] for row in selected), h_mm)
        for region in selected[-1]["regions"] for field in useful_fields
    }
    point_change = max(max(row["successive_changes_fraction"]) for row in point_results.values())
    region_change = max(max(row["successive_changes_fraction"]) for row in region_results.values())
    return dict(
        status="EVALUATED_THREE_LATEST",
        levels=[row["mesh_level"] for row in selected], local_sizes_mm=h_mm,
        max_fixed_point_change_fraction=point_change, max_regional_change_fraction=region_change,
        fixed_points_pass_5_percent=point_change<CONVERGENCE_LIMIT,
        regional_envelopes_pass_5_percent=region_change<CONVERGENCE_LIMIT,
        fixed_points=point_results, regional_envelopes=region_results,
    )


def collect(allow_partial):
    rows = [read_json(path) for level in LEVELS
            if (path:=HERE/f"cap_fea/{COVER_STEM}_{level}.json").exists()]
    if not rows or (len(rows)!=len(LEVELS) and not allow_partial):
        raise RuntimeError(f"Round-2 mesh collection is incomplete ({len(rows)}/{len(LEVELS)}).")
    baseline = read_json(ROOT/"calc/T-2.2/cap_fea/retained_rear_cap_2.json")
    strength = rows[-1]["regions"]["global"]
    mesh = convergence(rows)
    if not all(row["physical_surface_normals_only"] for row in rows):
        raise RuntimeError("Round-2 summaries must use physical surface normals.")
    max_balance = max(case["residual_fraction"] for level in rows for case in level["balances"].values())
    limits = yaml.safe_load((ROOT/"ops/criteria/design_criteria.yaml").read_text(encoding="utf-8"))["criteria"]
    min_static = limits["C-STR-01"]["min_safety_factor_yield"]
    target_cycles = int(float(limits["C-FAT-01"]["min_cycles"]))
    assert min_static==1.5 and target_cycles==10_000_000
    zsf = vdi_study()
    mass = mass_study(ROOT,baseline,rows[-1],zsf["proposal"])
    holding_B = [
        "Confirm forged disc ruling section and the T/4 mechanical properties.",
        "Qualify the MA collector, pressure taps, and the local barrel/tie/valve interface boundary conditions.",
    ]
    numerical_pass = len(rows)==len(LEVELS) and mesh["fixed_points_pass_5_percent"] \
        and max_balance<=BALANCE_LIMIT and strength["fkm_factor"]>=1. \
        and all(strength[field]>=min_static for field in (
            "static_yield_factor", "fixed_preload_load_to_yield_factor", "static_yield_factor_without_preload"))
    if not numerical_pass:
        holding_B.append("One or more mesh, static, fatigue or reaction conditions are unverified.")
    values = dict(
        task="T-2.2", round=2, structural_status="HOLD", accepted_for_CAD=False,
        criteria=dict(C_STR_01_min=min_static,C_FAT_01_min=1.,cycles=target_cycles,
                      convergence_limit_fraction=CONVERGENCE_LIMIT,balance_limit_fraction=BALANCE_LIMIT),
        pressure_cases=dict(relief_bar=315., pulse_bar=[0.,300.], hydrostatic_relief_N=31.5*pi*140**2,
                            hydrostatic_300_bar_N=30.*pi*140**2,product_force_300_bar_N=1.70e6),
        zsf=zsf,
        cover=dict(status="HOLD", configuration="recessed_taps", material=ruling_section(),
                   reference=baseline, levels=rows, convergence=mesh, latest_strength=strength,
                   max_force_balance_residual_fraction=max_balance, numerical_criteria_pass=numerical_pass,
                   held_for=holding_B, MA_equivalent_ID_mm=44*8**.5,
                   MA_nominal_ligament_at_M36_mm=225*sin(radians(11.25))-19.5-22.),
        chamber=dict(status="HOLD_G_FEA",transferred_to="T-2.2b (D-GK-07)"),
        mass=mass,gates=gates(),
    )
    return values


def design_record(values):
    cap,zsf,weights = (values[key] for key in ("cover","zsf","mass"))
    tool = zsf["tool"]
    return dict(
        task="T-2.2", round=2, status="HOLD", accepted_for_CAD=False,
        design_basis=["D1","D-GK-01","D-GK-03","D-GK-05","D-GK-06","D-GK-07"],
        cover=dict(
            status="HOLD", selected_execution="recessed_taps", material="34CrNiMo6+QT (1.6582)",
            material_requirements=dict(cap["material"], rule="EN 10083-1 Annex A.2.2 / EN 10083-3 Table 8",
                specimen="Tangential specimen at T/4 under the quenched working face; EN 10204 type 3.1."),
            OD_mm=520., thickness_mm=144., through_ZSF_ID_mm=124., through_ZSF_entry_blend_R_mm=4.,
            ZSF_blind_tap_count=8, ZSF_blind_hole_depth_mm=55., ZSF_recess_depth_mm=10.,
            ZSF_recess_diameter_at_surface_mm=30., ZSF_through_H1_reference_mm=145., MA_line_DN=125, MA_branches=8, MA_branch_ID_mm=44.,
            MA_junction_fillet_mm=1.2, MA_centrelines_from_barrel_seat_mm=51.,
            MA_angles_from_Gmsh_X_deg=list(range(0,360,45)),
            M36_angles_from_Gmsh_X_deg=[11.25+22.5*i for i in range(16)],
            MA_equivalent_ID_mm=cap["MA_equivalent_ID_mm"],
            MA_nominal_ligament_to_M36_mm=cap["MA_nominal_ligament_at_M36_mm"],
            finest_mesh_level=cap["levels"][-1]["mesh_level"], strength=cap["latest_strength"],
            force_balance_residual_fraction=cap["max_force_balance_residual_fraction"],
            convergence={key:val for key,val in cap["convergence"].items()
                         if key not in ("fixed_points","regional_envelopes")},
            held_for=cap["held_for"]),
        ZSF=dict(
            NG=100, status=zsf["status"], catalogue=zsf["catalogue"],
            machining_and_assembly=zsf["proposal"], service_tool=tool,
            service_tool_plan_section_mm=dict(
                origin="ZSF axis", coordinates="r radial to bolt, z along bolt away from cover",
                bolt_axis_r_mm=120., catalogue_D2_r_mm=106.,
                tool_radial_intervals_at_full_OD_mm=[120-tool["tool_OD_mm"]/2,120+tool["tool_OD_mm"]/2],
                nearest_bolt_chord_mm=tool["fastener_chord_mm"],
                bolt_tips_z_from_nut_bearing_mm=tool["stud_above_bearing_seat_mm"],
                require_body_radius_at_tool_OD_height_mm=tool["central_clear_radius_at_full_tool_OD_with_2mm_gap_mm"],
                radial_interference_if_D2_and_tool_overlap_axially_mm=
                    -tool["nominal_gap_against_body_D2_if_same_height_mm"],
                nominal_valve_to_tool_radial_clearance_mm=None,
                plan_sketch=[
                    "Adjacent axes at R120, chord 91.84 mm; both tools OD 87 mm.",
                    "Radial section at full OD: ZSF axis (r=0) ... body limit (r=74.5) | 2 mm | tool (r=76.5..163.5).",
                    "Axial section above nut bearing: nut z=0..23.8; stud tip z=56.8; tool service envelope z=0..145.",
                    "Catalogue body D2 projects to r=106; compare only where its axial interval meets tool OD.",
                ],
                unresolved="Map axial profile of the ZSF body, bridge toe load area and puller access before release."),
            engagement=zsf["engagement"],
            diameters=[{key:val for key,val in row.items() if key!="rows"} for row in zsf["pressure_diameter_cases"]],
            held_for=zsf["holds"]),
        integration=weights["geometry"],
        mass=dict(A_delta_kg=weights["A"]["delta_A_kg"], B_delta_kg=weights["B"]["delta_B_kg"],
                  nominal_machine_AB_kg=weights["nominal_AB_kg"],
                  nominal_reserve_for_T22b_kg=weights["nominal_reserve_for_T22b_kg"]),
    )


def chamber_record():
    path = ROOT/"design/chamber_lateral.t22.yaml"
    src = path.read_bytes()
    data = yaml.safe_load(src)
    assert data["status"]=="HOLD_G_FEA"
    expected = "T-2.2b (D-GK-07)"
    if "transferred_to" in data:
        assert data["transferred_to"]==expected
        return src
    newline = b"\r\n" if b"\r\n" in src else b"\n"
    return src+(b"" if src.endswith(b"\n") else newline)+b"transferred_to: T-2.2b (D-GK-07)"+newline


def metrics(values):
    cap,zsf,mass = (values[k] for k in ("cover","zsf","mass"))
    return dict(
        task="T-2.2",round=2,structural_status=values["structural_status"],gates=values["gates"],
        pressure=values["pressure_cases"],
        zsf=dict(proposal=zsf["proposal"],diameters=[
            {k:v for k,v in row.items() if k!="rows"} for row in zsf["pressure_diameter_cases"]],
            fill_stop_gauge_bar=zsf["transient"]["fill_stop_gauge_bar"]),
        cap=dict(material=cap["material"],strength=cap["latest_strength"],numerical_criteria_pass=cap["numerical_criteria_pass"],
                 meshes=len(cap["levels"]),convergence={k:v for k,v in cap["convergence"].items()
                      if k not in ("fixed_points","regional_envelopes")},
                 max_force_balance_residual_fraction=cap["max_force_balance_residual_fraction"]),
        chamber=values["chamber"],mass=mass,
    )


def generate(allow_partial):
    out = collect(allow_partial)
    dump_json(HERE/"results.json",out)
    dump_yaml(OUTPUT/"design/main_cylinder_rear.t22.yaml",design_record(out))
    (OUTPUT/"design/chamber_lateral.t22.yaml").write_bytes(chamber_record())
    dump_json(OUTPUT/"metrics.json",metrics(out))
    (OUTPUT/"report.md").write_text(render_report(out),encoding="utf-8",newline="\n")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solve",action="store_true",help="Replay all four cover meshes before collecting.")
    parser.add_argument("--allow-partial",action="store_true",help="Collect an explicitly incomplete HOLD with available meshes.")
    args = parser.parse_args()
    if args.solve:
        run_solver(LEVELS)
    result = generate(args.allow_partial)
    print(f"{result['structural_status']}, cover meshes = {len(result['cover']['levels'])}, "
          f"nominal machine = {result['mass']['nominal_AB_kg']:.2f} kg")


if __name__=="__main__":
    main()
