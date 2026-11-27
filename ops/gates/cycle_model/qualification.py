"""Source-qualified input bounds for the T-2.6 G-CYCLE model."""

from math import isclose
from operator import ge, le

from .drive import linear_value
from .inputs import FLOW, cylinder_from, metering_areas_m2


ENGINEERING = "calc/T-2.6/cycle/sources.yaml engineering_inputs"
STUDY = "calc/T-2.6/sources.yaml study"
REGULATOR = "calc/T-2.1/sources.yaml engineering.dfe1z_main_shaft_limit_kW"
GATE_TRIAL = "calc/T-1.7d/round2.py OPTIONS"
MOTION = "calc/T-2.6/cycle/x1_calc.py motions"
BASE_CAM = "calc/T-1.2b/shoe_load.py design_lock"
A_CAM = "calc/T-2.2f/candidates.py drive, A_90"
BASE_RETURN = "calc/T-2.6/cycle/drive.py scenario: 6000 N + excess shoe weight from T-1.2b design_lock"
A_RETURN = "calc/T-2.6/cycle/compare.py CandidateStudy.configuration: 6000 N + excess shoe weight from T-2.2f A_90"

MINIMUMS = (
    ("process.valve_switch_s", .070, f"{ENGINEERING}.valve_allowance_s (24 + 20 + 26 ms)"),
    ("process.hold_s", .30, f"{ENGINEERING}.hold_s"),
    ("process.unload_s", .20, f"{ENGINEERING}.unload_s"),
    ("process.feed_s", .64, f"{STUDY}.feed_s"),
    ("process.handover_interlock_s", .02,
     "design/hydraulics/T-1.6_interlocks.yaml handover_regen_press.modeled_switch_budget_s (90 − 70 ms)"),
    ("pump.destroke_s", .110, "RE 92088, calc/T-2.1/sources.yaml catalogs.dfe1z.destroke_ms_at_100bar"),
    ("pump.onstroke_s", .105, "RE 92088, calc/T-2.1/sources.yaml catalogs.dfe1z.onstroke_ms_at_100bar"),
    ("pump.control_delay_s", .010, "calc/T-2.6/cycle/drive.py PV180Drive.control_delay_s"),
    ("pilot.valve_response_s", .050, "calc/T-1.6/sources.yaml revision.pilot.valve_response_s"),
    ("mechanics.gate_residual_N", 100_000, f"{STUDY}.residual_gate_force_N"),
    ("mechanics.gate_breakaway_N", 10_000, f"{MOTION}: gate_open"),
    ("mechanics.gate_close_N", 8_000, f"{MOTION}: gate_close"),
    ("mechanics.rapid_return_resistance_N", 40_000, f"{MOTION}: rapid return"),
    ("mechanics.main_guide_N", 8_000, f"{MOTION}: main punch guide"),
    ("mechanics.pre_guide_N", 5_000, "calc/T-2.6/cycle/drive.py scenario: shoe guide"),
    ("mechanics.die_ejection_N", 100_000, "calc/T-1.2b/shoe_load.py EJECTION_FORCE_N"),
    ("mechanics.transfer_edge_N", 12_000, "calc/T-1.2b/shoe_load.py closed_zone_B edge_drag_N"),
    ("mechanics.gate_mu", .15, "calc/T-2.6/cycle/evaluate.py configure: gate_open_residual_friction_N"),
    ("rapid_pair.float_drag_N", 8_000, f"{ENGINEERING}.prefill_auxiliary_cylinders.main_float_drag_kN"),
    ("outlet.crumbs_N", 5_000, "calc/T-2.6/cycle/evaluate.py configure: stack load"),
    ("material.scale_MPa", 56.89401598364152, "calc/T-1.1/curve.yaml models.power.scale_MPa"),
    ("material.lateral_K", .45, "calc/T-1.1/curve.yaml K.base"),
    ("material.wall_mu", .25, "calc/T-1.1/curve.yaml mu.base"),
)

MAXIMUMS = (
    ("oil.bulk_modulus_Pa", 1.4e9, f"{ENGINEERING}.bulk_modulus_Pa"),
    ("mechanics.crosshead_accel_m_s2", 5, f"{ENGINEERING}.rapid_accel_m_s2"),
    ("mechanics.gate_accel_m_s2", 40, f"{GATE_TRIAL}.gate_accel_m_s2"),
    ("lp.delivery_L_min", 180, f"{GATE_TRIAL}.lp_flow_L_min"),
    ("pump.delivery_fraction", 1, "RE 92050: unity at nominal catalogue delivery"),
    ("pump.regulator_fraction", 1, "calc/T-2.6/cycle/operating_point.py OperatingPoint.regulator_fraction"),
    ("pump.rated_motor_rpm", 1480, "MEC OMT3-IE3 200L-4, calc/T-2.1/sources.yaml catalogs.motor.rated_rpm"),
    ("pump.nominal_regulator_kW", 33.5, REGULATOR),
    ("valves.zsf_max_L_min", 1600, "RE 20478, calc/T-2.6/sources.yaml round2.suction.case_2_flow_L_min"),
)

METERING_MAXIMUMS_M_S = (
    ("main_metering_L_min", .24, f"{MOTION}: main cylinder"),
    ("mc_reference_L_min", .35, f"{ENGINEERING}.rapid_return_m_s (annulus makeup reference)"),
    ("pre_metering_L_min", .65, f"{MOTION}: precompaction shoe"),
    ("gate_metering_L_min", 1., f"{GATE_TRIAL}.gate_speed_m_s"),
    ("rapid_feed_metering_L_min", .42, f"{STUDY}.rapid_approach_m_s"),
    ("rapid_out_metering_L_min", .42, f"{STUDY}.rapid_eject_m_s"),
    ("rapid_back_metering_L_min", .43, f"{STUDY}.rapid_return_m_s"),
)

LINE_LOSS_MINIMUMS_BAR = (4, 3, 4)
CATALOG_SOURCE = "RE 92050, calc/T-2.1/sources.yaml catalogs.rexroth.curve_bar_L_min_kW_kW"
CATALOG_RPM = 1500
# Pressure, full-stroke delivery, full-stroke absorbed power, zero-stroke absorbed power.
CATALOG_CURVE = (
    (0, 270, 2, 2), (50, 267, 24, 3), (100, 265, 48, 4), (150, 263, 72, 5),
    (200, 260, 96, 6), (250, 258, 121, 7), (300, 255, 145, 8), (350, 253, 170, 9),
)
CURVE_BOUNDS = (("full_flow_L_min", le), ("full_swash_kW", ge), ("zero_swash_kW", ge))

# The two roof geometries use different cams and shoe masses. For another roof
# use the stricter limit for each quantity from the two qualified calculations.
SHOE_LIMITS = {
    15: ((.30, BASE_CAM), (15593.727049292605, BASE_CAM), (6443.106909, BASE_RETURN)),
    90: ((.15, f"{A_CAM}: 12 mm / 80 ms"), (31672.44772222222, A_CAM), (6182.73192948, A_RETURN)),
}
SHOE_FIELDS = (("valves.cam_metering_L_min", le), ("mechanics.cam_resistance_N", ge),
               ("mechanics.pre_return_resistance_N", ge))


def input_violations(params):
    cfg = params["cycle_model"]
    pump, mech, valves = (cfg[name] for name in ("pump", "mechanics", "valves"))
    violations = []

    def check(field, actual, compare, limit, source, quantity=None):
        if compare(actual, limit) or isclose(actual, limit, rel_tol=1e-12):
            return
        operator = "<=" if compare is le else ">="
        label = f"cycle_model.{field}"
        subject = f"{label} ({quantity})" if quantity else label
        violations.append(dict(field=label, actual=actual, operator=operator, limit=limit, source=source,
                               message=f"{subject}: {actual:.12g}; требуется {operator} {limit:.12g} ({source})"))

    for rules, compare in ((MINIMUMS, ge), (MAXIMUMS, le)):
        for field, limit, source in rules:
            section, key = field.split(".")
            check(field, cfg[section][key], compare, limit, source)
    check("pump.motor_rpm", pump["motor_rpm"], le, pump["rated_motor_rpm"],
          "cycle_model.pump.rated_motor_rpm (MEC OMT3-IE3)")
    check("pump.main_shaft_limit_kW", pump["main_shaft_limit_kW"], le, pump["nominal_regulator_kW"],
          f"cycle_model.pump.nominal_regulator_kW ({REGULATOR})")

    main = cylinder_from(params["main_cylinder"], mech["main_rod_mm"])
    pre = cylinder_from(params["precompaction"]["cylinder"])
    gate = cylinder_from(params["drive"]["slide_gate_cylinder"])
    areas_m2 = metering_areas_m2(main, pre, gate, cfg["rapid_pair"])
    for key, limit, source in METERING_MAXIMUMS_M_S:
        check(f"valves.{key}", valves[key] / (FLOW * areas_m2[key]), le, limit, source, "Q/A, m/s")
    cam, cam_load, return_load = SHOE_LIMITS.get(
        mech["roof_mm"], (SHOE_LIMITS[90][0], SHOE_LIMITS[90][1], SHOE_LIMITS[15][2]))
    shoe_values = (valves["cam_metering_L_min"] / (FLOW * areas_m2["cam_metering_L_min"]),
                   mech["cam_resistance_N"], mech["pre_return_resistance_N"])
    for (field, compare), actual, (limit, source), quantity in zip(
        SHOE_FIELDS, shoe_values, (cam, cam_load, return_load), ("Q/A, m/s", None, None), strict=True
    ):
        check(field, actual, compare, limit, source, quantity)
    for index, limit in enumerate(LINE_LOSS_MINIMUMS_BAR):
        check(f"valves.line_loss_bar[{index}]", valves["line_loss_bar"][index], ge, limit,
              f"{ENGINEERING}.line_drop_inlet_tank_regen_bar")

    curve = pump["curve"]
    low_bar, high_bar = CATALOG_CURVE[0][0], CATALOG_CURVE[-1][0]
    check("pump.curve[0][0]", curve[0][0], le, low_bar, CATALOG_SOURCE, "bar")
    check("pump.curve[-1][0]", curve[-1][0], ge, high_bar, CATALOG_SOURCE, "bar")
    # Both curves are piecewise linear. Checking the union of in-range knots
    # also detects optimistic peaks inserted between catalogue pressures.
    pressures_bar = sorted({row[0] for row in (*curve, *CATALOG_CURVE) if low_bar <= row[0] <= high_bar})
    rpm_ratio = CATALOG_RPM / pump["map_rpm"]
    for column, (quantity, compare) in enumerate(CURVE_BOUNDS, 1):
        series = [(row[0], row[column]) for row in curve]
        catalog = [(row[0], row[column]) for row in CATALOG_CURVE]
        for pressure_bar in pressures_bar:
            check(f"pump.curve@{pressure_bar:g}bar.{quantity}",
                  linear_value(pressure_bar, series) * rpm_ratio, compare,
                  linear_value(pressure_bar, catalog), CATALOG_SOURCE)
    return violations
