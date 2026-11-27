"""A4VSO180/DFE1Z map and shaft regulator from T-2.1 and T-2.6."""

from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
from math import log10


def linear_value(x, points):
    index = max(1, min(len(points) - 1, bisect_right(points, x, key=lambda row: row[0])))
    (x0, y0), (x1, y1) = points[index - 1:index + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def viscosity_mm2_s(temperature_C, points):
    """ASTM D341 Walther equation used by T-2.6 for Shell Tellus S2 MX 46."""
    endpoints = [(log10(t + 273.15), log10(log10(v + .7))) for t, v in points]
    return 10**(10**linear_value(log10(temperature_C + 273.15), endpoints)) - .7


@dataclass(frozen=True)
class PumpPoint:
    flow_L_min: float
    deadhead_kW: float
    full_stroke_kW: float


class A4VSO180Drive:
    names = ("A4VSO180",)
    anticipation = True
    record_power_steps = True

    def __init__(self, cfg, oil, pilot_standby_kW):
        self.limit_kW = cfg["main_shaft_limit_kW"] * cfg["regulator_fraction"]
        self.loss_kW = cfg["coupling_loss_kW"] + pilot_standby_kW
        self.standby_bar = cfg["standby_bar"]
        self.standby_pressures_bar = (self.standby_bar,)
        self.control_delay_s = cfg["control_delay_s"]
        self.response_s = cfg["destroke_s"], cfg["onstroke_s"]
        self.apply_leakage = (cfg["motor_rpm"] != cfg["rated_motor_rpm"]
                              or cfg["main_shaft_limit_kW"] * cfg["regulator_fraction"] != cfg["nominal_regulator_kW"]
                              or oil["temperature_C"] != oil["map_temperature_C"])
        self.speed_ratio = cfg["motor_rpm"] / cfg["map_rpm"]
        self.geometric_L_min = cfg["motor_rpm"] * cfg["displacement_cm3_rev"] / 1000
        self.delivery_fraction = cfg["delivery_fraction"]
        self.curves = tuple(tuple((row[0], row[column]) for row in cfg["curve"])
                            for column in (1, 2, 3))
        viscosity = oil["viscosity_C_mm2_s"]
        self.leakage_multiplier = (viscosity_mm2_s(oil["map_temperature_C"], viscosity)
                                   / viscosity_mm2_s(oil["temperature_C"], viscosity))
        # Keep the interpolation cache local to this drive.
        self.section = lru_cache(maxsize=8192)(self.section)

    def section(self, name, pressure_bar):
        flow_L_min, full_kW, zero_kW = (linear_value(pressure_bar, curve) * self.speed_ratio
                                       for curve in self.curves)
        # Recover the catalogue-speed leakage from the flow deficit, then
        # subtract viscosity-adjusted leakage from the actual swept volume.
        if self.apply_leakage:
            catalog_leak_L_min = max(0., self.geometric_L_min - flow_L_min) / self.speed_ratio
            flow_L_min = self.geometric_L_min - catalog_leak_L_min * self.leakage_multiplier
        return PumpPoint(flow_L_min * self.delivery_fraction, zero_kW, full_kW)

    def fractions(self, pressure_bar, requested_L_min, actual=()):
        point = self.section(self.names[0], max(pressure_bar, self.standby_bar))
        remaining_kW = max(0., self.limit_kW - self.loss_kW - point.deadhead_kW)
        hydraulic_kW = point.full_stroke_kW - point.deadhead_kW
        flow_L_min = min(point.flow_L_min, requested_L_min, remaining_kW / (hydraulic_kW / point.flow_L_min))
        return (flow_L_min / point.flow_L_min,)

    def instant(self, pressure_bar, fractions, connected):
        outlet_bar = max(pressure_bar if connected[0] else 0., self.standby_bar)
        point = self.section(self.names[0], outlet_bar)
        flow_L_min = fractions[0] * point.flow_L_min
        shaft_kW = self.loss_kW + point.deadhead_kW + fractions[0] * (point.full_stroke_kW - point.deadhead_kW)
        if connected[0]:
            return flow_L_min, shaft_kW, (outlet_bar - pressure_bar) * flow_L_min / 600
        return 0., shaft_kW, outlet_bar * flow_L_min / 600

    def connected(self, pressure_bar, actual, setpoints):
        return (pressure_bar > 0.,)

    def capacity_L_min(self, pressure_bar):
        fractions = self.fractions(pressure_bar, float("inf"))
        return self.instant(pressure_bar, fractions, self.connected(pressure_bar, fractions, fractions))[0]

    def slew(self, pressure_bar, increasing):
        return 1 / self.response_s[increasing]

    def update(self, pressure_bar, previous, setpoints, dt_s):
        old, = previous
        goal, = setpoints
        if goal < old:
            return (max(goal, old - self.slew(pressure_bar, False) * dt_s),)
        return (min(goal, old + self.slew(pressure_bar, True) * dt_s),)

