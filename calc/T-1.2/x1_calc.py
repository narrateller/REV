"""X-1 hydraulic solver copied for the T-1.2 geometry and material curve."""

from dataclasses import dataclass, field
from math import ceil, exp, pi
from typing import Callable

from geometry import DUMP_TIMES_S, Material

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
    material: Material
    case: str
    dose_kg: float
    width_m: float
    height_m: float
    feed_length_m: float
    in_die_kg_m3: float
    pre_guide_force_N: float
    nominal_N: float
    overtravel_m: float
    approach_m: float
    pre_travel_m: float
    pre_cylinder: Cylinder
    gate_cylinder: Cylinder
    ejection_N: float = 100_000  # X-1 ejection resistance scenario.

    @property
    def section_m2(self):
        return self.width_m * self.height_m

    @property
    def pre_section_m2(self):
        return self.width_m * self.feed_length_m

    @property
    def die_length_m(self):
        return self.dose_kg / (self.section_m2 * self.in_die_kg_m3)

    @property
    def press_end_m(self):
        return self.approach_m + self.feed_length_m - self.die_length_m

    @property
    def main_travel_m(self):
        return self.approach_m + self.feed_length_m + self.overtravel_m

    def axial_force_N(self, travel_m, bulk_kg_m3):
        if travel_m < self.approach_m:
            return 0.0
        length_m = self.feed_length_m + self.approach_m - travel_m
        density_kg_m3 = self.dose_kg / (self.section_m2 * length_m)
        return self.section_m2 * self.material.face_MPa(
            density_kg_m3, bulk_kg_m3, self.case, dose_kg=self.dose_kg) * 1e6

    def pre_force_N(self, travel_m, bulk_kg_m3):
        height_m = self.height_m + self.pre_travel_m - travel_m
        density_kg_m3 = self.dose_kg / (self.pre_section_m2 * height_m)
        if density_kg_m3 <= bulk_kg_m3:
            return 0.0
        pressure_MPa = self.material.face_MPa(
            density_kg_m3, bulk_kg_m3, self.case,
            dose_kg=self.dose_kg, section_mm=[self.feed_length_m * 1000, self.width_m * 1000], wall_case=self.case)
        return pressure_MPa * self.pre_section_m2 * 1e6


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
    pre_cylinder, gate_cylinder = model.pre_cylinder, model.gate_cylinder
    pre = Motion("pre_down", "precompaction", pre_cylinder, "extend", model.pre_travel_m, 0.65,
                 lambda x: supply_bar(pre_cylinder, model.pre_force_N(x, bulk_kg_m3) + model.pre_guide_force_N, "extend"))

    def pressing_bar(x, mode):
        guide_load_N = 0 if mode == "extend" else 8000
        return supply_bar(cylinder, model.axial_force_N(x, bulk_kg_m3) + guide_load_N, mode)

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
        "gate_open": fixed_motion("gate_open", "slide_gate", gate_cylinder, "retract", .070, .25, 10000),
        "eject": Motion("eject", "main_cylinder", cylinder, "regen", model.main_travel_m - model.press_end_m,
                        0.24, ejection_bar),
        "return": fixed_motion("return", "main_cylinder", cylinder, "retract", model.main_travel_m, .25, 40000),
        "gate_close": fixed_motion("gate_close", "slide_gate", gate_cylinder, "extend", .070, .25, 8000),
        "pre_up": fixed_motion("pre_up", "precompaction", pre_cylinder, "retract", model.pre_travel_m, .65, 6000),
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
             bulk_kg_m3=90, dt_s=DT_S, cylinder, accumulator_shell_L=5.0):
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
    cycle = Cycle(max_L_min, dt_s, Accumulator(shell_L=accumulator_shell_L) if accumulator else None)
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
        "accumulator_shell_L": accumulator_shell_L if accumulator else 0, "dose_kg": model.dose_kg,
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


def make_model(material, results, row, params):
    axis, pre = results["axis"], results["precompaction"]
    width_mm, height_mm = results["main_section_mm"]
    main = params["main_cylinder"]
    gate = params["drive"]["slide_gate_cylinder"]
    model = Model(
        material, row["case"], row["dose_kg"], width_mm / 1000, height_mm / 1000,
        axis["transferred_fill_length_mm"] / 1000, row["in_die_density_kg_m3"], pre["guide_force_N"],
        row["face_MPa"] * width_mm * height_mm, axis["ejection_overtravel_mm"] / 1000,
        axis["approach_stroke_mm"] / 1000, pre["stroke_mm"] / 1000,
        Cylinder(pre["bore_mm"], pre["rod_mm"], pre["cylinder_stroke_mm"], pre["cylinder_eta"]),
        Cylinder(gate["bore_mm"], gate["rod_mm"], gate["stroke_mm"], 0.92),
    )
    return model, Cylinder(main["bore_mm"], main["rod_mm"], axis["main_installed_stroke_mm"], 0.94)


def converged_run(model, cylinder, density, feed_s, pump_L_min, limit_s):
    assert abs(model.axial_force_N(model.press_end_m, density) - model.nominal_N) < 1e-6
    settings = dict(max_L_min=pump_L_min, overlap=True, accumulator=True, feed_s=feed_s,
                    bulk_kg_m3=density, cylinder=cylinder)
    coarse, fine, refined = [simulate(model, dt_s=step_s, **settings)
                             for step_s in (DT_S, DT_S / 2, DT_S / 4)]
    assert coarse["feasible"] and fine["feasible"] and refined["feasible"]
    assert abs(fine["cycle_s"] - refined["cycle_s"]) < 0.03
    assert abs(coarse["cycle_s"] - fine["cycle_s"]) < 0.05
    for run in (coarse, fine, refined):
        check_sequence(run, model.overtravel_m)
    sequence = motions(model, cylinder, density)
    return {"case": model.case, **refined, "cycle_at_dt_0p005_s": coarse["cycle_s"],
            "cycle_at_dt_0p0025_s": fine["cycle_s"], "cycle_limit_pass": refined["cycle_s"] <= limit_s,
            "press_cap_stroke_mm": sequence["press"].stroke_m * 1000,
            "maximum_feed_time_s": limit_s - refined["hydraulic_s"]}


def run_cases(material, results, briquettes, params, criteria):
    pump_L_min = params["drive"]["pump_max_flow_L_min"]
    limit_s = criteria["C-PERF-01"]["max_cycle_s"]
    nominal_rows = [row for row in briquettes if row["pressure_basis"] == "nominal_force"]
    runs = []
    length_110_runs = []
    for row in nominal_rows:
        if row["case"] not in ("base", "high"):
            continue
        model, cylinder = make_model(material, results, row, params)
        density = row["bulk_density_kg_m3"]
        assert abs(model.main_travel_m * 1000 - results["axis"]["main_required_travel_mm"]) < 1e-9
        for feed_s in DUMP_TIMES_S:
            runs.append(converged_run(model, cylinder, density, feed_s, pump_L_min, limit_s))
        if row["case"] == "base":
            endpoint = row["length_endpoints"][-1]
            length_model, _ = make_model(material, results, {**row, **endpoint}, params)
            run = converged_run(length_model, cylinder, density, max(DUMP_TIMES_S), pump_L_min, limit_s)
            run["throughput_limit_pass"] = run["dose_throughput_kg_h"] >= criteria["C-PERF-01"]["min_kg_h"]
            length_110_runs.append(run)
    accumulator = Accumulator()
    main = params["main_cylinder"]
    max_force_N = (main["p_relief_bar"] - supply_bar(cylinder, 0, "extend")) * BAR_PA * cylinder.cap_m2 * cylinder.eta
    reserve_face_MPa = max_force_N / model.section_m2 / 1e6
    density_target_kg_m3 = criteria["C-PROD-03"]["min_kg_m3"]
    return {"accumulator_shell_L": accumulator.shell_L,
            "accumulator_usable_oil_L": (accumulator.oil_at_m3(accumulator.high_bar)
                                         - accumulator.oil_at_m3(accumulator.low_bar)) * M3_TO_L,
            "main_force_at_relief_with_losses_N": max_force_N, "reserve_face_MPa": reserve_face_MPa,
            "face_required_for_immediate_density_MPa": {
                case: material.face_MPa(density_target_kg_m3 * material.volume_ratio(case), density, case)
                for case in ("base", "low", "high")
            },
            "high_immediate_density_at_reserve_kg_m3": material.loaded_density_kg_m3(
                reserve_face_MPa, density, "high") / material.volume_ratio("high"),
            "runs": runs, "length_110_base_runs": length_110_runs}


def hydraulic_requirements(material, selected, common, base_rows, params, criteria):
    layout = {**common, "axis": selected["axis"], "precompaction": selected["precompaction"]}
    models = [(row["bulk_density_kg_m3"], *make_model(material, layout, row, params)) for row in base_rows]
    limit_s = criteria["C-PERF-01"]["max_cycle_s"]
    base_flow_L_min = params["drive"]["pump_max_flow_L_min"]
    flows_L_min = (base_flow_L_min, 380, 400, 420, 450, 475, 500, 525, 550)
    shells_L = (5, 7.5, 10, 15)
    results = []
    for shell_L in shells_L:
        accumulator = Accumulator(shell_L=shell_L)
        usable_oil_L = (accumulator.oil_at_m3(accumulator.high_bar)
                        - accumulator.oil_at_m3(accumulator.low_bar)) * M3_TO_L
        for flow_L_min in flows_L_min:
            settings = dict(max_L_min=flow_L_min, overlap=True, accumulator=True, feed_s=max(DUMP_TIMES_S),
                            accumulator_shell_L=shell_L, dt_s=DT_S / 4)
            runs = [simulate(model, bulk_kg_m3=density, cylinder=cylinder, **settings)
                    for density, model, cylinder in models]
            for (_, model, _), run in zip(models, runs, strict=True):
                check_sequence(run, model.overtravel_m)
            worst = max(runs, key=lambda run: run["cycle_s"])
            results.append({key: worst[key] for key in (
                "pump_max_flow_L_min", "peak_pump_flow_L_min", "accumulator_shell_L", "cycle_s", "boost_L",
                "recharged_L", "peak_shaft_kW", "peak_working_bar", "bulk_density_kg_m3")})
            results[-1]["accumulator_usable_oil_L"] = usable_oil_L
            results[-1]["cycle_limit_pass"] = worst["cycle_s"] <= limit_s
    return results


def check_sequence(run, overtravel_m):
    assert run["peak_shaft_kW"] <= MOTOR_KW + 1e-9 and run["switch_count"] == 10
    assert abs(run["boost_L"] - run["recharged_L"]) < 0.00001
    phase = run["motion_events"]
    switches = {event["command"]: event["time_s"] for event in run["switches"]}
    assert switches["gate_open"] >= switches["unload"] + 0.25 - 1e-9
    assert phase["eject"]["start_s"] >= phase["gate_open"]["end_s"]
    assert switches["gate_close"] >= phase["return"]["start_s"] + (overtravel_m + 0.010) / 0.25 - 1e-9


if __name__ == "__main__":
    from geometry import calculate

    material, results = calculate()
    for option in results["window_comparison"]:
        for run in option["cycle"]["runs"]:
            print(f"{option['window_axial_mm']:3} mm, {run['case']:4}, {run['bulk_density_kg_m3']:3} kg/m3, "
                  f"feed {run['feed_s']:.2f} s: {run['cycle_s']:.4f} s, {run['peak_working_bar']:.2f} bar")
