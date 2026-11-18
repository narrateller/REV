"""Render proposed documentary definitions; never execute engineering methods."""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUTS = ("definition_register.md", "verification_plan.md", "readiness.md", "source_applicability.md", "quantity_crosswalk.md", "record_retention_plan.md")


def load(name):
    return json.loads((HERE / name).read_text())


def render():
    register = load("definition_register.json")
    methods = load("method_catalog.json")
    decisions = load("decision_register.json")
    source = load("source_applicability.json")
    limits = (
        "DRAFT / NOT_APPROVED / independent OUTPUT-review NOT_RUN. Общий WARNING. "
        "Новых инженерных чисел, назначений и разрешений выполнения нет. "
        "42 состояния не рассчитаны; §4/5/6 NOT_RUN; G1 OPEN; W02/physical READY NO-GO. "
        "Прочность, устойчивость и реальные реакции не подтверждены. "
        "Численный/физический этап, CAD-build/rebuild и испытания не начинались и не разрешены."
    )
    text = ["# Определения критериев всех REQ/VAL — проект", "", limits, "",
            "Это новая надстройка определений над неизменённой rev8 и исправленным supplement. "
            "Она не заменяет их тексты и не наследует их review на новый target. "
            "Предложенные составы области ниже ещё должны пройти независимую оценку достаточности. "
            "Предложение метода DM не означает утверждения метода или выполнения проверки.", ""]
    for row in register["rows"]:
        text.extend([f"## {row['requirement_id']} / {row['validation_id']} — {row['object']}", "",
                     row["requirement_text"], "", f"Режим: {row['mode']}. Тип: {row['criterion_kind']}.", "",
                     "Предложенная область определения:", ""])
        text.extend(f"- {s['scope_item_id']}: {s['description']}." for s in row["proposed_enumerated_scope"])
        text.extend(["", "Нужно определить: " + "; ".join(row["observations_to_define"]) + ".", "",
                     f"Документальный метод: {row['definition_method_id']} / DRAFT-01. "
                     f"Будущий предикат соответствия: {row['future_conformity_predicate_ref']}.", "",
                     "Будущие поля доказательства: " + ", ".join(row["future_evidence_fields"]) + ". "
                     "Каналы: " + ", ".join(row["channel_ids"]) + ".", "",
                     "Открытые определения: " + "; ".join(row["open_definition_decisions"]) + ".", "",
                     "Численный предел, единица собственного критерия, допуск, допустимая неопределённость "
                     "и назначенный инженерный владелец: UNKNOWN. Для чистого качественного аудита численная "
                     "метрология неприменима только к его качественным подутверждениям. "
                     f"Предлагаемые функции: {row['suggested_engineering_functions']}; это не назначения. "
                     "Владелец документальной координации — действующая R1. Утверждение — отдельное решение пользователя.", ""])
    plan = ["# Проект документальных методов и будущей проверки", "", limits, "",
            "## DOC-DEFINITION-AUDIT-01 / DRAFT-01", ""]
    plan.extend(f"{i}. {step}." for i, step in enumerate(methods["common_protocol"]["steps"], 1))
    plan.extend(["", "Предложенные диспозиции: INCLUDED, JUSTIFIED_EXCLUSION, UNRESOLVED. "
                 "Отсутствие ответа/источника — UNRESOLVED. Исключения требуют обоснования и независимой оценки. "
                 "Документальная полнота определения и фактическое соответствие машины — отдельные решения.", "",
                 "DOCUMENTARY_AUDIT применим только к чистым качественным подутверждениям. "
                 "MIXED/NUMERIC/MODEL сохраняют применимые единицы, калибровку, время, неопределённость, "
                 "покрытие и контроль модели. Физический метод, средства, серия, критерии остановов и "
                 "разрешение выполнения не выбираются этими документальными DM.", ""])
    for method in methods["rows"]:
        plan.extend([f"## {method['method_id']} — {method['requirement_id']} / {method['validation_id']}", "",
                     method["procedure"], "",
                     "Входная область: " + ", ".join(method["input_scope_items"]) + ". "
                     "Выход: " + ", ".join(method["output_record_fields"]) + ". "
                     "Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.", ""])
    ready = ["# Решения, необходимые для согласуемого G1", "", limits, "",
             "BP500 — основа; E55/WEIMA/ARS по релевантности. Площадка адаптируется под пресс. "
             "Страна эксплуатации UNKNOWN: вопрос уже задан, ответа нет. Изготовление в РФ не определяет юрисдикцию.", "",
             "| Открыто | REQ | Что нужно для закрытия |", "| --- | --- | --- |"]
    ready.extend(f"| {x['issue_id']} | {', '.join(x['requirement_ids'])} | {x['closure_needed']} |" for x in decisions["rows"])
    ready.extend(["", "Новая редакция не закрывает B01/B02/B03 и противоречия первоисточников. "
                  "R5 должен самостоятельно оценить достаточность определений и программы на exact новом C. "
                  "Прежние акты остаются действующими только для своих exact C; DOC01/TRACE02 не переоткрываются "
                  "задним числом и не считаются автоматически закрытыми для изменённого выхода.", "",
                  "После независимого review R1 обрабатывает замечания и готовит конкретный согласуемый пакет. "
                  "ТЗ/G1 утверждает пользователь отдельно. Будущие G2–G4 результаты, готовый полный CAD и "
                  "физические испытания не требуются вместо определения требований G1. Дата G1 UNKNOWN.", ""])
    sources = ["# Применимость всех референтных полей", "", limits, "",
               "Все диспозиции перенесены побайтно по значениям полей из замороженной rev8. "
               "Числа остаются только в scoped RAW-кандидате; инженерное использование и повышение запрещены.", "",
               "| Поле | Референс | Диспозиция | REQ |", "| --- | --- | --- | --- |"]
    sources.extend(f"| {r['field_id']}@{r['candidate_revision']} | {r['source']} | {r['disposition']} | {', '.join(r['requirement_ids'])} |" for r in source["rows"])
    outputs = dict(zip(OUTPUTS[:4], ("\n".join(x) for x in [text, plan, ready, sources])))
    crosswalk = load("quantity_crosswalk.json")
    cross = ["# Явная привязка плотности и массы", "", limits, "", "Предлагаемые привязки; фактические величины, методы и критерии UNKNOWN. OBS-01 остаётся OPEN до независимого recheck.", ""]
    for row in crosswalk["rows"]:
        cross.extend([f"## {row['mapping_id']}", "", f"{row['source_text_locator']} → {', '.join(row['scope_item_ids'])}; {row['requirement_id']}/{row['validation_id']}, канал {row['channel_id']}.", "", row["definition_needed"], ""])
    retention = load("record_retention_plan.json")
    keep = ["# DM03: сохранение исходов всех циклов", "", limits, "", "Проект правила NOT_APPROVED / execution NOT_RUN; OBS-02 OPEN до независимого recheck.", "", "Обязательные будущие поля: " + ", ".join(retention["required_future_fields"]) + ".", ""]
    keep.extend(f"- {rule}" for rule in retention["rules"])
    keep.extend(["", "Связи полного учёта: " + ", ".join(retention["full_series_accounting_refs"]) + ".", "", "Изделие/измерение может отсутствовать; запись попытки цикла, его исход, качество, причина отсутствия и диспозиция сохраняются. Фактических циклов/измерений/результатов здесь нет.", ""])
    outputs["quantity_crosswalk.md"] = "\n".join(cross)
    outputs["record_retention_plan.md"] = "\n".join(keep)
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, text in render().items():
        (args.output_dir / name).write_text(text)
    print(f"Rendered {len(OUTPUTS)} documentary outputs; no engineering execution")
