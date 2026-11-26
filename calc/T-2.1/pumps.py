"""Catalogue curves, fixed-speed power limiting and the neutral VFD model."""
from functools import lru_cache
from math import fsum, pi, sqrt

from drive import PV180Drive, PumpPoint, linear_value, source_data


class A4VSO180Drive(PV180Drive):
    """Positive-swivel DFE1Z with external control oil and a shaft limit."""

    names = ("A4VSO180",)

    def __init__(self, sources, limit_kW, profile):
        engineering = sources["engineering"]
        super().__init__(source_data(), limit_kW=limit_kW,
                         response_multiplier=engineering["dfe1z_response_multiplier"][profile])
        self.catalogue = sources["catalogs"]["rexroth"]
        self.curve = self.catalogue["curve_bar_L_min_kW_kW"]
        self.standby_bar = self.catalogue["standby_gauge_bar"]
        self.standby_pressures_bar = (self.standby_bar,)
        controller = sources["catalogs"]["dfe1z"]
        self.response_ms = (controller["destroke_ms_at_100bar"],
                            controller["onstroke_ms_at_100bar"])

    @lru_cache(maxsize=8192)
    def section(self, name, pressure_bar):
        speed_ratio = self.rpm / self.catalogue["reference_rpm"]

        def value(column):
            return linear_value(pressure_bar, [(row[0], row[column]) for row in self.curve]) * speed_ratio

        flow_L_min, full_kW, zero_kW = (value(i) for i in (1, 2, 3))
        geometric_L_min = self.rpm * self.catalogue["displacement_cm3_rev"] / 1000
        return PumpPoint(flow_L_min, zero_kW, full_kW, flow_L_min / geometric_L_min,
                         geometric_L_min * pressure_bar / (600 * full_kW))

    def slew(self, pressure_bar, increasing):
        return 1000 / (self.response_ms[increasing] * self.response_multiplier)


def pump_curve(pump, configured_max_L_min):
    """Raw map and usable delivery at the common project motor speed."""
    rows = []
    for pressure_bar in range(0, 301, 25):
        point = pump.section(pump.names[0], pressure_bar)
        header_bar = max(pressure_bar, pump.standby_bar)
        flow_L_min, kW = pump.operating_point(header_bar, configured_max_L_min)
        rows.append(dict(pressure_bar=pressure_bar, effective_header_bar=header_bar,
                         catalogue_full_stroke_flow_L_min=point.flow_L_min,
                         catalogue_full_stroke_shaft_kW=point.full_stroke_kW,
                         catalogue_zero_stroke_shaft_kW=point.deadhead_kW,
                         catalogue_eta_v_full_stroke=point.eta_v,
                         catalogue_eta_hm_full_stroke=point.eta_hm if pressure_bar else None,
                         limited_flow_L_min=flow_L_min, limited_shaft_kW=kW,
                         working_point_net_efficiency=header_bar * flow_L_min / (600 * kW)))
    return rows


def vfd_replay(run, sources, tolerance):
    """Slow in the longest idle window at zero swash and zero pilot charging."""
    config = sources["engineering"]["vfd"]
    motor = sources["catalogs"]["motor"]
    converter = sources["catalogs"]["vfd"]
    speed_rad_s = motor["rated_rpm"] * pi / 30
    min_rad_s = config["min_rpm"] * pi / 30
    inertia_kg_m2 = fsum((motor["rotor_inertia_kg_m2"], sources["catalogs"]["parker"]["inertia_kg_m2"],
                          config["additional_rotating_inertia_kg_m2"]))
    accel_rad_s2 = config["acceleration_and_deceleration_rad_s2"]
    ramp_s = (speed_rad_s - min_rad_s) / accel_rad_s2
    loads = run["pilot_loads_kW"]
    steps = run["power_steps"]
    pause_windows = [run["stage_events"][name] for name in ("hold", "unload", "feed")]
    windows = []
    current_window = []
    for index, ((time_s, dt_s, stage, _, _, _, _, _, _, swash), pilot_kW) in enumerate(zip(steps, loads)):
        in_pause = any(start_s - 1e-9 <= time_s + dt_s / 2 <= end_s + 1e-9
                       for start_s, end_s in pause_windows)
        if in_pause and stage == "neutral" and swash <= 1e-10 and pilot_kW == 0:
            current_window.append(index)
        elif current_window:
            windows.append(current_window)
            current_window = []
    if current_window:
        windows.append(current_window)

    speed_fraction = [1.] * len(steps)
    accel_torque_Nm = [0.] * len(steps)
    slowing_s = 0.
    deepest_rpm = motor["rated_rpm"]
    longest_window = max(windows, key=lambda indices: fsum(steps[i][1] for i in indices), default=[])
    brake_heat_kJ = 0.
    for window in (longest_window,) if longest_window else ():
        start_s = steps[window[0]][0]
        end_s = fsum(steps[window[-1]][:2])
        trough_rad_s = max(min_rad_s, speed_rad_s - accel_rad_s2 * (end_s - start_s) / 2)
        actual_ramp_s = (speed_rad_s - trough_rad_s) / accel_rad_s2
        slowing_s += end_s - start_s
        deepest_rpm = min(deepest_rpm, trough_rad_s * 30 / pi)
        for index in window:
            time_s, dt_s = steps[index][:2]
            midpoint_s = time_s + dt_s / 2
            elapsed_s = midpoint_s - start_s
            until_end_s = end_s - midpoint_s
            omega_rad_s = max(trough_rad_s, speed_rad_s - accel_rad_s2 * min(elapsed_s, until_end_s))
            speed_fraction[index] = omega_rad_s / speed_rad_s
            if elapsed_s < actual_ramp_s:
                accel_torque_Nm[index] = -inertia_kg_m2 * accel_rad_s2
            elif until_end_s < actual_ramp_s:
                accel_torque_Nm[index] = inertia_kg_m2 * accel_rad_s2

    oil_energy_delta_kJ = 0.
    shaft_energy_delta_kJ = 0.
    shaft_square_delta_kW2_s = 0.
    peak_current_A = 0.
    current_square_A2_s = 0.
    torque_square_Nm2_s = 0.
    max_speed_derated_torque_square_Nm2_s = 0.
    max_reacceleration_shaft_kW = 0.
    magnetizing = config["current_magnetizing_fraction_assumption"]
    for step, load_kW, ratio, acceleration_Nm in zip(steps, loads, speed_fraction, accel_torque_Nm):
        _, dt_s, _, _, main_kW, main_peak_kW, main_square_kW2, *_ = step
        base_kW = main_kW + load_kW
        base_square_kW2 = main_square_kW2 + 2 * main_kW * load_kW + load_kW**2
        drag_kW = base_kW * ratio
        inertia_kW = acceleration_Nm * ratio * speed_rad_s / 1000
        shaft_kW = drag_kW + inertia_kW
        # The deceleration can return energy to the DC link, budget it as brake loss.
        shaft_energy_delta_kJ += dt_s * (max(0., shaft_kW) - base_kW)
        brake_heat_kJ += dt_s * max(0., -shaft_kW)
        if ratio < 1.:
            shaft_square_delta_kW2_s += dt_s * (shaft_kW**2 - base_square_kW2)
            max_reacceleration_shaft_kW = max(max_reacceleration_shaft_kW, shaft_kW)
        oil_energy_delta_kJ += dt_s * (drag_kW - base_kW)
        rms_torque_Nm = (sqrt(base_square_kW2) * 1000 / speed_rad_s if ratio == 1.
                         else abs(shaft_kW) * 1000 / (ratio * speed_rad_s))
        peak_torque_Nm = ((main_peak_kW + load_kW) * 1000 / speed_rad_s if ratio == 1. else rms_torque_Nm)
        cooling_ratio = max(config["neutral_motor_cooling_ratio_floor"], ratio)
        torque_square_Nm2_s += dt_s * rms_torque_Nm**2
        max_speed_derated_torque_square_Nm2_s += dt_s * rms_torque_Nm**2 / cooling_ratio
        current_factor = motor["rated_A"] * config["current_pwm_allowance_factor"]

        def current_A(torque_Nm):
            return current_factor * sqrt(magnetizing**2 + (1 - magnetizing**2) *
                                         (tolerance * torque_Nm / motor["rated_Nm"])**2)

        peak_current_A = max(peak_current_A, current_A(peak_torque_Nm))
        current_square_A2_s += dt_s * current_A(rms_torque_Nm)**2
    current_rms_A = sqrt(current_square_A2_s / run["cycle_s"])
    derated_rms_Nm = tolerance * sqrt(max_speed_derated_torque_square_Nm2_s / run["cycle_s"])
    return dict(
        slowing_s=slowing_s, min_speed_rpm=deepest_rpm, half_ramp_1480_to_750_s=ramp_s,
        inertia_kg_m2=inertia_kg_m2, acceleration_torque_Nm=inertia_kg_m2 * accel_rad_s2,
        oil_energy_delta_kJ=oil_energy_delta_kJ, shaft_energy_delta_kJ=shaft_energy_delta_kJ,
        shaft_square_delta_kW2_s=shaft_square_delta_kW2_s,
        max_reacceleration_shaft_kW=max_reacceleration_shaft_kW,
        motor_torque_rms_Nm=tolerance * sqrt(torque_square_Nm2_s / run["cycle_s"]),
        motor_cooling_adjusted_rms_Nm=derated_rms_Nm,
        converter_current_rms_A=current_rms_A, converter_peak_current_A=peak_current_A,
        direct_on_line_start_A=motor["rated_A"] * motor["DOL_current_to_rated"],
        initial_no_load_ramp_current_estimate_A=current_A(inertia_kg_m2 * accel_rad_s2
                                                          + steps[0][4] * 1000 / speed_rad_s),
        cabinet_loss_upper_kW=converter["max_cabinet_loss_kW"],
        brake_energy_kJ_per_cycle=brake_heat_kJ,
        motor_plus_cabinet_budget_kW=motor["rated_kW"] + converter["max_cabinet_loss_kW"],
        motor_load_screen_pass=derated_rms_Nm <= motor["rated_Nm"],
        converter_current_screen_pass=(current_rms_A <= converter["light_duty_A"]
                                       and peak_current_A <= converter["peak_A"]),
    )

