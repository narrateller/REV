"""Replacement chamber, axial growth and station mass ledger in kg."""

from math import fsum, pi

DENSITY_KG_MM3 = 7.85e-6
BASE_MACHINE_KG = 4942.65
BASE_CHAMBER_KG = 180.22
H2_KG = (5., 18.)
MACHINE_LIMIT_KG = 5000.


def chamber(roof_mm, geo, *, for_frame=False):
    b = geo["station_breadth_x_mm"]
    x_pad = geo["pad_x_mm"]
    chamber_y_mm = geo["body_y_mm"]
    shoe_h_mm = geo["shoe_depth_mm"]
    seat_y_mm = geo["pad_y_mm"]
    leg_x_mm = geo["limb_x_mm"]
    leg_y_mm = geo["limb_y_mm"]
    leg_h_mm = geo["limb_height_mm"]
    cap_h_mm = geo["cap_depth_mm"]
    depth_mm = geo["fixed_roof_depth_mm"]
    floor_skin_mm = 24.
    axial_length_mm = 259. + roof_mm
    # Non-overlapping gross core, ribs, wings and side cheeks. Machining
    # deductions only for the rectangular die and the open key pockets.
    volumes_mm3 = {
        "floor_skin": axial_length_mm*chamber_y_mm*floor_skin_mm,
        "ribs_below_window": sum(b.values())*chamber_y_mm*(geo["floor_depth_mm"]-floor_skin_mm),
        "longitudinal_floor_band": max(0.,geo["station_x_mm"]["front"]-geo["station_x_mm"]["rear"]-
                                      sum(b.values())/2)*geo["longitudinal_floor_band_y_mm"]*
                                      (geo["floor_depth_mm"]-floor_skin_mm),
        "fixed_roof_and_additional_floor": roof_mm*(150.+2*geo["roof_wall_mm"])*(
            2*depth_mm-floor_skin_mm) if roof_mm else 0.,
        "channel_sidewalls_60_mm": 2*(259*38+roof_mm*geo["roof_wall_mm"])*60.,
        "shoe_core": 200*150*shoe_h_mm,
        "wings_and_portal_ties": 2*sum(b.values())*(geo["span_mm"]/2+seat_y_mm/2-75)*shoe_h_mm,
        "integral_closed_cheeks": 2*sum(2*leg_x_mm*leg_y_mm*leg_h_mm + (
            width_mm+2*leg_x_mm)*leg_y_mm*cap_h_mm for width_mm in x_pad.values()),
        "four_keys": 2*sum(x_pad.values())*(seat_y_mm+16)*cap_h_mm,
        "frame_shoulders_and_two_axial_collector_pairs": (
            4*leg_y_mm*geo["frame_arm_depth_mm"]*geo["frame_arm_mm"] if for_frame else 0.),
    }
    # The front rib may extend into the stationary channel length. Credit the
    # volume common to the rib and the deeper fixed lower bridge only once.
    x_front_mm = geo["station_x_mm"]["front"]
    start_mm = max(205., x_front_mm - b["front"]/2)
    end_mm = min(205.+roof_mm, x_front_mm + b["front"]/2)
    overlap_mm = max(0., end_mm-start_mm)
    overlap_mm3 = overlap_mm*(150.+2*geo["roof_wall_mm"])*max(
        0., min(depth_mm,geo["floor_depth_mm"])-floor_skin_mm)
    volumes_mm3["fixed_roof_and_additional_floor"] -= overlap_mm3
    rows_kg = {key: vol*DENSITY_KG_MM3 for key,vol in volumes_mm3.items()}
    rows_kg.update(inserts_and_retainers=5., synchronizer_and_guards=7., interfaces_and_local_ribs=10.)
    return rows_kg


def ledger(rows_kg, roof_mm, frame, *, hydraulic_delta_kg=0.):
    main = frame["mass_budget"]["delta_rows"]
    increment = {row["item"]:row["delta_kg"] for row in main}
    columns = frame["columns"]
    delta_frame_kg = (columns["quantity"]*pi/4*columns["smooth_span_diameter_mm"]**2*
                      roof_mm*DENSITY_KG_MM3)
    shift = dict(frame_columns_kg=delta_frame_kg,
                 main_cylinder_filled_kg=increment["CY-MAIN"]*roof_mm/17,
                 rapid_cylinder_pair_filled_kg=increment["CY-RAPID"]*roof_mm/17)
    chamber_kg = fsum(rows_kg.values())
    delta_kg = chamber_kg - BASE_CHAMBER_KG
    before_H2_kg = BASE_MACHINE_KG + delta_kg + fsum(shift.values()) + hydraulic_delta_kg
    with_H2_kg = [before_H2_kg + h2 for h2 in H2_KG]
    return dict(chamber_rows_kg=rows_kg, chamber_kg=chamber_kg,
                baseline_chamber_kg=BASE_CHAMBER_KG, delta_chamber_kg=delta_kg,
                baseline_machine_kg=BASE_MACHINE_KG, shift_rows_kg=shift,
                hydraulic_delta_kg=hydraulic_delta_kg, machine_before_H2_kg=before_H2_kg,
                H2_delta_kg=list(H2_KG), machine_with_H2_kg=with_H2_kg,
                station_reduction_kg=[max(0.,kg-MACHINE_LIMIT_KG) for kg in with_H2_kg])
