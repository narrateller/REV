# Дозатор и гидростанция — ASSUMED A/B

T-r4-layout-build-01, R4 r4-linked-20261111. База a5d5bad6dd8928045512bca16836fd1d2544b7ca, RECHECK c2e96a58d7efd64ea3364b2bcbfb3f0642bbc430. Отдельные inputs.assumed.json rev8 зафиксированы до построения на 450e869. Реальные параметры REV UNKNOWN; все условные значения имеют ASSUMED-ID/revision. Точный C результата — в следующей эстафете, проверять C отдельно от H.

Все **34 прежних Python-модуля неизменны**, включая исследовательский core/layout/classifier/frame generator/verifier. Новая папка — адаптация checked public API к новой геометрии, самостоятельная область независимого review; прошлую приёмку инструмента на неё не переносить. Исходные модели/отчёты/акты/RECHECK/independent probes сохранены в своих папках.

[Отчёт](../build/feed_power/assessment.md), [конечный реестр](../build/feed_power/inventory/inventory.md), [native before/after](../build/feed_power/before_after_native.json), [точные изменения и ID](../build/feed_power/changes.json).

- [A FCStd](../build/feed_power/A/layout_A.FCStd), [A STEP](../build/feed_power/A/layout_A.step), [вид A](../build/feed_power/A/isometric.png).
- [B FCStd](../build/feed_power/B/layout_B.FCStd), [B STEP](../build/feed_power/B/layout_B.step), [вид B](../build/feed_power/B/isometric.png).
- До/после: doser_mount_before_after, doser_service_before_after, powerpack_before_after — PNG/SVG в output. Это native проекции; их наложение не самостоятельное доказательство positive solid volume.

**14 статических исходных native проникновений устранены. Шесть прежних проникновений при прямом подъёме дозатора через неподвижный бункер остаются BLOCKED и видимы в полных матрицах.** Для сервиса дозатора предложен дополнительный retract по существующей оси Y, затем UP/DOWN и возврат. Это исследовательский путь, не подтверждение дополнительного хода реального привода. Его реальная реализуемость INDETERMINATE (COTS/расстыковка/оснастка UNKNOWN). Положительные legacy объёмы не переименованы в INDETERMINATE и не скрыты разрешающими исключениями. Новый сервис проверяется отдельными полными all-pair сценами.

Также проверяются motor UP/DOWN, powerpack module UP/DOWN и tank после подъёма/парковки motor/двух плит. Все тела сохранены и возвращаются. Номинальный силовой/монтажный путь показан положительными площадями contact faces и zero common volume, но крепёж, радиальная фиксация, реальная стенка tank и прочность UNKNOWN. Рабочая геометрия doser_slide и ходы/оси всех прежних движущихся тел не менялись. Точные collar/ring float-derived границы нормализованы с явными revision/diff.

Из корня материализованного Git checkout:

```bash
git lfs pull
# Явная генерация:
/usr/bin/python3 -B cad/feed_power/generate.py
# Проверка отдельно; сохранять stdout вне publication-каталога:
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B -m unittest discover -s cad/feed_power -p 'test_*.py'
```

Verifier проверяет сохранённые manifest/каталог/хэши, actual FCStd/STEP/все QueryVolumes, strict eight-case cycle oracle, полные матрицы/critical evidence/остаток. Он не пишет входы/manifest/доказательства или diagnostic файл; только JSON/stdout и exit. Старый hardcoded frame verifier применим к своей прежней редакции; для этой папки нужен новый отдельный verifier. FreeCAD 1.0.0/Part, Python 3.13.5, PIL/reportlab/PySide2.QtSvg. Native binary metadata могут отличаться после явного rebuild; semantic/native/PNG повтор проверяется.

До генерации в копии проверяемого C сохранить исходные артефакты и запустить verifier дважды. Затем отдельная явная генерация и проверка. Временные JSON/логи направлять за пределы cad/feed_power и cad/build/feed_power; незарегистрированный файл внутри package даёт отказ каталога.

Весь пресс не принят, whole press READY INDETERMINATE. Остальные касания, оболочки и UNKNOWN видимы. Архитектура и ТЗ не утверждены; физические испытания NOT_RUN; G1 OPEN.

## Исправление R5-FP-NEW-B01

Входной акт `2592b470940cea886e033a999c889c15a92889f6` отклонил новый adapter из-за stale semantic evidence при изменённой траектории. Новая проверка пересчитывает все текущие пары/интервалы и заявленный состав/план движения; полный cached matrix/evidence/classification/assessment должен совпасть со свежим расчётом. `changed_body_IDs` выводится из текущих inputs, все пары сервисов обязательны, moving sets выводятся из реальных delta/method. Manifest hash этого не заменяет.

```bash
# Чистый расчёт текущих сервисов, JSON/exit без записи:
/usr/bin/python3 -B cad/feed_power/service_semantics.py
# Явная повторная генерация только semantic evidence/report, CAD не сохраняется:
/usr/bin/python3 -B cad/feed_power/generate.py --reanalyze
# Отдельная readonly проверка полного сохранённого пакета:
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
```

`CONFIRMED_NO_POSITIVE_VOLUME` — только геометрия полного пути в поддерживаемой модели, не физическое разрешение. Подтверждённый collision даёт BLOCKED, unknown/unsupported mandatory условие — INDETERMINATE; известный blocking дефект сохраняется и при одновременном unknown. Успех команды/negative expectation отделён от `limited_geometry_success`. Общий сервис и физическая выполнимость L-пути остаются INDETERMINATE. Составные ошибки и пять исходных R5 случаев — `test_service_semantics.py` и verification/r4_fp_fix/; B01 OPEN до независимого RECHECK.
