"""Build the T-2.6 physical load curves and hydraulic topology from gate inputs."""

from dataclasses import replace
from math import expm1, prod

from .drive import A4VSO180Drive, linear_value
from .hydraulics import BAR_PA, Cylinder, Model, area_m2


FLOW = 60_000  # L/min per m³/s
GRAVITY_M_S2 = 9.81


class Material:
    """T-1.1 power law with the nominal T-1.2 Janssen wall transfer."""

    def __init__(self, cfg, section_mm):
        self.cfg = cfg
        self.section_mm = section_mm

    def face_MPa(self, density_kg_m3, bulk_kg_m3, case, *, dose_kg, section_mm=None, wall_case=None):
        cfg = self.cfg
        onset = min(1, max(0, (density_kg_m3 - bulk_kg_m3) / (cfg["rho_join_kg_m3"] - bulk_kg_m3)))
        delta = max(0, density_kg_m3 - cfg["rho_ref_kg_m3"])
        mean_MPa = cfg["scale_MPa"] * (delta / 1000)**cfg["exponent"] * onset * (2 - onset)
        section = self.section_mm if section_mm is None else section_mm
        length_mm = dose_kg * 1e9 / (prod(section) * density_kg_m3)
        return mean_MPa / self.transfer(section, length_mm)

    def attenuation_per_mm(self, section_mm):
        diameter_mm = 2 * prod(section_mm) / sum(section_mm)
        return 4 * self.cfg["lateral_K"] * self.cfg["wall_mu"] / diameter_mm

    def transfer(self, section_mm, length_mm):
        q = self.attenuation_per_mm(section_mm) * length_mm
        return -expm1(-q) / q

    def loaded_density_kg_m3(self, face_MPa, bulk_kg_m3, dose_kg):
        lo, hi = bulk_kg_m3, self.cfg["density_max_kg_m3"]
        if not 0 < face_MPa <= self.face_MPa(hi, bulk_kg_m3, "base", dose_kg=dose_kg):
            raise ValueError("cycle_model.material: pressing force outside material curve")
        for _ in range(50):
            mid = (lo + hi) / 2
            if self.face_MPa(mid, bulk_kg_m3, "base", dose_kg=dose_kg) < face_MPa:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2


def stack_force(model, section_mm, cfg):
    """T-1.7d outlet load and T-1.2b residual radial-pressure reconstruction."""
    die_mm = model.die_length_m * 1000
    growth_mm = die_mm * ((1 + model.material.cfg["axial_springback"]) - 1)
    engagement_mm = max(0., model.overtravel_m * 1000 - 2 * growth_mm)
    p_MPa = (model.material.cfg["lateral_K"] * model.ejection_N / prod(section_mm)
             / expm1(model.material.attenuation_per_mm(section_mm) * die_mm))
    local_force_N = cfg["guide_mu"] * p_MPa * 2 * sum(section_mm) * cfg["transition_mm"]
    max_supported_kg = (model.in_die_kg_m3 * prod(cfg["section_mm"])
                        * (cfg["length_mm"] + cfg["overhang_mm"]) * 1e-9)
    guide_force_N = cfg["crumbs_N"] + (cfg["guide_mu"] * max_supported_kg * GRAVITY_M_S2
                                     * (1 + cfg["side_load_to_weight"]))
    def force_N(displacement_m):
        x_mm = displacement_m * 1000
        # The 1 mm ramps are the contact regularization in T-1.7d/stack.py.
        entry = min(1., max(0., x_mm))
        exit = min(1., max(0., die_mm + cfg["transition_mm"] - x_mm))
        engagement = min(1., max(0., x_mm - engagement_mm))
        return local_force_N * entry * exit + guide_force_N * engagement
    return force_N


def fill_routes(model, cylinder, rapid, valves, tank, oil):
    """Calculate the MF/MC and ZSF losses and impose the legacy intake derating."""
    pcfg = valves["fill_pipe"]
    tank_nominal = tank["gauge_bar"]
    tank_upper = tank_nominal + tank["band_bar"]
    tank_lower = tank_nominal - tank["band_bar"]
    rho = oil["density_kg_m3"]
    ambient_bar = tank["ambient_bar"]
    gravity_bar = rho * GRAVITY_M_S2 * pcfg["static_head_m"] / BAR_PA

    def pipe_losses_bar(port_m2, pipe_mm, velocity_m_s):
        pipe_m2 = area_m2(pipe_mm)
        line_m_s = port_m2 * velocity_m_s / pipe_m2
        k = pcfg["darcy_factor"] * pcfg["length_m"] / (pipe_mm / 1000) + pcfg["local_K"]
        return (k * rho * line_m_s**2 / (2 * BAR_PA)
                + rho * pcfg["length_m"] * model.rapid_accel_m_s2 * port_m2 / (pipe_m2 * BAR_PA))

    def intake(velocity_m_s):
        flow_L_min = cylinder.cap_m2 * velocity_m_s * FLOW
        drop_bar = linear_value(flow_L_min, valves["zsf_curve_L_min_bar"])
        pressure_abs_bar = (ambient_bar + tank_lower + gravity_bar - drop_bar
                            - pipe_losses_bar(cylinder.cap_m2, pcfg["cap_ID_mm"], velocity_m_s))
        return pressure_abs_bar, flow_L_min

    if tank["enforce_saturation_reserve"]:
        def limited(velocity_m_s):
            lo, hi = 0., velocity_m_s
            for _ in range(50):
                trial = (lo + hi) / 2
                pressure_abs_bar, flow_L_min = intake(trial)
                if (pressure_abs_bar - ambient_bar >= tank["saturation_reserve_bar"]
                        and flow_L_min <= valves["zsf_max_L_min"]):
                    lo = trial
                else:
                    hi = trial
            return lo
        model = replace(model, rapid_approach_m_s=limited(model.rapid_approach_m_s),
                        rapid_eject_m_s=limited(model.rapid_eject_m_s))

    # Max flow at the MC suction branch sets the fast return envelope.
    return_m_s = model.rapid_return_m_s
    annulus_makeup_bar = valves["mc_drop_bar"] * (return_m_s / rapid["mc_reference_m_s"])**2
    use_vr_curve = rapid["vr_exhaust_curve"]
    if tank["enforce_saturation_reserve"] and return_m_s > rapid["mc_reference_m_s"]:
        return_m_s = rapid["mc_reference_m_s"]
        annulus_makeup_bar *= (return_m_s / model.rapid_return_m_s)**2
        model = replace(model, rapid_return_m_s=return_m_s)
        use_vr_curve = False

    mf_flow_L_min = FLOW * cylinder.cap_m2 * return_m_s
    return_a_bar = (tank_upper + gravity_bar + pipe_losses_bar(cylinder.cap_m2, pcfg["cap_ID_mm"], return_m_s)
                    + valves["mf_rated_drop_bar"] * (mf_flow_L_min / valves["mf_rated_L_min"])**2)
    return_b_bar = (tank_upper + gravity_bar - annulus_makeup_bar
                    - pipe_losses_bar(cylinder.annulus_m2, pcfg["annulus_ID_mm"], return_m_s))
    drag_N = BAR_PA * (return_a_bar * cylinder.cap_m2 - return_b_bar * cylinder.annulus_m2)
    if use_vr_curve:
        vr_flow_L_min = FLOW * rapid["cap_m2"] * return_m_s
        inlet, exhaust, regen = model.losses_bar
        exhaust = max(exhaust, valves["vr_rated_drop_bar"] * (vr_flow_L_min / valves["vr_rated_L_min"])**2)
        model = replace(model, return_losses_bar=(inlet, exhaust, regen))
    intake_limits = [intake(model.rapid_approach_m_s), intake(model.rapid_eject_m_s)]
    fill = dict(cap_intake_min_abs_bar=min(pressure for pressure, _ in intake_limits),
                cap_intake_max_L_min=max(flow for _, flow in intake_limits),
                annulus_intake_min_abs_bar=ambient_bar + return_b_bar - (tank_upper - tank_lower),
                cap_exhaust_bar=return_a_bar)
    fill["admissible"] = (min(fill["cap_intake_min_abs_bar"], fill["annulus_intake_min_abs_bar"])
                          >= tank["minimum_abs_bar"]
                          and fill["cap_intake_max_L_min"] <= valves["zsf_max_L_min"]
                          and fill["cap_exhaust_bar"] <= valves["mf_exhaust_budget_bar"])
    if tank["gross_L"]:
        oil_used_L = cylinder.rod_m2 * cylinder.stroke_mm
        cap_volume_L = cylinder.cap_m2 * cylinder.stroke_mm + oil["cap_dead_L"]
        fill["buffer_min_L"] = 1.5 * cap_volume_L + oil_used_L
    else:
        fill["buffer_min_L"] = 1.5 * cylinder.cap_m2 * cylinder.stroke_mm
    fill["admissible"] &= tank["oil_L"] >= fill["buffer_min_L"]
    return model, drag_N, fill


def cylinder_from(row, rod_mm=None):
    return Cylinder(row["bore_mm"], row["rod_mm"] if rod_mm is None else rod_mm,
                    row["stroke_mm"], row["eta"])


def metering_areas_m2(main, pre, gate, rapid):
    cap_m2 = rapid["count"] * area_m2(rapid["bore_mm"])
    rod_m2 = rapid["count"] * area_m2(rapid["rod_mm"])
    return {
        "main_metering_L_min": main.cap_m2,
        "mc_reference_L_min": main.annulus_m2,
        "pre_metering_L_min": pre.cap_m2,
        "cam_metering_L_min": pre.cap_m2,
        "gate_metering_L_min": gate.cap_m2,
        "rapid_feed_metering_L_min": rod_m2 if rapid["rapid_regeneration"] else cap_m2,
        "rapid_out_metering_L_min": cap_m2,
        "rapid_back_metering_L_min": cap_m2 - rod_m2,
    }


def accumulator_kwargs(cfg):
    return {name: cfg[name] for name in ("shell_L", "precharge_bar", "low_bar", "high_bar", "exponent", "delivery_L_min")}


def configure(params, max_working_bar):
    cfg = params["cycle_model"]
    mech, process, oil = (cfg[name] for name in ("mechanics", "process", "oil"))
    rapid, valves, tank = (cfg[name] for name in ("rapid_pair", "valves", "tank"))
    lp, mp, pilot, pump_cfg = (cfg[name] for name in ("lp", "mp", "pilot", "pump"))
    main = cylinder_from(params["main_cylinder"], mech["main_rod_mm"])
    pre = cylinder_from(params["precompaction"]["cylinder"])
    gate = cylinder_from(params["drive"]["slide_gate_cylinder"])
    section_mm = params["chamber"]["section_mm"]
    width_mm, height_mm = section_mm
    dose_kg = params["raw"]["dose_kg"]
    bulk_kg_m3 = process["bulk_density_kg_m3"]
    nominal_N = params["main_cylinder"]["nominal_force_N"]
    material = Material(cfg["material"], section_mm)
    in_die_kg_m3 = material.loaded_density_kg_m3(nominal_N / prod(section_mm), bulk_kg_m3, dose_kg)
    approach_mm = params["chamber"]["approach_stroke_mm"]
    feed_mm = mech["feed_length_mm"]
    roof_mm = mech["roof_mm"]
    overtravel_mm = main.stroke_mm - mech["main_cushion_mm"] - approach_mm - feed_mm - roof_mm
    if overtravel_mm <= mech["gate_close_inset_mm"]:
        raise ValueError("cycle_model.mechanics: insufficient clearance beyond the gate")
    pre_section = [feed_mm, width_mm]
    density_kg_m3 = dose_kg * 1e9 / (prod(pre_section) * height_mm)
    radial_MPa = material.face_MPa(density_kg_m3, bulk_kg_m3, "base", dose_kg=dose_kg, section_mm=pre_section)
    transfer_N = (cfg["material"]["wall_mu"] * radial_MPa * 2 * sum(section_mm) * feed_mm
                  + mech["transfer_edge_N"])
    areas_m2 = metering_areas_m2(main, pre, gate, rapid)
    limits_m_s = {key: valves[key] / (FLOW * area) for key, area in areas_m2.items()}
    pump = A4VSO180Drive(pump_cfg, oil, pilot["standby_kW"])
    max_L_min = min(pump_cfg["line_limit_L_min"], pump.capacity_L_min(pump.standby_bar))
    model = Model(
        material, "base", dose_kg, width_mm / 1000, height_mm / 1000, feed_mm / 1000,
        in_die_kg_m3, mech["pre_guide_N"], nominal_N, overtravel_mm / 1000, approach_mm / 1000,
        mech["shoe_travel_mm"] / 1000, pre, gate, ejection_N=mech["die_ejection_N"],
        transfer_m=roof_mm / 1000, transfer_drag_N=transfer_N, cam_m=mech["cam_stroke_mm"] / 1000,
        cam_force_N=mech["cam_resistance_N"], cam_stem_speed_m_s=limits_m_s["cam_metering_L_min"],
        gate_travel_m=mech["gate_travel_mm"] / 1000,
        gate_speed_m_s=limits_m_s["gate_metering_L_min"],
        pre_return_force_N=mech["pre_return_resistance_N"], losses_bar=tuple(valves["line_loss_bar"]),
        regen_switch_bar=valves["main_regen_changeover_bar"],
        rapid_approach_m_s=limits_m_s["rapid_feed_metering_L_min"],
        rapid_eject_m_s=limits_m_s["rapid_out_metering_L_min"],
        rapid_return_m_s=limits_m_s["rapid_back_metering_L_min"],
        rapid_mass_kg=mech["crosshead_mass_kg"], rapid_accel_m_s2=mech["crosshead_accel_m_s2"],
        gate_mass_kg=mech["gate_mass_kg"], gate_accel_m_s2=mech["gate_accel_m_s2"],
        gate_open_residual_friction_N=mech["gate_mu"] * (
            mech["gate_residual_N"] + process["gate_release_cap_bar"] * BAR_PA * main.cap_m2),
        gate_open_weight_N=GRAVITY_M_S2 * mech["gate_mass_kg"],
        gate_close_punch_inset_m=mech["gate_close_inset_mm"] / 1000,
        oil_bulk_Pa=oil["bulk_modulus_Pa"], cap_dead_m3=oil["cap_dead_L"] / 1000, rod_dead_m3=oil["rod_dead_L"] / 1000,
        main_limit_m_s=limits_m_s["main_metering_L_min"],
        pre_limit_m_s=limits_m_s["pre_metering_L_min"],
        main_guide_N=mech["main_guide_N"], rapid_return_resistance_N=mech["rapid_return_resistance_N"],
        gate_breakaway_N=mech["gate_breakaway_N"], gate_close_N=mech["gate_close_N"],
    )
    rapid = rapid | dict(cap_m2=areas_m2["rapid_out_metering_L_min"],
                         mc_reference_m_s=limits_m_s["mc_reference_L_min"])
    model, return_drag_N, fill = fill_routes(model, main, rapid, valves, tank, oil)
    if not tank["gross_L"]:
        return_drag_N = max(rapid["float_drag_N"], return_drag_N)
    model = replace(model, stack_force_N=stack_force(model, section_mm, cfg["outlet"]))
    prefill = {name: rapid[name] for name in ("count", "bore_mm", "rod_mm", "eta", "switch_force_N", "rapid_regeneration")}
    prefill.update(float_gauge_bar=tank["gauge_bar"], main_float_drag_kN=rapid["float_drag_N"] / 1000,
                   return_float_drag_kN=return_drag_N / 1000)
    lp_settings = accumulator_kwargs(lp)
    settings = dict(overlap=True, accumulator=True, deficit_only=True, lp_window_guard=True, pump=pump,
                    max_L_min=max_L_min, max_working_bar=max_working_bar, unlock_x_m=(approach_mm + feed_mm + roof_mm) / 1000,
                    switch_s=process["valve_switch_s"], hold_s=process["hold_s"], unload_s=process["unload_s"],
                    accumulator_shell_L=lp_settings.pop("shell_L"), accumulator_kwargs=lp_settings,
                    boost_branches=tuple(lp["routes"]), charge_drop_bar=lp["charge_drop_bar"],
                    prefill=prefill, pilot_idle_s=pilot["idle_charge_reserve_s"])
    if mp is not None:
        recharge_s = 60 * mp["cycle_budget_L"] / pump.capacity_L_min(mp["high_bar"] + lp["charge_drop_bar"])
        settings.update(mp_accumulator_kwargs=accumulator_kwargs(mp), mp_branches=tuple(mp["routes"]),
                        mp_cycle_budget_L=mp["cycle_budget_L"], lp_tail_reserve_s=mp["changeover_allowance_s"] + recharge_s)
    return model, main, settings, fill

