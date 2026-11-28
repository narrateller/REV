"""One-dimensional lossless method of characteristics for TF and the fill line."""
import json
from math import ceil, pi, sin, sqrt
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BAR_PA = 100_000


def loads():
    project = json.loads((ROOT / "calc/T-2.6/results.json").read_text(encoding="utf-8"))
    params = yaml.safe_load((HERE / "params/params.t29.yaml").read_text(encoding="utf-8"))
    variant = project["variants"]["A_combined_NG50_33p25_kW_50ms_AX"]
    return params, variant["prefill"]


def wave_speed(density_kg_m3, bulk_Pa, bore_m, wall_m, steel_Pa):
    return (density_kg_m3 * (1 / bulk_Pa + bore_m / (steel_Pa * wall_m))) ** -0.5


def stop(length_m, area_m2, wave_m_s, density_kg_m3, flow_m3_s, close_s,
         bore_share, gas_m3, gas_initial_Pa, gas_exponent, atmospheric_Pa, cells,
         final_cut_fraction=0):
    """QR is imposed by the moving piston/valve. QL sees the nonlinear gas C.

    No wall friction is credited for attenuation. Limit the integration to the
    time of interest so sealed gas does not stand in for the steady regulator.
    """
    dt_s = length_m / (cells * wave_m_s)
    impedance = density_kg_m3 * wave_m_s / area_m2
    initial_gas_m3 = gas_m3
    head_Pa = [gas_initial_Pa] * (cells + 1)
    rate_m3_s = [flow_m3_s] * (cells + 1)
    peak_port_Pa = peak_tank_Pa = gas_initial_Pa
    low_port_Pa = gas_initial_Pa
    low_tank_Pa = gas_initial_Pa
    end_s = close_s + 8 * length_m / wave_m_s
    for step in range(1, ceil(end_s / dt_s) + 1):
        time_s = step * dt_s
        fraction = (1 - (1 - final_cut_fraction) * sin(pi / 2 * time_s / close_s)
                    if time_s < close_s else 0.)
        outlet_m3_s = flow_m3_s * fraction
        incoming = [head_Pa[i] + impedance * rate_m3_s[i] for i in range(cells)]
        outgoing = [head_Pa[i] - impedance * rate_m3_s[i] for i in range(1, cells + 1)]
        tank_Pa = gas_initial_Pa * (initial_gas_m3 / gas_m3)**gas_exponent
        tank_flow_m3_s = (tank_Pa - outgoing[0]) / impedance
        # Companion main volume. Intake has B-to-TF replenishment and exhaust
        # has MC makeup. Disabling it in a sensitivity bounds asynchrony.
        gas_m3 += (tank_flow_m3_s - bore_share * outlet_m3_s) * dt_s
        port_Pa = incoming[-1] - impedance * outlet_m3_s
        head_Pa = [tank_Pa, *[(left + right) / 2 for left, right in zip(incoming, outgoing[1:])], port_Pa]
        rate_m3_s = [tank_flow_m3_s, *[(left - right) / (2 * impedance)
                                     for left, right in zip(incoming, outgoing[1:])], outlet_m3_s]
        peak_port_Pa = max(peak_port_Pa, port_Pa)
        low_port_Pa = min(low_port_Pa, port_Pa)
        peak_tank_Pa = max(peak_tank_Pa, tank_Pa)
        low_tank_Pa = min(low_tank_Pa, tank_Pa)
    return {
        "port_peak_gauge_bar": (peak_port_Pa - atmospheric_Pa) / BAR_PA,
        "port_min_abs_bar": low_port_Pa / BAR_PA,
        "tf_peak_gauge_bar": (peak_tank_Pa - atmospheric_Pa) / BAR_PA,
        "tf_min_gauge_bar": (low_tank_Pa - atmospheric_Pa) / BAR_PA,
        "time_step_s": dt_s,
    }


def calculate():
    params, fill = loads()
    cm = params["cycle_model"]
    pipe = cm["valves"]["fill_pipe"]
    density = cm["oil"]["density_kg_m3"]
    bulk = cm["oil"]["bulk_modulus_Pa"]
    diameter_m = pipe["cap_ID_mm"] / 1000
    area_m2 = pi / 4 * diameter_m**2
    a_m_s = wave_speed(density, bulk, diameter_m, .004, 210e9)
    inflow = fill["cap_intake"]["approach"]["flow_L_min"] / 60_000
    outflow = fill["cap_exhaust"]["flow_L_min"] / 60_000
    abrupt_bar = density * a_m_s * inflow / area_m2 / BAR_PA
    high_gauge = cm["tank"]["gauge_bar"] + cm["tank"]["band_bar"]
    low_gauge = cm["tank"]["gauge_bar"] - cm["tank"]["band_bar"]
    ambient_Pa = cm["tank"]["ambient_bar"] * BAR_PA
    gas_L = cm["tank"]["gross_L"] - cm["tank"]["oil_L"]
    gas_exponent = 1.4
    p0_Pa = ambient_Pa + high_gauge * BAR_PA
    initial_head_bar = fill["liquid_level_head_bar"]
    pair_ratio = fill["annulus_intake"]["flow_L_min"] / fill["cap_exhaust"]["flow_L_min"]
    normal_s = inflow / (pi / 4 * .280**2) / cm["mechanics"]["crosshead_accel_m_s2"]
    # 2WRCE NG50 2K7L graph is a typical stepped-spool characteristic under
    # standard pilot conditions. Screen 5 ms too, since command response is
    # not a guaranteed lower bound on the time to interrupt the oil column.
    timing_s = {
        "normal": normal_s,
        "rapid_VR_step": .036,
        "MF_ng50_step_screen": .018,
        "fast_edge_5ms": .005,
        "loss_of_control_1ms": .001,
    }
    rows = []
    for length_m in (.20, .25, .5, 1., 2.):
        for label, close_s in timing_s.items():
            for flow_name, flow in (("intake", inflow), ("exhaust", -outflow)):
                ratio = pair_ratio if flow > 0 else 0.
                args = (length_m, area_m2, a_m_s, density, flow, close_s, ratio,
                        gas_L / 1000, p0_Pa, gas_exponent, ambient_Pa)
                fine = stop(*args, 64)
                coarse = stop(*args, 32)
                rows.append({
                    "length_m": length_m, "case": label, "flow": flow_name, "close_s": close_s,
                    "round_trip_s": 2 * length_m / a_m_s,
                    "slow_closure_criterion": 2 * length_m / a_m_s < close_s,
                    "port_A_peak_gauge_bar": fine["port_peak_gauge_bar"] + initial_head_bar,
                    "port_A_low_abs_bar_single_phase": fine["port_min_abs_bar"] + initial_head_bar,
                    "subatmospheric_port_A_single_phase": fine["port_min_abs_bar"] + initial_head_bar < ambient_Pa / BAR_PA,
                    "tf_peak_gauge_bar": fine["tf_peak_gauge_bar"],
                    "tf_min_gauge_bar": fine["tf_min_gauge_bar"],
                    "mesh_delta_bar": abs(fine["port_peak_gauge_bar"] - coarse["port_peak_gauge_bar"]),
                })
    intermediate = [row for row in rows if row["case"] in ("rapid_VR_step", "MF_ng50_step_screen", "fast_edge_5ms")]
    exhaust = [row for row in rows if row["flow"] == "exhaust"]
    intake = [row for row in rows if row["flow"] == "intake"]
    by_length = {
        str(length): {row["case"]: row["port_A_peak_gauge_bar"] for row in intake if row["length_m"] == length}
        for length in (.20, .25, .5, 1., 2.)
    }
    # Report the T-2.6 MF B/GC exhaust envelope plus computed TF rise as a
    # deliberately conservative cross-check; MF loss is not TF vessel pressure.
    tf_dynamic_rise = max(row["tf_peak_gauge_bar"] for row in exhaust) - high_gauge
    net_intake_L = fill["net_withdrawal_bound_L"]
    sealed_end_bar = ((ambient_Pa + low_gauge * BAR_PA) / BAR_PA
                      * (gas_L / (gas_L + net_intake_L))**gas_exponent)
    tank_gas_flow_L_min = fill["max_gas_flow_at_TF_L_min"]
    with (ROOT / "design/hydraulics/station.t25c.yaml").open(encoding="utf-8") as stream:
        goetze = yaml.safe_load(stream)["qualification"]["tf"]
    return {
        "oil_bulk_modulus_Pa": bulk, "steel_modulus_Pa": 210e9, "pipe_wall_mm": 4,
        "wave_m_s": a_m_s, "m5_wave_m_s": 1268.5, "fill_flow_L_min": inflow * 60_000,
        "exhaust_flow_L_min": outflow * 60_000, "pipe_ID_mm": pipe["cap_ID_mm"],
        "gas_volume_initial_L": gas_L, "gas_exponent": gas_exponent,
        "gas_compliance_L_per_bar_at_high": gas_L * BAR_PA / (gas_exponent * p0_Pa),
        "gas_regulator_demand_L_min_at_TF": tank_gas_flow_L_min,
        "sealed_full_stroke_end_abs_bar": sealed_end_bar,
        "zsf_port_A_allowed_bar": 16.,
        "zsf_port_A_peak_bar": {
            "normal": by_length["0.5"]["normal"],
            "emergency": by_length["0.5"]["fast_edge_5ms"],
            "emergency_fast_edge_1ms": by_length["0.5"]["loss_of_control_1ms"],
            "instantaneous": high_gauge + initial_head_bar + density * 1268.5 * inflow / area_m2 / BAR_PA,
            "instantaneous_M5_rise": density * 1268.5 * inflow / area_m2 / BAR_PA,
            "instantaneous_steel_total": high_gauge + initial_head_bar + abrupt_bar,
        },
        "zsf_stop_by_length": by_length,
        "stop_sensitivity_max_catalogue_or_5ms_bar": max(row["port_A_peak_gauge_bar"] for row in intermediate),
        "required_snap_downstream_flow_L_min_at_16bar": (
            (16 - high_gauge - initial_head_bar) * BAR_PA * area_m2 / (1268.5 * density) * 60_000),
        "tf_peak_bar": max(row["tf_peak_gauge_bar"] for row in exhaust),
        "tf_exhaust_conservative_combined_bar": fill["cap_exhaust"]["peak_gauge_bar"] + tf_dynamic_rise,
        "t26_cap_exhaust_at_MF_B_bar": fill["cap_exhaust"]["peak_gauge_bar"],
        "tf_relief_bar": 1.9, "tf_vessel_limit_bar": 3.,
        "rtf_t25c_corrected_screen_L_min": goetze["retained"]["screen"]["corrected_L_min"],
        "rtf_nominal_ideal_flow_L_min": .54 * pi / 4 * .059**2
        * sqrt(2 * (3 - .2) * BAR_PA / density) * 60_000,
        "tf_short_stop_cases": rows,
        "limits": [
            "The normal case assumes a decelerated piston ending without a poppet step at nonzero flow.",
            "The catalogue spool response is typical; neither it nor the cycle gate bounds the shortest actual shutoff edge at loss of power.",
            "RE 20478 p. 4 specifies seat behaviour and the nozzle, without a guaranteed passive closing time.",
            "The initial gas state bounds each local transient. Over a full stroke, the catalogue gas regulator must independently meet the flow and pressure requirement.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=False, indent=2))
