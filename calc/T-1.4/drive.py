"""Drive, duty points, and hydraulic energy calculations for T-1.4."""
import json
from bisect import bisect_right
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from itertools import product
from math import ceil, floor, fsum, pi, sqrt
from pathlib import Path

import yaml

from x1_calc import Accumulator, BAR_PA, MOTOR_KW, OIL_BULK_PA, Cylinder, Model, area_m2, converged_run, motions, periodic_run, simulate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
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


class Tandem:
    """Two regulated PVplus pumps sharing a shaft and a hydraulic header."""

    def __init__(self, data, low_stage="PV360", high_stage="PV046", limit_kW=None, *,
                 response_multiplier=1., anticipation=True):
        self.response_multiplier = response_multiplier
        self.anticipation = anticipation
        self.tolerance = data["engineering_inputs"]["torque_estimate_tolerance"]
        self.catalog = data["catalogs"]["parker_pvplus"]
        config = data["engineering_inputs"]
        self.low_stage, self.high_stage = low_stage, high_stage
        self.rpm = config["motor_rpm"]
        self.limit_kW = config["shaft_limit_kW"] if limit_kW is None else limit_kW
        self.loss_kW = config["coupling_loss_allowance_kW"]
        self.standby_bar = self.catalog["fdv_min_pilot_bar"]
        self.hp_standby_bar = config["hp_standby_bar"]
        self.names = (high_stage, low_stage) if high_stage else (low_stage,)
        self.standby_pressures_bar = (self.hp_standby_bar, self.standby_bar) if high_stage else (self.standby_bar,)
        self.omega_rad_s = self.rpm * 2 * pi / 60
        self.control_delay_s = .010

    @lru_cache(maxsize=8192)
    def section(self, name, pressure_bar):
        model = self.catalog["models"][name]
        geometric_L_min = self.rpm * model["displacement_cm3_rev"] / 1000
        ratio = self.rpm / self.catalog["reference_speed_rpm"]
        if "volumetric_efficiency_by_bar" in model:
            eta_v = linear_value(max(25, pressure_bar), model["volumetric_efficiency_by_bar"])
            zero_kW = linear_value(pressure_bar, model["zero_stroke_power_kW_by_bar"]) * ratio
            full_points = model["full_stroke_power_kW_by_bar"] + [[350, model["full_stroke_power_at_350bar_kW"]]]
            graph_kW = linear_value(pressure_bar, full_points) * ratio
            eta_points = model["total_efficiency_by_bar"]
            start_bar, start_eta = eta_points[0]
            if pressure_bar < start_bar:
                start_kW = start_bar * geometric_L_min * eta_v / (600 * start_eta)
                efficiency_kW = linear_value(pressure_bar, ((0, full_points[0][1] * ratio), (start_bar, start_kW)))
            else:
                efficiency_kW = pressure_bar * geometric_L_min * eta_v / (600 * linear_value(pressure_bar, eta_points))
            full_kW = max(graph_kW, efficiency_kW)
        else:
            nominal_bar = self.catalog["continuous_pressure_bar"]
            eta_v = linear_value(pressure_bar, ((0, 1.), (nominal_bar, model["full_stroke_eta_v_at_350bar"])))
            zero_kW = linear_value(pressure_bar, tuple(zip((0, nominal_bar), model["zero_stroke_power_kW_endpoints"]))) * ratio
            full_kW = linear_value(pressure_bar, tuple(zip((0, nominal_bar), model["full_stroke_power_kW_endpoints"]))) * ratio
        flow_L_min = geometric_L_min * eta_v - self.catalog["pilot_flow_allowance_L_min"]
        eta_hm = pressure_bar * geometric_L_min / (600 * full_kW)
        return PumpPoint(flow_L_min, zero_kW, full_kW, eta_v, eta_hm)

    def fractions(self, pressure_bar, requested_L_min, actual=()):
        """Torque budget for both shafts, including a large section still destroking."""
        points = self.points(pressure_bar)
        small = points[0]
        remaining_kW = self.limit_kW - self.loss_kW - small.deadhead_kW
        if len(points) == 2:
            large = points[1]
            remaining_kW -= self.section(self.low_stage, self.standby_bar).deadhead_kW
            if len(actual) == 2 and actual[1] > 1e-10 and pressure_bar > self.standby_bar:
                remaining_kW -= large.deadhead_kW - self.section(self.low_stage, self.standby_bar).deadhead_kW
        small_q = min(small.flow_L_min, requested_L_min,
                      max(0., remaining_kW) / small.incremental_kW_per_L_min)
        if len(points) == 1:
            return (small_q / small.flow_L_min,)
        if not actual or actual[1] <= 1e-10:
            remaining_kW -= large.deadhead_kW - self.section(self.low_stage, self.standby_bar).deadhead_kW
        remaining_kW -= small_q * small.incremental_kW_per_L_min
        large_q = min(large.flow_L_min, requested_L_min - small_q,
                      max(0., remaining_kW) / large.incremental_kW_per_L_min)
        return small_q / small.flow_L_min, large_q / large.flow_L_min

    @lru_cache(maxsize=8192)
    def points(self, pressure_bar):
        return tuple(self.section(name, max(pressure_bar, standby_bar))
                     for name, standby_bar in zip(self.names, self.standby_pressures_bar))

    def instant(self, pressure_bar, fractions, connected):
        """Actual shaft demand at the measured displacement, including idle work."""
        flow_L_min = 0.
        shaft_kW = self.loss_kW
        bypass_kW = 0.
        for i, (name, standby_bar) in enumerate(zip(self.names, self.standby_pressures_bar)):
            outlet_bar = max(pressure_bar if connected[i] else 0., standby_bar)
            point = self.section(name, outlet_bar)
            q_L_min = fractions[i] * point.flow_L_min
            shaft_kW += point.deadhead_kW + fractions[i] * (point.full_stroke_kW - point.deadhead_kW)
            if connected[i]:
                flow_L_min += q_L_min
                bypass_kW += (outlet_bar - pressure_bar) * q_L_min / 600
            else:
                bypass_kW += outlet_bar * q_L_min / 600
        return flow_L_min, shaft_kW, bypass_kW

    def connected(self, pressure_bar, actual, setpoints):
        return tuple(pressure_bar > 0. and (i == 0 or x > 1e-10 or y > 1e-10)
                     for i, (x, y) in enumerate(zip(actual, setpoints)))

    def operating_point(self, pressure_bar, requested_L_min=float("inf")):
        fractions = self.fractions(pressure_bar, requested_L_min)
        q, power, _ = self.instant(pressure_bar, fractions, self.connected(pressure_bar, fractions, fractions))
        return q, power

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

def configuration(inputs, *, data=None, variant="V1", profile="realistic", anticipation=True,
                  limit_kW=None, losses_bar=None):
    data = data or source_data()
    cfg = data["engineering_inputs"]
    catalog = data["catalogs"]
    profiles = {
        "realistic": (cfg["valve_allowance_s"], cfg["unload_s"], 1., 1.),
        "optimistic": (.050, .150, 1., 1.),
        "pessimistic": (.100, .250, 1.25, .40 / .45),
    }
    valve_s, unload_s, multiplier, gate_ratio = profiles[profile]
    stages = {"V1": ("PV360", "PV046"), "V2": ("PV180", None), "V3": ("PV270", "PV046")}
    model, cylinder = scenario(inputs, gate_m_s=cfg["slide_gate_mean_speed_mm_s"] * gate_ratio / 1000,
                               losses_bar=losses_bar or tuple(cfg["line_drop_inlet_tank_regen_bar"]))
    pump = Tandem(data, *stages[variant], limit_kW=limit_kW, response_multiplier=multiplier, anticipation=anticipation)
    settings = dict(
        EARLY_SETTINGS, switch_s=valve_s, hold_s=cfg["hold_s"], unload_s=unload_s,
        pump=pump, max_L_min=pump.capacity_L_min(pump.standby_bar), deficit_only=True,
        boost_branches=("return", "pre_up"), accumulator_shell_L=catalog["hydac_sb330"]["effective_gas_volume_L"],
        accumulator_kwargs=dict(
            precharge_bar=cfg["accumulator_precharge_bar_at_operating_temperature"],
            low_bar=cfg["accumulator_gas_low_bar"], high_bar=cfg["accumulator_gas_high_bar"],
            delivery_L_min=cfg["accumulator_branch_flow_L_min"], exponent=cfg["accumulator_polytropic_exponent"],
        ),
        charge_drop_bar=cfg["accumulator_charge_and_delivery_drop_bar"],
    )
    if variant == "V2":
        settings["prefill"] = dict(cfg["prefill_auxiliary_cylinders"],
                                   switch_force_N=cfg["prefill_fast_to_regen_force_N"],
                                   float_gauge_bar=cfg["prefill_pipe"]["tank_gauge_bar"])
        settings["boost_branches"] += ("pre_down",)
    if variant == "V3":
        hp = catalog["high_pressure_sb330"]
        low_bar, high_bar = cfg["hp_window_bar"]
        settings.update(hp_accumulator_kwargs=dict(shell_L=hp["effective_gas_volume_L"],
                        precharge_bar=cfg["hp_precharge_bar"], low_bar=low_bar, high_bar=high_bar,
                        exponent=cfg["accumulator_polytropic_exponent"],
                        delivery_L_min=cfg["hp_assist_L_min"]), hp_threshold_bar=cfg["hp_assist_threshold_bar"])
        assert high_bar + settings["charge_drop_bar"] <= 300
        assert settings["hp_accumulator_kwargs"]["delivery_L_min"] <= hp["vertical_discharge_max_L_min"]
        check_accumulator(Accumulator(**settings["hp_accumulator_kwargs"]), catalog["hydac_sb330"])
    # The gate has one eta and a static hyperbola. Use the actual net
    # torque-limited delivery over the complete nominal direct press range.
    press = motions(model, cylinder, 90)["press"]
    start_bar, end_bar = press.pressure_bar(0.), press.pressure_bar(press.stroke_m)
    pressures_bar = [start_bar + i * (end_bar - start_bar) / 1000 for i in range(1001)]
    envelope_eta = min(pump.capacity_L_min(bar) * bar / (600 * MOTOR_KW) for bar in pressures_bar)
    projection = dict(motor_kW=MOTOR_KW, installed_kW=fsum(cfg["installed_kW"].values()),
                      pump_max_flow_L_min=settings["max_L_min"], eta=floor(envelope_eta * 1000) / 1000)
    charge = Accumulator(shell_L=settings["accumulator_shell_L"], **settings["accumulator_kwargs"])
    check_accumulator(charge, catalog["hydac_sb330"])
    charge_plan = dict(
        usable_oil_L=1000 * (charge.oil_at_m3(charge.high_bar) - charge.oil_at_m3(charge.low_bar)),
        max_flow_L_min=charge.delivery_L_min, min_delivery_pressure_bar=charge.low_bar,
        charge_pressure_bar=charge.high_bar + settings["charge_drop_bar"],
        round_trip_eta=1., recharge_when_idle=True,
    )
    return model, cylinder, settings, projection, charge_plan


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
        prefill_and_float=e["prefill_float_kJ"],
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


def run_scenario(inputs, data, variant, profile, curve, density, feed_s, dose_kg, pressure_bar, *,
                 converge=False, full_convergence=False, anticipation=True, limit_kW=None):
    base_model, cylinder, settings, _, _ = configuration(
        inputs, data=data, variant=variant, profile=profile, anticipation=anticipation, limit_kW=limit_kW)
    model, _ = scenario(inputs, curve, density, dose_kg, pressure_bar,
                        base_model.gate_speed_m_s, base_model.losses_bar)
    if converge:
        steps_s = (.0025, .00125, .000625, .0003125) if full_convergence else (.00125, .000625)
        run = converged_run(model, cylinder, density, feed_s, settings, steps_s)
    else:
        run = periodic_run(model, cylinder, density, feed_s, settings, .00125)
    if not run["feasible"]:
        raise RuntimeError((variant, profile, curve, density, pressure_bar, run))
    pump = settings["pump"]
    run["shaft_peak_with_tolerance_kW"] = run["peak_shaft_kW"] * (1 + pump.tolerance)
    run["peak_shaft_torque_Nm"] = 1000 * run["peak_shaft_kW"] / pump.omega_rad_s
    run.update(variant=variant, profile=profile, case=curve, specified_max_pressure_bar=pressure_bar,
               nominal_force_N=model.nominal_N,
               immediate_density_kg_m3=model.in_die_kg_m3 / model.material.volume_ratio(curve))
    run["decompression"] = decompression(run, model, cylinder, data)
    run["decompression"]["available_orifice_time_s"] = settings["unload_s"] - settings["switch_s"]
    run["heat"] = heat_balance(run, run["decompression"], data)
    if variant == "V3":
        e = run["energy"]
        run["hp_accumulator_balance"] = dict(
            header_input_kJ=e["hp_charge_kJ"], stored_gas_energy_kJ=e["hp_gas_in_kJ"],
            returned_gas_energy_kJ=e["hp_gas_out_kJ"], press_header_delivery_kJ=e["hp_boost_kJ"],
            hydraulic_round_trip_eta=(e["hp_boost_kJ"] / e["hp_charge_kJ"] if e["hp_charge_kJ"] else None),
        )
    return run


def simulate_levers(inputs, data):
    standard, cylinder = scenario(inputs)
    full_mm = inputs[0]["alternatives"]["A"]["dimensions"]["max_pre_shoe_stroke_mm"]
    full = replace(standard, pre_travel_m=full_mm / 1000)
    working = dict(BASE_SETTINGS)
    rows = []

    def record(name, model, options):
        cycle_s = periodic_run(model, cylinder, 90, .64, options, .00125)["cycle_s"]
        rows.append(dict(lever=name, cycle_s=cycle_s,
                         delta_s=None if not rows else cycle_s - rows[-1]["cycle_s"]))

    record("full_shoe_travel", full, working)
    record("dose_parking", standard, working)
    working.update(EARLY_SETTINGS)
    record("early_unlock", standard, working)
    working["switch_s"] = .07
    record("valve_allowance_70_ms", standard, working)
    working["unload_s"] = .20
    record("metered_decompression_200_ms", standard, working)
    faster, _, real, *_ = configuration(inputs, data=data)
    working.update({key: real[key] for key in ("accumulator_kwargs", "accumulator_shell_L",
                                               "boost_branches", "deficit_only")})
    record("sb330_and_boost_dispatch", standard, working)
    record("slide_gate_speed_450_mm_s", faster, working)
    # Show each Round 2 correction on the dynamic catalogue drive.
    optimistic_tract, _, optimistic, *_ = configuration(inputs, data=data, profile="optimistic", losses_bar=(2., 2., 2.))
    record("catalogue_linear_response_no_prestroke_cap_360_L_min", optimistic_tract,
           optimistic | {"max_L_min": 360.})
    record("catalogue_linear_response_no_prestroke_full_flow", optimistic_tract, optimistic)
    record("upstream_flow_path_drops_4_3_4_bar", faster, optimistic)
    record("restore_70_ms_valve_budget", faster, optimistic | {"switch_s": .070})
    record("restore_200_ms_decompression", faster, real)
    return rows


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


def prefill_budget(cylinder, data):
    cfg = data["engineering_inputs"]
    catalog = data["catalogs"]["rexroth_sfa"]
    pipe = cfg["prefill_pipe"]
    density = cfg["oil_density_kg_m3"]
    diameter_m = pipe["inside_diameter_mm"] / 1000
    cap_max_volume_L = cylinder.cap_m2 * cylinder.stroke_mm
    cap_flow_m3_s = cylinder.cap_m2 * .24
    pipe_velocity_m_s = cap_flow_m3_s / area_m2(pipe["inside_diameter_mm"])
    loss_coeff = pipe["darcy_factor"] * pipe["length_m"] / diameter_m + pipe["local_K"]
    pipe_loss_bar = loss_coeff * density * pipe_velocity_m_s**2 / (2 * BAR_PA)
    hydrostatic_bar = density * 9.81 * pipe["static_head_m"] / BAR_PA
    cap_absolute_bar = 1.01325 + pipe["tank_gauge_bar"] + hydrostatic_bar - pipe_loss_bar - catalog["suction_drop_budget_bar"]
    return_flow_L_min = cylinder.cap_m2 * .25 * 60000
    exhaust = data["catalogs"]["rexroth_2wrce"]
    reverse_loss_bar = exhaust["reference_drop_bar"] * (return_flow_L_min / exhaust["rated_flow_L_min_by_ng"][50])**2
    return dict(cap_flow_L_min=cap_flow_m3_s * 60000, max_cap_exhaust_L_min=return_flow_L_min,
                pipe_velocity_m_s=pipe_velocity_m_s, pipe_drop_bar=pipe_loss_bar,
                max_prefill_valve_drop_bar=catalog["suction_drop_budget_bar"], hydrostatic_head_bar=hydrostatic_bar,
                cap_absolute_bar=cap_absolute_bar, cap_margin_bar=cap_absolute_bar - pipe["cap_min_abs_bar"],
                cap_absolute_without_boost_bar=cap_absolute_bar - pipe["tank_gauge_bar"],
                minimum_buffer_L=1.5 * cap_max_volume_L, proposed_buffer_L=30.,
                reverse_dedicated_NG50_valve_drop_bar=reverse_loss_bar,
                case_2_flow_margin_L_min=catalog["case_2_flow_L_min"] - cap_flow_m3_s * 60000)


def station_budget(inputs, data, variant, base, worst_heat_kW):
    cfg, catalog = data["engineering_inputs"], data["catalogs"]
    _, cylinder, settings, gate_drive, charge = configuration(inputs, data=data, variant=variant)
    pump = settings["pump"]
    # Main cylinder: P-A, P-B, A-T (also prefill exhaust), B-T, B-A.
    # Auxiliary actuator directional valves are P/T metering edges, 4 per cylinder pair.
    # The two high-flow neutral outlets of a tandem each count as a valve.
    schedule = dict(main_NG40=3, main_NG50=2, pre_NG25=4, gate_NG16=4, lp_NG25=3, relief_NG16=len(pump.names))
    if variant == "V2":
        schedule.update(prefill_NG80=1, paired_rapid_ram_NG32=4, neutral_NG32=1)
    else:
        schedule.update(tandem_join_NG40=1, neutral_NG40=1, neutral_NG16=1)
    if variant == "V3":
        schedule["hp_NG16"] = 3
    working_L, gross_L = cfg["tank_working_gross_L"][variant]
    average_flow_L_min = base["pump_oil_L"] * 60 / base["cycle_s"]
    thermal = cooling(data, worst_heat_kW, settings["max_L_min"], working_L, gross_L, average_flow_L_min)
    mass_kg = dict(
        motor=catalog["ie3_motor"]["mass_kg"],
        pumps=sum(pump.catalog["models"][name]["mass_kg"] for name in pump.names),
        lp_and_pilot_vessels=catalog["hydac_sb330"]["mass_kg"] + catalog["hydac_sb330"]["pilot_mass_kg"],
        tank=cfg["station_mass_allowance_kg"][variant + "_tank"],
        main_and_large_valves=sum(
            count * catalog["rexroth_2wrce"]["mass_kg_by_ng"][int(key.rsplit("NG", 1)[1])]
            for key, count in schedule.items() if int(key.rsplit("NG", 1)[1]) in (32, 40, 50)
        ),
        manifold_pipes_cooling_and_skid_allowance=
            cfg["station_mass_allowance_kg"]["manifold_pipes_pilot_cooling_small_valves_and_skid"],
        oil=working_L * cfg["oil_density_kg_m3"] / 1000,
    )
    if variant == "V2":
        mass_kg["sfa_prefill_valve"] = catalog["rexroth_sfa"]["mass_kg"]
        mass_kg["prefill_buffer_and_its_oil_allowance"] = 40
    if variant == "V3":
        mass_kg["hp_vessel"] = catalog["high_pressure_sb330"]["mass_kg"]
    return dict(valve_schedule=schedule, valve_count=sum(schedule.values()), approximate_mass_breakdown_kg=mass_kg,
                approximate_station_filled_kg=sum(mass_kg.values()), cooling=thermal, pump_curve=pump_curve(pump),
                gate_drive_projection=gate_drive, lp_accumulator=charge,
                prefill=prefill_budget(cylinder, data) if variant == "V2" else None,
                hp_accumulator=settings.get("hp_accumulator_kwargs"),
                rated_breakdown_torque_Nm=catalog["ie3_motor"]["rated_torque_Nm"]
                * catalog["ie3_motor"]["breakdown_to_rated_torque"])


def additional_power(inputs, data):
    # Counterfactual only. Keep all cycle logic, phase limits and geometry.
    rows = []
    for variant in ("V1", "V2", "V3"):
        for effective_kW in (28.5, 34., 38., 42., 48., 54.):
            run = run_scenario(inputs, data, variant, "realistic", "base", 90, .64, .83, None,
                               limit_kW=effective_kW)
            rows.append(dict(variant=variant, torque_command_kW=effective_kW,
                             nameplate_with_5pct_tolerance_kW=effective_kW * 1.05, cycle_s=run["cycle_s"]))
    return rows


def calculate_variant(variant):
    inputs, data = get_inputs(), source_data()
    duties = []
    for curve, density, feed_s, dose_kg, pressure_bar in product(
        ("base", "high"), (90, 160), (.50, .64), (.83, 1.068), (None, 270, 300)
    ):
        # Full matrix for the prefill screen. For the tandem variants
        # keep the entire .64 s matrix and the nominal .50 s cases.
        if variant != "V2" and feed_s != .64 and (dose_kg != .83 or pressure_bar is not None):
            continue
        comparison_duty = feed_s == .64 and dose_kg == .83 and curve == "base"
        duties.append(run_scenario(inputs, data, variant, "realistic", curve, density, feed_s, dose_kg,
                                   pressure_bar, converge=True, full_convergence=comparison_duty))
    comparison = [run for run in duties if run["case"] == "base" and run["feed_s"] == .64
                  and run["dose_kg"] == .83 and run["specified_max_pressure_bar"] is None]
    for profile, density in product(("optimistic", "pessimistic"), (90, 160)):
        comparison.append(run_scenario(inputs, data, variant, profile, "base", density, .64, .83, None,
                                       converge=True, full_convergence=True))
    transients = []
    for body in (None, 300):
        unprotected = run_scenario(inputs, data, variant, "realistic", "base", 90, .64, .83, body,
                                   anticipation=False)
        transients.append(dict(specified_max_pressure_bar=body, peak_shaft_kW=unprotected["peak_shaft_kW"],
                               peak_shaft_torque_Nm=unprotected["peak_shaft_torque_Nm"],
                               contact_and_press_entry=unprotected["contact_and_press_entry"],
                               peak_shaft_by_stage=unprotected["peak_shaft_by_stage"]))
    worst_heat_kW = max(run["heat"]["oil_heat_budget_kW"] for run in duties + comparison)
    return dict(comparison=comparison, duty_matrix=duties, unguarded_transients=transients,
                station=station_budget(inputs, data, variant, comparison[0], worst_heat_kW))


def calculate():
    inputs, data = get_inputs(), source_data()
    baseline_model, cylinder = scenario(inputs)
    upstream_s = inputs[0]["alternatives"]["A"]["cycle"]["0.64"]["cycle_s"]
    baseline_s = simulate(baseline_model, cylinder=cylinder, dt_s=.00125, feed_s=.64, **BASE_SETTINGS)["cycle_s"]
    assert abs(baseline_s - upstream_s) < 1e-9
    names = ("V1", "V2", "V3")
    with ProcessPoolExecutor(max_workers=len(names)) as pool:
        results = dict(zip(names, pool.map(calculate_variant, names)))
    base_90 = {variant: result["comparison"][0]["cycle_s"] for variant, result in results.items()}
    best = min(base_90, key=base_90.get)
    meets = [variant for variant, result in results.items()
             if all(run["cycle_s"] <= 5.85 and run["shaft_peak_with_tolerance_kW"] <= 30.
                    for run in result["comparison"] if run["profile"] == "realistic")]
    chosen = min(meets, key=base_90.get) if meets else None
    return dict(task="T-1.4", round=2, selected_variant=chosen, fastest_at_90_kg_m3=best,
                upstream_overlap_recheck_s=baseline_s, upstream_report_s=upstream_s,
                levers=simulate_levers(inputs, data), counterfactual_power=additional_power(inputs, data),
                variants=results)
