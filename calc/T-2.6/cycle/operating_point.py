"""Oil-property sensitivities and the low-pressure filling circuit."""

from dataclasses import dataclass, replace
from functools import lru_cache
from math import log10, pi

from drive import linear_value, prefill_budget
from pumps import A4VSO180Drive
from x1_calc import area_m2


@dataclass(frozen=True)
class OperatingPoint:
    valve_s: float | None = None
    unload_s: float | None = None
    regulator_fraction: float = 1.
    rpm: int = 1480
    oil_C: float = 50.
    tank_gauge_bar: float | None = None


def viscosity_mm2_s(temperature_C, oil):
    """ASTM D341 Walther equation over the Shell 40–100 °C data interval."""
    x = log10(temperature_C + 273.15)
    endpoints = [(log10(t + 273.15), log10(log10(v + .7))) for t, v in oil["viscosity_C_mm2_s"]]
    return 10**(10**linear_value(x, endpoints)) - .7


class OilAdjustedDrive(A4VSO180Drive):
    """Apply the viscosity trend of internal leakage to the catalogue p/Q map."""

    @lru_cache(maxsize=8192)
    def section(self, name, pressure_bar):
        point = super().section(name, pressure_bar)
        # Laminar clearance leakage scales with dynamic viscosity to first order.
        # Use the catalogue speed to recover leakage, then subtract from Vg*n
        # independently of speed. Keep the catalogue shaft-loss map at new rpm.
        geometric_L_min = self.rpm * self.catalogue["displacement_cm3_rev"] / 1000
        catalogue_leak_L_min = max(0., geometric_L_min - point.flow_L_min) * self.catalogue["reference_rpm"] / self.rpm
        q_L_min = geometric_L_min - catalogue_leak_L_min * self.leakage_multiplier
        return replace(point, flow_L_min=q_L_min, eta_v=q_L_min / geometric_L_min)


def configure_operating_point(study, settings, condition, oil, maximum_L_min):
    pump = settings["pump"]
    ref_C = oil["pump_catalogue_temperature_C"]
    nu_ref = viscosity_mm2_s(ref_C, oil)
    nu = viscosity_mm2_s(condition.oil_C, oil)
    if condition.rpm != pump.rpm or condition.oil_C != ref_C or condition.regulator_fraction != 1.:
        adjusted = OilAdjustedDrive(study.sources, pump.limit_kW * condition.regulator_fraction,
                                    "realistic" if pump.response_multiplier == 1 else "pessimistic")
        adjusted.rpm = condition.rpm
        adjusted.omega_rad_s = condition.rpm * pi / 30
        adjusted.leakage_multiplier = nu_ref / nu
        adjusted.loss_kW = pump.loss_kW
        adjusted.pilot_standby_kW = pump.pilot_standby_kW
        adjusted.record_power_steps = True
        settings.update(pump=adjusted, max_L_min=min(maximum_L_min, adjusted.capacity_L_min(adjusted.standby_bar)))
    if condition.valve_s is not None:
        settings["switch_s"] = condition.valve_s
    if condition.unload_s is not None:
        settings["unload_s"] = condition.unload_s
    return dict(oil_C=condition.oil_C, viscosity_mm2_s=nu, viscosity_at_map_mm2_s=nu_ref,
                leakage_multiplier=nu_ref / nu)


def cap_intake(speed_m_s, cylinder, model, cfg, zsf, tank_bar):
    pipe = cfg["prefill_pipe"]
    rho = cfg["oil_density_kg_m3"]
    pipe_m2 = area_m2(pipe["inside_diameter_mm"])
    q_m3_s = speed_m_s * cylinder.cap_m2
    q_L_min = q_m3_s * 60000
    # RE 20478 A→B curve read-offs, with the application-2 1600/0.30
    # point used as a conservative upper anchor in the design range.
    valve_bar = linear_value(q_L_min, zsf["intake_curve_L_min_bar"])
    steady_bar = (pipe["darcy_factor"] * pipe["length_m"] / (pipe["inside_diameter_mm"] / 1000)
                  + pipe["local_K"]) * rho * (q_m3_s / pipe_m2)**2 / 2e5
    acceleration_bar = rho * pipe["length_m"] * model.rapid_accel_m_s2 * cylinder.cap_m2 / pipe_m2 / 1e5
    static_bar = rho * 9.81 * pipe["static_head_m"] / 1e5
    loss_bar = valve_bar + steady_bar + acceleration_bar - static_bar
    atm_bar = zsf["ambient_absolute_bar"]
    minimum_abs_bar = atm_bar + tank_bar - loss_bar
    return dict(flow_L_min=q_L_min, pipe_velocity_m_s=q_m3_s / pipe_m2, valve_drop_bar=valve_bar,
                steady_drop_bar=steady_bar, acceleration_head_bar=acceleration_bar,
                min_absolute_bar=minimum_abs_bar, without_boost_min_absolute_bar=minimum_abs_bar - tank_bar,
                minimum_separated_tank_gauge_bar=loss_bar,
                atmospheric_saturation_margin_bar=minimum_abs_bar - atm_bar,
                original_absolute_floor_margin_bar=minimum_abs_bar - pipe["cap_min_abs_bar"],
                equilibrated_tank_air_saturation_ratio=minimum_abs_bar / (atm_bar + tank_bar),
                case_2_flow_margin_L_min=zsf["case_2_flow_L_min"] - q_L_min)


def limit_intake_speed(model, cylinder, cfg, zsf, guaranteed_tank_bar):
    """Limit forward speed where atmospheric-saturated oil would release air."""
    def limited(speed_m_s):
        low, high = 0., speed_m_s
        for _ in range(50):
            speed = (low + high) / 2
            budget = cap_intake(speed, cylinder, model, cfg, zsf, guaranteed_tank_bar)
            if (budget["atmospheric_saturation_margin_bar"] >= zsf["derated_saturation_reserve_bar"]
                    and budget["case_2_flow_margin_L_min"] >= 0.):
                low = speed
            else:
                high = speed
        return min(speed_m_s, low)

    return replace(model, rapid_approach_m_s=limited(model.rapid_approach_m_s),
                   rapid_eject_m_s=limited(model.rapid_eject_m_s))


def verified_fill(model, cylinder, sources, zsf, guaranteed_tank_bar):
    cfg = sources["engineering_inputs"]
    fill = prefill_budget(model, cylinder, sources)
    fill["cap_intake"] = {
        name: cap_intake(speed, cylinder, model, cfg, zsf, guaranteed_tank_bar)
        for name, speed in (("approach", model.rapid_approach_m_s), ("ejection", model.rapid_eject_m_s))
    }
    fill["tank_min_gauge_bar"] = guaranteed_tank_bar
    # `prefill_budget` reports the annular branch at the upper tank pressure,
    # which bounds exhaust loading. Also evaluate its intake at the lower setting.
    annulus = fill["annulus_intake"]
    annulus["min_absolute_bar"] -= cfg["prefill_pipe"]["tank_gauge_bar"] - guaranteed_tank_bar
    annulus["atmospheric_saturation_margin_bar"] = annulus["min_absolute_bar"] - zsf["ambient_absolute_bar"]
    fill["atmospheric_saturation_screen_pass"] = (
        min(row["atmospheric_saturation_margin_bar"] for row in fill["cap_intake"].values()) >= -1e-10
        and annulus["atmospheric_saturation_margin_bar"] >= -1e-10)
    return fill
