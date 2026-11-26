"""Drive, duty points, and hydraulic energy calculations for T-1.4b V2."""
import json
from bisect import bisect_right
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from itertools import product
from math import ceil, floor, fsum, pi, sqrt
from pathlib import Path

import yaml

from x1_calc import Accumulator, BAR_PA, MOTOR_KW, OIL_BULK_PA, Cylinder, Model, area_m2, converged_run, motions, periodic_run

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE_SETTINGS = dict(overlap=True, accumulator=True)
EARLY_SETTINGS = dict(BASE_SETTINGS, unlock_x_m=.205)


def get_inputs():
    upstream = json.loads((ROOT / "calc/T-1.2b/results.json").read_text(encoding="utf-8"))
    params = yaml.safe_load((ROOT / "design/params.t12b.yaml").read_text(encoding="utf-8"))
    curve = yaml.safe_load((ROOT / "calc/T-1.1/curve.yaml").read_text(encoding="utf-8"))
    old = json.loads((ROOT / "calc/T-1.2/results.json").read_text(encoding="utf-8"))
    spec = spec_from_file_location("geometry_t12_readonly", ROOT / "calc/T-1.2/geometry.py")
    geometry = module_from_spec(spec)
    spec.loader.exec_module(geometry)
    return upstream, params, old, geometry.Material(curve, params["raw"]["dose_kg"], params["chamber"]["section_mm"])


def scenario(inputs, case="base", bulk_kg_m3=90, dose_kg=.83, pressure_bar=None, gate_m_s=.25,
             losses_bar=(4., 3., 4.)):
    upstream, params, old, material = inputs
    axis = upstream["axis_A"]
    lock = upstream["mechanical_lock_A"]
    pre = params["precompaction"]["cylinder"]
    ram = params["main_cylinder"]
    gate = params["drive"]["slide_gate_cylinder"]
    main_cylinder = Cylinder(ram["bore_mm"], ram["rod_mm"], ram["stroke_mm"], .94)
    gate_cylinder = Cylinder(gate["bore_mm"], gate["rod_mm"], gate["stroke_mm"], gate["eta"])
    pre_cylinder = Cylinder(pre["bore_mm"], pre["rod_mm"], pre["stroke_mm"], pre["eta"])
    width_mm, height_mm = params["chamber"]["section_mm"]
    window_mm = axis["transferred_fill_length_mm"]
    force_N = ram["nominal_force_N"]
    if pressure_bar is not None:
        inlet_bar, tank_bar, _ = losses_bar
        force_N = ((pressure_bar - inlet_bar) * main_cylinder.cap_m2
                   - tank_bar * main_cylinder.annulus_m2) * BAR_PA * main_cylinder.eta
    loaded_kg_m3 = material.loaded_density_kg_m3(force_N / (width_mm * height_mm), bulk_kg_m3, case,
                                                dose_kg=dose_kg)
    upstream_pre = old["precompaction"]
    if dose_kg == .83 and bulk_kg_m3 == 90:
        parking_mm = upstream["alternatives"]["A"]["dimensions"]["nominal_pre_shoe_stroke_mm"]
    else:
        parking_mm = ceil(dose_kg * 1e9 / (width_mm * window_mm * bulk_kg_m3) - height_mm
                          + upstream_pre["freeboard_mm"])
    loaded_length_mm = dose_kg * 1e9 / (width_mm * height_mm * loaded_kg_m3)
    grow_mm = loaded_length_mm * (material.axial_ratio(case) - 1)
    overtravel_mm = max(axis["ejection_overtravel_mm"], ceil(upstream["gate"]["thickness_mm"] + 5 + grow_mm))
    model = Model(material, case, dose_kg, width_mm / 1000, height_mm / 1000, window_mm / 1000, loaded_kg_m3,
                  upstream_pre["guide_force_N"], force_N, overtravel_mm / 1000,
                  axis["approach_stroke_mm"] / 1000, parking_mm / 1000, pre_cylinder, gate_cylinder,
                  cam_m=lock["cam_extra_pre_cylinder_stroke_mm"] / 1000,
                  cam_force_N=lock["equivalent_cam_force_N"],
                  cam_stem_speed_m_s=lock["cam_stem_speed_limit_mm_s"] / 1000,
                  gate_travel_m=upstream["gate"]["gate_opening_travel_mm"] / 1000, gate_speed_m_s=gate_m_s,
                  pre_return_force_N=6000 + max(0, lock["shoe_mass_kg"] - 200 * 150 * 45 * 7850 / 1e9) * 9.81,
                  losses_bar=losses_bar)
    return model, main_cylinder


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def source_data():
    return yaml.safe_load((HERE / "sources.yaml").read_text(encoding="utf-8"))


def linear_value(x, points):
    index = max(1, min(len(points) - 1, bisect_right(points, x, key=lambda point: point[0])))
    (x0, a), (x1, b) = points[index - 1:index + 1]
    return a + (b - a) * (x - x0) / (x1 - x0)


@dataclass(frozen=True)
class PumpPoint:
    flow_L_min: float
    deadhead_kW: float
    full_stroke_kW: float
    eta_v: float
    eta_hm: float

    @property
    def incremental_kW_per_L_min(self):
        return (self.full_stroke_kW - self.deadhead_kW) / self.flow_L_min


class PV180Drive:
    """Catalogue-based, torque-limited PV180 at a fixed reference speed."""

    names = ("PV180",)
    anticipation = True
    control_delay_s = .010

    def __init__(self, data, limit_kW=None, *, response_multiplier=1.):
        config = data["engineering_inputs"]
        self.response_multiplier = response_multiplier
        self.tolerance = config["torque_estimate_tolerance"]
        self.catalog = data["catalogs"]["parker_pvplus"]
        self.rpm = config["motor_rpm"]
        self.limit_kW = config["shaft_limit_kW"] if limit_kW is None else limit_kW
        self.loss_kW = config["coupling_loss_allowance_kW"]
        self.standby_bar = self.catalog["fdv_min_pilot_bar"]
        self.standby_pressures_bar = (self.standby_bar,)
        self.omega_rad_s = self.rpm * 2 * pi / 60

    @lru_cache(maxsize=8192)
    def section(self, name, pressure_bar):
        model = self.catalog["models"][name]
        geometric_L_min = self.rpm * model["displacement_cm3_rev"] / 1000
        ratio = self.rpm / self.catalog["reference_speed_rpm"]
        nominal_bar = self.catalog["continuous_pressure_bar"]
        eta_v = linear_value(pressure_bar, ((0, 1.), (nominal_bar, model["full_stroke_eta_v_at_350bar"])))
        zero_points = tuple(zip((0, nominal_bar), model["zero_stroke_power_kW_endpoints"]))
        full_points = tuple(zip((0, nominal_bar), model["full_stroke_power_kW_endpoints"]))
        zero_kW = linear_value(pressure_bar, zero_points) * ratio
        full_kW = linear_value(pressure_bar, full_points) * ratio
        flow_L_min = geometric_L_min * eta_v - self.catalog["pilot_flow_allowance_L_min"]
        eta_hm = pressure_bar * geometric_L_min / (600 * full_kW)
        return PumpPoint(flow_L_min, zero_kW, full_kW, eta_v, eta_hm)

    def fractions(self, pressure_bar, requested_L_min, actual=()):
        point = self.section("PV180", max(pressure_bar, self.standby_bar))
        remaining_kW = self.limit_kW - self.loss_kW - point.deadhead_kW
        flow_L_min = min(point.flow_L_min, requested_L_min,
                        max(0., remaining_kW) / point.incremental_kW_per_L_min)
        return (flow_L_min / point.flow_L_min,)

    def instant(self, pressure_bar, fractions, connected):
        outlet_bar = max(pressure_bar if connected[0] else 0., self.standby_bar)
        point = self.section("PV180", outlet_bar)
        flow_L_min = fractions[0] * point.flow_L_min
        shaft_kW = (self.loss_kW + point.deadhead_kW
                    + fractions[0] * (point.full_stroke_kW - point.deadhead_kW))
        if connected[0]:
            return flow_L_min, shaft_kW, (outlet_bar - pressure_bar) * flow_L_min / 600
        return 0., shaft_kW, outlet_bar * flow_L_min / 600

    def connected(self, pressure_bar, actual, setpoints):
        return (pressure_bar > 0.,)

    def operating_point(self, pressure_bar, requested_L_min=float("inf")):
        fractions = self.fractions(pressure_bar, requested_L_min)
        flow_L_min, power_kW, _ = self.instant(pressure_bar, fractions, self.connected(pressure_bar, fractions, fractions))
        return flow_L_min, power_kW

    def capacity_L_min(self, pressure_bar):
        return self.operating_point(pressure_bar)[0]

    @lru_cache(maxsize=8192)
    def slew(self, pressure_bar, increasing):
        direction = "onstroke" if increasing else "destroke"
        times_ms = [(bar, self.catalog[f"pv360_fdv_{direction}_at_{bar}bar_ms"]) for bar in (50, 350)]
        duration_s = linear_value(min(350, max(50, pressure_bar)), times_ms) / 1000
        return 1 / (duration_s * self.response_multiplier)

    def update(self, pressure_bar, previous, setpoints, dt_s):
        return tuple(
            max(goal, old - self.slew(pressure_bar, False) * dt_s) if goal < old
            else min(goal, old + self.slew(pressure_bar, True) * dt_s)
            for old, goal in zip(previous, setpoints)
        )

def configuration(inputs, *, data=None, profile="realistic", limit_kW=None):
    data = data or source_data()
    cfg = data["engineering_inputs"]
    catalog = data["catalogs"]
    valve_s, unload_s, multiplier, gate_ratio = {
        "realistic": (cfg["valve_allowance_s"], cfg["unload_s"], 1., 1.),
        "optimistic": (.050, .150, 1., 1.),
        "pessimistic": (.100, .250, 1.25, cfg["pessimistic_gate_speed_mm_s"] / cfg["slide_gate_speed_mm_s"]),
    }[profile]
    model, cylinder = scenario(inputs, gate_m_s=cfg["slide_gate_speed_mm_s"] * gate_ratio / 1000,
                               losses_bar=tuple(cfg["line_drop_inlet_tank_regen_bar"]))
    model = replace(model, regen_switch_bar=cfg["regen_switch_bar"],
                    rapid_approach_m_s=cfg["rapid_approach_m_s"],
                    rapid_eject_m_s=cfg["rapid_eject_m_s"], rapid_return_m_s=cfg["rapid_return_m_s"],
                    rapid_mass_kg=cfg["rapid_moving_mass_kg"], rapid_accel_m_s2=cfg["rapid_accel_m_s2"],
                    gate_mass_kg=cfg["gate_moving_mass_kg"], gate_accel_m_s2=cfg["gate_accel_m_s2"])
    pump = PV180Drive(data, limit_kW=limit_kW, response_multiplier=multiplier)
    settings = dict(
        EARLY_SETTINGS, switch_s=valve_s, hold_s=cfg["hold_s"], unload_s=unload_s,
        pump=pump, max_L_min=pump.capacity_L_min(pump.standby_bar), deficit_only=True,
        lp_window_guard=True,
        boost_branches=("return", "pre_up", "pre_down"),
        accumulator_shell_L=catalog["hydac_sb330"]["effective_gas_volume_L"],
        accumulator_kwargs=dict(
            precharge_bar=cfg["accumulator_precharge_bar_at_operating_temperature"],
            low_bar=cfg["accumulator_gas_low_bar"], high_bar=cfg["accumulator_gas_high_bar"],
            delivery_L_min=cfg["accumulator_branch_flow_L_min"], exponent=cfg["accumulator_polytropic_exponent"],
        ),
        charge_drop_bar=cfg["accumulator_charge_and_delivery_drop_bar"],
        prefill=dict(cfg["prefill_auxiliary_cylinders"],
                     switch_force_N=cfg["prefill_fast_to_regen_force_N"],
                     float_gauge_bar=cfg["prefill_pipe"]["tank_gauge_bar"],
                     return_float_drag_kN=max(cfg["prefill_auxiliary_cylinders"]["main_float_drag_kN"],
                                              prefill_budget(model, cylinder, data)["return_drag_budget_N"] / 1000)),
    )
    press = motions(model, cylinder, 90, settings["prefill"])["press"]
    # Lower envelope of net hydraulic/shaft efficiency on the torque-limited
    # nominal direct press range, where the gate actually uses the hyperbola.
    end_bar = press.pressure_bar(press.stroke_m)
    corner_bar = bisect_power_corner_bar(pump, end_bar)
    pressures_bar = [corner_bar + i * (end_bar - corner_bar) / 1000 for i in range(1001)]
    envelope_eta = min(bar * pump.capacity_L_min(bar) / (600 * pump.limit_kW) for bar in pressures_bar)
    projection = dict(motor_kW=MOTOR_KW, installed_kW=fsum(cfg["installed_kW"].values()),
                      peak_kW=pump.limit_kW, idle_kW=pump.operating_point(pump.standby_bar, 0)[1],
                      pump_max_flow_L_min=settings["max_L_min"], eta=floor(envelope_eta * 1000) / 1000)
    charge = Accumulator(shell_L=settings["accumulator_shell_L"], **settings["accumulator_kwargs"])
    check_accumulator(charge, catalog["hydac_sb330"])
    charge_plan = dict(
        usable_oil_L=1000 * (charge.oil_at_m3(charge.high_bar) - charge.oil_at_m3(charge.low_bar)),
        max_flow_L_min=charge.delivery_L_min,
        min_delivery_pressure_bar=charge.low_bar - settings["charge_drop_bar"],
        charge_pressure_bar=charge.high_bar + settings["charge_drop_bar"],
        round_trip_eta=1., recharge_when_idle=True,
    )
    return model, cylinder, settings, projection, charge_plan


def bisect_power_corner_bar(pump, max_bar):
    low_bar, high_bar = pump.standby_bar, max_bar
    for _ in range(32):
        pressure_bar = (low_bar + high_bar) / 2
        point = pump.section("PV180", pressure_bar)
        if point.full_stroke_kW + pump.loss_kW < pump.limit_kW:
            low_bar = pressure_bar
        else:
            high_bar = pressure_bar
    return high_bar


def check_accumulator(acc, catalog):
    assert acc.oil_at_m3(acc.low_bar) * 1000 >= acc.shell_L * catalog["residual_oil_fraction"]
    assert acc.precharge_bar <= acc.low_bar * catalog["precharge_to_min_pressure_max_ratio"]
    assert acc.high_bar <= acc.precharge_bar * catalog["max_pressure_ratio"]
    assert acc.delivery_L_min <= catalog["vertical_discharge_max_L_min"]


def decompression(run, model, cylinder, data):
    cfg = data["engineering_inputs"]
    inlet_bar, tank_bar, _ = model.losses_bar
    pressure_start_bar = run["nominal_setpoint_bar"] - inlet_bar
    pressure_end_bar = cfg["decompression_cap_target_bar"]
    cap_volume_m3 = .0008 + cylinder.cap_m2 * model.press_end_m
    effective_compliance_m3_Pa = cap_volume_m3 / OIL_BULK_PA * cfg["decompression_compliance_multiplier"]
    head_start_Pa = (pressure_start_bar - tank_bar) * BAR_PA
    head_end_Pa = (pressure_end_bar - tank_bar) * BAR_PA
    throat_m2 = cfg["decompression_discharge_coefficient"] * area_m2(cfg["decompression_orifice_diameter_mm"])
    time_s = effective_compliance_m3_Pa * sqrt(2 * cfg["oil_density_kg_m3"]) * (
        sqrt(head_start_Pa) - sqrt(head_end_Pa)) / throat_m2
    return dict(cap_volume_L=cap_volume_m3 * 1000,
                oil_elastic_release_L=cap_volume_m3 * (head_start_Pa - head_end_Pa) / OIL_BULK_PA * 1000,
                effective_release_L=effective_compliance_m3_Pa * (head_start_Pa - head_end_Pa) * 1000,
                estimated_orifice_time_s=time_s,
                available_orifice_time_s=cfg["unload_s"] - cfg["valve_allowance_s"],
                peak_orifice_flow_L_min=60000 * throat_m2 * sqrt(2 * head_start_Pa / cfg["oil_density_kg_m3"]),
                oil_elastic_energy_kJ=cap_volume_m3 * (head_start_Pa**2 - head_end_Pa**2) / (2 * OIL_BULK_PA * 1000),
                effective_release_energy_kJ=effective_compliance_m3_Pa * (head_start_Pa**2 - head_end_Pa**2) / 2000)


def heat_balance(run, decompression_result, data):
    e = run["energy"]
    losses_kJ = dict(
        pump_and_coupling=run["shaft_energy_kJ"] - e["header_kJ"] - e["bypass_kJ"],
        standby_and_transition_bypass=e["bypass_kJ"],
        metering_and_backpressure=e["valves_kJ"], sharing=e["sharing_kJ"],
        accumulator=e["charge_kJ"] - e["boost_kJ"] + e["hp_charge_kJ"] - e["hp_boost_kJ"], cylinder_friction=e["cylinder_friction_kJ"],
        decompression=decompression_result["effective_release_energy_kJ"],
        prefill_and_float=e["prefill_float_kJ"], ramp_damping=run["damping_heat_kJ"],
    )
    inputs = data["engineering_inputs"]
    aux_heat_kW = inputs["installed_kW"]["pilot_pack"] + inputs["installed_kW"]["cooler_circulation"]
    main_heat_kW = fsum(losses_kJ.values()) / run["cycle_s"]
    return dict(losses_kJ=losses_kJ, main_heat_kW=main_heat_kW, auxiliary_heat_budget_kW=aux_heat_kW,
                oil_heat_budget_kW=main_heat_kW + aux_heat_kW,
                main_shaft_upper_heat_kW=run["average_shaft_kW"] + aux_heat_kW)


def cooling(data, heat_kW, full_flow_L_min, working_volume_L, gross_volume_L, mean_flow_L_min):
    cfg = data["engineering_inputs"]
    cooler = data["catalogs"]["parker_lac"]
    circulation_L_min = cooler["selected_oil_flow_L_min"]
    specific_kW_K = cooler["selected_capacity_design_kW_K"] * (1 - cooler["tolerance_fraction"])
    supply_kW = (cfg["cooler_oil_limit_C"] - cfg["ambient_C"]) * specific_kW_K
    circulation_kW = circulation_L_min * cfg["cooling_circuit_drop_budget_bar"] / (
        600 * cfg["cooling_circuit_pump_efficiency"])
    return dict(cooler_capacity_at_design_kW=supply_kW, cooling_margin_kW=supply_kW - heat_kW,
                predicted_oil_C=cfg["ambient_C"] + heat_kW / specific_kW_K,
                circulation_L_min=circulation_L_min, circulation_shaft_kW=circulation_kW,
                tank_working_oil_L=working_volume_L, tank_gross_L=gross_volume_L,
                tank_time_at_full_flow_s=60 * working_volume_L / full_flow_L_min,
                tank_time_at_mean_flow_s=60 * working_volume_L / mean_flow_L_min,
                tank_reference_min_3min_L=3 * full_flow_L_min, tank_reference_max_5min_L=5 * full_flow_L_min,
                installed_kW=cfg["installed_kW"], installed_total_kW=fsum(cfg["installed_kW"].values()))


def evaluated_run(model, cylinder, settings, data, profile, density, feed_s, pressure_bar,
                  steps_s):
    if len(steps_s) > 1:
        run = converged_run(model, cylinder, density, feed_s, settings, steps_s)
    else:
        run = periodic_run(model, cylinder, density, feed_s, settings, steps_s[0])
    if not run["feasible"]:
        raise RuntimeError((model.case, profile, density, pressure_bar, run))
    pump = settings["pump"]
    cfg = data["engineering_inputs"]
    power_factor = (1 + pump.tolerance) * cfg["regulator_speed_ceiling_rpm"] / pump.rpm
    run["shaft_peak_with_tolerance_kW"] = run["peak_shaft_kW"] * power_factor
    run["shaft_rms_with_tolerance_kW"] = run["rms_shaft_kW"] * power_factor
    run["shaft_average_with_tolerance_kW"] = run["average_shaft_kW"] * power_factor
    run["peak_shaft_torque_with_tolerance_Nm"] = 1000 * run["peak_shaft_kW"] * (1 + pump.tolerance) / pump.omega_rad_s
    run.update(profile=profile, case=model.case, specified_max_pressure_bar=pressure_bar,
               nominal_force_N=model.nominal_N,
               immediate_density_kg_m3=model.in_die_kg_m3 / model.material.volume_ratio(model.case),
               released_length_mm=1000 * model.die_length_m * model.material.axial_ratio(model.case))
    run["decompression"] = decompression(run, model, cylinder, data)
    run["decompression"]["available_orifice_time_s"] = settings["unload_s"] - settings["switch_s"]
    run["heat"] = heat_balance(run, run["decompression"], data)
    assert run["decompression"]["estimated_orifice_time_s"] <= run["decompression"]["available_orifice_time_s"]
    assert run["peak_working_bar"] <= 300 + 1e-8
    return run


def run_scenario(inputs, data, profile, curve, density, feed_s, dose_kg, pressure_bar):
    base, cylinder, settings, _, _ = configuration(inputs, data=data, profile=profile)
    geometry, _ = scenario(inputs, curve, density, dose_kg, pressure_bar, base.gate_speed_m_s, base.losses_bar)
    model = replace(base, case=geometry.case, dose_kg=geometry.dose_kg, in_die_kg_m3=geometry.in_die_kg_m3,
                    nominal_N=geometry.nominal_N, overtravel_m=geometry.overtravel_m,
                    pre_travel_m=geometry.pre_travel_m)
    reference = feed_s == .64 and dose_kg == .83 and curve == "base" and pressure_bar is None
    steps_s = (.0025, .00125, .000625, .0003125) if reference else (.0025, .00125, .000625)
    return evaluated_run(model, cylinder, settings, data, profile, density, feed_s, pressure_bar, steps_s)


def simulate_levers(inputs, data):
    model, cylinder, settings, _, _ = configuration(inputs, data=data)
    old_model = replace(model, gate_speed_m_s=.45, rapid_approach_m_s=.24, rapid_eject_m_s=.24,
                        rapid_return_m_s=.25, regen_switch_bar=120., rapid_accel_m_s2=0., gate_accel_m_s2=0.)
    old_pump = PV180Drive(data, limit_kW=28.5)
    working = settings | {"pump": old_pump, "max_L_min": old_pump.capacity_L_min(old_pump.standby_bar)}
    other_switch_bar = 70. if model.regen_switch_bar == 120. else 120.
    old_model_changes = (
        ("rapid_return", {"rapid_return_m_s": model.rapid_return_m_s}),
        ("rapid_ejection", {"rapid_eject_m_s": model.rapid_eject_m_s}),
        ("rapid_approach", {"rapid_approach_m_s": model.rapid_approach_m_s}),
        ("gate_speed", {"gate_speed_m_s": model.gate_speed_m_s}),
        ("regen_switch_70_bar_trial", {"regen_switch_bar": other_switch_bar}),
        ("retain_regen_switch_120_bar", {"regen_switch_bar": model.regen_switch_bar}),
        ("rapid_motion_ramps", {"rapid_accel_m_s2": model.rapid_accel_m_s2}),
        ("gate_motion_ramps", {"gate_accel_m_s2": model.gate_accel_m_s2}),
    )
    rows = []

    def record(name, geometry, options):
        run = periodic_run(geometry, cylinder, 90, .64, options, .000625)
        cycle_s = run["cycle_s"]
        rows.append(dict(lever=name, cycle_s=cycle_s, extra_recharge_s=run["extra_recharge_s"],
                         delta_s=None if not rows else cycle_s - rows[-1]["cycle_s"]))

    original_prefill = {k: v for k, v in settings["prefill"].items() if k != "return_float_drag_kN"}
    working.update(prefill=original_prefill, lp_window_guard=False)
    record("T-1.4_round_2_V2", old_model, working)
    old_model = replace(old_model, rapid_mass_kg=model.rapid_mass_kg, gate_mass_kg=model.gate_mass_kg)
    working = settings | {"prefill": original_prefill, "lp_window_guard": False}
    record("37_5_kW_torque_command", old_model, working)
    for name, changes in old_model_changes:
        old_model = replace(old_model, **changes)
        record(name, old_model, working)
    working["prefill"] = settings["prefill"]
    record("return_float_drag", old_model, working)
    working["lp_window_guard"] = True
    record("lp_charge_window_guard", old_model, working)
    # Each terminal sensitivity branches from the selected design.
    sensitivities = {}
    for name, geometry, options in (
        ("alternate_regen_switch", replace(model, regen_switch_bar=other_switch_bar), working),
        ("lp_equivalent_10_L", model, working | {"accumulator_shell_L":
                                                  data["catalogs"]["high_pressure_sb330"]["effective_gas_volume_L"]}),
        ("hold_0_25_s", model, working | {"hold_s": .25}),
    ):
        run = periodic_run(geometry, cylinder, 90, .64, options, .000625)
        sensitivities[name] = dict(cycle_s=run["cycle_s"], delta_s=run["cycle_s"] - rows[-1]["cycle_s"],
                                   extra_recharge_s=run["extra_recharge_s"])
    return rows, sensitivities


def pump_curve(pump):
    rows = []
    for pressure_bar in (15, 20, 25, 32, 40, 50, 70, 100, 120, 150, 200, 250, 270, 300):
        flow, power = pump.operating_point(pressure_bar)
        rows.append(dict(header_pressure_bar=pressure_bar, flow_L_min=flow, shaft_power_kW=power,
                         standstill_delivery_kW=pump.operating_point(pressure_bar, 0)[1],
                         net_hydraulic_efficiency=pressure_bar * flow / (600 * power),
                         full_stroke_eta_v={name: pump.section(name, pressure_bar).eta_v for name in pump.names},
                         full_stroke_eta_hm={name: pump.section(name, pressure_bar).eta_hm for name in pump.names}))
    return rows




def prefill_budget(model, cylinder, data):
    cfg, catalogs = data["engineering_inputs"], data["catalogs"]
    valve = catalogs["rexroth_zsf100"]
    pipe = cfg["prefill_pipe"]
    density_kg_m3 = cfg["oil_density_kg_m3"]
    gravity_head_bar = density_kg_m3 * 9.81 * pipe["static_head_m"] / BAR_PA
    boosted_head_bar = pipe["tank_gauge_bar"] + gravity_head_bar

    def leg(flow_area_m2, pipe_ID_mm, speed_m_s):
        flow_m3_s = flow_area_m2 * speed_m_s
        pipe_area_m2 = area_m2(pipe_ID_mm)
        velocity_m_s = flow_m3_s / pipe_area_m2
        loss_coefficient = pipe["darcy_factor"] * pipe["length_m"] / (pipe_ID_mm / 1000) + pipe["local_K"]
        return dict(flow_L_min=60000 * flow_m3_s, pipe_velocity_m_s=velocity_m_s,
                    steady_drop_bar=loss_coefficient * density_kg_m3 * velocity_m_s**2 / (2 * BAR_PA),
                    acceleration_head_bar=density_kg_m3 * pipe["length_m"] * model.rapid_accel_m_s2
                    * flow_area_m2 / (pipe_area_m2 * BAR_PA))

    cap_out = leg(cylinder.cap_m2, pipe["inside_diameter_mm"], model.rapid_return_m_s)
    annulus_in = leg(cylinder.annulus_m2, cfg["rapid_annulus_line_ID_mm"], model.rapid_return_m_s)
    exhaust = catalogs["rexroth_2wrce"]
    ng = cfg["local_exhaust_NG"]
    cap_out["valve_drop_bar"] = exhaust["reference_drop_bar"] * (
        cap_out["flow_L_min"] / exhaust["rated_flow_L_min_by_ng"][ng])**2
    out_losses_bar = cap_out["steady_drop_bar"] + cap_out["acceleration_head_bar"] + cap_out["valve_drop_bar"]
    makeup_losses_bar = (annulus_in["steady_drop_bar"] + annulus_in["acceleration_head_bar"]
                         + cfg["annulus_makeup_drop_allowance_bar"])
    annulus_in["min_absolute_bar"] = 1.01325 + boosted_head_bar - makeup_losses_bar
    cap_out["peak_gauge_bar"] = boosted_head_bar + out_losses_bar
    return_drag_N = BAR_PA * (cap_out["peak_gauge_bar"] * cylinder.cap_m2
                             - (annulus_in["min_absolute_bar"] - 1.01325) * cylinder.annulus_m2)
    cap_in = {}
    for name, speed_m_s in (("approach", model.rapid_approach_m_s), ("ejection", model.rapid_eject_m_s)):
        budget = leg(cylinder.cap_m2, pipe["inside_diameter_mm"], speed_m_s)
        budget["min_absolute_bar"] = (1.01325 + boosted_head_bar - budget["steady_drop_bar"]
                                      - budget["acceleration_head_bar"] - valve["suction_drop_budget_bar"])
        budget["without_boost_min_absolute_bar"] = budget["min_absolute_bar"] - pipe["tank_gauge_bar"]
        budget["case_2_flow_margin_L_min"] = valve["case_2_flow_L_min"] - budget["flow_L_min"]
        cap_in[name] = budget
    annulus_out = leg(cylinder.annulus_m2, cfg["rapid_annulus_line_ID_mm"], model.rapid_eject_m_s)
    annulus_out["pressure_budget_bar"] = 3.
    intake_cap_min_bar = min(row["min_absolute_bar"] for row in cap_in.values())
    minimum_buffer_L = 1.5 * cylinder.cap_m2 * cylinder.stroke_mm
    assert minimum_buffer_L <= cfg["buffer_oil_L"]
    assert min(intake_cap_min_bar, annulus_in["min_absolute_bar"]) >= pipe["cap_min_abs_bar"]
    assert all(row["case_2_flow_margin_L_min"] >= 0 for row in cap_in.values())
    assert cap_out["peak_gauge_bar"] <= cfg["cap_exhaust_restriction_budget_bar"]
    assert valve["port_B_max_bar"] >= cfg["relief_max_with_tolerance_bar"]
    return dict(cap_intake=cap_in, cap_exhaust=cap_out, annulus_intake=annulus_in, annulus_exhaust=annulus_out,
                return_drag_budget_N=return_drag_N, minimum_buffer_L=minimum_buffer_L,
                buffer_oil_L=cfg["buffer_oil_L"], speed_limit_m_s=model.rapid_return_m_s,
                local_exhaust_NG=ng, liquid_level_head_bar=gravity_head_bar,
                head_at_tank_gauge_bar=pipe["tank_gauge_bar"])


def station_budget(model, cylinder, settings, projection, charge, data, reference, duties):
    cfg, catalogs = data["engineering_inputs"], data["catalogs"]
    pump = settings["pump"]
    # The T-1.4 V2 manifold uses a separate NG50 cap exhaust, counted here.
    schedule = dict(main_NG40=3, main_NG50=2, pre_NG25=4, gate_NG16=4, lp_NG25=3, relief_NG16=1,
                    prefill_NG100=1, paired_rapid_ram_NG32=4, neutral_NG32=1)
    volume_L, gross_L = cfg["tank_working_gross_L"]["V2"]
    mean_flow_L_min = reference["pump_oil_L"] * 60 / reference["cycle_s"]
    worst_nominal_heat_kW = max(row["heat"]["oil_heat_budget_kW"] for row in duties)
    # Treat all additional shaft input allowed by the torque/speed tolerances as heat.
    worst_heat_kW = max(row["heat"]["oil_heat_budget_kW"] + row["shaft_average_with_tolerance_kW"]
                       - row["average_shaft_kW"] for row in duties)
    cooling_result = cooling(data, worst_heat_kW, settings["max_L_min"], volume_L, gross_L, mean_flow_L_min)
    motor = catalogs["ie3_motor"]
    breakdown_Nm = motor["rated_torque_Nm"] * motor["breakdown_to_rated_torque"]
    peak_Nm = max(row["peak_shaft_torque_with_tolerance_Nm"] for row in duties)
    mass_kg = dict(
        motor=motor["mass_kg"], pv180=pump.catalog["models"]["PV180"]["mass_kg"],
        lp_and_pilot_vessels=catalogs["hydac_sb330"]["mass_kg"] + catalogs["hydac_sb330"]["pilot_mass_kg"],
        tank=cfg["station_mass_allowance_kg"]["V2_tank"],
        large_valves=sum(
            count * catalogs["rexroth_2wrce"]["mass_kg_by_ng"][int(key.rsplit("NG", 1)[1])]
            for key, count in schedule.items() if int(key.rsplit("NG", 1)[1]) in (32, 40, 50)
        ),
        cooler_with_fan=catalogs["parker_lac"]["mass_kg"],
        **cfg["station_installation_allowance_kg"],
        main_tank_oil=volume_L * cfg["oil_density_kg_m3"] / 1000,
        prefill_valve=catalogs["rexroth_zsf100"]["mass_kg"],
        prefill_buffer_and_oil=cfg["buffer_filled_mass_allowance_kg"],
        enlarged_prefill_piping=cfg["enlarged_piping_mass_allowance_kg"],
    )
    motion_budget = {}
    for motion in motions(model, cylinder, 90, settings["prefill"]).values():
        if motion.accel_m_s2:
            speed_m_s, a_m_s2 = motion.speed_m_s, motion.accel_m_s2
            braking_force_N = motion.mass_kg * a_m_s2
            brake_area_m2 = motion.cylinder.annulus_m2 if motion.mode == "extend" else motion.cylinder.cap_m2
            motion_budget[motion.name] = dict(
                mass_kg=motion.mass_kg, speed_limit_m_s=speed_m_s, accel_m_s2=a_m_s2,
                braking_distance_mm=1000 * speed_m_s**2 / (2 * a_m_s2),
                deceleration_time_s=speed_m_s / a_m_s2,
                pdiff_braking_bar=braking_force_N / (brake_area_m2 * BAR_PA),
                pdiff_acceleration_bar=braking_force_N / (motion.flow_area_m2 * motion.cylinder.eta * BAR_PA),
                kinetic_energy_J=motion.mass_kg * speed_m_s**2 / 2,
            )
    return dict(valve_schedule=schedule, valve_count=sum(schedule.values()),
                approximate_mass_breakdown_kg=mass_kg, approximate_station_filled_kg=fsum(mass_kg.values()),
                worst_oil_heat_kW=worst_heat_kW, worst_nominal_oil_heat_kW=worst_nominal_heat_kW,
                cooling=cooling_result, pump_curve=pump_curve(pump),
                lp_accumulator=charge, gate_drive_projection=projection, prefill=prefill_budget(model, cylinder, data),
                motion_budget=motion_budget, motor=dict(
                    breakdown_Nm=breakdown_Nm, peak_with_tolerance_Nm=peak_Nm,
                    breakdown_to_peak_ratio=breakdown_Nm / peak_Nm,
                    worst_rms_with_tolerance_kW=max(row["shaft_rms_with_tolerance_kW"] for row in duties),
                    rated_kW=motor["rated_kW"], rated_Nm=motor["rated_torque_Nm"],
                    rated_rpm=motor["rated_rpm"],
                ))


def calculate():
    from copy import deepcopy

    inputs, data = get_inputs(), source_data()
    model, cylinder, settings, projection, charge = configuration(inputs, data=data)
    duties = [run_scenario(inputs, data, "realistic", curve, density, feed_s, dose_kg, pressure_bar)
              for curve, density, feed_s, dose_kg, pressure_bar in product(
                  ("base", "high"), (90, 160), (.64, .50), (.83, 1.068), (None, 270, 300))]
    references = [r for r in duties if r["case"] == "base" and r["feed_s"] == .64
                  and r["dose_kg"] == .83 and r["specified_max_pressure_bar"] is None]
    screen = [run_scenario(inputs, data, profile, "base", density, .64, .83, None)
              for profile, density in product(("optimistic", "pessimistic"), (90, 160))]
    lever_rows, sensitivities = simulate_levers(inputs, data)
    more_loss = deepcopy(data)
    extra_kW = more_loss["engineering_inputs"]["pump_deadhead_sensitivity_kW"]
    limits = more_loss["catalogs"]["parker_pvplus"]["models"]["PV180"]["zero_stroke_power_kW_endpoints"]
    limits[:] = [x + extra_kW for x in limits]
    sensitivity = run_scenario(inputs, more_loss, "realistic", "base", 90, .64, .83, None)
    sensitivities["pv180_additive_deadhead_kW"] = dict(
        added_loss_kW=extra_kW, cycle_s=sensitivity["cycle_s"],
        delta_s=sensitivity["cycle_s"] - references[0]["cycle_s"],
        rms_with_tolerance_kW=sensitivity["shaft_rms_with_tolerance_kW"])
    station = station_budget(model, cylinder, settings, projection, charge, data, references[0], duties + screen)
    main_coverage = [r for r in duties if r["dose_kg"] == 1.068]
    checks = dict(
        reference_time=all(r["cycle_s"] <= 5.85 for r in references),
        reference_peak=all(r["shaft_peak_with_tolerance_kW"] <= 40 for r in references),
        reference_rms=all(r["shaft_rms_with_tolerance_kW"] <= 30 for r in references),
        reference_average=all(r["shaft_average_with_tolerance_kW"] <= 30 for r in references),
        production_upper_dose=all(r["dose_throughput_kg_h"] >= 498 for r in main_coverage),
        recharge_in_allocated_windows=all(r["extra_recharge_s"] == 0 for r in duties + screen),
        all_cases_peak=all(r["shaft_peak_with_tolerance_kW"] <= 40 for r in duties + screen),
        all_cases_rms=all(r["shaft_rms_with_tolerance_kW"] <= 30 for r in duties + screen),
        all_cases_average=all(r["shaft_average_with_tolerance_kW"] <= 30 for r in duties + screen),
    )
    return dict(task="T-1.4b", variant="V2", acceptance=checks, reference=references,
                duty_matrix=duties, edge_profiles=screen, levers=lever_rows, sensitivities=sensitivities,
                station=station)


if __name__ == "__main__":
    write_json(HERE / "results.json", calculate())
