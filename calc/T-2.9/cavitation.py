"""Prefill pressure budget at the cold and hot ends of the operating range."""
import json
from math import pi
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from hoses import HERE, PARAMS, cycle_row, gate
from pc_branch import viscosity_mm2_s
from transient import loads


def screen(params, fill, viscosity_table, temperature_C, length_m, boost_bar,
           flow_L_min, accel_m_s2):
    cm = params["cycle_model"]
    rho = cm["oil"]["density_kg_m3"]
    pipe = cm["valves"]["fill_pipe"]
    diameter_m = pipe["cap_ID_mm"] / 1000
    velocity = flow_L_min / 60_000 / (pi / 4 * diameter_m**2)
    nu = viscosity_mm2_s(temperature_C, viscosity_table)
    reynolds = velocity * diameter_m / (nu * 1e-6)
    darcy = max(pipe["darcy_factor"], 64 / reynolds)
    pipe_bar = (pipe["local_K"] + darcy * length_m / diameter_m) * rho * velocity**2 / 2e5
    acceleration_bar = rho * accel_m_s2 * length_m * (.280 / diameter_m)**2 / 1e5
    # Retain the T-2.6 read-off at nominal Q; bound the viscosity-sensitive
    # part using spring offset plus the larger of linear viscous/inertial scalings.
    ref = fill["cap_intake"]["approach"]
    dynamic_bar = ref["valve_drop_bar"] - .135
    q_ratio = flow_L_min / ref["flow_L_min"]
    valve_bar = .135 + dynamic_bar * max(q_ratio**2, q_ratio * nu / 46)
    p_atm = cm["tank"]["ambient_bar"]
    p_A_bar = p_atm + boost_bar + fill["liquid_level_head_bar"] - pipe_bar - acceleration_bar
    cap_bar = p_A_bar - valve_bar
    # At the same oil temperature as T0, the Bunsen alpha cancels by Henry's
    # law. In the hot case use the greater of the same-temperature screen
    # and the separately reported supersaturation tolerance.
    return {
        "temperature_C": temperature_C, "viscosity_mm2_s": nu, "length_m": length_m,
        "tf_gauge_bar": boost_bar, "flow_L_min": flow_L_min, "accel_m_s2": accel_m_s2,
        "reynolds": reynolds, "pipe_dp_bar": pipe_bar, "accel_head_bar": acceleration_bar,
        "zsf_dp_bar": valve_bar, "zsf_port_A_abs_bar": p_A_bar, "cap_abs_bar": cap_bar,
        "air_release_pressure_bar": p_atm, "air_release_margin_bar": cap_bar - p_atm,
        "maximum_allowed_zsf_dp_bar": p_A_bar - p_atm,
        "maximum_allowed_alpha_T0_to_alpha_local": cap_bar / p_atm,
        "oil_vapor_margin_bar": cap_bar - 0.5e-5 if temperature_C == 20 else None,
        "oil_vapor_margin_vs_water_55C_bound_bar": cap_bar - .1576 if temperature_C == 55 else None,
    }


def cold_gate(params, flow_L_min, accel_m_s2):
    cm = params["cycle_model"]
    old_speed_m_s = .42
    new_speed_m_s = flow_L_min / 60_000 / (pi / 4 * .280**2)
    for tag in ("rapid_feed_metering_L_min", "rapid_out_metering_L_min"):
        cm["valves"][tag] *= new_speed_m_s / old_speed_m_s
    cm["mechanics"]["crosshead_accel_m_s2"] = accel_m_s2
    # Use the qualified oil-temperature model. This represents only the
    # mechanical speed/acceleration derate, not a validated cold pump map.
    with TemporaryDirectory(prefix="cold_gate_", dir=HERE) as folder:
        folder = Path(folder)
        candidate = folder / PARAMS.name
        candidate.write_text(yaml.safe_dump(params, sort_keys=False), encoding="utf-8")
        return cycle_row(gate(candidate, folder / "gate.json"), cm["oil"]["bulk_modulus_Pa"])


def calculate(run_gate=False):
    params, fill = loads()
    cm = params["cycle_model"]
    table = yaml.safe_load((HERE / "sources.yaml").read_text(encoding="utf-8"))[
        "screen_inputs"]["tellus_viscosity_T_C_mm2_s"]
    nominal = fill["cap_intake"]["approach"]["flow_L_min"]
    accel = cm["mechanics"]["crosshead_accel_m_s2"]
    low = round(cm["tank"]["gauge_bar"] - cm["tank"]["band_bar"], 3)
    high = round(cm["tank"]["gauge_bar"] + cm["tank"]["band_bar"], 3)
    rows = [screen(params, fill, table, temp, length, boost, nominal, accel)
            for length in (.5, 1., 2.) for temp in (0, 20, 55) for boost in (low, high)]
    target = [row for row in rows if row["length_m"] == .5 and row["temperature_C"] >= 20]
    # Shorten first. Then find the largest cold Q meeting a 0.02 bar
    # commissioning reserve in the pessimistic viscous-loss sensitivity.
    low_Q, high_Q = 1., nominal
    for _ in range(40):
        q = (low_Q + high_Q) / 2
        current = screen(params, fill, table, 20, .5, low, q, accel)
        if current["air_release_margin_bar"] >= .02:
            low_Q = q
        else:
            high_Q = q
    cold = screen(params, fill, table, 20, .5, low, low_Q, accel)
    softer = screen(params, fill, table, 20, .5, low, nominal, 2.)
    required_p_tf_bar = low - min(row["air_release_margin_bar"] for row in target)
    threshold_lo_C, threshold_hi_C = 20., 55.
    for _ in range(32):
        temp_C = (threshold_lo_C + threshold_hi_C) / 2
        if screen(params, fill, table, temp_C, .5, low, nominal, accel)["air_release_margin_bar"] >= .02:
            threshold_hi_C = temp_C
        else:
            threshold_lo_C = temp_C
    derated_gate = cold_gate(params, low_Q, accel) if run_gate else None
    return {
        "cap_min_abs_bar": min(row["cap_abs_bar"] for row in target),
        "air_release_margin_bar": min(row["air_release_margin_bar"] for row in target),
        "port_A_min_abs_bar": min(row["zsf_port_A_abs_bar"] for row in target),
        "bunsen_HLP46_measured_at_20C": .077,
        "catalogue_flow_reserve_L_min": cm["valves"]["zsf_max_L_min"] - nominal,
        "reference_cap_abs_bar": fill["cap_intake"]["approach"]["min_absolute_bar"],
        "reference_cap_without_tf_gauge_abs_bar": fill["cap_intake"]["approach"]["without_boost_min_absolute_bar"],
        "lower_level_height_m": cm["valves"]["fill_pipe"]["static_head_m"],
        "full_speed_results": rows,
        "mitigations": {"short_pipe_target_m": .5, "cold_slower_accel_only": softer,
                        "cold_flow_derate": cold, "cold_flow_derate_gate": derated_gate,
                        "minimum_TF_gauge_bar_for_20C_full_rate": required_p_tf_bar,
                        "minimum_preheat_temperature_C_for_0p02_bar_margin_screen": threshold_hi_C},
        "notes": [
            "20 °C is the T-2.5b Opus startup comparison. Also screen 0 °C per T-2.5c; negative absolute values indicate single-phase model breakdown. RE 20478 uses 40±5 °C.",
            "The viscous case is an engineering bound on the non-spring term, pending supplier low-temperature curves.",
            "0.1576 bar is the water saturation pressure at 55 °C, a separate contamination sensitivity; the oil SDS gives a number at 20 °C only.",
            "Assume saturation in T0 at the local test temperature. Rapid heating of previously air-saturated cold oil requires measured alpha(T) or degassing data.",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(calculate(run_gate=True), ensure_ascii=False, indent=2))
