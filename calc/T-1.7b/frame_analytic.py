"""T-1.7 section equilibrium and VDI 2230 spring model (N, mm, MPa)."""
from dataclasses import dataclass, replace
from math import cos, hypot, log10, pi, radians, sin, sqrt, tan
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
E_MPa = 210000.0
NU = 0.30
RHO_kg_mm3 = 7.85e-6
HALF_PITCH_mm = 270.0
ECC_mm = 10.0
STATIC_N = 1_940_000.0
CYCLIC_N = 1_700_000.0
CYCLES = 10_000_000
CORNERS = [(-270., -270.), (270., -270.), (270., 270.), (-270., 270.)]
DISCHARGE_BAY_mm = 190.0
MID_SPAN_mm = 550.0 + DISCHARGE_BAY_mm
COLUMN_D_mm = 100.0
COLUMN_MID_D_mm = 70.
COLUMN_MID_BLEND_mm = 18.
COLUMN_OUTER_BLEND_mm = 16.
COLUMN_HOLE_mm = 104.0
COLUMN_INNER_SEAT_BORE_mm = COLUMN_D_mm+2*COLUMN_OUTER_BLEND_mm+2.
THREAD_P_mm = 6.0
NUT_S_mm = 145.0
NUT_H_mm = 80.0
NUT_BEAR_OD_mm = 176.0
WASHER_H_mm = 12.0
COLLAR_H_mm = 40.0
PRELOAD_N = 735_000.0
PRELOAD_SCATTER = 0.05
SETTLEMENT_mm = 0.04
ADAPTER_mm = 55.0
CHAMBER_MODEL = "separate_wide_discharge_pads"
PLATE_HALF_mm = 370.0
DEFLECTION_LIMIT_mm = 0.15


@dataclass(frozen=True)
class Variant:
    name: str
    depth_mm: float
    radius_mm: float
    material: str
    yield_MPa: float
    tensile_MPa: float
    roughness_Rz_um: float
    flange_mm: float = 0.
    chamber_depth_mm: float = 0.
    ring_radius_mm: float = 0.
    rib_half_width_mm: float = 0.

    def at_end(self, end):
        if end == "cylinder":
            return self
        return replace(self, depth_mm=self.chamber_depth_mm,
                       yield_MPa=380. if self.name == "plate" else self.yield_MPa,
                       ring_radius_mm=275. if self.name == "cast" else 0.,
                       rib_half_width_mm=83. if self.name == "cast" else 0.)


VARIANTS = (
    Variant("plate", 190., 48., "S460NL", 370., 530., 12.5, chamber_depth_mm=140.),
    Variant("cast", 238., 36., "G35CrNiMo6-6+QT1", 650., 800., 25.,
            chamber_depth_mm=205., ring_radius_mm=300., rib_half_width_mm=96.),
    Variant("weld", 218., 48., "S460NL", 380., 530., 12.5, 35., chamber_depth_mm=158.),
)

CYLINDER = yaml.safe_load((ROOT / "design/cylinders.t16.yaml").read_text(encoding="utf-8"))["cylinders"][0]
CHAMBER = yaml.safe_load((ROOT / "design/params.t12b.yaml").read_text(encoding="utf-8"))["chamber"]
T12B = json.loads((ROOT/"calc/T-1.2b/results.json").read_text(encoding="utf-8"))
COVER_RADIUS_mm = CYLINDER["cover_OD_mm"] / 2
STUD_RADIUS_mm = CYLINDER["tie_rods"]["PCD_mm"] / 2
STUD_HOLE_RADIUS_mm = CYLINDER["tie_rods"]["hole_diameter_mm"] / 2
STUDS = [(STUD_RADIUS_mm * cos(radians(i * 22.5)),
          STUD_RADIUS_mm * sin(radians(i * 22.5))) for i in range(16)]
REAR_INNER_RADIUS_mm = (CYLINDER["barrel_OD_mm"] + 8) / 2
BRIQUETTE_PATH_WIDTH_mm = CHAMBER["section_mm"][0] + 14
BRIQUETTE_PATH_HEIGHT_mm = CHAMBER["section_mm"][1] + 2
OUTLET_WIDTH_mm, OUTLET_HEIGHT_mm, OUTLET_RADIUS_mm = 176., 74., 20.
PAD_WIDTH_mm, PAD_HEIGHT_mm = 340., 180.
MIN_BEARING_WIDTH_mm, MIN_BEARING_HEIGHT_mm = 260.,160.
RAIL_WIDTH_mm = (PAD_WIDTH_mm-OUTLET_WIDTH_mm)/2
BASE_RHS_LENGTH_mm = 1100.
PLATE_WAIST_mm = 332.
WELD_WAIST_mm = 330.


def outline_radius_mm(variant, end):
    if variant.name == "cast":
        return variant.ring_radius_mm
    if variant.flange_mm:
        return WELD_WAIST_mm
    return PLATE_WAIST_mm if end == "cylinder" else 296.


def chamber_bearing():
    width_mm, height_mm, radius_mm = OUTLET_WIDTH_mm, OUTLET_HEIGHT_mm, OUTLET_RADIUS_mm
    aperture_mm2 = width_mm*height_mm - (4-pi)*radius_mm**2
    min_footprint_area_mm2 = MIN_BEARING_WIDTH_mm*MIN_BEARING_HEIGHT_mm-aperture_mm2
    rail_area_mm2 = 2*RAIL_WIDTH_mm*PAD_HEIGHT_mm
    bay_face_from_home_mm = T12B["axis_A"]["gate_outer_x_mm"]+DISCHARGE_BAY_mm
    upper_dose = T12B["gate"]["clearance_cases"]["upper_dose"]
    longest_mm = max(row["loaded_length_mm"]+row["axial_growth_mm"]
                     for regime in upper_dose.values() for row in regime.values())
    eject_rows = T12B["gate"]["clearance_cases"]
    minimum_tail_clearance_mm = min(
        row["travel_overrun_mm"]-T12B["gate"]["thickness_mm"]-row["axial_growth_mm"]
        for dose in eject_rows.values() for regime in dose.values() for row in regime.values())
    leading_edge_mm = CYLINDER["stroke_installed_mm"]+longest_mm
    return {"gross_patch_mm2":PAD_WIDTH_mm*PAD_HEIGHT_mm,"bearing_area_mm2":rail_area_mm2,
            "minimum_260x160_net_footprint_mm2":min_footprint_area_mm2,
            "required_area_mm2_at_0p6_Rp02": STATIC_N/(.6*800.),
            "mean_pressure_MPa": STATIC_N/rail_area_mm2, "pressure_limit_MPa": .6*800.,
            "rail_bearing_area_mm2":rail_area_mm2,"rail_mean_pressure_MPa":STATIC_N/rail_area_mm2,
            "open_discharge_bay_mm":DISCHARGE_BAY_mm,
            "longest_relaxed_briquette_mm":longest_mm,
            "maximum_leading_edge_from_punch_home_mm":leading_edge_mm,
            "first_closed_outlet_from_punch_home_mm":bay_face_from_home_mm,
            "discharge_axial_clearance_mm":bay_face_from_home_mm-leading_edge_mm,
            "minimum_ejected_tail_to_gate_clearance_mm":minimum_tail_clearance_mm,
            "discharge_clear_width_mm":OUTLET_WIDTH_mm,
            "aperture_corner_reserve_mm": radius_mm - hypot(
                (BRIQUETTE_PATH_WIDTH_mm-width_mm)/2+radius_mm,
                (BRIQUETTE_PATH_HEIGHT_mm-height_mm)/2+radius_mm)}


def discharge_rails():
    clear_radius_mm = OUTLET_WIDTH_mm/2
    pad_radius_mm = PAD_WIDTH_mm/2
    area_mm2 = 2*RAIL_WIDTH_mm*PAD_HEIGHT_mm
    inertia_x_mm4 = 2*RAIL_WIDTH_mm*PAD_HEIGHT_mm**3/12
    inertia_y_mm4 = 2*PAD_HEIGHT_mm*(pad_radius_mm**3-clear_radius_mm**3)/3
    pressure_delta_MPa = STATIC_N*ECC_mm*(pad_radius_mm/inertia_y_mm4+PAD_HEIGHT_mm/2/inertia_x_mm4)
    mean_MPa = STATIC_N/area_mm2
    peak_MPa = mean_MPa+pressure_delta_MPa
    amp_MPa = .4*1000*(1-.22*log10(12.5)*log10(2*1000/400))*10**(-1/15)/1.5
    return {"pressure_max_MPa":peak_MPa,"pressure_min_MPa":mean_MPa-pressure_delta_MPa,
            "static_factor":800/peak_MPa,"nominal_fatigue_factor":amp_MPa/(peak_MPa*CYCLIC_N/STATIC_N/2),
            "axial_opening_mm":STATIC_N*DISCHARGE_BAY_mm/(E_MPa*area_mm2),
            "relative_tilt_rad_xy":[STATIC_N*ECC_mm*DISCHARGE_BAY_mm/(E_MPa*inertia)
                                    for inertia in (inertia_y_mm4,inertia_x_mm4)],
            "euler_pinned_single_N":pi**2*E_MPa*(PAD_HEIGHT_mm*RAIL_WIDTH_mm**3/12)/DISCHARGE_BAY_mm**2}


def annulus_mm2(outer_mm, inner_mm=0.):
    return pi / 4 * (outer_mm**2 - inner_mm**2)


def round_transition(radius_mm, blend_mm):
    """Volume and axial compliance of the quarter-circle shoulder transition."""
    steps = 512
    dtheta_rad = pi/(2*steps)
    volume_mm3 = compliance_mm_N = 0.
    for i in range(steps):
        theta_rad = (i+.5)*dtheta_rad
        r_mm = radius_mm+blend_mm*(1-cos(theta_rad))
        axial_mm = blend_mm*cos(theta_rad)*dtheta_rad
        area_mm2 = pi*r_mm**2
        volume_mm3 += axial_mm*area_mm2
        compliance_mm_N += axial_mm/(E_MPa*area_mm2)
    return volume_mm3,compliance_mm_N


def middle_span():
    span_mm = MID_SPAN_mm-2*COLLAR_H_mm
    blend_mm = COLUMN_MID_BLEND_mm
    smooth_mm = span_mm-2*blend_mm
    shaft_area_mm2 = annulus_mm2(COLUMN_MID_D_mm)
    blend_volume_mm3,blend_compliance_mm_N = round_transition(COLUMN_MID_D_mm/2,blend_mm)
    return {
        "smooth_length_mm":smooth_mm, "between_collars_mm":span_mm,
        "tension_area_mm2":shaft_area_mm2,
        "volume_mm3":shaft_area_mm2*smooth_mm+2*blend_volume_mm3,
        "compliance_mm_N":smooth_mm/(E_MPa*shaft_area_mm2)+2*blend_compliance_mm_N,
    }


def corner_forces_N(force_N, ex_mm=ECC_mm, ey_mm=ECC_mm):
    return [force_N / 4 * (1 + (ex_mm*x + ey_mm*y) / HALF_PITCH_mm**2)
            for x, y in CORNERS]


def column(variant):
    """Local preload closes between an outer nut and an integral inner collar."""
    d_mm, p_mm = COLUMN_D_mm, THREAD_P_mm
    root_mm = d_mm - 1.226869 * p_mm
    pitch_d_mm = d_mm - .649519 * p_mm
    area_stress_mm2 = annulus_mm2(d_mm - .938194 * p_mm)
    area_root_mm2 = annulus_mm2(root_mm)
    area_shank_mm2 = annulus_mm2(d_mm)
    pkg_mm = variant.depth_mm + WASHER_H_mm
    thread_free_mm = 30.0
    # VDI substitution 0.4d under the active nut; 0.2d at the integral shoulder.
    bolt_mm_N = ((pkg_mm - thread_free_mm + .2 * d_mm) / area_shank_mm2
                 + (thread_free_mm + .4 * d_mm) / area_root_mm2) / E_MPa
    washer_area_mm2 = annulus_mm2(NUT_BEAR_OD_mm, COLUMN_HOLE_mm)
    # Cone from each washer face towards the midplane, capped at the boss width.
    # Smallest cone diameter is taken for each 1 mm integration strip.
    d_face_mm = NUT_BEAR_OD_mm
    d_cap_mm = 194.
    half_mm = variant.depth_mm / 2
    strips = int(half_mm)
    def cone_area_mm2(i, inside):
        z_mm = i*half_mm/strips
        bore_mm = COLUMN_HOLE_mm
        if inside:
            bore_mm += (COLUMN_INNER_SEAT_BORE_mm-COLUMN_HOLE_mm)*max(0.,1-z_mm/COLUMN_OUTER_BLEND_mm)
        return annulus_mm2(min(d_cap_mm,d_face_mm+2*z_mm*tan(radians(30))),bore_mm)

    cone_mm_N = (half_mm/strips)*sum(1/(E_MPa*cone_area_mm2(i,inside))
        for i in range(strips) for inside in (False,True))
    clamp_mm_N = cone_mm_N + WASHER_H_mm / (washer_area_mm2 * E_MPa)
    phi = clamp_mm_N / (bolt_mm_N + clamp_mm_N)
    embed_N = SETTLEMENT_mm / (bolt_mm_N + clamp_mm_N)
    maximum_N = max(corner_forces_N(STATIC_N))
    cyclic_N = max(corner_forces_N(CYCLIC_N))
    residual_N = PRELOAD_N * (1 - PRELOAD_SCATTER) - embed_N - (1 - phi) * maximum_N
    out_N = PRELOAD_N * (1 + PRELOAD_SCATTER) + phi * maximum_N
    thread_amplitude_MPa = phi * cyclic_N / (2 * area_stress_mm2)
    # EN 13001-3-1: Δσc 63 for M>30 rolled. Preserve m=3 through 10^7 as a lower bound.
    endurance_amplitude_MPa = .5 * 63 * (2e6 / CYCLES)**(1/3)
    vdi_amplitude_MPa = .85 * (150 / d_mm + 45)
    yield_MPa = 500.  # 42CrMo4+QT, include the 176 mm integral shoulder stock.
    proof_factor = 1.35
    engagement_mm = 65.  # 80 mm total, minus thread ends and chamfers.
    # ISO basic form shear plane, narrower male flank at the minor diameter.
    thread_shear_mm2 = pi * root_mm * engagement_mm * .5
    nut_share = .6  # Screening derating for nonuniform engagement and dilation.
    span = middle_span()
    return {
        "load_fraction": phi, "bolt_compliance_mm_N": bolt_mm_N,
        "clamp_compliance_mm_N": clamp_mm_N, "embedment_loss_N": embed_N,
        "residual_clamp_min_N": residual_N, "outer_nut_static_max_N": out_N,
        "thread_area_mm2": area_stress_mm2, "thread_root_mm": root_mm,
        "pitch_diameter_mm": pitch_d_mm, "thread_engagement_mm": engagement_mm,
        "thread_yield_factor": yield_MPa * area_root_mm2 / out_N,
        "thread_strip_screen_factor": nut_share * yield_MPa / sqrt(3) * thread_shear_mm2 / out_N,
        "thread_amplitude_MPa": thread_amplitude_MPa,
        "thread_amplitude_VDI_MPa": vdi_amplitude_MPa,
        "thread_amplitude_EN13001_MPa": endurance_amplitude_MPa,
        "thread_fatigue_factor": min(endurance_amplitude_MPa, vdi_amplitude_MPa)
        / (proof_factor * thread_amplitude_MPa),
        "seat_pressure_max_MPa": out_N / washer_area_mm2,
        "inside_seat_max_pressure_MPa":PRELOAD_N*(1+PRELOAD_SCATTER)
            /annulus_mm2(NUT_BEAR_OD_mm,COLUMN_INNER_SEAT_BORE_mm),
        "smooth_span_area_mm2": span["tension_area_mm2"],
        "smooth_span_static_MPa": maximum_N / span["tension_area_mm2"],
        "smooth_span_fatigue_range_MPa": cyclic_N / span["tension_area_mm2"],
        "middle_span_compliance_mm_N": span["compliance_mm_N"],
        "tie_length_mm": MID_SPAN_mm + variant.depth_mm + variant.chamber_depth_mm + 2 * (NUT_H_mm + WASHER_H_mm + 14.),
    }


def section(variant, end, force_N=STATIC_N, cut_axis=0):
    """Cut at x=0 or y=0 and balance all forces on one transverse half.

    Tension in the ties includes the moment transmitted by the arms automatically.
    The centroid of the loaded half-annulus is integrated, without replacing
    the annular load by either a centre point or a pinned ring segment.
    """
    a_mm = HALF_PITCH_mm
    d_mm = variant.depth_mm
    cut_outer_mm = outline_radius_mm(variant, end)
    if end == "cylinder":
        ro_mm, ri_mm = COVER_RADIUS_mm, REAR_INNER_RADIUS_mm
        hole_area_mm2 = pi*STUD_HOLE_RADIUS_mm**2
        hole_first_moment_mm3 = hole_area_mm2*sum(x for x, _ in STUDS if x > 1e-5)
        hole_first_moment_mm3 += 4*STUD_HOLE_RADIUS_mm**3/3
        centroid_mm = ((2*(ro_mm**3-ri_mm**3)/3 - hole_first_moment_mm3)
                       / (pi*(ro_mm**2-ri_mm**2)/2-8*hole_area_mm2))
        breadth_mm = 2 * (cut_outer_mm - ri_mm - 2*STUD_HOLE_RADIUS_mm)
    else:
        # The two cuts see different pad resultants and outlet widths.
        opening_mm = (OUTLET_HEIGHT_mm,OUTLET_WIDTH_mm)[cut_axis]
        centroid_mm = (PAD_WIDTH_mm/2-RAIL_WIDTH_mm/2,PAD_HEIGHT_mm/4)[cut_axis]
        breadth_mm = 2*cut_outer_mm-opening_mm
    # Subtract the two open sections through box pockets.
    area_mm2 = breadth_mm*d_mm
    inertia_mm4 = breadth_mm * d_mm**3 / 12
    if variant.flange_mm:
        cavity_depth_mm = d_mm-2*variant.flange_mm
        area_mm2 -= 2*52.*cavity_depth_mm
        inertia_mm4 -= 2*52.*cavity_depth_mm**3/12
    moment_Nmm = force_N / 2 * (a_mm - centroid_mm)
    nominal_MPa = moment_Nmm * (d_mm / 2) / inertia_mm4
    return {"cut_x_mm": 0. if cut_axis==0 else None, "cut_axis":("x","y")[cut_axis],
            "load_half_centroid_mm": centroid_mm,
            "bending_moment_Nmm": moment_Nmm, "section_I_mm4": inertia_mm4,
            "section_nominal_bending_MPa": nominal_MPa,
            "cut_breadth_mm": breadth_mm,"traverse_cut_area_mm2":area_mm2,
            "section_outer_face_nominal_MPa":nominal_MPa}


def layout(variant):
    nut_R_mm = NUT_S_mm / sqrt(3)
    axis_to_tie_mm = hypot(HALF_PITCH_mm, HALF_PITCH_mm)
    rear_projection_mm = CYLINDER["body_length_mm"] - CYLINDER["cover_thickness_front_mm"]
    rod_tip_from_mount_mm = CYLINDER["rod_tip_retracted_length_mm"] - rear_projection_mm
    gate_outer_from_home_mm = T12B["axis_A"]["closed_gate_inner_face_x_mm"] + T12B["gate"]["thickness_mm"]
    punch_home_from_mount_mm = MID_SPAN_mm - ADAPTER_mm - DISCHARGE_BAY_mm - gate_outer_from_home_mm
    guide_lever_mm = punch_home_from_mount_mm - rod_tip_from_mount_mm
    return {
        "guide_station_at_press_end_mm": rod_tip_from_mount_mm+T12B["axis_A"]["press_end_x_mm"],
        "punch_station_at_press_end_mm": punch_home_from_mount_mm+T12B["axis_A"]["press_end_x_mm"],
        "guide_station_at_installed_stroke_mm": rod_tip_from_mount_mm+CYLINDER["stroke_installed_mm"],
        "punch_station_at_installed_stroke_mm": punch_home_from_mount_mm+CYLINDER["stroke_installed_mm"],
        "guide_to_punch_lever_mm": guide_lever_mm,
        "nut_across_corners_mm": 2 * nut_R_mm,
        "nut_radial_edge_clearance_mm": NUT_BEAR_OD_mm / 2 - nut_R_mm,
        "washer_outer_diameter_mm": NUT_BEAR_OD_mm,
        "seat_radial_edge_clearance_mm": 97 - max(NUT_BEAR_OD_mm/2, nut_R_mm),
        "rear_cylinder_projection_to_mount_mm": rear_projection_mm,
        "retracted_rod_tip_from_cylinder_mount_mm": rod_tip_from_mount_mm,
        "punch_home_from_cylinder_mount_mm": punch_home_from_mount_mm,
        "rod_tip_to_punch_home_in_stack_screen_mm": punch_home_from_mount_mm - rod_tip_from_mount_mm,
        "minimum_nut_to_cover_mm": axis_to_tie_mm - nut_R_mm - COVER_RADIUS_mm,
        "minimum_200mm_tool_to_cover_mm": axis_to_tie_mm - 100 - COVER_RADIUS_mm,
        "minimum_nut_to_barrel_mm": axis_to_tie_mm - nut_R_mm - CYLINDER["barrel_OD_mm"]/2,
        "stud_ligament_to_barrel_bore_mm": STUD_RADIUS_mm - STUD_HOLE_RADIUS_mm - REAR_INNER_RADIUS_mm,
        "stud_ligament_to_ring_OD_mm": outline_radius_mm(variant, "cylinder")
        - STUD_RADIUS_mm - STUD_HOLE_RADIUS_mm,
        "frame_axial_length_mm": column(variant)["tie_length_mm"],
        "end_projection_from_mount_mm": variant.depth_mm + NUT_H_mm + WASHER_H_mm + 14,
        "chamber_end_projection_from_mount_mm": variant.chamber_depth_mm+NUT_H_mm+WASHER_H_mm+14,
        "module_axial_excluding_ZSF_and_safety_guards_mm": (
            CYLINDER["body_length_mm"]-CYLINDER["cover_thickness_front_mm"]
            + MID_SPAN_mm + variant.chamber_depth_mm + NUT_H_mm + WASHER_H_mm + 14),
        "frame_transverse_max_mm": 2 * (HALF_PITCH_mm + 100)
        if variant.name == "cast" else 2 * PLATE_HALF_mm,
        "frame_height_with_feet_upper_mm": 740 + 80 + 30,
    }

if __name__ == "__main__":
    screens = {v.name: {"column": column(v), "layout": layout(v),
                        "cylinder_section": section(v, "cylinder"),
                        "chamber_sections": [section(v.at_end("chamber"),"chamber",cut_axis=i) for i in (0,1)]}
               for v in VARIANTS}
    print(json.dumps(screens, indent=2, allow_nan=False))
