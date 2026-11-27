"""Quantity and mass of the purchased parts affected by the scheme-A study."""

from math import fsum, pi, prod


def assemble(data, catalogs, scenario, density_kg_m3, fill, rails, prior):
    sections = {"existing", "revised"}
    if scenario.rapid_regen:
        sections.add("regen")
    if scenario.lp_eject:
        sections.add("lp_eject")
    if scenario.mp:
        sections.add("mp")
    catalog_sources = catalogs | data["extra_sources"]
    rows = {}
    for name, part in data["parts"].items():
        if part["section"] not in sections:
            continue
        row = dict(part)
        if name == "MF" and scenario.return_valve.startswith("NG63"):
            row.update(model="Rexroth 2WRCE NG63 4K5L WK E", unit_kg=catalogs["wrce"]["mf_NG63_WK_E_kg"])
        qty = row.get("qty", 1)
        if "unit_kg" in row:
            dry_kg = qty * row["unit_kg"]
            oil_kg = 0.
        else:
            dry_kg = qty * row["length_m"] * row["kg_per_m"]
            oil_kg = qty * row["length_m"] * pi / 4 * (row["id_mm"] / 1000)**2 * density_kg_m3
        source = catalog_sources[row["ref"]]
        existing = row["section"] == "existing"
        rows[name] = row | dict(source_url=source["url"], dry_kg=dry_kg, oil_kg=oil_kg,
                                delta_kg=0. if existing else dry_kg + oil_kg,
                                basis="catalogue" if "unit_kg" in row else "catalogue unit mass, layout length")
    rows["MF"]["delta_kg"] = rows["MF"]["dry_kg"] - data["parts"]["MF"]["unit_kg"]
    reference_block_kg = data["mf_reference_block_kg"]
    block_kg = reference_block_kg
    if scenario.return_valve == "NG50_double_B":
        block_kg = prod(data["mf_block_envelope_mm"]) / 1e9 * data["steel_density_kg_m3"]
    elif scenario.return_valve.startswith("NG63"):
        block_kg = data["mf_reference_block_NG63_kg"]
    rows["MF_housing"] = dict(model="MF housing with RE 29406 installation bore", dry_kg=block_kg,
                              old_proxy_kg=reference_block_kg, delta_kg=block_kg - reference_block_kg,
                              source_url=catalog_sources["cb"]["url"], drawing_source_url=catalogs["wrce"]["url"],
                              basis=data["mf_block_method"])
    shell_kg = data["tf_base_shell_membrane_regulator_kg"]
    vessel_kg = shell_kg * data["tf_A_gross_L"] / data["tf_base_gross_L"]
    oil_kg_per_L = density_kg_m3 / 1000
    oil_L = fill["buffer_oil_L"]
    rows["TF"] = dict(model="REV separated reservoir with N2 regulation", source_url=data["tf_url"],
                      basis=data["tf_shell_mass_method"], dry_kg=vessel_kg, oil_kg=oil_L * oil_kg_per_L,
                      delta_kg=vessel_kg - shell_kg + (oil_L - data["tf_base_oil_L"]) * oil_kg_per_L)
    if scenario.mp:
        oil_kg = rails["mp"]["initial_oil_L"] * oil_kg_per_L
        rows["mp_vessel"]["oil_kg"] = oil_kg
        rows["mp_vessel"]["delta_kg"] += oil_kg
    delta_kg = fsum(row["delta_kg"] for row in rows.values())
    machine_kg = [kg - prior["hydraulic_delta_kg"] + delta_kg for kg in prior["machine_with_H2_kg"]]
    return dict(added_hydraulics_kg=delta_kg, purchased_and_custom_rows=rows,
                subtotal_listed_kg=fsum(row["dry_kg"] + row.get("oil_kg", 0.) for row in rows.values()),
                original_A_hydraulic_budget_kg=prior["hydraulic_delta_kg"], machine_with_H2_kg=machine_kg,
                reduction_to_5000_kg=[max(0., kg - 5000) for kg in machine_kg],
                remaining_scope="Actual MF/TF housing, seals/fittings/supports, monitors and NG1/NR1 gas flow. "
                                "Reconcile the HYDAC 3047174 catalogue 63 kg against inherited 49 kg before G-MASS.")
