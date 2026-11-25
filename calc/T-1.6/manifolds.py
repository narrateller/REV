"""Reconcile valve packages and compare mounting-block layouts by valve tag."""
from math import ceil, fsum, hypot, pi, sqrt


def area_mm2(diameter_mm):
    return pi * diameter_mm**2 / 4


def round_up_5(value_mm):
    return 5 * ceil(value_mm / 5)


def block_screen(circuit, previous_circuit, data, prior, criteria):
    cfg = data["review_round_2"]["manifold"]
    cats = data["catalogs"]
    rho_kg_mm3 = data["project"]["steel_density_kg_m3"] / 1e9
    relief_MPa = criteria["C-HYD-01"]["max_relief_bar"] / 10
    allowable_MPa = cfg["material_Rp02_MPa"] / cfg["target_factor_yield"]
    # Pressurized thick cylinder with an unloaded outer surface, plane
    # closed-end Lamé stress. Adjacent/discontinuous holes still need FEA.
    wall_factor = sqrt(allowable_MPa / (allowable_MPa - sqrt(3) * relief_MPa)) - 1
    components = {}
    for tag, valve in circuit["elements"].items():
        family, ng = valve.get("source"), valve.get("DN_mm")
        if family not in {"WRC", "LC", "LC2A", "LC_MON"} or not ng or tag == "ZUP":
            continue
        old = previous_circuit["elements"][tag]
        assert old["series"] == valve["series"] and old["DN_mm"] == ng
        table = cfg["WRC"] if family == "WRC" else cfg["LC"]
        face, bore, _, dia_A, dia_B, depth_B, seat_H, bolt_H, bolt_pitch, bolt_d = table[ng]
        if family == "WRC":
            assert cfg["WRC_B_side_drill_mm"][ng] <= dia_B
            dia_B = cfg["WRC_B_side_drill_mm"][ng]
        else:
            dia_A, dia_B = dia_B, dia_A  # RE 21010 has separate standard and enlarged B dimensions.
        min_wall_mm = max(cfg["machining_min_ligament_mm"], max(bore, dia_B) / 2 * wall_factor)
        core_mm = round_up_5(max(face, bore + 2 * min_wall_mm, bolt_pitch + bolt_d + 2 * min_wall_mm))
        height_mm = round_up_5(seat_H + cfg["blank_drill_bottom_stock_mm"])
        bolt_xy_mm = bolt_pitch / 2
        # B side drill centered in the cell, ends at bore A. For WRC its
        # lower tangent is at H1. LC widths/heights are envelopes only.
        bore_to_bolt_mm = hypot(bolt_xy_mm, bolt_xy_mm) - (bore + bolt_d) / 2
        B_to_bolt_mm = hypot(bolt_xy_mm - bolt_d / 2, max(0, depth_B - dia_B / 2 - bolt_H)) - dia_B / 2
        edge_mm = round_up_5(min_wall_mm)
        components[tag] = {
            "family": family, "NG": ng, "series": valve["series"], "L1_mm": face, "max_bore_OD_mm": bore,
            "A_drill_mm": dia_A, "B_drill_mm": dia_B, "H2_catalog_mm": seat_H,
            "fastener_clearance_from_axial_bore_mm": bore_to_bolt_mm,
            "B_to_thread_ligament_mm": B_to_bolt_mm if family == "WRC" else None,
            "bottom_ligament_below_B_mm": height_mm - depth_B if family == "WRC" else None,
            "local_WRC_drawing_and_wall_screen_pass": (min(bore_to_bolt_mm, B_to_bolt_mm, height_mm - depth_B) >= min_wall_mm
                                                       if family == "WRC" else None),
            "wall_required_mm": min_wall_mm, "core_mm": core_mm, "stock_end_mm": edge_mm,
            "height_mm": height_mm, "reference_mount_measured_kg": None,
        }
        row = components[tag]
        if family == "WRC":
            package_kg = cats["WRC"]["mass_kg"][ng] + valve.get("catalogue_mass_extra_kg", 0)
            row.update(catalog_source="WRC (RE 29406 p. 6 and pp. 21–22)", package_kg=package_kg,
                       insert_kg=None, cover_kg=None, t15_booking="Картриджи 2WRCE, whole unit incl. cover")
        elif family == "LC2A":
            row.update(catalog_source="LC2A (RE 21040 p. 8 and pp. 23–24)",
                       package_kg=cats["LC2A"]["mass_kg"][ng], insert_kg=None, cover_kg=None,
                       t15_booking="Клапаны плавания и подпитки; separate M-3SEW and mount identification open")
        else:
            insert_kg = cats["LC"]["cartridge_mass_kg"][ng]
            cover_kg = cats["LC"]["cover_mass_kg"][ng]
            assembly_known = family == "LC" and tag != "LCH"
            booking = {"MRC": "Седло регенерации", "ZU": "monitored_unloader_and_adapter",
                       "RCA": "Клапаны плавания и подпитки + float_common_cover_and_mounts",
                       "RCB": "Клапаны плавания и подпитки + float_common_cover_and_mounts"}
            row.update(catalog_source="LC (RE 21010 pp. 5–6)" + ("; LC_MON (RE 21015)" if family == "LC_MON" else ""),
                       insert_kg=insert_kg, cover_kg=cover_kg if assembly_known else None,
                       generic_LFA_reference_kg=cover_kg, package_kg=insert_kg + cover_kg if assembly_known else None,
                       t15_booking=booking.get(tag, "Коллекторы, малая арматура и защита"))

    assigned = {tag for tags in cfg["groups"].values() for tag in tags}
    groups = cfg["groups"] | {tag: [tag] for tag in components if tag not in assigned}
    layouts = {}
    for name, tags in groups.items():
        width_mm = max(components[tag]["core_mm"] + 2 * components[tag]["stock_end_mm"] for tag in tags)
        height_mm = max(components[tag]["height_mm"] for tag in tags)
        end_mm = max(components[tag]["stock_end_mm"] for tag in tags)
        length_mm = sum(components[tag]["core_mm"] for tag in tags) + 2 * end_mm
        for idx, tag in enumerate(tags):
            row = components[tag]
            core_mm, edge_mm = row["core_mm"], row["stock_end_mm"]
            individual_side_mm = core_mm + 2 * edge_mm
            # Remove a through hole at the minimum A passage and only the
            # disjoint B side cylinder outboard of the main sleeve bore.
            # Mass stays an upper envelope, with unmodeled material retained.
            def envelope_kg(cell_length_mm, block_width_mm, block_height_mm):
                A_mm3 = area_mm2(row["A_drill_mm"]) * block_height_mm
                B_mm3 = area_mm2(row["B_drill_mm"]) * (block_width_mm - row["max_bore_OD_mm"]) / 2
                return (cell_length_mm * block_width_mm * block_height_mm - A_mm3 - B_mm3) * rho_kg_mm3

            apportioned_length_mm = core_mm + end_mm * (int(idx == 0) + int(idx == len(tags) - 1))
            row.update(group=name, distinct_blank_dims_mm=[individual_side_mm, individual_side_mm, row["height_mm"]],
                       separate_model_kg=envelope_kg(individual_side_mm, individual_side_mm, row["height_mm"]),
                       shared_model_share_kg=envelope_kg(apportioned_length_mm, width_mm, height_mm))
        ligaments_mm = [(components[a]["core_mm"] + components[b]["core_mm"]
                         - components[a]["max_bore_OD_mm"] - components[b]["max_bore_OD_mm"]) / 2
                        for a, b in zip(tags, tags[1:])]
        separate_kg = fsum(components[tag]["separate_model_kg"] for tag in tags)
        shared_kg = fsum(components[tag]["shared_model_share_kg"] for tag in tags)
        layouts[name] = {
            "tags": tags, "layout_blank_dims_mm": [length_mm, width_mm, height_mm],
            "total_separate_model_kg": separate_kg, "total_shared_model_kg": shared_kg,
            "geometry_delta_kg": shared_kg - separate_kg, "adjacent_main_bore_ligaments_mm": ligaments_mm,
            "credited_delta_kg": 0,
        }

    station = {row["node"]: row["T15_kg"] for row in prior["mass"]["station_rows"]}
    wrc_book_kg = station["Картриджи 2WRCE"]
    wrc_package_kg = fsum(row["package_kg"] for row in components.values() if row["family"] == "WRC")
    assert abs(wrc_package_kg - wrc_book_kg) < 1e-8
    float_cover_kg = fsum(components[tag]["cover_kg"] for tag in ("RCA", "RCB"))
    return {
        "items": components,
        "float_standard_covers_kg": float_cover_kg, "groups": layouts, "p_max_bar": relief_MPa * 10,
        "shared_geometry_mass_kg": fsum(group["total_shared_model_kg"] for group in layouts.values()),
        "geometry_delta_kg": fsum(group["geometry_delta_kg"] for group in layouts.values()),
        "WRC_package_sum_kg": wrc_package_kg, "T15_generic_collectors_and_protection_kg":
        station["Коллекторы, малая арматура и защита"],
        "credited_net_diff_kg": 0,
        "float_standard_covers_gap_kg": max(0, float_cover_kg - station["float_common_cover_and_mounts"]),
        "assessment": "RE 29406 and RE 21010/21040 provide fitting dimensions, not universal manifold web minima. Keep the original plate allowances. Verify threaded drill depth, vendor X/Y drilling, port flanges, ligaments at intersecting oilways, and billed masses by tag before changing the budget.",
    }


def passage_comparison(circuit, data, base_losses):
    """Compare just the flow length/ID in the MP, MT and MR oil ways."""
    cfg = data["review_round_2"]["manifold"]
    base = data["revision"]["main_manifold"]
    rho_kg_m3 = data["project"]["oil_density_kg_m3"]
    paths = {}
    trial_budgets = []
    for name, tag in (("inlet", "MP"), ("return", "MT"), ("regen", "MR")):
        valve = circuit["elements"][tag]
        item = base_losses[name]
        D_mm = cfg["nominal_WRC_passage_ID_mm"][valve["DN_mm"]]
        velocity_m_s = valve["Q_L_min"] / (60_000 * area_mm2(D_mm) * 1e-6)
        K = (base["darcy_friction_bound"] * cfg["active_comparison_passage_length_m"] / (D_mm / 1000)
             + base["passage_local_K"] + cfg["active_comparison_extra_local_K"])
        block_bar = K * rho_kg_m3 * velocity_m_s**2 / 2e5
        trial_bar = item["budget_bar"] - item["block_passage_drop_bar"] + block_bar
        trial_budgets.append(trial_bar)
        paths[tag] = {"ID_mm": D_mm, "Q_L_min": valve["Q_L_min"], "velocity_m_s": velocity_m_s,
                      "R1_passage_bar": item["block_passage_drop_bar"], "R2_passage_bar": block_bar,
                      "R1_total_bar": item["budget_bar"], "R2_total_bar": trial_bar}
    return paths, trial_budgets

