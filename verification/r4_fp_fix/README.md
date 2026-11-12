# Исправление R5-FP-NEW-B01 — полный сервисный semantic pipeline

R4 r4-linked-20261111, T-r4-layout-build-01. Входной акт **2592b470940cea886e033a999c889c15a92889f6**, проверяемый исходный C **8fbbef00023e146e32cb6ff290a0c19408ca13b5**. Новый независимый RECHECK NOT_RUN; **B01 OPEN** до решения R5. Прежние 14 геометрических исправлений и исходный L-путь приняты независимым актом только в конечной ASSUMED-области с WARNING.

## Исходная ошибка и воспроизведение

`before_counterexamples.json`, `before.log`: неизменённый независимый probe выполнен в отдельном clone до правки. Все пять проверяемых verifier-команд дали ложный exit 0 / PASS; источник кода/входы/native модели не менялись. Причина каждого случая — causes.md. Подъём без retract A/B, lift-before-retract и неподвижная front plate имеют независимо полученные positive native witness; rotation мотора неподдержан frozen engine. Успешный exit старого probe означает воспроизведение ошибки, не исправление.

## Исправление

`service_semantics.py` заново рассчитывает полный путь из текущих service state/time:

- обязательный набор сцен/фаз, начальные позы, registered body IDs/shape descriptors, состав и порядок движений из ASSUMED-плана;
- все пары каждого участка, включая неподвижные/неизменённые тела, actual raw matrix и полный нормированный интервал;
- обязательную поддержку метода/координат/времени, известные коллизии отдельно от неизвестных условий;
- межфазную непрерывность, номинальный возврат, method/plan/evidence completeness;
- сохранённые flags/counts не заменяют текущий расчёт; metadata группы сцены не может скрыть подтверждённую коллизию зарегистрированного solid.

Известная коллизия, доказанный разрыв/нарушение плана/возврата блокируют полный путь. Unknown/unsupported обязательный метод/участок/состав без блокирующего доказанного дефекта дают INDETERMINATE. Даже набор collision-free интервалов не подтверждает разорванный путь. Curve-bound overlap не выдаётся за доказанную solid-коллизию или clearance: при недостаточном методе остаётся INDETERMINATE.

Раздельные результаты:

| Поле | Значение |
|---|---|
| execution / calculation_execution | Команда/расчёт выполнены, не оценка пригодности |
| test_evaluation / matches_test_expectation | Совпадение с обязательным ожиданием, включая отрицательный legacy тест |
| interval_geometry_outcome | Наличие/неизвестность positive volume на рассчитанных интервалах |
| geometric_path_outcome / limited_geometry_success | Полный заявленный геометрический путь с continuity/plan/return/method |
| overall_service_outcome | BLOCKED при доказанном дефекте, иначе INDETERMINATE из-за UNKNOWN физических обязательных условий |
| physical_feasibility | Всегда INDETERMINATE для этой исследовательской модели |

В исходном корректном пакете: 20 geometric paths CONFIRMED_NO_POSITIVE_VOLUME, 2 legacy paths BLOCKED. Итог физических сервисов **20 INDETERMINATE / 2 BLOCKED**. Успех negative expectation legacy не делает его limited_geometry_success: false.

`service_evidence.py` связывает свежий расчёт со всеми сохранёнными matrices, interval_rows/evidence, classifications, assessment и service report. Changed-set выводится из текущих inputs, moving sets — из actual delta/method; все сервисные пары обязательны. Проверяются значения, не только состав ID/порядок строк. Полные counts/coverage тоже пересчитываются. Canonical native adapter/все QueryVolumes и strict eight-case work oracle сохранены.

Generator, presentation и readonly verifier используют этот расчёт. `generate.py --reanalyze` явно обновляет derived evidence/report из сохранённого фактического пути и **не сохраняет CAD**. Он не заменяет неправильный путь каноническим и не заверяет stale пакет; unexpected BLOCKED/INDETERMINATE даёт validation failure. `present.py --report-only` показывает свежие фактические outcomes и возвращает exit 1 при неверном пути. Verifier ничего не пишет и не ремонтирует, включая отказы.

Необходимый diff: новые service_semantics/service_evidence/service_fixtures/tests; common.py (input-derived set, все сервисные пары); generate.py (fresh aggregation/explicit reanalysis), present.py (fresh report/actual path), verify_output.py (fresh gate и полная сверка). **Все 34 прежних frozen модуля без изменений.** Новая правка не ослабляет принятый engine/другие закрытые блокеры.

## Результаты и сохранность

- unit_tests.json: шесть наборов; исходные 102 теста сохранены и восемь новых сервисных тестов, **110 всего**, все exit 0. Пять исходных случаев, четыре compound/unknown случая, сохранённый L, negative expectation отдельно от успеха пути, пропавшая фаза/сцена, time-gap и подмена group metadata.
- after/original_R5_after.json: тот же неизменённый независимый probe на исправленном verifier, actual exit **1 во всех пяти**, без записи. Первые четыре geometric path BLOCKED, пятый INDETERMINATE.
- after/commands.json, results.json: pure calculation → aggregation → report CLI → reanalysis CLI → verifier CLI. Первые пять и compound известная collision+unknown проверяются всей цепью; прочие составные ошибки — calculation и verifier. Правка исходных fixtures/manifest выполняется только harness в disposable clone. Failed reanalysis не ремонтирует и не заверяет сцену.
- Два verifier после явного восстановления fixtures сравниваются по stdout/stderr и SHA/size/mtime, actual saved derived данные целиком пересчитываются. Snapshot включает исходники/inputs/native CAD/evidence; .git/bytecode не являются проверяемыми артефактами.
- geometry_preservation.json фиксирует bytes входов/CAD/STEP/видов/нативных before-after/interfaces/inventory/actual scene matrices/classifications исходного C. Эти геометрические данные не менялись. Переизданы только semantic aggregates/report/расширенное interval evidence. Все **шесть BLOCKED legacy native-пар**, **14 устранённых static-пар** и исходный L-путь сохранены. Старые review/RECHECK/independent probes сохранены.

Первые промежуточные два fresh verifier прошли и заархивированы в intermediate_*; затем агрегатор дополнен whole-path/time-gap и registered metadata/missing-scene проверками. Финальную текущую версию проверяет after/ с восстановленными baseline fixtures. Не переносить промежуточный результат автоматически на последующую версию кода.

## Команды

Сначала checkout точного C и materialize LFS; сохранить оригинал и проверить до генерации. Команды из корня:

```bash
/usr/bin/python3 -B cad/feed_power/service_semantics.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
# Явная semantic regeneration без изменения native CAD:
/usr/bin/python3 -B cad/feed_power/generate.py --reanalyze
/usr/bin/python3 -B cad/feed_power/verify_output.py
# Отдельная копия/fixtures:
/usr/bin/python3 -B verification/r4_fp_fix/recheck_cases.py
/usr/bin/python3 -B -m unittest discover -s cad/feed_power -p 'test_*.py'
```

Полный build CAD при необходимости: generate.py без --reanalyze. Stdout/log сохранять вне publication-каталога. Geometry native models/query volumes отражают прежнюю ограниченную исследовательскую область; реальные COTS/расстыковка/опоры/масса/подъём/контакты/допуски/безопасность UNKNOWN.

Новый точный C публикуется в следующем H/NEXT_MODEL/капсуле. Задача IN_REVIEW, не DONE. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 OPEN, весь пресс READY INDETERMINATE.
