"""Reproduce HM46 secant modulus, Lamé compliance, and the frozen-gate sensitivity."""
import json
from math import floor, pi
from pathlib import Path
from tempfile import TemporaryDirectory

from build_scheme import HERE, ROOT, read
from hoses import cycle_row, gate
from revision import change_K, params_text


def displacement_volume_L(diameter_mm, length_mm):
    return pi / 4 * diameter_mm**2 * length_mm / 1e6


def wall_compliance_per_Pa(ID_mm, OD_mm, E_Pa, nu, *, closed_ends=False):
    """Lam? stress at the bore and volumetric strain (2 hoop + axial)."""
    denominator = OD_mm**2 - ID_mm**2
    sigma_theta_per_p = (OD_mm**2 + ID_mm**2) / denominator
    sigma_radial_per_p = -1.0
    sigma_axial_per_p = ID_mm**2 / denominator if closed_ends else 0
    hoop_per_p = (sigma_theta_per_p - nu * (sigma_radial_per_p + sigma_axial_per_p)) / E_Pa
    axial_per_p = (sigma_axial_per_p - nu * (sigma_theta_per_p + sigma_radial_per_p)) / E_Pa
    return 2 * hoop_per_p + axial_per_p


def calculate():
    sources = read(HERE / "sources.yaml")["oil_modulus_inputs"]
    barrel = read(ROOT / sources["barrel_file"])["cylinders"][0]
    cover = read(ROOT / sources["cover_file"])["cover"]
    p = read(HERE / "params/params.t29.yaml")
    model = p["cycle_model"]
    bore_mm, OD_mm = barrel["bore_mm"], barrel["barrel_OD_mm"]
    if bore_mm != p["main_cylinder"]["bore_mm"]:
        raise ValueError("Main cylinder geometry disagrees with the frozen gate")
    E_Pa, nu = sources["E_steel_Pa"], sources["steel_poisson"]
    dead_L = model["oil"]["cap_dead_L"]
    feed_mm = model["mechanics"]["feed_length_mm"]
    x_in_mm = p["chamber"]["approach_stroke_mm"] + model["mechanics"]["roof_mm"]
    width_mm, height_mm = p["chamber"]["section_mm"]
    area_m2 = width_mm * height_mm / 1e6
    # Same kinematic formula as cycle_model.hydraulics.Model.press_end_m.
    briquette_length_mm = 1000 * p["raw"]["dose_kg"] / (area_m2 * p["chamber"]["in_die_density_kg_m3"])
    x_end_mm = x_in_mm + feed_mm - briquette_length_mm
    model_points = [5, x_in_mm, (x_in_mm + x_end_mm) / 2, x_end_mm]
    volumes = []
    for entry in sources["routed_estimates"]:
        est = dict(entry)
        volumes.append(est)
    # Maximal geometric volumes, without subtracting intersecting bores.
    cutout_mm = cover["OD_mm"] / 2 - cover["through_ZSF_ID_mm"] / 2
    volumes += [
        {"name": "MA–CYM, radial cover bores", "ID_mm": cover["MA_branch_ID_mm"],
         "OD_mm": sources["cover_equivalent_OD_mm"],
         "length_mm": cover["MA_branches"] * cutout_mm},
        {"name": "CYM-side ZSF pocket, axial cover bore", "ID_mm": cover["through_ZSF_ID_mm"],
         "OD_mm": cover["OD_mm"], "length_mm": cover["thickness_mm"]},
    ]
    for row in volumes:
        row["volume_L"] = displacement_volume_L(row["ID_mm"], row["length_mm"])
        row["wall_compliance_per_Pa"] = wall_compliance_per_Pa(row["ID_mm"], row["OD_mm"], E_Pa, nu, closed_ends=True)

    barrel_compliance = wall_compliance_per_Pa(bore_mm, OD_mm, E_Pa, nu, closed_ends=True)
    # Keep the volume-based estimate conservative independently of routed volumes:
    # use the most compliant wall for all oil as a second bound.
    worst_wall = max(barrel_compliance, *(row["wall_compliance_per_Pa"] for row in volumes))
    temperatures = {}
    for temperature_C, factor in ((50, 0), (55, .5)):
        density = {pressure: measured[0] + factor * (measured[1] - measured[0])
                   for pressure, measured in sources["density_kg_m3_at_50_60_C"].items()}
        dp_bar = sources["secant_span_bar"]
        dp_Pa = dp_bar * 100_000
        end_abs_bar = 1 + dp_bar
        final_kg_m3 = density[201] + (end_abs_bar - 201) / 100 * (density[301] - density[201])
        base_kg_m3 = density[1]
        K_oil_Pa = dp_Pa / (1 - base_kg_m3 / final_kg_m3)
        positions = []
        for x_mm in model_points:
            cylinder_L = dead_L + displacement_volume_L(bore_mm, x_mm)
            volume_L = cylinder_L + sum(row["volume_L"] for row in volumes)
            expansion_L_Pa = (cylinder_L * barrel_compliance
                              + sum(row["volume_L"] * row["wall_compliance_per_Pa"] for row in volumes))
            K_eff_Pa = volume_L / (volume_L / K_oil_Pa + expansion_L_Pa)
            positions.append({"x_mm": x_mm, "cylinder_and_dead_L": cylinder_L, "total_modelled_L": volume_L,
                              "steel_compliance_mL_bar": expansion_L_Pa * 1e8, "K_eff_Pa": K_eff_Pa})
        temperatures[temperature_C] = {
            "rho_0_bar_gauge_kg_m3": base_kg_m3, "rho_270_bar_gauge_kg_m3": final_kg_m3,
            "K_oil_Pa": K_oil_Pa, "positions": positions,
            "air_sensitivity": [
                {"free_air_at_1bar_vol_fraction": a, "adiabatic_gas_exponent": 1.4,
                 "K_eff_Pa": 1 / ((1-a) / K_oil_Pa + a*(1-(1/end_abs_bar)**(1/1.4))/dp_Pa + worst_wall)}
                for a in (0.0005, 0.001, 0.002)],
            "K_eff_all_oil_at_most_compliant_wall_Pa": 1 / (1 / K_oil_Pa + worst_wall),
        }
    physical_K_Pa = min(row["K_eff_all_oil_at_most_compliant_wall_Pa"] for row in temperatures.values())
    return {
        "temperatures": temperatures, "barrel_ID_mm": bore_mm, "barrel_OD_mm": OD_mm,
        "barrel_wall_mm": (OD_mm - bore_mm) / 2, "E_steel_Pa": E_Pa, "steel_poisson": nu,
        "barrel_wall_compliance_per_Pa": barrel_compliance, "dead_L": dead_L,
        "press_end_x_mm": x_end_mm, "routed_segments": volumes,
        "K_eff_Pa": physical_K_Pa, "params_K_Pa": min(1_400_000_000, floor(physical_K_Pa)),
        "scope": "Conservative in wall expansion for the assumed pocket and tube wall thicknesses. "
                 "Line lengths and pocket estimates are screening assumptions. No free gas in nominal case. End-cover and frame compliance outside the Lam? wall model.",
    }


def scan():
    base = params_text(1_400_000_000)
    rows = {}
    with TemporaryDirectory(prefix="k_scan_", dir=HERE) as folder:
        candidate, output = Path(folder) / "sensitivity.yaml", Path(folder) / "gate.json"

        def sample(K_Pa):
            if K_Pa not in rows:
                candidate.write_text(change_K(base, K_Pa), encoding="utf-8", newline="\n")
                output.unlink(missing_ok=True)
                rows[K_Pa] = cycle_row(gate(candidate, output), K_Pa)
            return rows[K_Pa]

        fail_card = fail_gate = None
        for K_Pa in range(1_400_000_000, 499_999_999, -20_000_000):
            row = sample(K_Pa)
            if not row["card_pass"] and fail_card is None:
                fail_card = K_Pa
            if row["gate_status"] != "PASS":
                fail_gate = K_Pa
                break
        if fail_card is None or fail_gate is None:
            raise RuntimeError("No PASS-to-FAIL bracket in the frozen-gate scan")
        for limit in (fail_card, fail_gate):
            for K_Pa in range(limit + 18_000_000, limit, -2_000_000):
                sample(K_Pa)

    first_fail_Pa = max(K for K, row in rows.items() if not row["card_pass"])
    gate_first_fail_Pa = max(K for K, row in rows.items() if row["gate_status"] != "PASS")
    return {
        "k_threshold_t29b_Pa": min(K for K, row in rows.items() if K > first_fail_Pa and row["card_pass"]),
        "highest_sampled_failing_K_Pa": first_fail_Pa,
        "k_threshold_frozen_gate_Pa": min(K for K, row in rows.items()
                                          if K > gate_first_fail_Pa and row["gate_status"] == "PASS"),
        "highest_sampled_failing_frozen_gate_K_Pa": gate_first_fail_Pa,
        "k_scan": [rows[K] for K in sorted(rows, reverse=True)],
    }


if __name__ == "__main__":
    print(json.dumps(calculate(), ensure_ascii=False, indent=2))

