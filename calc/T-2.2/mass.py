"""Round-2 material, installed mass and axial packaging of the CY-MAIN rear module."""
import json
from math import pi, sqrt

import yaml
from scipy.integrate import quad

from vdi2230 import (
    D_MM, D3_MM, GRIP_MM, NECK_MM, NUT_THICK_MM, WASHER_ID_MM, WASHER_OD_MM,
    WASHER_THICK_MM, area_mm2, transition_radius_mm,
)

STEEL_KG_MM3 = 7.85e-6


def ruling_section():
    # Equal first heat-diffusion eigenvalue with a long cylinder, uniform
    # surface quench. J0 first zero 2.4048; flat slab limit also recorded.
    radius_mm, thickness_mm, j0_first = 260., 144., 2.4048255577
    eigen_per_mm2 = (j0_first/radius_mm)**2 + (pi/thickness_mm)**2
    return dict(
        blank_OD_mm=2*radius_mm, blank_thickness_mm=thickness_mm, T_over_4_mm=thickness_mm/4,
        equivalent_diameter_screen_mm=2*j0_first/sqrt(eigen_per_mm2),
        equivalent_infinite_plate_limit_mm=2*j0_first*thickness_mm/pi,
        equivalent_lumped_heat_transfer_screen_mm=4/(2/radius_mm+2/thickness_mm),
        table_round_diameter_range_mm=[160,250], Rp02_table_MPa=600., Rm_table_min_MPa=800.,
        Rp02_purchase_min_MPa=650., Rm_purchase_min_MPa=850.,
    )


def fastener_delta(stud):
    # The threaded material volume is bracketed by core and crest cylinders.
    # Using the pitch diameter estimates the part mass on the same basis.
    pitch_mm = D_MM-.649519*3.
    neck_len_mm = stud["nominal_neck_model_length_mm"]
    new_thread_len_mm = stud["stud_overall_mm"]-neck_len_mm
    taper_len_mm = stud["smooth_transition_length_each_mm"]
    neck_with_tapers_mm3 = (neck_len_mm-2*taper_len_mm)*area_mm2(NECK_MM)
    neck_with_tapers_mm3 += 2*quad(lambda x: pi*transition_radius_mm(x,NECK_MM)**2,0,taper_len_mm)[0]
    old_thread_len_mm = 66.
    hex_socket_mm2 = sqrt(3)/2*19.**2
    old_unthreaded_mm3 = (180.-old_thread_len_mm)*area_mm2(D_MM)
    old_unthreaded_mm3 += 27.*area_mm2(40.)-13.5*hex_socket_mm2
    nut_mm3 = NUT_THICK_MM*(sqrt(3)/2*41.**2-area_mm2(pitch_mm))
    washer_mm3 = WASHER_THICK_MM*area_mm2(WASHER_OD_MM,WASHER_ID_MM)

    def pair(diameter_mm):
        old_mm3 = old_unthreaded_mm3+old_thread_len_mm*area_mm2(diameter_mm)
        new_mm3 = neck_with_tapers_mm3+new_thread_len_mm*area_mm2(diameter_mm)
        new_mm3 += nut_mm3+washer_mm3
        return [8*STEEL_KG_MM3*value for value in (old_mm3,new_mm3)]

    old_kg, new_kg = pair(pitch_mm)
    old_low, new_low = pair(D3_MM)
    old_high, new_high = pair(D_MM)
    return dict(stock_screws_kg=old_kg, eight_stud_nut_washer_sets_kg=new_kg,
                delta_A_kg=new_kg-old_kg,
                material_volume_bracket_delta_A_kg=[new_low-old_high,new_high-old_low])


def study(root, baseline_cover, selected_cover, stud):
    t21 = json.loads((root/"calc/T-2.1/results.json").read_text(encoding="utf-8"))
    working = yaml.safe_load((root/"design/cylinders.t17d.yaml").read_text(encoding="utf-8"))
    base = yaml.safe_load((root/"design/cylinders.t16.yaml").read_text(encoding="utf-8"))
    frame = yaml.safe_load((root/"design/frame.t17d.yaml").read_text(encoding="utf-8"))
    criteria = yaml.safe_load((root/"ops/criteria/design_criteria.yaml").read_text(encoding="utf-8"))
    main = next(row for row in base["cylinders"] if row["id"]=="CY-MAIN")
    main_d1 = next(row for row in working["cylinders"] if row["id"]=="CY-MAIN")
    frame_layout = frame["interfaces"]["layout"]
    thickness_delta_mm = selected_cover["cap_thickness_mm"]-main["cover_thickness_rear_mm"]
    ties = main["tie_rods"]
    ties_delta_kg = ties["n"]*area_mm2(ties["diameter_mm"])*thickness_delta_mm*STEEL_KG_MM3
    cap_delta_kg = selected_cover["mass_kg"]-baseline_cover["mass_kg"]
    delta_B_kg = cap_delta_kg+ties_delta_kg
    delta_fasteners = fastener_delta(stud)
    nominal_base_kg = t21["candidates"][t21["selected"]]["summary"]["mass"]["estimated_machine_with_station_delta_kg"]
    new_kg = nominal_base_kg+delta_B_kg+delta_fasteners["delta_A_kg"]
    limit_kg = criteria["criteria"]["C-MASS-01"]["max_kg"]
    mounting_projection_mm = GRIP_MM+NUT_THICK_MM+stud["stand_proud_above_nut_mm"]
    geometry = dict(
        datum="front bearing plane CY-MAIN against separate cylinder traverse",
        cap_thickness_delta_mm=thickness_delta_mm,
        cylinder_body_before_after_mm=[main_d1["body_length_mm"],main_d1["body_length_mm"]+thickness_delta_mm],
        cylinder_retracted_before_after_mm=[main_d1["rod_tip_retracted_length_mm"],
                                            main_d1["rod_tip_retracted_length_mm"]+thickness_delta_mm],
        cylinder_extended_before_after_mm=[main_d1["rod_tip_extended_length_mm"],
                                          main_d1["rod_tip_extended_length_mm"]+thickness_delta_mm],
        cylinder_tie_elongation_mm=thickness_delta_mm,
        rear_cylinder_projection_to_mount_mm=frame_layout["rear_cylinder_projection_to_mount_mm"]+thickness_delta_mm,
        structural_frame_axial_before_after_mm=[frame_layout["frame_axial_length_mm"]]*2,
        four_column_smooth_span_before_after_mm=[frame["columns"]["smooth_span_mm"]]*2,
        structural_module_axial_excluding_ZSF_and_guards_before_after_mm=[
            frame_layout["module_axial_excluding_ZSF_and_safety_guards_mm"],
            frame_layout["module_axial_excluding_ZSF_and_safety_guards_mm"]+thickness_delta_mm,
        ],
        minimum_nut_clearance_lower_bound_mm=frame_layout["minimum_nut_to_cover_mm"]-thickness_delta_mm,
        minimum_column_tool_clearance_lower_bound_mm=frame_layout["minimum_200mm_tool_to_cover_mm"]-thickness_delta_mm,
        M27_stud_tip_from_cover_mount_mm=mounting_projection_mm,
        additional_projection_of_stud_beyond_catalogue_H1_mm=max(0.,mounting_projection_mm-145.),
        working_stroke_mm=main_d1["stroke_working_mm"], installed_stroke_mm=main_d1["stroke_installed_mm"],
        bore_and_rod_mm=[main["bore_mm"],main["rod_mm"]],
    )
    return dict(
        baseline_T21_kg=nominal_base_kg, limit_kg=limit_kg, nominal_AB_kg=new_kg,
        nominal_reserve_for_T22b_kg=limit_kg-new_kg, limit_pass=new_kg<=limit_kg,
        A=delta_fasteners, B=dict(cover_reference_kg=baseline_cover["mass_kg"],
            cover_selected_kg=selected_cover["mass_kg"], delta_cover_kg=cap_delta_kg,
            delta_M36_cylinder_ties_kg=ties_delta_kg, delta_four_frame_columns_kg=0., delta_B_kg=delta_B_kg),
        geometry=geometry,
        MA_collector_mounts_and_oil_delta_kg=None,
    )
