"""T-2.2f reproducible comparison. Run with Python 3.13 and -B from the worktree."""

from functools import lru_cache
from itertools import product
from math import fsum
from pathlib import Path
import argparse
import json
import sys

import hand
import mass
from load import read_yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE/"cycle"))
from compare import CandidateStudy, RECOVERY
from drive import source_data

FRAME = read_yaml("design/frame.t17d.yaml")
GATE = read_yaml("design/slide_gate.t17d.yaml")
MASS_LIMIT_KG = 40.
STATION_LIMIT_KG = 45.
GATE_LIMIT_S = 5.95
REFERENCE_LIMIT_S = 5.90
HEIGHT_LIMIT_MM = .60
LOCK_CAM_M = .012
D_X_MM = (30., 45., 60., 75., 89.)
# The assumed 10 kg allowance is the T-1.7d gate-line row. It is
# separately shown because the common SB330 vessel is already in the ledger.
HYDRAULIC_ALLOWANCE_KG = next(row["delta_kg"] for row in FRAME["mass_budget"]["delta_rows"]
                             if "линия ГА" in row["item"])


def geometry(kind, roof_mm, pad_y_mm, depth_shoe_mm, depth_floor_mm, roof_depth_mm, cap_depth_mm, limb_x_mm):
    frame_borne = kind=="C"
    front_pad_x_mm = 46. if not roof_mm else 58.
    rear_pad_x_mm = 46.
    body_y_mm = 600. if frame_borne else 432.
    span_mm = FRAME["columns"]["square_pitch_mm"] if frame_borne else 2*(78+pad_y_mm/2)
    # The steel overlap stays in the moving shoe (x < 205) in all cases.
    # In A/D the stationary front cheek can extend outside the opening.
    x_front_mm = min(202-front_pad_x_mm/2, 202+roof_mm-front_pad_x_mm/2-limb_x_mm)
    x_rear_mm = 59.
    limb_y_mm = 75. if frame_borne else 64.
    wall_mm = 48.
    data = dict(body_y_mm=body_y_mm, span_mm=span_mm, shoe_depth_mm=depth_shoe_mm, floor_depth_mm=depth_floor_mm,
                fixed_roof_depth_mm=roof_depth_mm, roof_wall_mm=wall_mm, cap_depth_mm=cap_depth_mm,
                limb_x_mm=limb_x_mm, limb_y_mm=limb_y_mm, limb_height_mm=96+depth_shoe_mm,
                station_x_mm={"rear":x_rear_mm,"front":x_front_mm},
                station_breadth_x_mm={"rear":rear_pad_x_mm+2*limb_x_mm,"front":front_pad_x_mm+2*limb_x_mm},
                pad_x_mm={"rear":rear_pad_x_mm,"front":front_pad_x_mm},
                pad_y_mm=pad_y_mm, pad_park_outer_abs_y_mm=78+2*pad_y_mm+4,
                longitudinal_floor_band_y_mm=135.,
                seat_offset_mm=8., bore_section_mm=[150,60], window_x_mm=[5,205],
                R_root_mm=hand.ROOT_R_MM, R_edge_mm=hand.EDGE_R_MM)
    if frame_borne:
        # Direct upper/lower collectors seated on the chamber crosshead.
        # No load-bearing bolt in the transverse circuit. The pair of arms sees
        # opposing loads; their flexure/shear are in series with the portal.
        arm_mm = GATE["face_x_mm"] + 18 - x_front_mm
        depth_mm = 115.
        I_mm4 = limb_y_mm*depth_mm**3/12
        data.update(frame_borne=True, frame_arm_mm=arm_mm, frame_arm_depth_mm=depth_mm,
                    side_share=.5+(.64-.5)*444/span_mm,
                    frame_mobility_mm_N=2*(arm_mm**3/(3*hand.E_MPa*I_mm4)
                                          + arm_mm/((5/6)*hand.G_MPa*limb_y_mm*depth_mm)))
    return data


@lru_cache(maxsize=None)
def loads_for(roof_mm,x_rear_mm,x_front_mm):
    return hand.extrema(hand.load_cases(roof_mm),x_rear_mm,x_front_mm)


@lru_cache(maxsize=None)
def axial_for(roof_mm,x_rear_mm,x_front_mm,shoe_mm,floor_mm,band_mm,frame_borne):
    geo = dict(station_x_mm={"rear":x_rear_mm,"front":x_front_mm},frame_borne=frame_borne,
               shoe_depth_mm=shoe_mm,floor_depth_mm=floor_mm,longitudinal_floor_band_y_mm=band_mm)
    return hand.axial_bridges(roof_mm,geo)


def drive(geom):
    # Double-acting common cam, four keys, starts on a proven unloaded seat.
    # 0.6 kN per key and 0.60 transmission efficiency from T-1.2b / T-2.2d.
    travel_mm = geom["pad_y_mm"] + 4.
    stem_speed_mm_s = 300.
    t_move_s = 2*12/stem_speed_mm_s
    travel_ratio = travel_mm / 12
    keys_kg = 2*fsum(geom["pad_x_mm"].values())*(geom["pad_y_mm"]+16)*geom["cap_depth_mm"]*mass.DENSITY_KG_MM3
    inertial_N = keys_kg * 4*(travel_mm/1000)/t_move_s**2
    guide_N = 4*600.
    residual_N = 2_000.
    cam_force_N = travel_ratio*(guide_N+inertial_N+2*.15*residual_N)/.60
    return dict(stroke_mm=travel_mm, stem_stroke_mm=12., total_keys_kg=keys_kg,
                peak_key_speed_mm_s=2*travel_mm/t_move_s, minimum_movement_s=t_move_s,
                guide_assumption_N=guide_N, stem_force_N=cam_force_N,
                stem_peak_speed_mm_s=stem_speed_mm_s,
                existing_cycle_screen_cam_time_s=12/300,
                residual_release_limit_N=residual_N,
                requires_confirmation=True)


def evaluate_geometry(kind, roof_mm, geo, hydraulic_delta_kg=0.):
    x1_mm,x2_mm = geo["station_x_mm"].values()
    load = loads_for(roof_mm,x1_mm,x2_mm)
    stations = hand.lock(load,geo)
    axial = axial_for(roof_mm,x1_mm,x2_mm,geo["shoe_depth_mm"],geo["floor_depth_mm"],
                      geo["longitudinal_floor_band_y_mm"],kind=="C")
    sections, fixed_height = hand.fixed_roof(load,geo["fixed_roof_depth_mm"],geo["roof_wall_mm"],150+geo["roof_wall_mm"])
    if kind=="C":
        force_N=max(row["peak_side_315_N"] for row in stations.values())
        b_mm, t_mm = geo["limb_y_mm"],geo["frame_arm_depth_mm"]
        sections["frame_collector"] = hand.strength(6*force_N*geo["frame_arm_mm"]/(b_mm*t_mm**2),
                                                    1.5*force_N/(b_mm*t_mm),hand.FORGE_THICK)
    sections.update({f"axial_{name}": row["strength"] for name,row in axial.items()})
    sections.update({f"{station}_{name}":value for station,row in stations.items()
                     for name,value in row["section_checks"].items()})
    # If the aft upper bearing is unloaded by the forward moment, provide a
    # distinct lower guide. Its clearance adds to motion on the loaded station.
    aft_uplift_N = -load["rear"]["min_reaction_N"]
    rocking_mm = .02 if aft_uplift_N > 1 else 0.
    axial_extra_mm = fsum(row["displacement_bound_mm"] for row in axial.values())
    joints_mm = max(row["height_with_joints_mm"] for row in stations.values()) + rocking_mm + axial_extra_mm
    ideal_mm = max(row["lower_bound_mm"] for row in stations.values())
    total_mm = max(joints_mm, fixed_height.get("total_mm",0.))
    contact_rows = {name:row["contact"] for name,row in stations.items()}
    static_key = min(sections,key=lambda name: sections[name]["static_factor"])
    fatigue_key = min(sections,key=lambda name:sections[name]["FKM"])
    contact_key = max(contact_rows,key=lambda name:contact_rows[name]["static_peak_MPa"]/contact_rows[name]["static_screen_MPa"])
    pulse_key = max(contact_rows,key=lambda name:contact_rows[name]["mean_300_MPa"]/contact_rows[name]["pulsating_screen_MPa"])
    package = mass.ledger(mass.chamber(roof_mm,geo,for_frame=kind=="C"),roof_mm,FRAME,
                          hydraulic_delta_kg=hydraulic_delta_kg)
    static = sections[static_key]["static_factor"]
    fkm = sections[fatigue_key]["FKM"]
    contact = contact_rows[contact_key]
    pulse = contact_rows[pulse_key]
    block = dict(static=static>=1.5, fatigue=fkm>=1., height=total_mm<=HEIGHT_LIMIT_MM,
                 contact=contact["static_peak_MPa"]<=contact["static_screen_MPa"],
                 pulsating_contact=pulse["mean_300_MPa"]<=pulse["pulsating_screen_MPa"],
                 node_mass=package["delta_chamber_kg"]<=MASS_LIMIT_KG,
                 station_mass=package["station_reduction_kg"][-1]<=STATION_LIMIT_KG)
    return dict(kind=kind, roof_mm=roof_mm, geometry=geo, load=load,
                stations=stations, aft_lower_guide_315_N=aft_uplift_N, extra_rocking_mm=rocking_mm,
                axial_bridge_checks=axial, extra_axial_mm=axial_extra_mm,
                sections=sections, static_controlling=static_key, fatigue_controlling=fatigue_key,
                static_factor=static, FKM=fkm, contact=contact, pulsating_contact=pulse,
                height_ideal_mm=max(ideal_mm,fixed_height.get("ideal_mm",0.)),
                height_with_attachments_mm=total_mm, fixed_roof_height=fixed_height,
                mass=package, cam=drive(geo), checks=block)


def loss(row):
    """Largest solid-structure shortfall within the mass budget."""
    return max(1.5/row["static_factor"],1/row["FKM"],row["height_with_attachments_mm"]/HEIGHT_LIMIT_MM)


def layout_search(kind, roof_mm):
    range_y_mm = (46.,56.,66.) if kind!="C" else (66.,82.,98.)
    roof_depths_mm = (105.,125.,145.,165.,195.,225.,255.) if roof_mm else (0.,)
    hydraulic_delta_kg = HYDRAULIC_ALLOWANCE_KG if kind in ("A","D") else 0.
    if roof_mm>=75:
        cfg=source_data()["engineering_inputs"]
        hydraulic_delta_kg += (40-cfg["buffer_oil_L"])/cfg["buffer_oil_L"]*cfg["buffer_filled_mass_allowance_kg"]
    sample_stats = dict(configurations=0,within_mass=0,all_structural=0,all_structural_and_mass=0)
    primary = best = least_volume = None
    primary_rank = best_rank = None
    shoe_depths_mm = (70.,95.,120.,145.,170.,200.,235.,275.,320.)
    floor_depths_mm = (80.,105.,130.,155.,180.,210.,250.,290.,345.)
    for args in product(range_y_mm, shoe_depths_mm, floor_depths_mm,
                        roof_depths_mm, (44.,60.,76.,96.,120.), (16.,23.,30.)):
        geo=geometry(kind,roof_mm,*args)
        if geo["pad_park_outer_abs_y_mm"]+2 > geo["body_y_mm"]/2:
            continue
        row = evaluate_geometry(kind,roof_mm,geo,hydraulic_delta_kg)
        checks = row["checks"]
        fit_mass = checks["node_mass"] and checks["station_mass"]
        fit_solid = checks["static"] and checks["fatigue"] and checks["height"]
        fit_structure = fit_solid and checks["contact"] and checks["pulsating_contact"]
        sample_stats["configurations"] += 1
        sample_stats["within_mass"] += fit_mass
        sample_stats["all_structural"] += fit_structure
        sample_stats["all_structural_and_mass"] += fit_structure and fit_mass
        delta_kg = row["mass"]["delta_chamber_kg"]
        rank = (not fit_mass, not checks["node_mass"],loss(row),row["pulsating_contact"]["mean_300_MPa"],delta_kg)
        if primary_rank is None or rank < primary_rank:
            primary, primary_rank = row, rank
        rank = (not fit_mass,row["mass"]["chamber_kg"])
        if fit_structure and (best_rank is None or rank < best_rank):
            best, best_rank = row, rank
        if fit_solid and (least_volume is None or row["mass"]["chamber_kg"] < least_volume["mass"]["chamber_kg"]):
            least_volume = row
    return primary, best, least_volume, sample_stats


def cycle_key(row):
    ref = row["reference"]["realistic"]
    valid = (row["G_DOSE"]["status"]==row["G_PFACE"]["status"]=="PASS"
             and ref["feasible"]
             and all(key=="cycle_time_limit" for key in row["G_CYCLE_failed_checks"]))
    return not valid, row["G_CYCLE_s"]


def table():
    layout_tradeoffs = {}
    for label,x_values in (("A",(90.,95.)),("B",(0.,)),("C",(0.,)),("D",D_X_MM)):
        for x_mm in x_values:
            print("Sections",label,x_mm,flush=True)
            best, structural_pass, volume, counts = layout_search(label,x_mm)
            layout_tradeoffs[f"{label}_{x_mm:g}"] = dict(best_within_mass=best,
                                                       least_mass_if_all_structural=structural_pass,
                                                       least_mass_strength_height_only=volume,
                                                       search_counts=counts)
    return layout_tradeoffs


def compact(row):
    if row is None:
        return None
    return dict(delta_chamber_kg=row["mass"]["delta_chamber_kg"],
                machine_with_H2_kg=row["mass"]["machine_with_H2_kg"],
                station_reduction_kg=row["mass"]["station_reduction_kg"],
                static_factor=row["static_factor"], FKM=row["FKM"],
                contact=row["contact"], pulsating_contact=row["pulsating_contact"],
                height_ideal_mm=row["height_ideal_mm"], height_with_attachments_mm=row["height_with_attachments_mm"],
                checks=row["checks"], geometry=row["geometry"])


def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+"\n",
                    encoding="utf-8",newline="\n")


def analyze_cycle(row, *, test_variants):
    cam = row["cam"]
    masses = row["mass"]["chamber_rows_kg"]
    shoe_kg = masses["shoe_core"] + masses["wings_and_portal_ties"]
    args = dict(cam_seconds=cam["minimum_movement_s"], cam_force_N=cam["stem_force_N"],
                shoe_mass_kg=shoe_kg)
    results = {}
    for name in test_variants:
        study = CandidateStudy(row["roof_mm"],name,**args)
        one, _ = study.evaluate(fast=True)
        results[name] = one
    best = min(results.values(),key=cycle_key)
    study = CandidateStudy(row["roof_mm"],best["variant"],**args)
    evaluated, _ = study.evaluate()
    reference = evaluated["reference"]["realistic"]
    evaluated["T_2_2f_pass"] = (evaluated["G_CYCLE_status"]=="PASS" and evaluated["G_CYCLE_s"]<=GATE_LIMIT_S
                               and evaluated["G_DOSE"]["status"]=="PASS" and evaluated["G_PFACE"]["status"]=="PASS"
                               and reference["feasible"] and reference["convergence_pass"]
                               and reference["cycle_with_T16_handover_s"]<=REFERENCE_LIMIT_S
                               and reference["rms_shaft_kW"]<=30 and reference["peak_shaft_kW"]<=40)
    return evaluated, {name:dict(G_CYCLE_s=item["G_CYCLE_s"],G_CYCLE_status=item["G_CYCLE_status"],
                         G_CYCLE_RMS_kW=item["G_CYCLE_RMS_kW"],G_CYCLE_peak_kW=item["G_CYCLE_peak_kW"],
                         failed_checks=item["G_CYCLE_failed_checks"],
                         reference=item["reference"]["realistic"].get("cycle_with_T16_handover_s"),
                         dose_status=item["G_DOSE"]["status"],
                         pressure_feasible=item["reference"]["realistic"]["feasible"])
                       for name,item in results.items()}


def calculate(geometries):
    series = {}
    for label,bucket in geometries.items():
        design = bucket["best_within_mass"]
        test_variants = tuple(RECOVERY) if design["roof_mm"] else ("existing",)
        print("A4VSO",label,flush=True)
        cycle, study = analyze_cycle(design,test_variants=test_variants)
        variant = cycle["variant"]
        # The common hydraulic allowance is a planning row only where the replay
        # changes the circuit. The larger A buffer is a separate added row.
        if variant=="existing" and design["roof_mm"]:
            old_kg = design["mass"]["hydraulic_delta_kg"]
            design["mass"] = mass.ledger(design["mass"]["chamber_rows_kg"],design["roof_mm"],FRAME,
                                          hydraulic_delta_kg=old_kg-HYDRAULIC_ALLOWANCE_KG)
            design["checks"]["station_mass"] = design["mass"]["station_reduction_kg"][-1]<=STATION_LIMIT_KG
        control = design["pulsating_contact"]
        station = max(design["stations"],key=lambda label:design["stations"][label]["contact"]["mean_300_MPa"])
        net_x_mm = design["geometry"]["pad_x_mm"][station] - 2*hand.EDGE_R_MM
        required_pad_y_mm = control["flat_min_area_required_mm2"]/net_x_mm + 2*hand.EDGE_R_MM
        quote = bucket["least_mass_strength_height_only"]
        price = dict(cycle_gap_task_s=max(0.,cycle["G_CYCLE_s"]-GATE_LIMIT_S),
                     required_gross_pad_y_nominal_mm=required_pad_y_mm,
                     parked_gross_pad_y_limit_mm=(design["geometry"]["body_y_mm"]/2-84.)/2,
                     minimum_sampled_mass_for_strength_height_kg=quote["mass"]["delta_chamber_kg"] if quote else None,
                     minimum_sampled_mass_for_all_structural_kg=(
                         bucket["least_mass_if_all_structural"]["mass"]["delta_chamber_kg"]
                         if bucket["least_mass_if_all_structural"] else None))
        series[label] = dict(hand=design,cycle=cycle,cycle_sensitivities=study,price=price,
                             least_mass_strength_height_only=compact(quote),
                             least_mass_if_all_structural=compact(bucket["least_mass_if_all_structural"]),
                             search_counts=bucket["search_counts"])
    optimistic,_ = CandidateStudy(90.,"regen_early",cam_m=0.).evaluate()
    base_gate,_ = CandidateStudy(15.,"existing").evaluate()
    if abs(base_gate["G_CYCLE_s"]-5.928629160188188)>1e-9:
        raise AssertionError("T-2.2d G-CYCLE did not reproduce")

    passed = [key for key,row in series.items() if (
        row["search_counts"]["all_structural_and_mass"]>0 and row["cycle"]["T_2_2f_pass"])]
    if passed:
        raise RuntimeError(f"Hand screen needs concept selection and FEA: {passed}")
    return dict(task="T-2.2f",status="STOP_HAND_SCREEN",selected=None,
                interpretation="Mechanical comparison with fixed geometry gates and optimistic recovery sensitivity",
                limits=dict(delta_chamber_kg=MASS_LIMIT_KG,station_reduction_kg=STATION_LIMIT_KG,
                            G_CYCLE_s=GATE_LIMIT_S,reference_cycle_s=REFERENCE_LIMIT_S,
                            height_300_mm=HEIGHT_LIMIT_MM),
                reference_T22d=base_gate,full_roof_optimistic_no_cam=optimistic,
                series=series,
                FEA=dict(status="not_run",reason="No hand-screened configuration meets the simultaneous limits"))


def metrics(result):
    rows = {}
    for name,item in result["series"].items():
        h,c = item["hand"],item["cycle"]
        ref = c["reference"]["realistic"]
        load = h["load"]
        rows[name] = dict(
            shoe_force_final_300_N=load["shoe_final"]["shoe"]["force_N"]/hand.RATIO,
            shoe_force_max_300_N=load["shoe_max"]["shoe"]["force_N"]/hand.RATIO,
            roof_force_max_300_N=load["roof_force"]["roof"]["force_N"]/hand.RATIO,
            static_factor=h["static_factor"], FKM=h["FKM"],
            nominal_stress_range_MPa=h["sections"][h["fatigue_controlling"]]["range_300_MPa"],
            FKM_allowable_stress_range_MPa=h["sections"][h["fatigue_controlling"]]["allowed_range_300_MPa"],
            contact_peak_315_MPa=h["contact"]["static_peak_MPa"],
            contact_screen_MPa=h["contact"]["static_screen_MPa"],
            contact_mean_300_MPa=h["pulsating_contact"]["mean_300_MPa"],
            contact_pulsating_screen_MPa=h["pulsating_contact"]["pulsating_screen_MPa"],
            height_lower_bound_mm=h["height_ideal_mm"],
            height_with_attachments_mm=h["height_with_attachments_mm"],
            chamber_delta_kg=h["mass"]["delta_chamber_kg"],
            machine_with_H2_kg=h["mass"]["machine_with_H2_kg"],
            required_station_reduction_kg=h["mass"]["station_reduction_kg"],
            G_CYCLE_s=c["G_CYCLE_s"], G_CYCLE_pass_T22f=c["T_2_2f_pass"],
            reference_cycle_s=ref.get("cycle_with_T16_handover_s"),
            RMS_shaft_kW=ref.get("rms_shaft_kW"), peak_shaft_kW=ref.get("peak_shaft_kW"),
            price=item["price"])
    return dict(task=result["task"],status=result["status"],selected=None,
                acceptance_limits=result["limits"],
                baseline_gate_cycle_s=result["reference_T22d"]["G_CYCLE_s"], candidates=rows)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--hand-only",action="store_true",help="print the scalar structural screen")
    args=parser.parse_args()
    geometries=table()
    for label,row in geometries.items():
        q=row["best_within_mass"]
        best=row["least_mass_strength_height_only"]
        print(label,round(q["static_factor"],3),round(q["FKM"],3),round(q["height_with_attachments_mm"],3),
              round(q["mass"]["delta_chamber_kg"],2),round(q["contact"]["static_peak_MPa"],1),
              round(q["pulsating_contact"]["mean_300_MPa"],1),None if best is None else
              round(best["mass"]["delta_chamber_kg"],2), flush=True)
    if args.hand_only:
        return
    result=calculate(geometries)
    write_json(HERE/"results.json",result)
    write_json(ROOT/"metrics.json",metrics(result))
    write_json(HERE/"fea"/"status.json",result["FEA"])


if __name__=="__main__":
    main()
