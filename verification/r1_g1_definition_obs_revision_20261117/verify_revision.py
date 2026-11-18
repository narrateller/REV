"""Verify bounded documentary correction and frozen evidence preservation."""
import hashlib
import json
import subprocess
from pathlib import Path

from render_register import HERE, render

ROOT = HERE.parents[1]
OLD = ROOT / "verification/r1_g1_definition_register_20261117"


def load(path):
    return json.loads(path.read_text())


def verify():
    checks = []

    def check(name, condition):
        checks.append({"id": name, "status": "PASS" if condition else "FAIL"})

    new = load(HERE / "definition_register.json")["rows"]
    old = load(OLD / "definition_register.json")["rows"]
    methods = load(HERE / "method_catalog.json")["rows"]
    prior_methods = load(OLD / "method_catalog.json")["rows"]
    check("all22_REQ_VAL_order_preserved", len(new) == len(old) == len(methods) == 22 and [r["requirement_id"] for r in new] == [r["requirement_id"] for r in old])
    all_ids = {s["scope_item_id"] for r in new for s in r["proposed_enumerated_scope"]}
    check("146_unique_scope_items", len(all_ids) == sum(len(r["proposed_enumerated_scope"]) for r in new) == 146)
    row_allowed = {"proposed_enumerated_scope", "observations_to_define", "open_definition_decisions", "additional_definition_evidence_fields"}
    method_allowed = {"revision_label", "input_scope_items", "procedure", "quantity_crosswalk_ref", "future_record_retention_ref", "required_future_cycle_fields"}
    for i, (row, prior, method, pm) in enumerate(zip(new, old, methods, prior_methods)):
        rid = row["requirement_id"]
        if i not in [1, 2]:
            check(rid + ":unchanged_full_row_and_method", row == prior and method == pm)
        else:
            check(rid + ":bounded_row_fields", {k:v for k,v in row.items() if k not in row_allowed} == {k:v for k,v in prior.items() if k not in row_allowed})
            check(rid + ":old_scope_prefix_preserved", row["proposed_enumerated_scope"][:-1] == prior["proposed_enumerated_scope"])
            check(rid + ":old_observations_and_gaps_preserved", row["observations_to_define"][:-1] == prior["observations_to_define"] and row["open_definition_decisions"][:-1] == prior["open_definition_decisions"])
            check(rid + ":bounded_method_fields", {k:v for k,v in method.items() if k not in method_allowed} == {k:v for k,v in pm.items() if k not in method_allowed})
            check(rid + ":DRAFT02_scope_link", method["revision_label"] == "DRAFT-02" and method["input_scope_items"] == [s["scope_item_id"] for s in row["proposed_enumerated_scope"]])
        check(rid + ":no_fabricated_engineering_values", all(row["numeric_criterion"][k] is None for k in ["value", "unit", "tolerance", "uncertainty_acceptance_limit"]) and row["numeric_criterion"]["approved_parameter_refs"] == [])
        check(rid + ":no_results_or_engineering_owner", row["actual_evidence_records"] == [] and row["assigned_engineering_owner_session"] is None and row["future_result_status"] == "NOT_RUN" and method["actual_results"] == [] and method["future_physical_method_revision"] is None)
    check("all144_original_scope_items_retained", all(s in new[i]["proposed_enumerated_scope"] for i,row in enumerate(old) for s in row["proposed_enumerated_scope"]))
    check("density_and_mass_items", new[1]["proposed_enumerated_scope"][-1]["scope_item_id"] == "DEF-02-G" and new[2]["proposed_enumerated_scope"][-1]["scope_item_id"] == "DEF-03-F")
    mappings = load(HERE / "quantity_crosswalk.json")["rows"]
    check("four_quantity_mappings", {r["mapping_id"] for r in mappings} == {"DENSITY_DEFINITION", "BULK_DENSITY_DEFINITION", "PRODUCT_MASS_DEFINITION", "RESIDUE_MASS_DEFINITION"})
    for row in mappings:
        check(row["mapping_id"] + ":controlled_scope_links", bool(row["scope_item_ids"]) and all(x in all_ids for x in row["scope_item_ids"]) and row["source_text_locator"] and row["channel_path"])
        check(row["mapping_id"] + ":no_value_or_execution", all(row[k] is None for k in ["value", "unit", "tolerance", "method_revision"]) and row["actual_records"] == [] and row["unknown_reason"])
    retention = load(HERE / "record_retention_plan.json")
    required = {"cycle_id", "outcome", "quality_flag", "missing_reason", "disposition", "raw_event_refs", "series_accounting_refs"}
    check("DM03_all_cycle_fields", required <= set(methods[2]["required_future_cycle_fields"]) == set(retention["required_future_fields"]))
    check("DM03_removes_ambiguous_phrase", "предусмотреть отсутствие результата" not in methods[2]["procedure"] and "запись цикла и его исход не удаляются" in methods[2]["procedure"])
    check("full_series_links", {"DEF-01-E", "DEF-04-D", "REQ-REV-22", "VAL-REV-22"} <= set(retention["full_series_accounting_refs"]))
    check("missing_reason_schema_mapping", retention["field_mapping_to_retained_schema"]["missing_reason"] == "evidence_schema.required_fields.unknown_reason")
    check("no_retention_execution", retention["execution_status"] == "NOT_RUN" and retention["actual_records"] == [] and retention["retention_duration"] is None and retention["retention_duration_unknown_reason"])
    for name in ["source_applicability.json", "decision_register.json"]:
        check(name + ":full_rows_unchanged", load(HERE / name)["rows"] == load(OLD / name)["rows"])
    obs = load(HERE / "observations.json")
    check("both_observations_still_open", len(obs["rows"]) == 2 and all(r["status"] == "OPEN_PENDING_INDEPENDENT_RECHECK" and r["closed_by_R1"] is False for r in obs["rows"]))
    for name in ["definition_register.json", "method_catalog.json", "source_applicability.json", "decision_register.json", "quantity_crosswalk.json", "record_retention_plan.json"]:
        d = load(HERE / name)
        check(name + ":scope_limits", d["G1"] == "OPEN" and d["independent_output_review"] == "NOT_RUN" and all(d[k] is False for k in ["requirements_approved", "engineering_started", "source_states_solved", "physical_tests_run", "execution_permission"]))
    manifest = load(HERE / "input_manifest.json")
    for row in manifest["inputs"]:
        check("frozen_input:" + row["path"], hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"])
    for folder, tree in manifest["protected_trees"].items():
        current = subprocess.check_output(["git", "rev-parse", "HEAD:" + folder], cwd=ROOT, text=True).strip()
        diff = subprocess.check_output(["git", "diff", manifest["working_base"], "--name-only", "--", folder], cwd=ROOT, text=True).strip()
        check("protected_tree:" + folder, current == tree and not diff)
    for name, text in render().items():
        check("renderer_MATCH:" + name, (HERE / name).read_text() == text)
    return {"scope": "Author bounded-change/traceability/preservation checks; not independent sufficiency, closure or physical validation", "counts": {"PASS": sum(x["status"] == "PASS" for x in checks), "FAIL": sum(x["status"] == "FAIL" for x in checks)}, "checks": checks}


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result["counts"]["FAIL"]))
