"""Check nose breakaway force with the existing Ø125/56 cylinder."""
import json
from math import pi

from transient import loads, ROOT


def calculate():
    params, _ = loads()
    model = params["cycle_model"]
    cyl = params["precompaction"]["cylinder"]
    cap_m2 = pi / 4 * (cyl["bore_mm"] / 1000)**2
    annulus_m2 = cap_m2 - pi / 4 * (cyl["rod_mm"] / 1000)**2
    eta = cyl["eta"]
    old = json.loads((ROOT / "calc/T-2.2i/results.json").read_text(encoding="utf-8"))
    load = old["shortened_nose_sweep"]["best_stem_load"]["drive"]
    background_N = model["mechanics"]["pre_return_resistance_N"]
    working_drive_load_N = model["mechanics"]["cam_resistance_N"] + background_N
    equivalent_bar = 35.0
    lp_delivery_bar = model["lp"]["low_bar"] - model["lp"]["charge_drop_bar"]
    return_bar = model["valves"]["line_loss_bar"][1]
    observed_force_N = load["stem_force_limit_N"]
    factor_N_per_bar = eta * annulus_m2 * 100_000
    demand_N = 1.25 * max(load["front_and_rear_stem_force_N_by_assumed_mu"].values())
    available_N = factor_N_per_bar * equivalent_bar - background_N
    return {
        "cap_m2": cap_m2, "annulus_m2": annulus_m2, "efficiency": eta,
        "legacy_cam_load_kN": observed_force_N / 1000,
        "legacy_equivalent_net_bar": observed_force_N / factor_N_per_bar,
        "legacy_equivalent_with_guides_bar": (observed_force_N + background_N) / factor_N_per_bar,
        "cam_load_origin": "T-1.2b/shoe_load.py: contact, inertia and cam efficiency, inherited in T-2.2i/hand.py. Its pressure values here are equivalent pressures, not the origin of that 15.59 kN.",
        "guide_and_weight_kN": background_N / 1000,
        "piston_return_side_assumed_bar": return_bar,
        "lp_source_min_bar": model["lp"]["low_bar"],
        "lp_delivery_min_bar_screen": lp_delivery_bar,
        "lp_only_breakaway_kN": (eta * 1e5 * (lp_delivery_bar * annulus_m2 - return_bar * cap_m2) - background_N) / 1000,
        "pump_source": "P1→PPB→PCY.B; A→PAT→T0. LP via PBB only supplements at lower pressure.",
        "minimum_net_equivalent_bar": equivalent_bar,
        "rod_chamber_min_bar_with_assumed_return": equivalent_bar + return_bar * cap_m2 / annulus_m2,
        "header_min_bar_with_inlet_loss": equivalent_bar + return_bar * cap_m2 / annulus_m2 + model["valves"]["line_loss_bar"][0],
        "unlock_required_kN": demand_N / 1000, "unlock_force_kN": available_N / 1000,
        "gate_first_12_mm_load_kN": working_drive_load_N / 1000,
        "gate_first_12_mm_available_equivalent_bar": working_drive_load_N / factor_N_per_bar,
        "gate_first_12_mm_reserve_kN": model["mechanics"]["cam_resistance_N"] / 1000 - demand_N / 1000,
        "screen_force_pass": available_N >= demand_N,
        "condition": "Validate PTPA/PB differential and measurement error, including minimum supply during overlapping eject. Existing qualified gate load is greater than the proposed force floor.",
    }


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=False, indent=2))
