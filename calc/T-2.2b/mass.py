"""Traceable nominal mass of the two compared chamber load paths."""
from math import pi, prod

from hand import (
    DENSITY_KG_MM3, HERE, ROOT, LOCK_X_MM, LOCK_Y_MM, LOCK_Z_MM, json_read, json_write,
    housing_boxes, shoe_boxes, symmetric_boxes, union_volume_mm3,
)

PORTAL_X_MM = ((-51., -1.), (207., 255.))
POST_X_MM = ((-65., 2.), (180., 257.))
PORTAL_Y_MM = (-216., 216.)
PORTAL_HEIGHT_MM = 140.
TIE_Y_MM = 189.
TIE_D_MM = 39.
TIE_CLEAR_D_MM = 42.
TIE_GRIP_MM = 510.
TIE_SEAT_ID_MM = 42.
TIE_SEAT_OD_MM = 66.
TIE_SEAT_HEIGHT_MM = 35.
LOCK_B_Z_MM = (160., 280.)
LOCK_B_X_MM = (-51., 257.)
LOCK_B_Y_MID_MM = (79., 145.)
LOCK_B_Y_END_MM = (62., 125.)
LOCK_PLAN_RIGHT_MM = ((-51.,62.),(-2.,62.),(5.,79.),(205.,79.),(212.,62.),(257.,62.),
                      (257.,125.),(178.,125.),(168.,145.),(5.,145.),(2.,125.),(-51.,125.))
B_HOUSING_EXTERIOR_Y_MM = 216.
B_HOUSING_SIDE_Y_MM = (162., 216.)
B_FLOOR_BOTTOM_Z_MM = -87.
ASSEMBLY_SEAT_AT_REST_OFFSET_MM = .85
B_POST_Z_MM = (-87., 280.+ASSEMBLY_SEAT_AT_REST_OFFSET_MM)
B_SHOE_XYZ_MM = (200., 222., 160.)
STEEL = DENSITY_KG_MM3
RETAINED_CAM_HARDWARE_KG = 5.
HYDRAULIC_TOOL_PROJECTION_MM = 78.


def b_housing_boxes():
    boxes = [(-55.,198.,-216.,216.,-87.,-60.)]
    boxes += symmetric_boxes(75.,116.,-55.,198.,-60.,0.)
    boxes += symmetric_boxes(162.,216.,-55.,257.,-87.,-18.)
    for x0,x1 in POST_X_MM:
        boxes += symmetric_boxes(162.,216.,x0,x1,-18.,B_POST_Z_MM[1])
    return boxes


def study():
    base = json_read(HERE / "reference/results.t22.json")["mass"]
    upstream = json_read(ROOT/"calc/T-1.7c/results.json")["mass"]["baseline_rows"]
    chamber_row = next(row for row in upstream if "T-1.3 grouping minus estimate for gate plate" in row["source"])
    replaced_kg = chamber_row["mass_kg"]
    a_kg = {"retained_mechanism_allowance_kg": RETAINED_CAM_HARDWARE_KG,"housing_gross_kg": union_volume_mm3(housing_boxes())*STEEL,
            "shoe_gross_kg": union_volume_mm3(shoe_boxes())*STEEL,
            "two_locks_gross_kg": 2*prod(b-a for a,b in (LOCK_X_MM,LOCK_Y_MM,LOCK_Z_MM))*STEEL}
    upper_mm3 = sum(x1-x0 for x0,x1 in PORTAL_X_MM)*(PORTAL_Y_MM[1]-PORTAL_Y_MM[0])*PORTAL_HEIGHT_MM
    bosses_mm3 = 2*54*PORTAL_HEIGHT_MM*sum(
        (pb-pa)-(xb-xa) for (pa,pb),(xa,xb) in zip(POST_X_MM,PORTAL_X_MM))
    bore_mm2 = pi/4*TIE_CLEAR_D_MM**2
    housing_mm3 = union_volume_mm3(b_housing_boxes())-4*bore_mm2*(B_POST_Z_MM[1]-B_POST_Z_MM[0])
    ring = (*LOCK_PLAN_RIGHT_MM,LOCK_PLAN_RIGHT_MM[0])
    key_area_mm2 = abs(sum(x0*y1-x1*y0 for (x0,y0),(x1,y1) in zip(ring,ring[1:])))/2
    key_mm3 = key_area_mm2*(LOCK_B_Z_MM[1]-LOCK_B_Z_MM[0])
    stud_mm3 = pi/4*(TIE_D_MM**2*(TIE_GRIP_MM+HYDRAULIC_TOOL_PROJECTION_MM)
                     +(TIE_SEAT_OD_MM**2-TIE_SEAT_ID_MM**2)*TIE_SEAT_HEIGHT_MM)
    b_kg = {"retained_mechanism_allowance_kg": RETAINED_CAM_HARDWARE_KG,
            "housing_minus_four_bores_kg": housing_mm3*STEEL,
            "shoe_gross_kg": prod(B_SHOE_XYZ_MM)*STEEL,
            "two_locks_gross_kg": 2*key_mm3*STEEL,
            "two_portal_yokes_minus_bores_kg": (upper_mm3+bosses_mm3-4*bore_mm2*PORTAL_HEIGHT_MM)*STEEL,
            "four_studs_nuts_seats_kg": 4*stud_mm3*STEEL}
    rear_width = PORTAL_X_MM[0][1]-PORTAL_X_MM[0][0]
    rear_lug_x_width = POST_X_MM[0][1]-POST_X_MM[0][0]
    rear_net_section_mm2 = rear_width*(PORTAL_Y_MM[1]-PORTAL_Y_MM[0])
    rear_net_section_mm2 += 2*54*(rear_lug_x_width-rear_width)-2*bore_mm2
    rear_yoke_112_delta_kg = rear_net_section_mm2*(112.-PORTAL_HEIGHT_MM)*STEEL
    key_x_length = LOCK_B_X_MM[1]-LOCK_B_X_MM[0]
    key_drill_30_delta_kg = -2*pi/4*30**2*key_x_length*STEEL
    key_box_I_mm4 = (LOCK_B_Y_MID_MM[1]-LOCK_B_Y_MID_MM[0])*(LOCK_B_Z_MM[1]-LOCK_B_Z_MM[0])**3/12
    waist_d = .90*(39.-1.226869*4.)
    waist_delta_kg = -4*pi/4*(39.**2-waist_d**2)*410.*STEEL
    pair_spreader_gross_kg = 4*14*((65.+74.)*54.-2*bore_mm2)*STEEL
    lower_nut_pair_kg = 4*44*(3**.5/2*60.**2-pi/4*(39.-1.082532*4.)**2)*STEEL
    output = dict(base_T22_round_2_kg=base["nominal_AB_kg"],
                  nominal_available_delta_kg=base["nominal_reserve_for_T22b_kg"],
                  machine_limit_kg=base["limit_kg"],
                  replaced_D1_row_kg=replaced_kg,
                  replaced_D1_row_source="calc/T-1.7c/results.json / mass.baseline_rows and ops/reports/D1/D1_package.md section 2",
                  base_source="calc/T-2.2/results.json / mass.nominal_AB_kg",
                  outstanding_MA_delta_kg=[5.,18.],
                  outstanding_MA_source="ops/reports/T-2.2/GK_review.md, H2")
    for name, rows in (("a",a_kg),("b",b_kg)):
        assembly_kg = sum(rows.values())
        delta_kg = assembly_kg-replaced_kg
        machine_kg = base["nominal_AB_kg"]+delta_kg
        h2 = [machine_kg+add for add in output["outstanding_MA_delta_kg"]]
        output[name] = dict(rows_kg=rows,assembly_kg=assembly_kg,delta_kg=delta_kg,
            machine_nominal_kg=machine_kg,reserve_kg=base["limit_kg"]-machine_kg,
            machine_with_H2_kg=h2, hyd_station_reduction_for_limit_kg=[max(0.,v-base["limit_kg"]) for v in h2])
    output["b_sensitivity"] = dict(reference_delta_kg=output["b"]["delta_kg"],target_delta_kg=40.,
        delta_over_target_kg=output["b"]["delta_kg"]-40.,
        row_basis=dict(housing="Union of chamber shell, side rails and four riser boxes less tie bores",
            shoe="Solid envelope 200 x 222 x 160 mm",
            bolts="Four gross 39 mm shanks with tensioning tails and modeled top seats",
            keys="Shoelace area of LOCK_PLAN_RIGHT_MM, thickness 120 mm, two mirrored parts",
            yokes="Both transverse blocks with outboard lugs less four tie bores",
            retained_mechanism="5 kg design allowance carried from round 1"),
        rear_yoke_112_mm=dict(delta_kg=rear_yoke_112_delta_kg,
            nominal_bending_stress_multiplier=(PORTAL_HEIGHT_MM/112.)**2,
            deflection_at_same_load_multiplier=(PORTAL_HEIGHT_MM/112.)**3),
        two_30_mm_lock_bores=dict(delta_kg=key_drill_30_delta_kg,axis_y_mm=102.,axis_z_mm=220.,
            length_mm=key_x_length,loss_of_midsection_I_fraction=(pi*30**4/64)/key_box_I_mm4,
            loss_of_midsection_shear_area_fraction=pi/4*30**2/(66*120.)),
        four_waists=dict(delta_kg=waist_delta_kg,diameter_mm=waist_d,length_mm=410.),
        additional_top_and_bottom_spreaders=dict(delta_kg=pair_spreader_gross_kg),
        four_lower_high_nuts=dict(delta_kg=lower_nut_pair_kg),
        package_without_unqualified_savings_delta_kg=output["b"]["delta_kg"]+pair_spreader_gross_kg+lower_nut_pair_kg,
        package_if_all_savings_verified_delta_kg=output["b"]["delta_kg"]+pair_spreader_gross_kg+lower_nut_pair_kg
                                                   +rear_yoke_112_delta_kg+key_drill_30_delta_kg+waist_delta_kg,
        accounting_note="Spreaders and bottom nuts are added gross; top seat retained. "
            "Cage, attachment details and machined fillets are excluded. None of the savings is credited in the current study mass.")
    return output


if __name__ == "__main__":
    json_write(HERE / "mass.json",study())

