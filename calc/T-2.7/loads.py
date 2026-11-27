"""T-2.7 calculations and reproducibility checks. Run with Python 3.13."""

import argparse
from hashlib import sha256
import importlib.util
from itertools import product
import json
from math import exp, expm1, isclose, log
from pathlib import Path
import subprocess
import sys

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARAMS = "calc/T-2.6/params/params.t26a.yaml"
CRITERIA = "ops/criteria/design_criteria.yaml"
REFERENCE = HERE.parent / "T-2.2h" / "loads.py"

# Geometry and functions band() and janssen() copied from T-2.2h/loads.py.
# The transfer/shoe calibration is outside the loaded-roof comparison.
WIDTH_MM, HEIGHT_MM = 150., 60.
AREA_MM2 = WIDTH_MM * HEIGHT_MM
PERIMETER_MM = 2 * (WIDTH_MM + HEIGHT_MM)
WINDOW_X_MM = (5., 205.)
ROOF_LENGTH_MM = 90.
GATE_X_MM = WINDOW_X_MM[1] + ROOF_LENGTH_MM
LOADED_LENGTH_MM = 89.4


def band(face_MPa, K, decay_mm_inv, start_mm, end_mm, punch_x_mm):
    if start_mm >= end_mm:
        return {"interval_x_mm": None, "integral_MPa_mm": 0., "centroid_x_mm": None}
    pressure_MPa = face_MPa * K * exp(-decay_mm_inv * (start_mm - punch_x_mm))
    length_mm = end_mm - start_mm
    integral_MPa_mm = pressure_MPa * -expm1(-decay_mm_inv * length_mm) / decay_mm_inv
    centroid_x_mm = start_mm + 1 / decay_mm_inv - length_mm / expm1(decay_mm_inv * length_mm)
    return {"interval_x_mm": [start_mm, end_mm], "inlet_MPa": pressure_MPa,
            "integral_MPa_mm": integral_MPa_mm, "centroid_x_mm": centroid_x_mm}


def janssen(main_force_N, K, mu, length_mm):
    punch_x_mm = GATE_X_MM - length_mm
    decay_mm_inv = K * mu * PERIMETER_MM / AREA_MM2
    face_MPa = main_force_N / AREA_MM2
    roof = band(face_MPa, K, decay_mm_inv, max(WINDOW_X_MM[1], punch_x_mm), GATE_X_MM, punch_x_mm)
    shoe = band(face_MPa, K, decay_mm_inv, max(WINDOW_X_MM[0], punch_x_mm), WINDOW_X_MM[1], punch_x_mm)
    channel = band(face_MPa, K, decay_mm_inv, punch_x_mm, GATE_X_MM, punch_x_mm)
    gate_force_N = main_force_N * exp(-decay_mm_inv * length_mm)
    traction_N = mu * PERIMETER_MM * channel["integral_MPa_mm"]
    return {
        "K": K, "mu": mu, "length_mm": length_mm, "punch_x_mm": punch_x_mm,
        "main_force_N": main_force_N, "face_MPa": face_MPa, "decay_mm_inv": decay_mm_inv,
        "gate_force_N": gate_force_N, "wall_friction_N": traction_N,
        "axial_balance_error_N": main_force_N - gate_force_N - traction_N,
        "roof": roof | {"normal_force_N": WIDTH_MM * roof["integral_MPa_mm"]},
        "shoe": shoe | {"normal_force_N": WIDTH_MM * shoe["integral_MPa_mm"]},
        "floor_normal_force_N": WIDTH_MM * channel["integral_MPa_mm"],
        "each_side_normal_force_N": HEIGHT_MM * channel["integral_MPa_mm"],
    }


def bounds(values):
    return [min(values), max(values)]


def run_grid(pressures_MPa, pairs):
    return [
        janssen(pressure_MPa * AREA_MM2, K, mu, LOADED_LENGTH_MM)
        for pressure_MPa, (K, mu) in product(pressures_MPa, pairs)
    ]


def summarize(rows, pressures_MPa):
    return {
        "friction_pct": bounds([100 * row["wall_friction_N"] / row["main_force_N"] for row in rows]),
        "roof_force_kN_by_face_pressure_MPa": {
            str(pressure_MPa): bounds([
                row["roof"]["normal_force_N"] / 1000 for row in rows if row["face_MPa"] == pressure_MPa
            ]) for pressure_MPa in pressures_MPa
        },
    }


def read_sources():
    return yaml.safe_load((HERE / "sources.yaml").read_text(encoding="utf-8"))


def source_products(sources):
    reed = sources["repsa2012"]
    yield "repsa2012", None, "closed_die_end_forces", [
        {"mu_times_K": reed["K_assumed_by_authors"] * mu}
        for mu in reed["mu_inferred_by_authors"]
    ]
    holm = sources["holm2007"]
    for species, fit in holm["data"].items():
        yield "holm2007", species, "open_die_exponential_fit", [
            {"mu_assumed": mu, "nu_LR_fit": nu, "mu_times_nu_LR": mu * nu,
             "mu_times_nu_LR_reported_plus_minus_scaled": mu * spread}
            for mu, nu, spread in zip(
                holm["mu_assumed"], fit["fitted_nu_LR"], fit["reported_nu_LR_plus_minus"], strict=True
            )
        ]
    stelte = sources["stelte2011"]
    mu, nu = stelte["mu_assumed"], stelte["fitted_nu_LR"]
    yield "stelte2011", None, "open_die_exponential_fit", [
        {"mu_assumed": mu, "nu_LR_fit": nu, "mu_times_nu_LR": mu * nu,
         "mu_times_nu_LR_reported_plus_minus_scaled": mu * stelte["reported_nu_LR_plus_minus"]}
    ]


def calculate(data):
    project = data["project"]
    pressures_MPa = project["sensitivity_face_pressure_MPa"]
    K_grid, mu_grid = project["K_grid"], project["mu_grid"]
    baseline = run_grid(pressures_MPa, list(product(K_grid, mu_grid)))
    envelope_product = bounds([K * mu for K, mu in product(K_grid, mu_grid)])
    cases = []
    for key, species, method, estimates in source_products(data["sources"]):
        source = data["sources"][key]
        field = "mu_times_K" if method == "closed_die_end_forces" else "mu_times_nu_LR"
        products = [row[field] for row in estimates]
        # Sensitivity only. The literature does not independently identify K for these tests.
        derived_pairs = [(K, fitted_product / K) for K, fitted_product in product(K_grid, products)]
        rows = run_grid(pressures_MPa, derived_pairs)
        cases.append({
            "source": key, "species": species, "method": method,
            "url": source["url"], "locator": source["locator"],
            "estimates": estimates, "source_product_field": field, "source_product_range": bounds(products),
            "conditional_transfer_using_project_K": summarize(rows, pressures_MPa) | {"cases": rows},
        })
    high_K_rows = [row for row in baseline if row["K"] == max(K_grid)]
    params = yaml.safe_load((ROOT / PARAMS).read_text(encoding="utf-8"))
    nominal_face_MPa = params["main_cylinder"]["nominal_force_N"] / AREA_MM2
    return {
        "task": "T-2.7",
        "status": "STOP_OPERATOR_REVIEW",
        "geometry": {"width_mm": WIDTH_MM, "height_mm": HEIGHT_MM, "area_mm2": AREA_MM2,
                     "perimeter_mm": PERIMETER_MM, "loaded_length_mm": LOADED_LENGTH_MM,
                     "roof_length_mm": ROOF_LENGTH_MM},
        "sensitivity_face_pressure_MPa": pressures_MPa,
        "nominal_face_pressure_MPa": nominal_face_MPa,
        "project_envelope": summarize(baseline, pressures_MPa) | {
            "K_grid": K_grid, "mu_grid": mu_grid, "mu_times_K_range": envelope_product,
            "at_max_K": summarize(high_K_rows, pressures_MPa), "cases": baseline,
            "at_nominal_face_pressure": summarize(
                run_grid([nominal_face_MPa], [(max(K_grid), mu) for mu in mu_grid]), [nominal_face_MPa]
            ),
        },
        "literature": cases,
    }


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def number(value, digits=1):
    return f"{value:.{digits}f}".replace(".", ",")


def span(interval, digits=1):
    low, high = interval
    low_text, high_text = number(low, digits), number(high, digits)
    return low_text if low_text == high_text else f"{low_text}–{high_text}"


def loads_cells(summary, pressures_MPa):
    roof = summary["roof_force_kN_by_face_pressure_MPa"]
    return f'{span(summary["friction_pct"])} | ' + " / ".join(
        span(roof[str(pressure_MPa)], 0) for pressure_MPa in pressures_MPa
    )


def write_report(data, results):
    sources = data["sources"]
    envelope = results["project_envelope"]
    pressures_MPa = results["sensitivity_face_pressure_MPa"]
    nominal = envelope["at_nominal_face_pressure"]
    nominal_roof = next(iter(nominal["roof_force_kN_by_face_pressure_MPa"].values()))
    lines = [
        "# T-2.7 — нагрузка на стенки камеры REV",
        "",
        "**STOP по карточке.** В опыте Holm et al. восстановленный по выталкиванию сосны "
        "показатель μνLR = 0,195–0,198 превышает проектный предел μ·K = 0,180. "
        "Это сигнал возможной неконсервативности по осевой потере в другом режиме. "
        "Предельные K и μ древесного сырья REV ещё требуют измерения. "
        "[Holm et al. (2007), с. 2448, табл. 1 и рис. 6](https://doi.org/10.1021/ef070156l).",
        "",
        "Закрытая матрица Repsa и Kronbergs дала μ·K = 0,090–0,108 по измеренным торцевым "
        "усилиям на тростнике. Действующая огибающая по D-GK-15 и D-OP-18 сохраняется. "
        "Открытый вопрос оператору — утвердить ли натурные измерения на сырье REV. "
        "[Repsa и Kronbergs (2012), с. 295–299](https://www.iitf.lbtu.lv/conference/proceedings2012/Papers/051_Repsa_E.pdf).",
        "",
        "## Пересчёт по T-2.2h",
        "",
        "Сечение 150 × 60 мм, длина под нагрузкой 89,4 мм, крыша 90 мм. Давление REV в правой "
        "колонке — 100 / 150 / 200 МПа на входном торце материала. В колонке p опыта указана "
        "подготовка образца либо максимум при сжатии. Для литературных произведений "
        "крышу рассчитали **условно** при проектном K = 0,35–0,60. Литературное значение "
        "самого K для этих строк отсутствует. Звёздочка обозначает показатель μνLR открытого канала.",
        "",
        "| Источник | Материал | p опыта, МПа | Влажность, % | T, °C | K | μ | μ·K или μνLR* | Трение, % усилия | Крыша, кН при p REV 100 / 150 / 200 |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---|",
        "| [T-2.2h](calc/T-2.2h/loads.py), огибающая | REV | 100–200 | — | — | 0,35–0,60 | "
        "0,20–0,30 | " + span(envelope["mu_times_K_range"], 3) + " | "
        + loads_cells(envelope, pressures_MPa) + " |",
    ]
    labels = {"repsa2012": "Repsa и Kronbergs 2012", "holm2007": "Holm et al. 2007",
              "stelte2011": "Stelte et al. 2011"}
    for case in results["literature"]:
        source = sources[case["source"]]
        label = labels[case["source"]]
        if case["species"]:
            material = source["data"][case["species"]]["material"]
            pressure_MPa = source["preparation_pressure_MPa"]
            moisture = source["moisture_wet_basis_pct"]
            temperature = source["die_temperature"]
        else:
            material = source["material"]
            pressure_MPa = source.get("preparation_pressure_MPa", source.get("max_compaction_pressure_MPa"))
            moisture = source["moisture_pct"]
            temperature = source.get("die_temperature_C", "—")
        star = " *" if case["method"] == "open_die_exponential_fit" else ""
        lines.append(
            f'| [{label}]({case["url"]}) | {material} | {pressure_MPa} | {number(moisture)} | '
            f'{temperature} | — | — | {span(case["source_product_range"], 3)}{star} | '
            f'{loads_cells(case["conditional_transfer_using_project_K"], pressures_MPa)} |'
        )
    oak = sources["oak2022"]
    lines += [
        f'| [Wilczyński et al. 2022]({oak["url"]}) | {oak["material"]} | Нагрузка 34 кН | 9,0 | '
        "25 | — | 0,25 | — | — | — |",
        "",
        f'При K = 0,60 получено {span(nominal["friction_pct"])} % трения и '
        f'{span(nominal_roof, 0)} кН на крышу при {number(results["nominal_face_pressure_MPa"], 2)} МПа. '
        "Максимум нормальной силы "
        "при этом K соответствует μ = 0,20. Чем больше μ, тем быстрее затухает осевое "
        "давление вдоль камеры. При фиксированном произведении μ·K нормальная сила "
        "крыши прямо пропорциональна K. Поэтому более низкое μ·K само по себе не даёт "
        "основания уменьшать нормальную нагрузку. Число μ = 0,25 для дуба относится к отдельному "
        "опыту скольжения по стальной пластине. Места в источниках и условия опытов "
        "приведены в [обзоре](calc/T-2.7/literature.md).",
        "",
        "## Испытание сырья для решения оператора",
        "",
        "Закрытая матрица REV с датчиками усилия на пуансоне и противоупоре, "
        "датчиками нормального давления на крыше и боковой стенке, сменными вкладышами "
        "и контролем температуры. План — 100 / 150 / 200 МПа, влажность 6 / 10 / 15 % "
        "на влажной основе, стенка 80 / 120 °C, длина под нагрузкой 40 / 65 / 89,4 мм, "
        "по пять независимых повторов на режим и два вида сырья. Из спада осевого "
        "усилия определить μ·K, из нормального давления и осевой нагрузки в том же "
        "сечении — K, затем оценить μ. Самая большая неопределённость — локальный K "
        "на крыше в конце сжатия REV при реальной фактуре вкладыша, плотности и ориентации частиц.",
        "",
        "КГАСУ — кандидат для полноразмерной установки, Университет Мишкольца — для пилота, "
        "DBFZ — для верификации методики брикетирования. Ориентир 8–12 недель после утверждения "
        "при доступном стенде. Стоимость — нет данных. "
        "[Программа испытания и первоисточники](calc/T-2.7/literature.md).",
        "",
        "## Проверка неизменности параметров",
        "",
        "G-PFACE PASS при 168,89 МПа, G-DOSE PASS при 396 мм. Полный скрипт также выводит "
        "G-CYCLE FAIL при 8,719 с на заданном входе, справочно по D-GK-13 и D-OP-16.",
    ]
    (ROOT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def generate():
    data = read_sources()
    results = calculate(data)
    write_json(HERE / "results.json", results)
    write_report(data, results)
    envelopes = results["project_envelope"]
    write_json(ROOT / "metrics.json", {
        "task": results["task"], "status": results["status"], **results["geometry"],
        "project_mu_times_K_range": envelopes["mu_times_K_range"],
        "project_friction_pct_full_grid": envelopes["friction_pct"],
        "project_friction_pct_at_K_max": envelopes["at_max_K"]["friction_pct"],
        "nominal_face_pressure_MPa": results["nominal_face_pressure_MPa"],
        "project_roof_force_kN_at_K_max_at_nominal_face_pressure": next(iter(
            envelopes["at_nominal_face_pressure"]["roof_force_kN_by_face_pressure_MPa"].values()
        )),
        "repsa_closed_die_mu_times_K_range": results["literature"][0]["source_product_range"],
        "holm_pine_open_die_mu_times_nu_LR_range": results["literature"][1]["source_product_range"],
        "stelte_spruce_open_die_mu_times_nu_LR": results["literature"][3]["source_product_range"][0],
    })


def verify():
    gate_cmd = ["ops/gates/calc_gates.py", "--params", PARAMS, "--criteria", CRITERIA,
                "--out", str(ROOT / "gates.t27.json")]
    inputs = [ROOT / PARAMS, ROOT / CRITERIA, ROOT / "DECISIONS.md", REFERENCE]
    initial_hashes = [sha256(path.read_bytes()).hexdigest() for path in inputs]
    gate_run = subprocess.run([sys.executable, "-B", *gate_cmd], cwd=ROOT, check=False)
    gate_report = json.loads((ROOT / "gates.t27.json").read_text(encoding="utf-8"))
    gates = {gate["id"]: {key: gate[key] for key in ("status", "value", "unit")}
             for gate in gate_report["gates"]}
    results_path = HERE / "results.json"
    subprocess.run([sys.executable, "-B", str(Path(__file__).resolve())], check=True)
    first = results_path.read_bytes()
    subprocess.run([sys.executable, "-B", str(Path(__file__).resolve())], check=True)
    second = results_path.read_bytes()

    sys.path.insert(0, str(REFERENCE.parent))
    spec = importlib.util.spec_from_file_location("t22h_loads", REFERENCE)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    results = json.loads(second)
    envelope = results["project_envelope"]
    all_rows = envelope["cases"] + [
        row for case in results["literature"] for row in case["conditional_transfer_using_project_K"]["cases"]
    ]
    max_balance_error_N = max(abs(row["axial_balance_error_N"]) for row in all_rows)
    report_bytes = (ROOT / "report.md").read_bytes()
    report = report_bytes.decode("utf-8")
    checks = {
        "G-PFACE": gates["G-PFACE"]["status"] == "PASS",
        "G-DOSE": gates["G-DOSE"]["status"] == "PASS",
        "gate_values_match_report": isclose(gates["G-PFACE"]["value"], results["nominal_face_pressure_MPa"])
        and gates["G-DOSE"]["value"] == 396 and round(gates["G-CYCLE"]["value"], 3) == 8.719,
        "two_fresh_runs_identical_results_json": first == second,
        "report_utf8_without_question_mark_or_replacement": "?" not in report and "\ufffd" not in report,
        "copied_model_matches_upstream": all(
            row == reference.janssen(row["main_force_N"], row["K"], row["mu"], row["length_mm"])
            for row in all_rows
        ),
        "axial_force_balance": max_balance_error_N < 1e-8,
        "closed_die_product_recovered_from_pressure_loss": all(isclose(
            row["K"] * row["mu"],
            -log(row["gate_force_N"] / row["main_force_N"])
            * AREA_MM2 / (PERIMETER_MM * row["length_mm"]),
        ) for row in all_rows),
        "project_inputs_unchanged": initial_hashes == [sha256(path.read_bytes()).hexdigest() for path in inputs],
        "calc_directory_size_below_2_MB": sum(
            path.stat().st_size for path in HERE.rglob("*") if path.is_file()
        ) <= 2_000_000,
    }
    write_json(ROOT / "self_check.json", {
        "task": "T-2.7", "status": "PASS" if all(checks.values()) else "FAIL",
        "cmd_gate": [sys.executable, *gate_cmd], "gate_exit_code": gate_run.returncode,
        "gate_overall": gate_report["overall"], "gates": gates, "checks": checks,
        "calc_cases_checked": len(all_rows), "max_axial_balance_error_N": max_balance_error_N,
        "results_sha256": sha256(second).hexdigest(), "report_bytes": len(report_bytes),
    })
    if not all(checks.values()):
        raise SystemExit("T-2.7 checks failed. See self_check.json.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Run gates and check two independent executions.")
    if parser.parse_args().verify:
        verify()
    else:
        generate()
