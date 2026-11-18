"""Check exact traceability and preservation, without claiming independent review."""
import hashlib
import json
import subprocess
from pathlib import Path

from render_register import HERE, load, render

ROOT = HERE.parents[1]


def verify():
    checks = []

    def check(name, condition):
        checks.append({"id": name, "status": "PASS" if condition else "FAIL"})

    rows = load("definition_register.json")["rows"]
    methods = load("method_catalog.json")["rows"]
    reqs = json.loads((ROOT / "verification/r1_requirements_draft_20261117/draft_requirements.json").read_text())["requirements"]
    old = json.loads((ROOT / "verification/r1_g1_observation_revision_20261117/criterion_cards.json").read_text())["rows"]
    expected = [r["id"] for r in reqs]
    check("22_unique_pairs", len(rows) == 22 and [r["requirement_id"] for r in rows] == expected)
    check("22_controlled_method_proposals", len(methods) == 22 and len({m["method_id"] for m in methods}) == 22)
    all_scope_ids = []
    for row, req, prior, method in zip(rows, reqs, old, methods):
        rid = row["requirement_id"]
        check(rid + ":frozen_requirement", row["requirement_text"] == req["proposed_requirement"] and row["validation_id"] == req["validation_id"])
        check(rid + ":preserved_channels_sources_evidence", row["channel_ids"] == prior["measurement_channel_ids"] and row["source_field_refs"] == prior["source_field_refs"] and row["future_evidence_fields"] == prior["mandatory_evidence_fields"])
        scope = row["proposed_enumerated_scope"]
        ids = [s["scope_item_id"] for s in scope]
        all_scope_ids.extend(ids)
        check(rid + ":enumerated_scope", bool(scope) and len(ids) == len(set(ids)) and all(s["description"] and s["future_disposition"] is None for s in scope))
        check(rid + ":method_link", method["method_id"] == row["definition_method_id"] and method["requirement_id"] == rid and method["validation_id"] == row["validation_id"] and method["input_scope_items"] == ids)
        check(rid + ":no_fabricated_limits", all(row["numeric_criterion"][x] is None for x in ["value", "unit", "tolerance", "uncertainty_acceptance_limit"]) and row["numeric_criterion"]["approved_parameter_refs"] == [])
        check(rid + ":no_execution_or_owner", row["assigned_engineering_owner_session"] is None and row["actual_evidence_records"] == [] and row["future_result_status"] == "NOT_RUN" and method["actual_results"] == [] and method["future_physical_method_revision"] is None)
        check(rid + ":open_approval_and_definitions", row["open_definition_decisions"] and row["criterion_approval"] == "NOT_APPROVED" and row["method_approval"] == "NOT_APPROVED" and method["authority_status"] == "PROPOSED_NOT_APPROVED")
        check(rid + ":profile_scope", (row["evidence_profile"] == "DOCUMENTARY_AUDIT") == (prior["criterion_kind"] == "OBJECTIVE_COMPLETENESS"))
    check("globally_unique_scope_ids", len(all_scope_ids) == len(set(all_scope_ids)))
    force = json.loads((ROOT / "verification/r1_g1_observation_revision_20261117/force_evidence_plan.json").read_text())
    check("force_reaction_trace_preserved", force["channel_id"] == "FORCE_REACTION" and force["requirement_ids"] == ["REQ-REV-09", "REQ-REV-16", "REQ-REV-17"] and "FORCE_REACTION" in rows[8]["channel_ids"] and all("H01" in methods[i]["procedure"] for i in [8, 15]))
    source = load("source_applicability.json")
    old_source = json.loads((ROOT / source["source_frozen_path"]).read_text())
    check("40_dispositions_unchanged", source["rows"] == old_source["rows"] and len(source["rows"]) == 40)
    check("RAW_not_promoted", all(not r["parameter_promotion"] and not r["numerical_engineering_use"] and r["REV_realized_value"] is None for r in source["rows"]))
    decisions = load("decision_register.json")
    check("all_decisions_open", len(decisions["rows"]) == 9 and all(r["status"] == "OPEN" and r["closure_evidence"] == [] and not r["closed_by_this_package"] for r in decisions["rows"]))
    check("country_unknown", decisions["operating_country"] is None)
    for name in ["definition_register.json", "method_catalog.json", "source_applicability.json", "decision_register.json"]:
        doc = load(name)
        check(name + ":gates_and_scope", doc["G1"] == "OPEN" and not doc["requirements_approved"] and not doc["engineering_started"] and not doc["source_states_solved"] and not doc["physical_tests_run"] and not doc["execution_permission"] and doc["independent_output_review"] == "NOT_RUN")
    manifest = load("input_manifest.json")
    for row in manifest["inputs"]:
        check("input_pin:" + row["path"], hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"])
    for folder, tree in manifest["protected_trees"].items():
        current = subprocess.check_output(["git", "rev-parse", "HEAD:" + folder], cwd=ROOT, text=True).strip()
        modified = subprocess.check_output(["git", "diff", manifest["base_main"], "--name-only", "--", folder], cwd=ROOT, text=True).strip()
        check("protected_tree:" + folder, current == tree and not modified)
    for name, expected_text in render().items():
        check("render_MATCH:" + name, (HERE / name).read_text() == expected_text)
    result = {"scope": "Author documentary traceability/preservation checks; not independent sufficiency or physical validation", "counts": {"PASS": sum(c["status"] == "PASS" for c in checks), "FAIL": sum(c["status"] == "FAIL" for c in checks)}, "scope_item_count": len(all_scope_ids), "checks": checks}
    return result


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result["counts"]["FAIL"]))
