# Геометрическая корректировка T-r4-layout-build-01

Исследовательские A/B, не конструкция REV. Tool code de377f0 побайтно сохранён; его WARNING review 214b055 не является review нового набора геометрии или нового анализатора.

Из корня после materialize LFS:

```sh
git lfs pull
/usr/bin/python3 cad/layout_correction/run_revision.py
/usr/bin/python3 cad/layout_correction/verify_output.py
python3 scripts/check_registry.py --check-git
```

FreeCAD 1.0.0/Part + /usr/bin/python3 3.13.5, Pillow/ReportLab как в проверенной среде. Исходный freecadcmd не используется. Команда сохраняет FCStd/STEP, PNG/SVG/PDF, перечни пар, service states, native witnesses, изменённые bounds и hashes. Проверенные cad/layout/*.py и models/rev_linked_scene/engine.py не модифицируются. Старые исходные inputs и results в cad/build/research_layout сохранены.

Редактировать исследовательские входы в [inputs.assumed.json](inputs.assumed.json); все численные значения имеют ASSUMED ID/revision/source, реальные registry UNKNOWN. FCStd редактируется через Spreadsheet Inputs, затем recompute; после ручной правки расчётные отчёты STALE до согласованной пересборки. Параметры и изображения синхронны с сохранённым набором rev6; исходные ID всех тел сохранены.

| Артефакт | До | После |
|---|---|---|
| A editable FCStd | [исходный](../build/research_layout/A/layout_A.FCStd) | [исправленный](../build/layout_correction/A/layout_A.FCStd) |
| B editable FCStd | [исходный](../build/research_layout/B/layout_B.FCStd) | [исправленный](../build/layout_correction/B/layout_B.FCStd) |
| A общий вид | [PNG](../build/research_layout/A/isometric.png) | [PNG](../build/layout_correction/A/isometric.png) |
| B общий вид | [PNG](../build/research_layout/B/isometric.png) | [PNG](../build/layout_correction/B/isometric.png) |
| Сечение узла заслонки | — | [before/after SVG](../build/layout_correction/gate_before_after.svg) |
| План выходного узла B | — | [before/after SVG](../build/layout_correction/stop_before_after.svg) |

STEP и четыре вида SVG/PDF/PNG, section/phase/load-path SVG лежат рядом с FCStd каждого варианта. Ограждения скрыты только на cutaway-видах, сохранены в моделях и матрицах; их перенос отдельно виден на плане B.

[Причины, численная геометрия до/после и результаты](../build/layout_correction/assessment.md). [Машинный отчёт](../build/layout_correction/assessment.json), [команды/версии/hash](../build/layout_correction/run.json), [параметрические изменения](change_inputs.json), [нативные контрпримеры до/после](../build/layout_correction/before_after_native.json).

Новая оркестрация, сервисные планы и классификатор assess.py требуют отдельного независимого review. Они не ослабляют core: raw_checked_tool сохраняет его исходные статусы и полные матрицы; дополнительная классификация не удаляет COLLISION, отделяет строгий overlap от условного face-touch и неизвестности. Политика face-touch — исследовательская гипотеза интерфейса, не физическое разрешение движения. Положительные пересечения при любой политике сохраняются.

Полный прямой/обратный рабочий ход покрывается reference sufficient A/B и точными event-partitions; short/collision/unknown не получают выдуманный READY. 12 отдельных сервисных последовательностей содержат все тела и возврат позиций. Новые gate/lock/stop/portal проверены против всех тел. Неустранённые статические и сервисные дефекты/UNKNOWN перечислены без сокрытия. Готовность всего пресса INDETERMINATE.

Строковые baseline-metadata source_commit_inputs/known_native_penetrations/tool_blockers в frozen checker исторические; текущий источник — новый input hash/run.json. Исходный run_all проверяет неизменность старой геометрии и сохраняется как regression harness старого C; командой новой геометрии является run_revision.py. История выявленных ошибок и двух пробных расстановок — history в новом output.

Реальные параметры, физические удержание/разгрузка/выдача/прочность/безопасность UNKNOWN. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Задача IN_REVIEW до независимого решения.

verify_output.py — отдельная новая самопроверка результатов: hashes, неизменность checked tool, 216 дополнительных строк guard/pump_motor и bridge/output_support по всей траектории, отсутствие новых penetration/envelope rows с добавленными телами и восстановление сервисных позиций. Результат verification/r4_layout_correction/final_checks.json, требует независимого review вместе с новой оркестрацией.
