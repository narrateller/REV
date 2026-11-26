"""Gross-volume estimate of the compared lock packages. Units are mm and kg."""

from math import fsum, pi


STEEL_KG_MM3 = 7.85e-6
BASE_MACHINE_KG = 4942.65
REPLACED_CHAMBER_KG = 180.22
H2_KG = (5.0, 18.0)
MACHINE_LIMIT_KG = 5000.0


def box_mm3(x_mm, y_mm, z_mm):
    return x_mm * y_mm * z_mm


def annulus_mm2(outer_mm, inner_mm):
    return pi * (outer_mm**2 - inner_mm**2)


def steel_rows(volumes_mm3, allowances_kg):
    return {name: volume * STEEL_KG_MM3 for name, volume in volumes_mm3.items()} | allowances_kg


def budget(rows_kg):
    assembly_kg = fsum(rows_kg.values())
    delta_kg = assembly_kg - REPLACED_CHAMBER_KG
    machine_kg = BASE_MACHINE_KG + delta_kg
    with_h2_kg = [machine_kg + add_kg for add_kg in H2_KG]
    return {
        "rows_kg": rows_kg,
        "assembly_kg": assembly_kg,
        "delta_kg": delta_kg,
        "machine_kg": machine_kg,
        "machine_with_H2_kg": with_h2_kg,
        "station_reduction_to_5000_with_H2_kg": [
            max(0.0, mass_kg - MACHINE_LIMIT_KG) for mass_kg in with_h2_kg
        ],
    }


def lower_box_mm3(x_mm, y_mm, height_mm, wall_mm):
    # Box with open transverse ends. Diaphragms and end features are added separately.
    return (x_mm * height_mm - (x_mm - 2 * wall_mm) * (height_mm - 2 * wall_mm)) * y_mm


def full_block(key_x_mm, key_y_mm, key_z_mm, shoe_z_mm):
    return budget(steel_rows({
        "closed_floor_box": lower_box_mm3(314, 430, 125, 20),
        "throat_and_guide_walls": 2 * box_mm3(259, 40, 60),
        "shoe_blank_including_rear_guide_riser": box_mm3(200, 150, shoe_z_mm) + box_mm3(82, 120, 80),
        "transverse_lock_blank": box_mm3(key_x_mm, key_y_mm, key_z_mm),
        "two_portal_roofs": 2 * box_mm3(248, 80, 66),
        "four_portal_legs": 4 * box_mm3(68, 80, 192),
    }, {"working_inserts_guides_and_retainers": 10.0, "drive_and_park_support": 15.0}))


def bayonet(post, sector_fraction, floor_x_mm, floor_y_mm, floor_height_mm, interior_web_mm):
    bore_r_mm = post["head_r_mm"] + 1
    shank_r_mm = post["shank_r_mm"]
    head_r_mm = post["head_r_mm"]
    sleeve_r_mm = post["sleeve_r_mm"]
    height_mm = post["tooth_height_mm"]
    lobe_area_mm2 = sector_fraction * annulus_mm2(head_r_mm, shank_r_mm)
    volumes_mm3 = {
        "closed_floor_box": lower_box_mm3(floor_x_mm, floor_y_mm, floor_height_mm, 20),
        "two_floor_webs": 2 * box_mm3(interior_web_mm, floor_y_mm, floor_height_mm - 40),
        "floor_end_diaphragms": 2 * box_mm3(floor_x_mm - 40, 16, floor_height_mm - 40),
        "throat_and_guide_walls": 2 * box_mm3(260, 38, 60),
        "shoe_core": box_mm3(200, 150, 146),
        "shoe_carrier_bridges": 2 * (box_mm3(120, 50, 135) + box_mm3(90, 50, 33)),
        "posts": 2 * pi * shank_r_mm**2 * (post["seat_length_mm"] + height_mm),
        "heads": 2 * lobe_area_mm2 * height_mm,
        "anchor_flange_addition": 2 * annulus_mm2(post["foot_r_mm"], shank_r_mm) * 30,
        "collar_sleeves": 2 * annulus_mm2(sleeve_r_mm, bore_r_mm) * height_mm,
        "collar_lobes": 2 * lobe_area_mm2 * height_mm,
        "carrier_lands": 2 * annulus_mm2(sleeve_r_mm + 7, bore_r_mm) * 25,
    }
    return budget(steel_rows(volumes_mm3, {
        "inserts_and_mechanical_retainers": 5.0,
        "gearing_rack_indexing_and_guards": 7.0,
        "interfaces_and_local_ribs": 10.0,
    }))


def main_frame_block():
    # Reuse the aggregate D1 die module as a mass reference. The obsolete bolts
    # are credited only at their documented T-1.2b geometric mass.
    return budget(steel_rows({"bridges_and_struts": 2 * box_mm3(32, 150, 270) + box_mm3(105, 320, 54)},
                             {"D1_chamber_less_old_keys": REPLACED_CHAMBER_KG - 2 * 9.6084,
                              "replaceable_pads_and_drive": 8.0}))


def closed_zone():
    # Additional enclosed die blank 320 x 260 before the central passage.
    return budget(steel_rows({"die_extension": (320 * 260 - 150 * 60) * 120,
                               "four_longer_smooth_columns": 4 * pi * 35**2 * 120},
                             {"D1_chamber_less_old_keys": REPLACED_CHAMBER_KG - 2 * 9.6084,
                              "longer_main_and_rapid_cylinders_T17d_gross_scaling":
                                  (12.713969 + 2.286638) * 120 / 17}))
