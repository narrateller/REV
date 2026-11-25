"""Independent D0 force balance, chamber geometry and hydraulic simulation."""

from dataclasses import dataclass, field, replace
import json
from math import ceil, exp, log, pi, sqrt
from pathlib import Path
from typing import Callable

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BAR_PA = 1e5
M3_TO_L = 1000
M3_S_TO_L_MIN = 60000
DT_S = 0.005
PUMP_ETA = 0.84
MOTOR_KW = 30.0
IDLE_KW = 0.5
SWITCH_S = 0.10
OIL_BULK_PA = 1.4e9
MAX_WORKING_BAR = 300


def area_m2(diameter_mm):
    return pi * (diameter_mm / 2000) ** 2


@dataclass(frozen=True)
class Cylinder:
    bore_mm: float
    rod_mm: float
    stroke_mm: float
    eta: float

    @property
    def cap_m2(self):
        return area_m2(self.bore_mm)

    @property
    def rod_m2(self):
        return area_m2(self.rod_mm)

    @property
    def annulus_m2(self):
        return self.cap_m2 - self.rod_m2


MAIN = Cylinder(280, 200, 230, 0.94)
PRE = Cylinder(100, 56, 330, 0.92)
GATE = Cylinder(80, 45, 70, 0.92)


def supply_bar(cylinder, force_N, mode):
    """4 bar inlet drop, 3 bar tank backpressure, 4 bar recirculation drop."""
    area, opposite_area, backpressure_bar = {
        "extend": (cylinder.cap_m2, cylinder.annulus_m2, 3),
        "retract": (cylinder.annulus_m2, cylinder.cap_m2, 3),
        "regen": (cylinder.rod_m2, cylinder.annulus_m2, 4),
    }[mode]
    return 4 + (force_N / cylinder.eta / BAR_PA + backpressure_bar * opposite_area) / area


@dataclass(frozen=True)
class Model:
    dose_kg: float = 0.83
    width_m: float = 0.150
    height_m: float = 0.060
    feed_length_m: float = 0.200
    in_die_kg_m3: float = 1150.0
    axial_recovery: float = 0.08
    pressure_exponent: float = 3.0
    pre_scale_MPa: float = 3.5
    nominal_N: float = 1_520_000
    ejection_N: float = 100_000
    overtravel_m: float = 0.010
    approach_m: float = 0.0

    @property
    def section_m2(self):
        return self.width_m * self.height_m

    @property
    def pre_section_m2(self):
        return self.width_m * self.feed_length_m

    @property
    def pre_density_kg_m3(self):
        return self.dose_kg / (self.pre_section_m2 * self.height_m)

    @property
    def die_length_m(self):
        return self.dose_kg / (self.section_m2 * self.in_die_kg_m3)

    @property
    def press_end_m(self):
        return self.approach_m + self.feed_length_m - self.die_length_m

    @property
    def main_travel_m(self):
        return self.approach_m + self.feed_length_m + self.overtravel_m

    def loose_height_m(self, bulk_kg_m3):
        return self.dose_kg / (self.pre_section_m2 * bulk_kg_m3)

    @property
    def pre_travel_m(self):
        # Start set by the worst fill, plus 10 mm clearance above the free surface.
        return self.loose_height_m(90) + 0.010 - self.height_m

    def axial_pressure_Pa(self, density_kg_m3):
        # Scenario constitutive law. The endpoint is a design target, not a fit.
        relative_density = (density_kg_m3 - self.pre_density_kg_m3) / (
            self.in_die_kg_m3 - self.pre_density_kg_m3
        )
        return self.nominal_N / self.section_m2 * max(0, relative_density) ** self.pressure_exponent

    def axial_force_N(self, travel_m):
        if travel_m < self.approach_m:
            return 0.0
        length_m = self.feed_length_m + self.approach_m - travel_m
        density_kg_m3 = self.dose_kg / (self.section_m2 * length_m)
        return self.section_m2 * self.axial_pressure_Pa(density_kg_m3)

    def pre_force_N(self, travel_m, bulk_kg_m3):
        height_m = self.height_m + self.pre_travel_m - travel_m
        density_kg_m3 = self.dose_kg / (self.pre_section_m2 * height_m)
        density_term = (density_kg_m3 / self.pre_density_kg_m3) ** 2.5
        initial_term = (bulk_kg_m3 / self.pre_density_kg_m3) ** 2.5
        # Janssen stress transfer with illustrative mu=0.30 and K=0.40.
        perimeter_m = 2 * (self.width_m + self.feed_length_m)
        friction_factor = exp(0.30 * 0.40 * perimeter_m * height_m / self.pre_section_m2)
        return max(0.0, density_term - initial_term) * self.pre_scale_MPa * 1e6 * (
            self.pre_section_m2 * friction_factor
        )


M1_PRESSURE_POINTS = [(461, 3), (600, 8), (800, 30), (1000, 80), (1180, 166.7)]


def integrated_work_J(mass_kg, pressure_Pa, low_kg_m3, high_kg_m3):
    """Midpoint quadrature in specific volume, dW = p * m * (-d(1/rho))."""
    count = 10000
    delta_m3_kg = (1 / low_kg_m3 - 1 / high_kg_m3) / count
    return mass_kg * delta_m3_kg * sum(
        pressure_Pa(1 / (1 / high_kg_m3 + (i + 0.5) * delta_m3_kg)) for i in range(count)
    )


def m1_placeholder_work_J(dose_kg):
    total_J = 0.0
    for (lo_kg_m3, lo_MPa), (hi_kg_m3, hi_MPa) in zip(M1_PRESSURE_POINTS, M1_PRESSURE_POINTS[1:]):
        def pressure_Pa(density_kg_m3):
            fraction = (density_kg_m3 - lo_kg_m3) / (hi_kg_m3 - lo_kg_m3)
            return 1e6 * exp(log(lo_MPa) + fraction * log(hi_MPa / lo_MPa))

        total_J += integrated_work_J(dose_kg, pressure_Pa, lo_kg_m3, hi_kg_m3)
    return total_J


@dataclass
class Accumulator:
    shell_L: float = 5.0
    precharge_bar: float = 28.0
    high_bar: float = 75.0
    low_bar: float = 38.0
    exponent: float = 1.4
    delivery_L_min: float = 150.0
    oil_m3: float = field(init=False)

    def __post_init__(self):
        self.oil_m3 = self.oil_at_m3(self.high_bar)

    def oil_at_m3(self, gauge_bar):
        return self.shell_L / M3_TO_L * (1 - ((self.precharge_bar + 1) / (gauge_bar + 1)) ** (1 / self.exponent))

    @property
    def pressure_bar(self):
        gas_fraction = 1 - self.oil_m3 * M3_TO_L / self.shell_L
        return (self.precharge_bar + 1) / gas_fraction**self.exponent - 1


@dataclass(frozen=True)
class Motion:
    name: str
    actuator: str
    cylinder: Cylinder
    mode: str
    stroke_m: float
    speed_m_s: float
    pressure_bar: Callable[[float], float]
    oil_compliance: bool = False
    offset_m: float = 0.0

    @property
    def flow_area_m2(self):
        return {"extend": self.cylinder.cap_m2, "retract": self.cylinder.annulus_m2,
                "regen": self.cylinder.rod_m2}[self.mode]

    def storage_area_m2(self, position_m):
        """Local dV/dx with compression of the filled pressure-side cavities."""
        if not self.oil_compliance:
            return 0.0
        next_m = min(self.stroke_m, position_m + 0.00001)
        if next_m <= position_m:
            return 0.0
        slope_Pa_m = BAR_PA * (self.pressure_bar(next_m) - self.pressure_bar(position_m)) / (next_m - position_m)
        oil_m3 = 0.0008 + self.cylinder.cap_m2 * (self.offset_m + position_m)
        if self.mode == "regen":
            oil_m3 += 0.0004 + self.cylinder.annulus_m2 * (self.cylinder.stroke_mm / 1000 - position_m)
        return oil_m3 * max(0.0, slope_Pa_m) / OIL_BULK_PA


def motions(model, cylinder, bulk_kg_m3):
    pre = Motion("pre_down", "precompaction", PRE, "extend", model.pre_travel_m, 0.65,
                 lambda x: supply_bar(PRE, model.pre_force_N(x, bulk_kg_m3) + 5000, "extend"))

    def pressing_bar(x, mode):
        guide_load_N = 0 if mode == "extend" else 8000
        return supply_bar(cylinder, model.axial_force_N(x) + guide_load_N, mode)

    low_m, high_m = 0.0, model.press_end_m
    for _ in range(45):
        mid_m = (low_m + high_m) / 2
        if pressing_bar(mid_m, "regen") <= 120:
            low_m = mid_m
        else:
            high_m = mid_m
    regen_m = low_m

    def fixed_motion(name, actuator, ram, mode, stroke_m, speed_m_s, force_N):
        required_bar = supply_bar(ram, force_N, mode)
        return Motion(name, actuator, ram, mode, stroke_m, speed_m_s, lambda _: required_bar)

    def ejection_bar(x):
        fraction_in_die = max(0, 1 - x / model.die_length_m)
        return supply_bar(cylinder, 8000 + model.ejection_N * fraction_in_die, "regen")

    return {
        "pre_down": pre,
        "regen": Motion("regen", "main_cylinder", cylinder, "regen", regen_m, 0.24,
                        lambda x: pressing_bar(x, "regen"), True),
        "press": Motion("press", "main_cylinder", cylinder, "extend", model.press_end_m - regen_m, 0.24,
                         lambda x: pressing_bar(regen_m + x, "extend"), True, regen_m),
        "gate_open": fixed_motion("gate_open", "slide_gate", GATE, "retract", .070, .25, 10000),
        "eject": Motion("eject", "main_cylinder", cylinder, "regen", model.main_travel_m - model.press_end_m,
                        0.24, ejection_bar),
        "return": fixed_motion("return", "main_cylinder", cylinder, "retract", model.main_travel_m, .25, 40000),
        "gate_close": fixed_motion("gate_close", "slide_gate", GATE, "extend", .070, .25, 8000),
        "pre_up": fixed_motion("pre_up", "precompaction", PRE, "retract", model.pre_travel_m, .65, 6000),
    }


@dataclass
class Cycle:
    max_L_min: float
    dt_s: float
    accumulator: Accumulator | None
    time_s: float = 0.0
    flow_m3_s: float = 0.0
    shaft_kJ: float = 0.0
    pump_oil_L: float = 0.0
    peak_kW: float = 0.0
    peak_bar: float = 0.0
    peak_pump_L_min: float = 0.0
    boost_L: float = 0.0
    charge_L: float = 0.0
    switches: list = field(default_factory=list)
    events: dict = field(default_factory=dict)

    def pump_capacity_m3_s(self, header_bar, demand_m3_s, step_s):
        cap_m3_s = min(self.max_L_min / M3_S_TO_L_MIN, demand_m3_s,
                       1000 * (MOTOR_KW - IDLE_KW) * PUMP_ETA / (header_bar * BAR_PA))
        rise_fraction = 1 - exp(-step_s / 0.035)
        return min(cap_m3_s, self.flow_m3_s + (cap_m3_s - self.flow_m3_s) * rise_fraction)

    def advance(self, step_s, header_bar, pump_m3_s):
        self.time_s += step_s
        self.flow_m3_s = pump_m3_s
        shaft_kW = IDLE_KW + header_bar * BAR_PA * pump_m3_s / PUMP_ETA / 1000
        self.shaft_kJ += shaft_kW * step_s
        self.pump_oil_L += pump_m3_s * step_s * M3_TO_L
        self.peak_kW = max(self.peak_kW, shaft_kW)
        self.peak_bar = max(self.peak_bar, header_bar)
        self.peak_pump_L_min = max(self.peak_pump_L_min, pump_m3_s * M3_S_TO_L_MIN)

    def idle_step(self, step_s):
        accumulator = self.accumulator
        if accumulator:
            missing_m3 = accumulator.oil_at_m3(accumulator.high_bar) - accumulator.oil_m3
            if missing_m3 > 1e-12:
                header_bar = accumulator.pressure_bar + 3
                flow_m3_s = self.pump_capacity_m3_s(header_bar, missing_m3 / step_s, step_s)
                accumulator.oil_m3 += flow_m3_s * step_s
                self.charge_L += flow_m3_s * step_s * M3_TO_L
                self.advance(step_s, header_bar, flow_m3_s)
                return
        self.advance(step_s, 0, 0)

    def idle(self, duration_s):
        steps = ceil(duration_s / self.dt_s)
        for _ in range(steps):
            self.idle_step(duration_s / steps)

    def switch(self, name):
        self.switches.append({"command": name, "time_s": self.time_s})
        self.idle(SWITCH_S)

    def run_group(self, group):
        """Independent spool delays, common pump pressure, main → gate → pre priority."""
        start_s = self.time_s
        positions_m = dict.fromkeys((motion.name for motion in group), 0.0)
        commanded = {}
        while any(positions_m[m.name] < m.stroke_m - 1e-10 for m in group):
            if self.time_s - start_s > 15:
                raise RuntimeError("hydraulic stage timeout")
            step_s = self.dt_s
            demands = []
            for motion in group:
                name = motion.name
                position_m = positions_m[name]
                remaining_m = motion.stroke_m - position_m
                if remaining_m <= 1e-10:
                    continue
                if name not in commanded:
                    # Close only when the face has returned at least 10 mm behind the gate.
                    if name == "gate_close" and "return" in positions_m and positions_m["return"] < 0.020:
                        continue
                    commanded[name] = self.time_s
                    self.switches.append({"command": name, "time_s": self.time_s})
                if self.time_s - commanded[name] + 1e-10 < SWITCH_S:
                    continue
                pressure_bar = motion.pressure_bar(position_m)
                area = motion.flow_area_m2 + motion.storage_area_m2(position_m)
                demand_m3_s = min(motion.speed_m_s, remaining_m / step_s) * area
                demands.append((motion, area, pressure_bar, demand_m3_s))
            if not demands:
                self.idle_step(step_s)
                continue

            header_bar = max(pressure for _, _, pressure, _ in demands)
            boosted_m3_s = self.discharge_m3_s(demands, step_s)
            pump_m3_s = self.pump_capacity_m3_s(
                header_bar, sum(item[3] for item in demands) - boosted_m3_s, step_s
            )
            available_m3_s = pump_m3_s
            for motion, area_m2, pressure_bar, demand_m3_s in demands:
                boost = boosted_m3_s if motion.name == "return" else 0.0
                flow_m3_s = min(demand_m3_s - boost, available_m3_s)
                available_m3_s -= flow_m3_s
                positions_m[motion.name] += (flow_m3_s + boost) * step_s / area_m2
                if flow_m3_s + boost > 0:
                    event = self.events.setdefault(
                        motion.name, {"start_s": self.time_s, "peak_supply_bar": 0.0}
                    )
                    event["peak_supply_bar"] = max(event["peak_supply_bar"], pressure_bar)
                    event["end_s"] = self.time_s + step_s
            self.advance(step_s, header_bar, pump_m3_s)

    def discharge_m3_s(self, demands, step_s):
        accumulator = self.accumulator
        if accumulator is None or demands[0][0].name != "return":
            return 0.0
        # Pressure-reducing/check circuit on the return branch. The minimum
        # discharge pressure follows the local branch plus its valve loss.
        delivery_bar = max(accumulator.low_bar, demands[0][2] + 3)
        available_m3 = max(0, accumulator.oil_m3 - accumulator.oil_at_m3(delivery_bar))
        boosted_m3_s = min(accumulator.delivery_L_min / M3_S_TO_L_MIN, available_m3 / step_s, demands[0][3])
        accumulator.oil_m3 -= boosted_m3_s * step_s
        self.boost_L += boosted_m3_s * step_s * M3_TO_L
        return boosted_m3_s


def simulate(model, *, max_L_min=360, overlap=False, accumulator=False, feed_s=0.50,
             bulk_kg_m3=90, dt_s=DT_S, cylinder=MAIN):
    assert 0 < dt_s <= DT_S
    sequence = motions(model, cylinder, bulk_kg_m3)
    required_peak_bar = max(
        motion.pressure_bar(position_m)
        for motion in sequence.values()
        for position_m in (0, motion.stroke_m)
    )
    if required_peak_bar > MAX_WORKING_BAR:
        return {
            "feasible": False, "reason": "working_pressure_limit",
            "required_peak_working_bar": required_peak_bar, "limit_working_bar": MAX_WORKING_BAR,
        }
    cycle = Cycle(max_L_min, dt_s, Accumulator() if accumulator else None)
    for key in ("pre_down", "regen", "press"):
        cycle.run_group([sequence[key]])
    cycle.switch("hold")
    cycle.idle(0.20)
    cycle.switch("unload")
    cycle.idle(0.15)
    for key in ("gate_open", "eject"):
        cycle.run_group([sequence[key]])
    tail = [sequence[key] for key in ("return", "gate_close", "pre_up")]
    if overlap:
        cycle.run_group(tail)
    else:
        for motion in tail:
            cycle.run_group([motion])
    hydraulic_s = cycle.time_s
    cycle.idle(feed_s)
    recharge_tail_s = 0.0
    if cycle.accumulator:
        while cycle.boost_L - cycle.charge_L > 1e-6:
            cycle.idle_step(dt_s)
            recharge_tail_s += dt_s
            if recharge_tail_s > 2:
                raise RuntimeError("accumulator did not recharge")
    return {
        "pump_max_flow_L_min": max_L_min, "peak_pump_flow_L_min": cycle.peak_pump_L_min,
        "feasible": True, "overlap": overlap, "accumulator": accumulator, "bulk_density_kg_m3": bulk_kg_m3,
        "feed_s": feed_s, "dt_s": dt_s, "cycle_s": cycle.time_s, "margin_to_6_s": 6.0 - cycle.time_s,
        "hydraulic_s": hydraulic_s, "briquettes_per_h": 3600 / cycle.time_s,
        "dose_throughput_kg_h": 3600 * model.dose_kg / cycle.time_s,
        "pump_oil_L": cycle.pump_oil_L, "peak_working_bar": max(cycle.peak_bar, required_peak_bar),
        "nominal_setpoint_bar": supply_bar(cylinder, model.nominal_N, "extend"),
        "shaft_energy_kJ": cycle.shaft_kJ, "peak_shaft_kW": cycle.peak_kW,
        "average_shaft_kW": cycle.shaft_kJ / cycle.time_s, "recharged_L": cycle.charge_L,
        "boost_L": cycle.boost_L, "extra_recharge_s": recharge_tail_s,
        "switch_count": len(cycle.switches), "switches": cycle.switches, "motion_events": cycle.events,
    }


def geometry(model, length_range_mm, min_released_density_kg_m3):
    recovered_m = model.die_length_m * (1 + model.axial_recovery)
    max_length_mm = length_range_mm[1]
    min_long_briquette_kg = model.section_m2 * max_length_mm / 1000 * min_released_density_kg_m3
    fill_capacity_kg = model.pre_section_m2 * (model.height_m + model.pre_travel_m) * 90
    return {
        "pre_density_kg_m3": model.pre_density_kg_m3,
        "single_load_at_90_kg_m3": {
            "max_fill_kg": fill_capacity_kg,
            "max_length_mm_at_minimum_released_density": (
                1000 * fill_capacity_kg / (model.section_m2 * min_released_density_kg_m3)
            ),
            "dose_lower_bound_kg_for_max_length": min_long_briquette_kg,
            "loose_volume_lower_bound_L_for_max_length": min_long_briquette_kg / 90 * M3_TO_L,
        },
        "dose_kg": model.dose_kg,
        "chamber_area_mm2": model.section_m2 * 1e6,
        "pre_window_area_mm2": model.pre_section_m2 * 1e6,
        "loose_fill": [
            {
                "bulk_density_kg_m3": density,
                "loose_volume_L": model.dose_kg / density * M3_TO_L,
                "total_height_mm": model.loose_height_m(density) * 1000,
                "height_above_channel_mm": (model.loose_height_m(density) - model.height_m) * 1000,
            }
            for density in (90, 160)
        ],
        "fill_height_from_floor_mm": (model.height_m + model.pre_travel_m) * 1000,
        "pre_required_travel_mm": model.pre_travel_m * 1000,
        "pre_chamber_volume_L": model.pre_section_m2 * (model.height_m + model.pre_travel_m) * M3_TO_L,
        "main_required_travel_mm": model.main_travel_m * 1000,
        "main_installed_stroke_mm": MAIN.stroke_mm,
        "main_stroke_ratio": MAIN.stroke_mm / (model.main_travel_m * 1000),
        "approach_mm": model.approach_m * 1000,
        "compression_mm": (model.press_end_m - model.approach_m) * 1000,
        "ejection_mm": (model.main_travel_m - model.press_end_m) * 1000,
        "in_die_length_mm": model.die_length_m * 1000,
        "in_die_density_kg_m3": model.in_die_kg_m3,
        "released_length_mm": recovered_m * 1000,
        "released_density_kg_m3": model.dose_kg / (model.section_m2 * recovered_m),
        "axial_recovery_fraction": model.axial_recovery,
        "control_dose_kg_at_released_lengths": [
            {"length_mm": length_mm, "dose_kg": model.section_m2 * length_mm / 1000 *
             model.in_die_kg_m3 / (1 + model.axial_recovery)}
            for length_mm in length_range_mm
        ],
        "punch_reference_to_inner_gate_mm": {
            "home": -(model.feed_length_m + model.approach_m) * 1000,
            "precompacted_contact": -model.feed_length_m * 1000,
            "compacted": -model.die_length_m * 1000,
            "ejection_complete": model.overtravel_m * 1000,
        },
    }


def force_balance(model, criteria):
    maximum_bar = criteria["C-HYD-01"]["max_working_bar"]
    # At limit, use the chosen rho-independent mechanical efficiency and losses.
    min_area_m2 = (model.nominal_N / MAIN.eta / BAR_PA - 3 * MAIN.rod_m2) / (maximum_bar - 4 - 3)
    return {
        "nominal_force_N": model.nominal_N,
        "criteria_exact_force_N": max(float(criteria["C-PFACE-01"]["nominal_force_min_N"]),
                                     criteria["C-PFACE-01"]["min_MPa"] * 1e6 * model.section_m2),
        "face_pressure_MPa": model.nominal_N / model.section_m2 / 1e6,
        "minimum_ideal_bore_mm": 2000 * sqrt(model.nominal_N / (pi * maximum_bar * BAR_PA)),
        "minimum_bore_for_loss_model_with_200_mm_rod_mm": 2000 * sqrt(min_area_m2 / pi),
        "area_ratio_cap_to_annulus": MAIN.cap_m2 / MAIN.annulus_m2,
        "cap_area_mm2": MAIN.cap_m2 * 1e6,
        "rod_area_mm2": MAIN.rod_m2 * 1e6,
        "annulus_area_mm2": MAIN.annulus_m2 * 1e6,
        "at_270_bar_available_force_N": MAIN.eta * BAR_PA * (266 * MAIN.cap_m2 - 3 * MAIN.annulus_m2),
        "ideal_relief_force_N": maximum_bar * MAIN.cap_m2 * BAR_PA,
        "candidates": [
            {
                "bore_mm": bore_mm, "rod_mm": rod_mm,
                "ideal_for_nominal_bar": model.nominal_N / cylinder.cap_m2 / BAR_PA,
                "nominal_supply_bar": supply_bar(cylinder, model.nominal_N, "extend"),
                "supply_for_1p5_MN_bar": supply_bar(cylinder, 1.5e6, "extend"),
                "working_limit_met": supply_bar(cylinder, model.nominal_N, "extend") <= maximum_bar,
            }
            for bore_mm, rod_mm in ((250, 180), (280, 200), (320, 220))
            for cylinder in (replace(MAIN, bore_mm=bore_mm, rod_mm=rod_mm),)
        ],
        "loss_sensitivity": [
            {"eta": eta, "nominal_supply_bar": supply_bar(replace(MAIN, eta=eta), model.nominal_N, "extend")}
            for eta in (0.90, 0.94, 0.97)
        ],
    }


def material(model):
    cases = []
    for exponent in (2, 3, 5, 6):
        case = replace(model, pressure_exponent=exponent)
        work_J = integrated_work_J(case.dose_kg, case.axial_pressure_Pa,
                                   case.pre_density_kg_m3, case.in_die_kg_m3)
        cases.append({
            "exponent": exponent,
            "axial_work_kJ": work_J / 1000,
            "p_at_1000_kg_m3_MPa": case.axial_pressure_Pa(1000) / 1e6,
            "pressure_curve": [
                {"density_kg_m3": density, "pressure_MPa": case.axial_pressure_Pa(density) / 1e6}
                for density in (case.pre_density_kg_m3, 600, 800, 1000, case.in_die_kg_m3)
            ],
        })
    return {
        "calibration_status": "No locally available primary pressure-density data with verified test conditions.",
        "literature_trigger_state": "unknown",
        "reference_pressure_at_1000_kg_m3_MPa": 80,
        "trigger_boundaries_at_1000_kg_m3_MPa": [40, 160],
        "m1_documented_work_kJ": 32,
        "m1_curve_reintegrated_work_kJ": m1_placeholder_work_J(model.dose_kg) / 1000,
        "axial_cases": cases,
        "pre_cases": [
            {
                "scale_MPa": scale_MPa, "bulk_density_kg_m3": density,
                "force_N": case.pre_force_N(model.pre_travel_m, density),
                "peak_supply_bar": motions(case, MAIN, density)["pre_down"].pressure_bar(model.pre_travel_m),
            }
            for scale_MPa in (2.0, model.pre_scale_MPa, 6.0)
            for density in (90, 160)
            for case in (replace(model, pre_scale_MPa=scale_MPa),)
        ],
    }


def minimum_flow(model, overlap, accumulator):
    """Integer L/min screening threshold for the nominal case."""
    low, high = 260, 500
    if simulate(model, max_L_min=high, overlap=overlap, accumulator=accumulator)["cycle_s"] > 6:
        return None
    while high - low > 1:
        mid = (low + high) // 2
        if simulate(model, max_L_min=mid, overlap=overlap, accumulator=accumulator)["cycle_s"] <= 6:
            high = mid
        else:
            low = mid
    return high


def motion_gate_rows(model):
    """Export conservative sequential pressure steps for the unmodified gate."""
    sequence = motions(model, MAIN, 90)
    rows = []
    gate_pump_eta = PUMP_ETA * (MOTOR_KW - IDLE_KW) / MOTOR_KW
    for name, motion in sequence.items():
        count = {"pre_down": 24, "regen": 16, "press": 24, "eject": 8}.get(name, 1)
        for index in range(count):
            start_m = motion.stroke_m * index / count
            end_m = motion.stroke_m * (index + 1) / count
            pressure_bar = max(motion.pressure_bar(start_m), motion.pressure_bar(end_m))
            max_pump_m3_s = min(360 / M3_S_TO_L_MIN, 1000 * MOTOR_KW * gate_pump_eta / (pressure_bar * BAR_PA))
            speed_mm_s = motion.speed_m_s * 1000 if motion.speed_m_s * motion.flow_area_m2 < max_pump_m3_s else "pump"
            final = index == count - 1
            rows.append({
                "name": f"{name} {index + 1}", "actuator": motion.actuator,
                "stroke_mm": (end_m - start_m) * 1000,
                "direction": "retract" if motion.mode == "retract" else "extend",
                "regeneration": motion.mode == "regen",
                "speed_mm_s": speed_mm_s,
                "pressure_bar": pressure_bar,
                "dwell_s": {"press": 0.55, "pre_up": 0.50}.get(name, 0) if final else 0,
                "continues": index > 0,
            })
            if final and name == "press":
                rows[-1]["press"] = True
    return rows


def gate_parameters(model, m1_params):
    """Use baseline schema metadata and X-1 lengths, forces and motion."""
    m1_params["description"] = "X-1 conditional example, 360 L/min, sequential equivalent for calc_gates"
    m1_params["main_cylinder"]["eta"] = MAIN.eta
    m1_params["chamber"].update({
        "in_die_density_kg_m3": model.in_die_kg_m3,
        "ejection_stroke_mm": (model.main_travel_m - model.press_end_m) * 1000,
    })
    m1_params["product"]["density_kg_m3"] = model.in_die_kg_m3 / (1 + model.axial_recovery)
    m1_params["precompaction"].update({
        "loose_fill_length_mm": (model.height_m + model.pre_travel_m) * 1000,
        "stroke_mm": model.pre_travel_m * 1000,
        "post_precompaction_density_kg_m3": model.pre_density_kg_m3,
    })
    m1_params["precompaction"]["cylinder"]["eta"] = PRE.eta
    m1_params["drive"]["slide_gate_cylinder"]["eta"] = GATE.eta
    m1_params["drive"]["eta"] = PUMP_ETA * (MOTOR_KW - IDLE_KW) / MOTOR_KW
    m1_params["cycle"] = motion_gate_rows(model)
    return m1_params


def check_model(model, results, geometrical, force, materials):
    assert abs(integrated_work_J(1, lambda _: 1e6, 500, 1000) - 1000) < 1e-9
    assert abs(geometrical["main_required_travel_mm"] - 210) < 1e-10
    assert geometrical["main_stroke_ratio"] < 1.3
    length_check = geometrical["single_load_at_90_kg_m3"]
    assert length_check["max_fill_kg"] < length_check["dose_lower_bound_kg_for_max_length"]
    assert abs(model.axial_force_N(model.press_end_m) - model.nominal_N) < 1e-6
    assert abs(force["criteria_exact_force_N"] - 1_500_300) < 1e-6
    assert force["candidates"][0]["ideal_for_nominal_bar"] > 300
    assert 32 < materials["m1_curve_reintegrated_work_kJ"] < 33
    assert all(r["peak_shaft_kW"] <= MOTOR_KW + 1e-9 and r["switch_count"] == 10 for r in results)
    for row in results:
        assert row["extra_recharge_s"] < 2
        assert abs(row["boost_L"] - row["recharged_L"]) < 0.00001
        phase = row["motion_events"]
        switches = {event["command"]: event["time_s"] for event in row["switches"]}
        assert switches["gate_open"] >= switches["unload"] + 0.25 - 1e-9
        assert phase["eject"]["start_s"] >= phase["gate_open"]["end_s"]
        assert phase["gate_close"]["start_s"] >= phase["return"]["start_s"] + 0.020 / 0.25
    checks = []
    for overlap, accumulator in ((False, False), (True, False), (True, True)):
        coarse = simulate(model, dt_s=0.005, overlap=overlap, accumulator=accumulator)
        medium = simulate(model, dt_s=0.0025, overlap=overlap, accumulator=accumulator)
        fine = simulate(model, dt_s=0.00125, overlap=overlap, accumulator=accumulator)
        assert abs(coarse["cycle_s"] - fine["cycle_s"]) < 0.05
        assert abs(medium["cycle_s"] - fine["cycle_s"]) < 0.03
        checks.append({
            "overlap": overlap, "accumulator": accumulator,
            "cycle_at_dt_0p005_s": coarse["cycle_s"],
            "cycle_at_dt_0p0025_s": medium["cycle_s"],
            "cycle_at_dt_0p00125_s": fine["cycle_s"],
            "absolute_coarse_fine_difference_s": abs(coarse["cycle_s"] - fine["cycle_s"]),
        })
    return checks


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    criteria = yaml.safe_load((ROOT / "ops/criteria/design_criteria.yaml").read_text(encoding="utf-8"))["criteria"]
    assert criteria["C-HYD-01"]["max_working_bar"] == MAX_WORKING_BAR
    m1_params = yaml.safe_load((ROOT / "design/params.m1.yaml").read_text(encoding="utf-8"))
    model = Model()
    geometrical = geometry(model, criteria["C-PROD-02"]["range_mm"], criteria["C-PROD-03"]["min_kg_m3"])
    force = force_balance(model, criteria)
    materials = material(model)
    runs = [
        simulate(model, max_L_min=flow_L_min, overlap=overlap, accumulator=accumulator)
        for flow_L_min in (260, 320, 360, 420)
        for overlap in (False, True)
        for accumulator in (False, True)
    ]
    stress_runs = {
        "bulk_160_kg_m3": simulate(model, overlap=True, accumulator=True, bulk_kg_m3=160),
        "feed_1p0_s": simulate(model, overlap=True, accumulator=True, feed_s=1.0),
        "feed_1p6_s": simulate(model, overlap=True, accumulator=True, feed_s=1.6),
        "approach_10_mm": simulate(replace(model, approach_m=0.010), overlap=True, accumulator=True),
        "bore_320_rod_220": simulate(model, overlap=True, accumulator=True,
                                     cylinder=replace(MAIN, bore_mm=320, rod_mm=220)),
        "pre_scale_6_MPa": simulate(replace(model, pre_scale_MPa=6), overlap=True, accumulator=True),
        "ejection_150_kN": simulate(replace(model, ejection_N=150000), overlap=True, accumulator=True),
        "axial_exponent_2": simulate(replace(model, pressure_exponent=2), overlap=True, accumulator=True),
        "axial_exponent_2_at_420_L_min": simulate(replace(model, pressure_exponent=2), max_L_min=420,
                                                     overlap=True, accumulator=True),
        "axial_exponent_5": simulate(replace(model, pressure_exponent=5), overlap=True, accumulator=True),
        "in_die_density_1180_kg_m3": simulate(replace(model, in_die_kg_m3=1180), overlap=True, accumulator=True),
    }
    assert not stress_runs["pre_scale_6_MPa"]["feasible"]
    feasible_runs = [run for run in [*runs, *stress_runs.values()] if run["feasible"]]
    convergence = check_model(model, feasible_runs, geometrical, force, materials)
    charge = Accumulator()
    results = {
        "geometry": geometrical, "force_balance": force, "material": materials,
        "gas_accumulator": {
            "shell_L": charge.shell_L, "precharge_bar": charge.precharge_bar,
            "cutoff_bar": charge.low_bar, "full_bar": charge.high_bar, "polytropic_exponent": charge.exponent,
            "usable_L": (charge.oil_at_m3(charge.high_bar) - charge.oil_at_m3(charge.low_bar)) * M3_TO_L,
            "max_delivery_L_min": charge.delivery_L_min,
        },
        "cycle_cases": runs, "sensitivity_at_360_L_min_with_overlap_and_accumulator": stress_runs,
        "flow_thresholds_at_0p5_s_feed": [
            {"overlap": overlap, "accumulator": accumulator,
             "screening_min_L_min": minimum_flow(model, overlap, accumulator)}
            for overlap in (False, True) for accumulator in (False, True)
        ],
        "convergence": convergence,
    }
    write_json(HERE / "x1_results.json", results)
    gate_input = gate_parameters(model, m1_params)
    (HERE / "params.x1.yaml").write_text(
        "# Conditional X-1 scenario. Sequential gate approximation. D0 unmodified.\n"
        "# Valve overlap, pump transient, oil elasticity and parallel recharge are in x1_calc.py.\n"
        + yaml.safe_dump(gate_input, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    serial, serial_acc, overlap, both = (run for run in runs if run["pump_max_flow_L_min"] == 360)
    metrics = {
        "main_bore_mm": MAIN.bore_mm, "main_rod_mm": MAIN.rod_mm,
        "nominal_force_N": force["nominal_force_N"], "face_pressure_MPa": force["face_pressure_MPa"],
        "nominal_supply_pressure_bar": force["candidates"][1]["nominal_supply_bar"],
        "main_required_travel_mm": geometrical["main_required_travel_mm"],
        "pre_required_travel_mm": geometrical["pre_required_travel_mm"],
        "precompaction_force_N_scenario": materials["pre_cases"][2]["force_N"],
        "main_compaction_work_kJ_scenario": materials["axial_cases"][1]["axial_work_kJ"],
        "axial_pressure_at_1000_kg_m3_MPa_scenario": materials["axial_cases"][1]["p_at_1000_kg_m3_MPa"],
        "m1_reintegrated_work_kJ": materials["m1_curve_reintegrated_work_kJ"],
        "released_density_kg_m3_scenario": geometrical["released_density_kg_m3"],
        "q_max_L_min": 360, "batch_feed_s": both["feed_s"],
        "cycle_serial_s": serial["cycle_s"], "cycle_serial_accumulator_s": serial_acc["cycle_s"],
        "cycle_overlap_s": overlap["cycle_s"], "cycle_overlap_accumulator_s": both["cycle_s"],
        "cycle_margin_with_overlap_and_accumulator_s": both["margin_to_6_s"],
        "max_feed_time_at_360_L_min_with_overlap_and_accumulator_s": 6 - both["hydraulic_s"],
        "single_load_max_briquette_length_at_90_kg_m3_mm": (
            geometrical["single_load_at_90_kg_m3"]["max_length_mm_at_minimum_released_density"]
        ),
        "main_peak_shaft_kW": both["peak_shaft_kW"], "main_avg_shaft_kW": both["average_shaft_kW"],
        "main_installed_kW": MOTOR_KW, "total_installed_kW_estimate": m1_params["drive"]["installed_kW"],
        "accumulator_boost_L": both["boost_L"], "throughput_kg_h_scenario": both["dose_throughput_kg_h"],
        "literature_trigger_state": materials["literature_trigger_state"],
    }
    write_json(ROOT / "metrics.json", metrics)


if __name__ == "__main__":
    main()

