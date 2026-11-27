"""Dimensions of analysis solids and dimensional interface checks."""

from dataclasses import asdict, dataclass
from math import pi

from loads import GATE_X_MM, WINDOW_X_MM, read_yaml


@dataclass(frozen=True)
class Layout:
    material: str
    roof_wall_mm: float
    roof_band_mm: float
    floor_band_mm: float
    key_depth_mm: float = 58.
    shoe_depth_mm: float = 74.

    @property
    def roof_width_mm(self):
        return 150. + 2 * self.roof_wall_mm

    def data(self):
        return asdict(self) | {
            "roof_width_mm": self.roof_width_mm, "stations": STATIONS,
            "shoe_abs_y_max_mm": SHOE_ABS_Y_MAX_MM, "structural_fillet_R_mm": ROOT_R_MM,
            "working_bore_corner_R_mm": BORE_CORNER_R_MM, "key_cam": KEY_CAM,
        }


ROOT_R_MM = 15.
BORE_CORNER_R_MM = 1.
SHOE_ABS_Y_MAX_MM = 132.
FLOOR_SKIN_DEPTH_MM = 70.
REAR_FLOOR_DEPTH_MM = 45.
FLOOR_TAPER_X_MM = (104., 138.)
WINDOW_FLOOR_ABS_Y_MM = 109.
WINDOW_SIDEWALL_ABS_Y_MM = 106.
WINDOW_REAR_X_MM = -4.
SEAT_Z_MM = 30. + 74.
LOCK_UPPER_Y_MM = (135., 198.)
LOCK_LOWER_Y_MM = (206., 246.)
KEY_CLOSED_Y_MM = (82., 246.)
KEY_TRAVEL_MM = 54.
LOCK_LEG_X_MM = 21.
LOCK_CAP_MM = 54.
LOWER_RETURN_DEPTH_MM = 57.
LOWER_RETURN_START_Y_MM = 178.
UPPER_ROOT_WIDTH_MM = 22.
WEAR_LAND_DEPTH_MM = 12.
EDGE_R_MM = 5.
CROWN_MM = 0.1
SEAT_ALLOWANCE_MM = 0.02
STATIONS = {"rear": {"x_mm": 55., "key_width_mm": 42., "key_depth_mm": 38.,
                     "leg_width_mm": 16., "cap_depth_mm": 36., "return_depth_mm": 42.},
            "front": {"x_mm": 169., "key_width_mm": 70., "key_depth_mm": 58.,
                      "leg_width_mm": 21., "cap_depth_mm": 54., "return_depth_mm": 57.}}
KEY_CAM = {"input_stroke_mm": 12., "key_stroke_mm": KEY_TRAVEL_MM, "motion_s": .08,
           "residual_load_limit_N": 2000., "efficiency_assumed": .60, "drag_N_per_key_assumed": 600.}
WING_RELIEF_Y_START_MM = 77.5
WING_RELIEF_Y_BLEND_MM = 2.5
WING_RELIEF_CLEARANCE_MM = .65
WING_RELIEF_DEPTH_MM = 6.15
WING_RELIEF_RUNOUT_MM = 25.


def smoothstep(u):
    u = min(1., max(0., u))
    return u * u * (3. - 2. * u)


def gate_wing_mm(y_mm):
    return 6. * smoothstep((abs(y_mm) - 80.) / 45.)


def gate_relief_mm(y_mm):
    y_mm = abs(y_mm)
    return (WING_RELIEF_CLEARANCE_MM * smoothstep((y_mm - WING_RELIEF_Y_START_MM) / WING_RELIEF_Y_BLEND_MM)
            + WING_RELIEF_DEPTH_MM * smoothstep((y_mm - 80.) / 45.))


def interface(layout):
    gate = read_yaml("design/slide_gate.t17d.yaml")
    frame = read_yaml("design/frame.t17d.yaml")
    main = {row["id"]: row for row in read_yaml("design/cylinders.t17d.yaml")["cylinders"]}
    rear = read_yaml("design/main_cylinder_rear.t22.yaml")["integration"]
    rise_mm = GATE_X_MM - gate["face_x_mm"]
    col = frame["columns"]
    span_mm = col["smooth_span_mm"] + rise_mm
    key_park_mm = [u_mm + KEY_TRAVEL_MM for u_mm in KEY_CLOSED_Y_MM]
    lock_z_max_mm = 30. + layout.shoe_depth_mm + layout.key_depth_mm + WEAR_LAND_DEPTH_MM + LOCK_CAP_MM
    # The column check uses its full 70 mm smooth diameter and the same Z datum.
    column_bottom_at_top_mm = col["square_pitch_mm"] / 2 - col["smooth_span_diameter_mm"] / 2
    gate_x_nearest_mm = GATE_X_MM - gate["axial_wing_height_mm"]
    gap_to_shoe_mm = gate_x_nearest_mm - WINDOW_X_MM[1]
    gate_wing_gap_mm = min(gate_relief_mm(y) - gate_wing_mm(y) for y in range(80, 131))
    return {
        "axes": "X towards gate, Y across 150 mm width, Z up, Z=0 at channel centre",
        "window_x_mm": list(WINDOW_X_MM), "window_xy_mm": [200., 150.],
        "working_channel_yz_mm": [150., 60.], "roof_x_mm": [WINDOW_X_MM[1], GATE_X_MM],
        "gate_plane_nominal_mm": GATE_X_MM, "gate_plane_delta_mm": rise_mm,
        "gate_blade_back_x_mm": gate["back_x_mm"] + rise_mm,
        "gate_wing_min_x_mm": gate_x_nearest_mm,
        "gate_plate_width_mm": gate["plate_outline_mm_R"][0],
        "gate_plate_thickness_mm": gate["thickness_mm"],
        "gate_plate_swept_z_mm": gate["swept_plate_vertical_limits_mm"],
        "gate_sweep_y_mm": [-130., 130.], "gate_travel_mm": gate["opening_travel_mm"],
        "gate_housing_pocket_yz_R_mm": gate["housing_pocket_width_height_R_mm"],
        "gate_close_permission_max_punch_x_mm": frame["geometry"]["punch_face_clear_for_gate_close_x_mm"] + rise_mm,
        "gate_wing_relief_min_axial_clearance_mm": gate_wing_gap_mm,
        "gate_wing_relief_max_axial_depth_mm": gate_relief_mm(130.),
        "gate_wing_relief_start_abs_y_mm": WING_RELIEF_Y_START_MM,
        "gate_wing_relief_runout_mm": WING_RELIEF_RUNOUT_MM,
        "clearance_gate_wing_to_shoe_x_mm": gap_to_shoe_mm,
        "cassette_yzx_R_mm": gate["bearing_pair"]["dimensions_mm_R"],
        "cassette_x_mm": [349., 404.],
        "traverse_x_mm": [349., 554.],
        "traverse_window_yz_R_mm": frame["interfaces"]["outlet_width_height_radius_mm"],
        "column_bearing_pitch_mm": col["square_pitch_mm"], "column_hole_mm": col["bore_mm"],
        "column_smooth_span_mm": span_mm, "column_D_mm": col["smooth_span_diameter_mm"],
        "column_preload_N": col["preload_N_per_end"],
        "column_axial_stiffness_each_N_mm": 210000. * pi / 4 * col["smooth_span_diameter_mm"]**2 / span_mm,
        "frame_axial_length_mm": frame["geometry"]["frame_axial_length_mm"] + rise_mm,
        "inner_bearing_planes_spacing_mm": frame["interfaces"]["inner_bearing_planes_spacing_mm"] + rise_mm,
        "main_body_mm": rear["cylinder_body_before_after_mm"][1] + rise_mm,
        "main_rear_cover_thickness_mm": 144.,
        "main_bore_and_rod_geometry_mm": rear["bore_and_rod_mm"],
        "rapid_body_mm": main["CY-RAPID"]["body_length_mm"] + rise_mm,
        "main_installed_stroke_mm": 306. + rise_mm, "main_working_stroke_mm": 281. + rise_mm,
        "main_overrun_mm": [item + rise_mm for item in gate["overtravel_mm"]],
        "min_relaxed_tail_after_axial_allowance_mm": frame["geometry"]["minimum_relaxed_tail_clearance_after_allowance_mm"],
        "shoe_sweep_y_mm": [-SHOE_ABS_Y_MAX_MM, SHOE_ABS_Y_MAX_MM],
        "key_closed_abs_y_mm": list(KEY_CLOSED_Y_MM), "key_park_abs_y_mm": key_park_mm,
        "key_park_to_shoe_clearance_mm": key_park_mm[0] - SHOE_ABS_Y_MAX_MM,
        "closed_cheek_to_shoe_clearance_mm": LOCK_UPPER_Y_MM[0] - SHOE_ABS_Y_MAX_MM,
        "lock_top_z_mm": lock_z_max_mm,
        "lock_to_column_z_clearance_mm": column_bottom_at_top_mm - lock_z_max_mm,
        "lock_to_frame_each_side_mm": frame["interfaces"]["layout"]["frame_transverse_max_mm"] / 2 - key_park_mm[1],
        "lock_x_max_mm": STATIONS["front"]["x_mm"] + STATIONS["front"]["key_width_mm"]/2 + LOCK_LEG_X_MM + .8,
        "lock_side_x_relief": "Cheeks extend across the roof entry only in outboard region |Y| >= 135 mm. Trim at X = 205 mm where closed-ring outline intersects.",
    }
