"""T-1.2b X-1 solver with T-1.4 drive and position-triggered overlap."""

from bisect import bisect_left
from dataclasses import dataclass, field, replace
from math import ceil, exp, pi, sqrt
from typing import Callable

BAR_PA = 1e5
M3_TO_L = 1000
M3_S_TO_L_MIN = 60000
DT_S = 0.0025
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


def supply_bar(cylinder, force_N, mode, losses_bar=(4.0, 3.0, 4.0)):
    """Required header pressure given inlet, tank, and regeneration drops."""
    inlet_bar, tank_bar, regen_bar = losses_bar
    area, opposite_area, backpressure_bar = {
        "extend": (cylinder.cap_m2, cylinder.annulus_m2, tank_bar),
        "retract": (cylinder.annulus_m2, cylinder.cap_m2, tank_bar),
        "regen": (cylinder.rod_m2, cylinder.annulus_m2, regen_bar),
    }[mode]
    return inlet_bar + (force_N / cylinder.eta / BAR_PA + backpressure_bar * opposite_area) / area


@dataclass(frozen=True)
class Model:
    material: object
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
    transfer_m: float = 0.0
    transfer_drag_N: float = 0.0
    cam_m: float = 0.0
    cam_force_N: float = 0.0
    cam_stem_speed_m_s: float = 0.0
    gate_travel_m: float = 0.070
    gate_speed_m_s: float = 0.25
    pre_return_force_N: float = 6000
    hold_supply_bar: float = 0.0
    takeoff_travel_m: float = 0.0
    losses_bar: tuple = (4.0, 3.0, 4.0)

    regen_switch_bar: float = 120.
    rapid_approach_m_s: float = .24
    rapid_eject_m_s: float = .24
    rapid_return_m_s: float = .25
    rapid_mass_kg: float = 0.
    rapid_accel_m_s2: float = 0.
    gate_mass_kg: float = 0.
    gate_accel_m_s2: float = 0.
    gate_added_weight_N: float = 0.
    gate_added_opening_drag_N: float = 0.

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
        return self.approach_m + self.transfer_m + self.feed_length_m - self.die_length_m

    @property
    def main_travel_m(self):
        return self.approach_m + self.transfer_m + self.feed_length_m + self.overtravel_m

    def axial_force_N(self, travel_m, bulk_kg_m3):
        if travel_m < self.approach_m:
            return 0.0
        compression_m = travel_m - self.approach_m - self.transfer_m
        length_m = self.feed_length_m - max(0.0, compression_m)
        density_kg_m3 = self.dose_kg / (self.section_m2 * length_m)
        if compression_m < 0:
            return self.transfer_drag_N
        material_force_N = self.section_m2 * self.material.face_MPa(
            density_kg_m3, bulk_kg_m3, self.case, dose_kg=self.dose_kg) * 1e6
        return max(self.transfer_drag_N, material_force_N)

    def pre_force_N(self, travel_m, bulk_kg_m3):
        height_m = self.height_m + max(0.0, self.pre_travel_m - travel_m)
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
    marker_m: float = 0.0
    speed_cap: Callable[[float], float] | None = None
    extra_fluid_drag_N: float = 0.
    entry_compress_m3: float = 0.
    entry_bar: float = 0.
    losses_bar: tuple = (4.0, 3.0, 4.0)

    accel_m_s2: float = 0.
    mass_kg: float = 0.

    def step_speed_m_s(self, position_m, prior_mean_m_s, step_s, accel_limit_m_s2):
        speed_m_s = self.speed_at_m_s(position_m)
        if not self.accel_m_s2:
            return speed_m_s
        accel = self.accel_m_s2
        remaining_m = self.stroke_m - position_m
        stop_time_s = sqrt(2 * remaining_m / accel)
        brake_mean_m_s = (accel * (stop_time_s - step_s / 2)
                          if stop_time_s > step_s else remaining_m / step_s)
        return min(speed_m_s, max(0., prior_mean_m_s + accel_limit_m_s2 * step_s), brake_mean_m_s)

    def speed_at_m_s(self, position_m):
        return self.speed_cap(position_m) if self.speed_cap else self.speed_m_s

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
            oil_m3 += 0.0004 + self.cylinder.annulus_m2 * (self.cylinder.stroke_mm / 1000 - self.offset_m - position_m)
        return oil_m3 * max(0.0, slope_Pa_m) / OIL_BULK_PA


def motions(model, cylinder, bulk_kg_m3, prefill=None):
    def required_header_bar(ram, force_N, mode):
        return supply_bar(ram, force_N, mode, model.losses_bar)

    pre_cylinder, gate_cylinder = model.pre_cylinder, model.gate_cylinder
    pre_stroke_m = model.pre_travel_m + model.cam_m

    def pre_down_bar(x):
        cam_force_N = model.cam_force_N if model.cam_m and x + 1e-10 >= model.pre_travel_m else 0.0
        return required_header_bar(pre_cylinder, model.pre_force_N(x, bulk_kg_m3) + model.pre_guide_force_N
                          + cam_force_N, "extend")

    def pre_up_bar(x):
        cam_force_N = model.cam_force_N if x + 1e-10 < model.cam_m else 0.0
        return required_header_bar(pre_cylinder, model.pre_return_force_N + cam_force_N, "retract")

    def pre_down_speed_m_s(x):
        return model.cam_stem_speed_m_s if model.cam_m and x + 1e-10 >= model.pre_travel_m else .65

    def pre_up_speed_m_s(x):
        return model.cam_stem_speed_m_s if x + 1e-10 < model.cam_m else .65

    pre = Motion("pre_down", "precompaction", pre_cylinder, "extend", pre_stroke_m, 0.65,
                 pre_down_bar, marker_m=model.pre_travel_m if model.cam_m else 0.0,
                 speed_cap=pre_down_speed_m_s, losses_bar=model.losses_bar)

    def pressing_bar(x, mode):
        guide_load_N = 0 if mode == "extend" else 8000
        return required_header_bar(cylinder, model.axial_force_N(x, bulk_kg_m3) + guide_load_N, mode)

    low_m, high_m = 0.0, model.press_end_m
    for _ in range(45):
        mid_m = (low_m + high_m) / 2
        if pressing_bar(mid_m, "regen") <= model.regen_switch_bar:
            low_m = mid_m
        else:
            high_m = mid_m
    regen_m = low_m

    def fixed_motion(name, actuator, ram, mode, stroke_m, speed_m_s, force_N):
        required_bar = required_header_bar(ram, force_N, mode)
        return Motion(name, actuator, ram, mode, stroke_m, speed_m_s, lambda _: required_bar, losses_bar=model.losses_bar)

    def ejection_bar(x):
        fraction_in_die = max(0, 1 - x / model.die_length_m)
        return required_header_bar(cylinder, 8000 + model.ejection_N * fraction_in_die, "regen")

    sequence = {"pre_down": pre}
    if model.hold_supply_bar:
        initial_bar = pre_down_bar(pre_stroke_m)
        pressurized_m3 = .0004 + pre_cylinder.cap_m2 * pre_stroke_m
        equivalent_travel_m = (pressurized_m3 * (model.hold_supply_bar - initial_bar) * BAR_PA
                               / OIL_BULK_PA / pre_cylinder.cap_m2)
        sequence["pre_hold_charge"] = Motion(
            "pre_hold_charge", "precompaction", pre_cylinder, "extend", equivalent_travel_m, .65,
            lambda x: initial_bar + (model.hold_supply_bar - initial_bar) * x / equivalent_travel_m)
    sequence.update({
        "regen": Motion("regen", "main_cylinder", cylinder, "regen", regen_m, 0.24,
                        lambda x: pressing_bar(x, "regen"), True, losses_bar=model.losses_bar),
        "press": Motion("press", "main_cylinder", cylinder, "extend", model.press_end_m - regen_m, 0.24,
                         lambda x: pressing_bar(regen_m + x, "extend"), True, regen_m, losses_bar=model.losses_bar),
        "gate_open": fixed_motion("gate_open", "slide_gate", gate_cylinder, "retract", model.gate_travel_m, model.gate_speed_m_s, 10000 + model.gate_added_weight_N + model.gate_added_opening_drag_N),
        "eject": Motion("eject", "main_cylinder", cylinder, "regen", model.main_travel_m - model.press_end_m,
                        0.24, ejection_bar, losses_bar=model.losses_bar),
        "return": fixed_motion("return", "main_cylinder", cylinder, "retract", model.main_travel_m, .25, 40000),
        "gate_close": fixed_motion("gate_close", "slide_gate", gate_cylinder, "extend", model.gate_travel_m, model.gate_speed_m_s, 8000 + model.gate_added_weight_N),
        "pre_up": Motion("pre_up", "precompaction", pre_cylinder, "retract", pre_stroke_m, .65,
                         pre_up_bar, marker_m=model.cam_m, speed_cap=pre_up_speed_m_s, losses_bar=model.losses_bar),
    })
    if model.takeoff_travel_m:
        gripper = Cylinder(32, 20, 15, .90)
        puller = Cylinder(40, 25, model.takeoff_travel_m * 1000, .90)
        for name, ram, mode, stroke_m, speed_m_s, force_N in (
            ("takeoff_grip", gripper, "extend", .015, .15, 3000),
            ("takeoff_pull", puller, "extend", model.takeoff_travel_m, .25, 6000),
            ("takeoff_release", gripper, "retract", .015, .15, 500),
            ("takeoff_reset", puller, "retract", model.takeoff_travel_m, .25, 1000),
        ):
            sequence[name] = fixed_motion(name, name, ram, mode, stroke_m, speed_m_s, force_N)
    if prefill:
        # Both auxiliary cylinders act on a guided crosshead, with the
        # main cap and annulus connected to the low-pressure header.
        pair = prefill["count"]
        driver = Cylinder(prefill["bore_mm"] * sqrt(pair), prefill["rod_mm"] * sqrt(pair),
                          cylinder.stroke_mm, prefill["eta"])
        drag_N = prefill["main_float_drag_kN"] * 1000
        return_drag_N = prefill.get("return_float_drag_kN", drag_N / 1000) * 1000
        lo_m, hi_m = 0., regen_m
        for _ in range(40):
            x_m = (lo_m + hi_m) / 2
            if model.axial_force_N(x_m, bulk_kg_m3) < prefill["switch_force_N"]:
                lo_m = x_m
            else:
                hi_m = x_m
        split_m = lo_m
        sequence["prefill"] = Motion(
            "prefill", "main_cylinder", driver, "extend", split_m, model.rapid_approach_m_s,
            lambda x: required_header_bar(driver, drag_N + model.axial_force_N(x, bulk_kg_m3), "extend"),
            extra_fluid_drag_N=drag_N, losses_bar=model.losses_bar)
        open_bar = prefill["float_gauge_bar"]
        closed_bar = pressing_bar(split_m, "regen")
        cap_m3 = .0008 + cylinder.cap_m2 * split_m
        rod_m3 = .0004 + cylinder.annulus_m2 * (cylinder.stroke_mm / 1000 - split_m)
        compression_m3 = (cap_m3 + rod_m3) * max(0., closed_bar - open_bar) * BAR_PA / OIL_BULK_PA
        sequence["regen"] = replace(sequence["regen"], stroke_m=regen_m - split_m,
                                    pressure_bar=lambda x: pressing_bar(x + split_m, "regen"),
                                    offset_m=split_m, entry_compress_m3=compression_m3, entry_bar=open_bar)
        sequence["eject"] = replace(
            sequence["eject"], cylinder=driver, mode="extend", extra_fluid_drag_N=drag_N,
            speed_m_s=model.rapid_eject_m_s,
            pressure_bar=lambda x: required_header_bar(
                driver, drag_N + model.ejection_N * max(0., 1 - x / model.die_length_m), "extend"))
        sequence["return"] = replace(fixed_motion("return", "main_cylinder", driver, "retract",
                                                  model.main_travel_m, model.rapid_return_m_s, 40000 + return_drag_N),
                                     extra_fluid_drag_N=return_drag_N)
        for name in ("prefill", "regen", "press", "eject", "return"):
            sequence[name] = replace(sequence[name], accel_m_s2=model.rapid_accel_m_s2,
                                     mass_kg=model.rapid_mass_kg)
    for name in ("gate_open", "gate_close"):
        sequence[name] = replace(sequence[name], accel_m_s2=model.gate_accel_m_s2, mass_kg=model.gate_mass_kg)
    return sequence


@dataclass
class Cycle:
    max_L_min: float
    dt_s: float
    accumulator: Accumulator | None
    pump: object = None
    switch_s: float = SWITCH_S
    boost_branches: tuple = ("return",)
    deficit_only: bool = False
    pump_tau_s: float = .035
    hp_accumulator: Accumulator | None = None
    hp_threshold_bar: float = 180.
    charge_drop_bar: float = 3.
    actual: tuple = ()
    charge_branch: str | None = None
    charge_ready_s: float = 0.
    guard_block_s: float = 0.
    peak_by_stage: dict = field(default_factory=dict)
    transition_trace: dict = field(default_factory=dict)
    entry_fill: dict = field(default_factory=dict)
    step_peak_kW: float = 0.
    approach_m: float = 0.
    peak_bypass_L_min: float = 0.
    hp_boost_L: float = 0.
    hp_charge_L: float = 0.
    time_s: float = 0.0
    flow_m3_s: float = 0.0
    shaft_kJ: float = 0.
    shaft_square_kW2_s: float = 0.0
    pump_oil_L: float = 0.0
    peak_kW: float = 0.0
    peak_bar: float = 0.0
    peak_pump_L_min: float = 0.0
    boost_L: float = 0.
    boost_L_by_motion: dict = field(default_factory=dict)
    lp_charge_s_by_window: dict = field(default_factory=dict)
    idle_window: str = "switch"
    lp_limit_m3_by_window: dict = field(default_factory=dict)
    charge_L: float = 0.0
    switches: list = field(default_factory=list)
    events: dict = field(default_factory=dict)
    stages: dict = field(default_factory=dict)
    energy: dict = field(default_factory=lambda: dict(header_kJ=0., bypass_kJ=0., charge_kJ=0.,
        boost_kJ=0., hp_charge_kJ=0., hp_boost_kJ=0., hp_gas_in_kJ=0., hp_gas_out_kJ=0.,
         sharing_kJ=0., valves_kJ=0., cylinder_friction_kJ=0., prefill_float_kJ=0.))

    def __post_init__(self):
        if self.pump and not self.actual:
            self.actual = (0.,) * len(self.pump.names)

    def steady_capacity_m3_s(self, pressure_bar):
        if self.pump:
            flow_m3_s = self.pump.capacity_L_min(pressure_bar) / M3_S_TO_L_MIN
        else:
            flow_m3_s = 1000 * (MOTOR_KW - IDLE_KW) * PUMP_ETA / (pressure_bar * BAR_PA)
        return min(self.max_L_min / M3_S_TO_L_MIN, flow_m3_s)

    def ideal_capacity_m3_s(self, header_bar, demand_m3_s, step_s):
        # Keep the T-1.2b comparator reproducible.
        cap_m3_s = min(self.steady_capacity_m3_s(header_bar), demand_m3_s)
        rise_fraction = 1 - exp(-step_s / self.pump_tau_s)
        return min(cap_m3_s, self.flow_m3_s + (cap_m3_s - self.flow_m3_s) * rise_fraction)

    def pressure_envelope(self, motion):
        """Latest permissible displacement on a max-speed position trajectory."""
        if not self.pump or not self.pump.anticipation:
            return None
        count = ceil(motion.stroke_m / .00025)
        dx_m = motion.stroke_m / count
        positions_m = [i * dx_m for i in range(count + 1)]
        pressures_bar = [motion.pressure_bar(x) for x in positions_m]
        travel_time_s = [0.]
        boost_L_min = 0.
        if self.accumulator and motion.name in self.boost_branches:
            boost_L_min += self.accumulator.delivery_L_min
        if self.hp_accumulator and motion.name == "press":
            boost_L_min += self.hp_accumulator.delivery_L_min
        for lower_bar in map(min, pressures_bar, pressures_bar[1:]):
            # Even at 100% efficiency the guarded shaft cannot displace
            # more fluid than this. Ignore compression for the speed bound.
            pump_L_min = min(self.max_L_min, 600 * self.pump.limit_kW / lower_bar)
            speed_m_s = min(motion.speed_m_s, (pump_L_min + boost_L_min)
                            / (M3_S_TO_L_MIN * motion.flow_area_m2))
            travel_time_s.append(travel_time_s[-1] + dx_m / speed_m_s)
        slew_s = self.pump.slew(50., False)
        envelope = []
        for i in range(count, -1, -1):
            j = min(count, bisect_left(travel_time_s, travel_time_s[i] + self.pump.control_delay_s, lo=i))
            nearby_bar = max(pressures_bar[i:j + 1])
            allowed = self.pump.fractions(nearby_bar, self.max_L_min)
            if envelope:
                available_s = travel_time_s[i + 1] - travel_time_s[i]
                allowed = tuple(min(limit, following + slew_s * available_s)
                                for limit, following in zip(allowed, envelope[-1]))
            envelope.append(allowed)
        return dx_m, list(reversed(envelope))

    def step_pump(self, step_s, header_bar, demand_m3_s, stage, envelope=None):
        requested_L_min = min(self.max_L_min, demand_m3_s * M3_S_TO_L_MIN)
        goals = self.pump.fractions(header_bar, requested_L_min, self.actual) if header_bar else (0.,) * len(self.actual)
        if envelope is not None:
            goals = tuple(min(goal, ceiling) for goal, ceiling in zip(goals, envelope))
        connected = self.pump.connected(header_bar, self.actual, goals)
        _, start_kW, _ = self.pump.instant(header_bar, self.actual, connected)
        resulting = self.pump.update(header_bar, self.actual, goals, step_s)
        _, end_kW, _ = self.pump.instant(header_bar, resulting, connected)
        peak_kW = max(start_kW, end_kW)
        if self.pump.anticipation and peak_kW > self.pump.limit_kW + 1e-7:
            # Hold the consumer with its check closed and unload. Recheck the
            # measured swash angles before admitting load on the next scan.
            self.guard_block_s += step_s
            return self.step_pump(step_s, 0., 0., stage + "/interlock")
        mean = tuple(
            y + (x - y) * abs(x - y) / (2 * step_s * self.pump.slew(header_bar, y >= x))
            for x, y in zip(self.actual, resulting)
        )
        previous = self.actual
        self.actual = resulting
        raw_L_min, shaft_kW, bypass_kW = self.pump.instant(header_bar, mean, connected)
        # Single PV180: affine shaft demand until the swash target, then constant.
        assert len(mean) == 1
        ramp_fraction = min(1., abs(resulting[0] - previous[0])
                            / (step_s * self.pump.slew(header_bar, resulting[0] >= previous[0])))
        mean_square_kW2 = (ramp_fraction * (start_kW**2 + start_kW * end_kW + end_kW**2) / 3
                           + (1 - ramp_fraction) * end_kW**2)
        useful_L_min = min(raw_L_min, requested_L_min)
        bypass_kW += (raw_L_min - useful_L_min) * header_bar / 600
        self.energy["bypass_kJ"] += bypass_kW * step_s
        raw_bypass_L_min = raw_L_min - useful_L_min + sum(
            x * self.pump.section(name, standby).flow_L_min
            for x, name, standby, active in zip(mean, self.pump.names, self.pump.standby_pressures_bar, connected)
            if not active
        )
        self.peak_bypass_L_min = max(self.peak_bypass_L_min, raw_bypass_L_min)
        self.advance(step_s, header_bar, useful_L_min / M3_S_TO_L_MIN, shaft_kW, peak_kW, stage,
                     mean_square_kW2)
        return useful_L_min / M3_S_TO_L_MIN

    def advance(self, step_s, header_bar, pump_m3_s, shaft_kW=None, peak_kW=None, stage="idle",
                mean_square_kW2=None):
        self.time_s += step_s
        self.flow_m3_s = pump_m3_s
        hydraulic_kW = header_bar * BAR_PA * pump_m3_s / 1000
        self.energy["header_kJ"] += hydraulic_kW * step_s
        if shaft_kW is None:
            shaft_kW = IDLE_KW + hydraulic_kW / PUMP_ETA
            peak_kW = shaft_kW
        self.shaft_kJ += shaft_kW * step_s
        self.shaft_square_kW2_s += step_s * (shaft_kW**2 if mean_square_kW2 is None else mean_square_kW2)
        self.pump_oil_L += pump_m3_s * step_s * M3_TO_L
        self.peak_kW = max(self.peak_kW, peak_kW)
        self.step_peak_kW = peak_kW
        if peak_kW > self.peak_by_stage.get(stage, {}).get("shaft_kW", 0.):
            self.peak_by_stage[stage] = dict(shaft_kW=peak_kW, header_bar=header_bar,
                                            time_s=self.time_s - step_s)
        self.peak_bar = max(self.peak_bar, header_bar)
        self.peak_pump_L_min = max(self.peak_pump_L_min, pump_m3_s * M3_S_TO_L_MIN)

    def move_pump(self, step_s, header_bar, demand_m3_s, stage, envelope=None):
        if self.pump:
            return self.step_pump(step_s, header_bar, demand_m3_s, stage, envelope)
        flow = self.ideal_capacity_m3_s(header_bar, demand_m3_s, step_s) if header_bar else 0.
        self.advance(step_s, header_bar, flow, stage=stage)
        return flow

    def idle_step(self, step_s, *, allow_charge=True):
        if allow_charge:
            for branch, accumulator in (("lp", self.accumulator), ("hp", self.hp_accumulator)):
                if accumulator and accumulator.oil_at_m3(accumulator.high_bar) - accumulator.oil_m3 > 1e-10:
                    if self.pump and self.charge_branch != branch:
                        self.charge_branch = branch
                        self.charge_ready_s = self.time_s + self.switch_s
                    if not self.pump or self.time_s + 1e-10 >= self.charge_ready_s:
                        self.charge_accumulator(branch, accumulator, step_s)
                        return
                    break
        else:
            self.charge_branch = None
        self.move_pump(step_s, 0., 0., "neutral")

    def charge_accumulator(self, branch, accumulator, step_s):
        fill_m3 = accumulator.oil_at_m3(accumulator.high_bar) - accumulator.oil_m3
        gas_start_bar = accumulator.pressure_bar
        header_bar = gas_start_bar + self.charge_drop_bar
        demand_m3_s = fill_m3 / step_s
        ceiling = None
        if self.pump and self.pump.anticipation:
            forecast_m3 = self.pump.capacity_L_min(header_bar) * self.pump.control_delay_s / M3_S_TO_L_MIN
            future_oil_m3 = min(accumulator.oil_m3 + forecast_m3, accumulator.oil_at_m3(accumulator.high_bar))
            gas_fraction = 1 - future_oil_m3 * M3_TO_L / accumulator.shell_L
            future_bar = (accumulator.precharge_bar + 1) / gas_fraction**accumulator.exponent - 1
            ceiling = self.pump.fractions(future_bar + self.charge_drop_bar, self.max_L_min, self.actual)
        flow_m3_s = self.move_pump(step_s, header_bar, demand_m3_s, branch + "_charge", ceiling)
        volume_m3 = flow_m3_s * step_s
        accumulator.oil_m3 += volume_m3
        charged_kJ = volume_m3 * header_bar * BAR_PA / 1000
        if branch == "lp":
            self.charge_L += volume_m3 * M3_TO_L
            if volume_m3:
                self.lp_charge_s_by_window[self.idle_window] = self.lp_charge_s_by_window.get(self.idle_window, 0.) + step_s
            self.energy["charge_kJ"] += charged_kJ
        else:
            self.hp_charge_L += volume_m3 * M3_TO_L
            self.energy["hp_charge_kJ"] += charged_kJ
            self.energy["hp_gas_in_kJ"] += volume_m3 * (gas_start_bar + accumulator.pressure_bar) * BAR_PA / 2000

    def idle(self, duration_s):
        steps = ceil(duration_s / self.dt_s)
        for _ in range(steps):
            self.idle_step(duration_s / steps)

    def switch(self, name):
        self.switches.append({"command": name, "time_s": self.time_s})
        self.idle(self.switch_s)

    def run_group(self, group, *, gate_clear_return_m=0.0, unlock_eject_m=None):
        """Independent spool delays, common pump pressure, main → gate → pre priority."""
        start_s = self.time_s
        positions_m = dict.fromkeys((motion.name for motion in group), 0.0)
        commanded = {}
        prior_mean_m_s = {m.name: -m.accel_m_s2 * self.dt_s / 2 for m in group}
        envelopes = {motion.name: self.pressure_envelope(motion) for motion in group}
        self.charge_branch = None
        group_name = "+".join(m.name for m in group)
        while any(positions_m[m.name] < m.stroke_m - 1e-10 for m in group):
            if self.time_s - start_s > 15:
                raise RuntimeError("hydraulic stage timeout")
            step_s = self.dt_s
            demands = []
            filled_entry = False
            for motion in group:
                name = motion.name
                position_m = positions_m[name]
                remaining_m = motion.stroke_m - position_m
                if remaining_m <= 1e-10:
                    continue
                if name not in commanded:
                    # Command only after the punch clears the inner plane by 10 mm.
                    if (name == "gate_close" and "return" in positions_m
                            and positions_m["return"] + 1e-10 < gate_clear_return_m):
                        continue
                    if name == "return" and "eject" in positions_m:
                        if positions_m["eject"] < group[0].stroke_m - 1e-10:
                            continue
                    if name == "pre_up" and unlock_eject_m is not None:
                        if positions_m["eject"] < unlock_eject_m - 1e-10:
                            continue
                    commanded[name] = self.time_s
                    self.switches.append({"command": name, "time_s": self.time_s})
                if self.time_s - commanded[name] + 1e-10 < self.switch_s:
                    continue
                if motion.entry_compress_m3 and name not in self.entry_fill:
                    assert len(group) == 1
                    self.fill_closed_main_ports(motion)
                    filled_entry = True
                    break
                pressure_bar = motion.pressure_bar(position_m)
                accel_limit_m_s2 = motion.accel_m_s2
                if motion.mass_kg and accel_limit_m_s2:
                    gain_bar_per_m_s2 = motion.mass_kg / (motion.cylinder.eta * motion.flow_area_m2 * BAR_PA)
                    # Meter positive acceleration inside the pressure ceiling,
                    # especially when approaching the 300 bar press endpoint.
                    accel_limit_m_s2 = min(accel_limit_m_s2, max(0., MAX_WORKING_BAR - pressure_bar) / gain_bar_per_m_s2)
                step_speed_m_s = motion.step_speed_m_s(position_m, prior_mean_m_s[name], step_s, accel_limit_m_s2)
                if accel_limit_m_s2:
                    accel_m_s2 = max(0., step_speed_m_s - max(0., prior_mean_m_s[name])) / step_s
                    pressure_bar += gain_bar_per_m_s2 * accel_m_s2
                area = motion.flow_area_m2 + motion.storage_area_m2(position_m)
                demand_m3_s = min(step_speed_m_s, remaining_m / step_s) * area
                demands.append((motion, area, pressure_bar, demand_m3_s))
            if filled_entry:
                continue
            if not demands:
                self.idle_step(step_s, allow_charge=not self.pump)
                continue

            header_bar = max(pressure for _, _, pressure, _ in demands)
            if self.pump:
                header_bar = max(self.pump.standby_bar, header_bar)
            boosts = self.discharge_m3_s(demands, header_bar, step_s)
            demand_m3_s = sum(item[3] for item in demands) - sum(boosts.values())
            limiting_motion = max(demands, key=lambda item: item[2])[0]
            envelope = None
            if self.pump and self.pump.anticipation:
                # Pre-limit during the valve-confirmation time for another
                # branch of this group that is about to join the header.
                for motion in group:
                    name = motion.name
                    if name not in commanded or positions_m[name] >= motion.stroke_m - 1e-10:
                        continue
                    dx_m, ceilings = envelopes[name]
                    ceiling = ceilings[min(len(ceilings) - 1, int(positions_m[name] / dx_m))]
                    if self.time_s < commanded[name] + self.switch_s:
                        time_left_s = commanded[name] + self.switch_s - self.time_s
                        ceiling = tuple(x + self.pump.slew(50., False) * time_left_s for x in ceiling)
                    envelope = ceiling if envelope is None else tuple(map(min, envelope, ceiling))
            pump_m3_s = self.move_pump(step_s, header_bar, demand_m3_s, limiting_motion.name, envelope)
            x_m = positions_m[limiting_motion.name] + limiting_motion.offset_m
            transition = None
            if limiting_motion.name in ("regen", "prefill") and abs(x_m - self.approach_m) <= .005:
                transition = "contact_x_plus_minus_5_mm"
            if limiting_motion.name == "press" and positions_m["press"] <= .005:
                transition = "direct_press_first_5_mm"
            if transition and self.step_peak_kW > self.transition_trace.get(transition, {}).get("shaft_kW", 0.):
                self.transition_trace[transition] = dict(
                    x_mm=x_m * 1000, header_demand_bar=header_bar, shaft_kW=self.step_peak_kW,
                    time_s=self.time_s, displacement_fraction=self.actual,
                )
            available_m3_s = pump_m3_s
            for motion, area_m2, pressure_bar, demand_m3_s in demands:
                boost = boosts.get(motion.name, 0.0)
                flow_m3_s = min(demand_m3_s - boost, available_m3_s)
                available_m3_s -= flow_m3_s
                position_m = positions_m[motion.name]
                prior_mean_m_s[motion.name] = (flow_m3_s + boost) / area_m2
                positions_m[motion.name] += prior_mean_m_s[motion.name] * step_s
                if flow_m3_s + boost > 0:
                    travel_m = positions_m[motion.name] - position_m
                    self.record_motion_losses(motion, travel_m, pressure_bar, header_bar, flow_m3_s * step_s)
                    event = self.events.setdefault(
                        motion.name, {"start_s": self.time_s - step_s, "peak_supply_bar": 0.0}
                    )
                    event["peak_supply_bar"] = max(event["peak_supply_bar"], pressure_bar)
                    event["end_s"] = self.time_s
                    event["peak_speed_m_s"] = max(event.get("peak_speed_m_s", 0.), prior_mean_m_s[motion.name])
                    if motion.name == "eject" and unlock_eject_m is not None and positions_m[motion.name] >= unlock_eject_m:
                        event.setdefault("unlock_clear_s", self.time_s)
                    if motion.name == "return" and positions_m[motion.name] >= gate_clear_return_m:
                        event.setdefault("gate_clear_s", self.time_s)
                    if motion.marker_m and position_m + 1e-10 < motion.marker_m <= positions_m[motion.name] + 1e-10:
                        event["marker_s"] = self.time_s
        self.stages[group_name] = [start_s, self.time_s]

    def fill_closed_main_ports(self, motion):
        """Raise oil pressure after closing the SFA and before the ram moves."""
        start_s = self.time_s
        delivered_m3 = 0.
        required_m3 = motion.entry_compress_m3
        final_bar = motion.pressure_bar(0.)
        while delivered_m3 < required_m3 - 1e-12:
            pressure_bar = motion.entry_bar + (final_bar - motion.entry_bar) * delivered_m3 / required_m3
            pressure_bar = max(pressure_bar, self.pump.standby_bar)
            remaining_m3_s = (required_m3 - delivered_m3) / self.dt_s
            # Reserve enough torque for the full load before pressurizing
            # the two closed ports.
            ceiling = self.pump.fractions(final_bar, self.max_L_min) if self.pump.anticipation else None
            delivered_m3 += self.move_pump(self.dt_s, pressure_bar, remaining_m3_s,
                                           "close_prefill_and_compress", ceiling) * self.dt_s
            if self.time_s - start_s > 1.:
                raise RuntimeError("prefill-to-regeneration pressure build timeout")
        self.entry_fill[motion.name] = dict(compressed_oil_L=delivered_m3 * M3_TO_L,
                                           time_s=self.time_s - start_s)

    def record_motion_losses(self, motion, travel_m, branch_bar, header_bar, pumped_m3):
        ram = motion.cylinder
        inlet_bar, tank_bar, regen_bar = motion.losses_bar
        backpressure_bar, opposite_m2 = {
            "extend": (tank_bar, ram.annulus_m2), "retract": (tank_bar, ram.cap_m2),
            "regen": (regen_bar, ram.annulus_m2)
        }[motion.mode]
        valve_bar_m2 = inlet_bar * motion.flow_area_m2 + backpressure_bar * opposite_m2
        force_before_friction_N = max(0, branch_bar * motion.flow_area_m2 - valve_bar_m2) * BAR_PA
        self.energy["valves_kJ"] += valve_bar_m2 * BAR_PA * travel_m / 1000
        self.energy["cylinder_friction_kJ"] += force_before_friction_N * (1 - ram.eta) * travel_m / 1000
        self.energy["prefill_float_kJ"] += motion.extra_fluid_drag_N * travel_m / 1000
        self.energy["sharing_kJ"] += (header_bar - branch_bar) * BAR_PA * pumped_m3 / 1000

    def discharge_m3_s(self, demands, header_bar, step_s):
        accumulator = self.accumulator
        if self.hp_accumulator and len(demands) == 1 and demands[0][0].name == "press":
            _, _, pressure_bar, demand_m3_s = demands[0]
            if pressure_bar >= self.hp_threshold_bar:
                acc = self.hp_accumulator
                gas_start_bar = acc.pressure_bar
                available_m3 = max(0., acc.oil_m3 - acc.oil_at_m3(max(acc.low_bar, pressure_bar + self.charge_drop_bar)))
                boost_m3_s = min(available_m3 / step_s, acc.delivery_L_min / M3_S_TO_L_MIN, demand_m3_s)
                volume_m3 = boost_m3_s * step_s
                acc.oil_m3 -= volume_m3
                self.hp_boost_L += volume_m3 * M3_TO_L
                self.energy["hp_boost_kJ"] += volume_m3 * pressure_bar * BAR_PA / 1000
                self.energy["hp_gas_out_kJ"] += volume_m3 * (gas_start_bar + acc.pressure_bar) * BAR_PA / 2000
                return {"press": boost_m3_s}
        if accumulator is None:
            return {}
        remaining_m3_s = accumulator.delivery_L_min / M3_S_TO_L_MIN
        if self.deficit_only:
            deficit_m3_s = sum(item[3] for item in demands) - self.steady_capacity_m3_s(header_bar)
            remaining_m3_s = min(remaining_m3_s, max(0, deficit_m3_s))
        boosts = {}
        for motion, _, pressure_bar, demand_m3_s in demands:
            if motion.name not in self.boost_branches:
                continue
            # Local reduction/check valves separate the accumulator from the header.
            delivery_bar = max(accumulator.low_bar, pressure_bar + self.charge_drop_bar)
            available_m3 = max(0, accumulator.oil_m3 - accumulator.oil_at_m3(delivery_bar))
            if self.lp_limit_m3_by_window:
                window = "pre_down" if motion.name == "pre_down" else "tail"
                deficit_m3 = accumulator.oil_at_m3(accumulator.high_bar) - accumulator.oil_m3
                available_m3 = min(available_m3, max(0., self.lp_limit_m3_by_window[window] - deficit_m3))
            boost_m3_s = min(remaining_m3_s, available_m3 / step_s, demand_m3_s)
            accumulator.oil_m3 -= boost_m3_s * step_s
            remaining_m3_s -= boost_m3_s
            self.boost_L += boost_m3_s * step_s * M3_TO_L
            if boost_m3_s:
                self.boost_L_by_motion[motion.name] = self.boost_L_by_motion.get(motion.name, 0.) + boost_m3_s * step_s * M3_TO_L
            self.energy["boost_kJ"] += pressure_bar * BAR_PA * boost_m3_s * step_s / 1000
            boosts[motion.name] = boost_m3_s
        return boosts


def simulate(model, *, max_L_min=360, overlap=False, accumulator=False, feed_s=0.50,
             bulk_kg_m3=90, dt_s=DT_S, cylinder, accumulator_shell_L=5.0,
             pump=None, switch_s=SWITCH_S, hold_s=.30, unload_s=.25, unlock_x_m=None,
             accumulator_kwargs=None, boost_branches=("return",), deficit_only=False,
             pump_tau_s=.035, prefill=None, hp_accumulator_kwargs=None, hp_threshold_bar=180.,
             charge_drop_bar=3., initial_swash=(), lp_window_guard=False):
    assert 0 < dt_s <= DT_S
    sequence = motions(model, cylinder, bulk_kg_m3, prefill)
    required_peak_bar = max(
        motion.pressure_bar(position_m)
        for motion in sequence.values()
        for position_m in (0, motion.stroke_m)
    )
    if required_peak_bar > MAX_WORKING_BAR + 1e-9:
        return {
            "feasible": False, "reason": "working_pressure_limit",
            "required_peak_working_bar": required_peak_bar, "limit_working_bar": MAX_WORKING_BAR,
        }
    charge = Accumulator(shell_L=accumulator_shell_L, **(accumulator_kwargs or {})) if accumulator else None
    hp_charge = Accumulator(**hp_accumulator_kwargs) if hp_accumulator_kwargs else None
    cycle = Cycle(max_L_min, dt_s, charge, pump, switch_s, boost_branches, deficit_only,
                  pump_tau_s, hp_charge, hp_threshold_bar, charge_drop_bar,
                  actual=initial_swash, approach_m=model.approach_m)
    if lp_window_guard:
        # Budget only oil chargeable at the worst pressure and with a stationary swash.
        peak_charge_bar = charge.high_bar + charge_drop_bar
        steady_m3_s = cycle.steady_capacity_m3_s(peak_charge_bar)
        rise_s = 1 / pump.slew(pump.standby_bar, True)
        for name, window_s in (("pre_down", hold_s + unload_s), ("tail", feed_s)):
            flow_s = max(0., window_s - switch_s - 2 * dt_s)
            ramp_s = min(flow_s, rise_s)
            equivalent_flow_s = .5 * ramp_s**2 / rise_s + flow_s - ramp_s
            cycle.lp_limit_m3_by_window[name] = steady_m3_s * equivalent_flow_s
    press_keys = ["pre_down"]
    if model.hold_supply_bar:
        press_keys.append("pre_hold_charge")
    if prefill:
        press_keys.append("prefill")
    press_keys.extend(["regen", "press"])
    for key in press_keys:
        cycle.run_group([sequence[key]])
    for name, duration_s in (("hold", hold_s), ("unload", unload_s)):
        start_s = cycle.time_s
        cycle.idle_window = name
        cycle.switch(name)
        cycle.idle(duration_s - switch_s)
        cycle.stages[name] = [start_s, cycle.time_s]
    cycle.run_group([sequence["gate_open"]])
    early_unlock = unlock_x_m is not None and overlap and not model.takeoff_travel_m
    if not early_unlock:
        cycle.run_group([sequence["eject"]])
    if model.takeoff_travel_m:
        for key in ("takeoff_grip", "takeoff_pull", "takeoff_release"):
            cycle.run_group([sequence[key]])
    tail = [sequence[key] for key in ("return", "gate_close", "pre_up")]
    if model.takeoff_travel_m:
        tail.append(sequence["takeoff_reset"])
    if overlap:
        if early_unlock:
            tail.insert(0, sequence["eject"])
        cycle.run_group(tail, gate_clear_return_m=model.overtravel_m + .010,
                        unlock_eject_m=unlock_x_m - model.press_end_m if early_unlock else None)
    else:
        for motion in tail:
            cycle.run_group([motion])
    hydraulic_s = cycle.time_s
    cycle.idle_window = "feed"
    cycle.idle(feed_s)
    cycle.idle_window = "after_feed"
    cycle.stages["feed"] = [hydraulic_s, cycle.time_s]
    recharge_tail_s = 0.0
    if cycle.accumulator or cycle.hp_accumulator:
        while (cycle.boost_L - cycle.charge_L > 1e-6
               or cycle.hp_boost_L - cycle.hp_charge_L > 1e-6):
            cycle.idle_step(dt_s)
            recharge_tail_s += dt_s
            if recharge_tail_s > 8:
                raise RuntimeError("accumulator did not recharge")
    return {
        "pump_max_flow_L_min": max_L_min, "peak_pump_flow_L_min": cycle.peak_pump_L_min,
        "feasible": True, "overlap": overlap, "accumulator": accumulator, "bulk_density_kg_m3": bulk_kg_m3,
        "accumulator_shell_L": accumulator_shell_L if accumulator else 0, "dose_kg": model.dose_kg,
        "feed_s": feed_s, "dt_s": dt_s, "cycle_s": cycle.time_s, "margin_to_6_s": 6.0 - cycle.time_s,
        "hydraulic_s": hydraulic_s, "briquettes_per_h": 3600 / cycle.time_s,
        "dose_throughput_kg_h": 3600 * model.dose_kg / cycle.time_s,
        "pump_oil_L": cycle.pump_oil_L, "peak_working_bar": max(cycle.peak_bar, required_peak_bar),
        "nominal_setpoint_bar": supply_bar(cylinder, model.nominal_N, "extend", model.losses_bar),
        "shaft_energy_kJ": cycle.shaft_kJ, "peak_shaft_kW": cycle.peak_kW,
        "average_shaft_kW": cycle.shaft_kJ / cycle.time_s,
        "shaft_square_kW2_s": cycle.shaft_square_kW2_s,
        "rms_shaft_kW": sqrt(cycle.shaft_square_kW2_s / cycle.time_s), "recharged_L": cycle.charge_L,
        "boost_L": cycle.boost_L, "extra_recharge_s": recharge_tail_s,
        "boost_L_by_motion": cycle.boost_L_by_motion, "lp_charge_s_by_window": cycle.lp_charge_s_by_window,
        "net_lp_oil_balance_L": cycle.boost_L - cycle.charge_L,
        "lp_deficit_limit_L_by_window": {key: volume_m3 * M3_TO_L
                                         for key, volume_m3 in cycle.lp_limit_m3_by_window.items()},
        "damping_heat_kJ": sum(sequence[name].mass_kg * event["peak_speed_m_s"]**2 / 2000
                               for name, event in cycle.events.items() if sequence[name].accel_m_s2),
        "hp_boost_L": cycle.hp_boost_L, "hp_recharged_L": cycle.hp_charge_L,
        "guard_block_s": cycle.guard_block_s, "final_swash": cycle.actual, "peak_bypass_L_min": cycle.peak_bypass_L_min,
        "peak_shaft_by_stage": cycle.peak_by_stage, "contact_and_press_entry": cycle.transition_trace, "entry_fill": cycle.entry_fill,
        "switch_count": len(cycle.switches), "switches": cycle.switches, "motion_events": cycle.events,
        "stage_events": cycle.stages, "main_travel_mm": model.main_travel_m * 1000,
        "shoe_parking_travel_mm": model.pre_travel_m * 1000,
        "loaded_density_kg_m3": model.in_die_kg_m3,
        "unlock_x_mm": unlock_x_m * 1000 if early_unlock else None,
        "energy": cycle.energy,
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


def check_sequence(run, model, *, unload_s, hold_s, unlock_x_m, shaft_limit_kW):
    assert run["peak_shaft_kW"] <= shaft_limit_kW + 1e-7
    assert abs(run["boost_L"] - run["recharged_L"]) < 1e-5
    assert abs(run["hp_boost_L"] - run["hp_recharged_L"]) < 1e-5
    phase = run["motion_events"]
    switches = {event["command"]: event["time_s"] for event in run["switches"]}
    assert switches["unload"] >= switches["hold"] + hold_s - 1e-9
    assert switches["gate_open"] >= switches["unload"] + unload_s - 1e-9
    assert switches["eject"] >= phase["gate_open"]["end_s"] - 1e-9
    assert switches["return"] >= phase["eject"]["end_s"] - 1e-9
    assert switches["gate_close"] >= phase["return"]["gate_clear_s"] - 1e-9
    assert run["stage_events"]["feed"][0] >= max(phase[k]["end_s"] for k in ("return", "gate_close", "pre_up"))
    if model.takeoff_travel_m:
        assert phase["takeoff_pull"]["end_s"] <= switches["gate_close"]
    if model.hold_supply_bar:
        assert phase["pre_hold_charge"]["end_s"] <= switches["regen"]
    if model.cam_m:
        assert phase["pre_down"]["marker_s"] < phase["pre_down"]["end_s"] <= switches["regen"]
        assert phase["pre_up"]["start_s"] < phase["pre_up"]["marker_s"]
        if unlock_x_m is None or model.takeoff_travel_m:
            assert switches["pre_up"] >= phase["eject"]["end_s"] - 1e-9
        else:
            assert switches["pre_up"] >= phase["eject"]["unlock_clear_s"] - 1e-9
    assert model.main_travel_m * 1000 <= 274 + 1e-9
    assert (model.pre_travel_m + model.cam_m) * 1000 <= 380 + 1e-9


def periodic_run(model, cylinder, bulk_kg_m3, feed_s, settings, dt_s):
    pump = settings.get("pump")
    initial_swash = (0.,) * len(pump.names) if pump else ()
    history = []
    displacement_tick = dt_s * pump.slew(350., True) if pump else 0.
    for turn in range(16):
        run = simulate(model, dt_s=dt_s, cylinder=cylinder, bulk_kg_m3=bulk_kg_m3,
                       feed_s=feed_s, initial_swash=initial_swash, **settings)
        if not run["feasible"] or not pump:
            return run
        run["initial_swash"] = initial_swash
        history.append(run)
        final_swash = run["final_swash"]
        for start in range(len(history) - 1, -1, -1):
            prior = history[start]["initial_swash"]
            delta = max(abs(a - b) for a, b in zip(prior, final_swash))
            if delta <= displacement_tick:
                # Retain the slowest member of a possible discrete cycle.
                repeated = history[start:]
                worst = max(repeated, key=lambda record: record["cycle_s"])
                return dict(worst, periodic_cycles=turn + 1, periodic_period_cycles=len(repeated),
                            periodic_closure_displacement_fraction=delta,
                            periodic_closure_tolerance_fraction=displacement_tick)
        initial_swash = final_swash
    raise RuntimeError(("periodic swash state did not converge", model.case, model.dose_kg, bulk_kg_m3,
                        feed_s, dt_s, [run["final_swash"] for run in history]))



def converged_run(model, cylinder, bulk_kg_m3, feed_s, settings, steps_s):
    assert abs(model.axial_force_N(model.press_end_m, bulk_kg_m3) - model.nominal_N) < 1e-6
    steps_s = list(steps_s)
    runs = [periodic_run(model, cylinder, bulk_kg_m3, feed_s, settings, step_s) for step_s in steps_s]
    while abs(runs[-2]["cycle_s"] - runs[-1]["cycle_s"]) > .015 and len(runs) < 6:
        steps_s.append(steps_s[-1] / 2)
        runs.append(periodic_run(model, cylinder, bulk_kg_m3, feed_s, settings, steps_s[-1]))
    for run in runs:
        assert run["feasible"], run
        check_sequence(run, model, unload_s=settings["unload_s"], hold_s=settings["hold_s"],
                       unlock_x_m=settings["unlock_x_m"], shaft_limit_kW=settings["pump"].limit_kW)
    cycle_by_step_s = [run["cycle_s"] for run in runs]
    delta_s = max(abs(a - b) for a, b in zip(cycle_by_step_s, cycle_by_step_s[1:]))
    fine_delta_s = abs(cycle_by_step_s[-2] - cycle_by_step_s[-1])
    assert fine_delta_s <= .015, (model.case, model.dose_kg, bulk_kg_m3, feed_s, steps_s, cycle_by_step_s)
    fine = runs[-1]
    return dict(fine, convergence=[dict(dt_s=step_s, cycle_s=run["cycle_s"]) for step_s, run in zip(steps_s, runs)],
                max_adjacent_step_delta_s=delta_s, final_step_delta_s=fine_delta_s)


if __name__ == "__main__":
    from drive import HERE, calculate, write_json

    write_json(HERE / "results.json", calculate())
