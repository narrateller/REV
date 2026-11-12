# Рамная/монтажная коррекция A/B — ASSUMED research

R4 / r4-linked-20261111, T-r4-layout-build-01. Продолжение `66924aed1cb2d193b9883d2140d85560b1e4b0cb` по независимому акту `04efe5703e339112b7d007665b9f3672f0572d37`.
Входы rev7 зафиксированы **до построения** на `17501de`; точный code/results C для review указан в актуальной эстафете `NEXT_MODEL.md` и капсуле задачи следующим документальным коммитом. Ветка результата — `work-r4/build-layout/r4-linked-20261111`, без слияния в main.

Результат и пределы — [assessment.md](../build/frame_mount/assessment.md). Полные модели: [A FCStd](../build/frame_mount/A/layout_A.FCStd), [A STEP](../build/frame_mount/A/layout_A.step), [B FCStd](../build/frame_mount/B/layout_B.FCStd), [B STEP](../build/frame_mount/B/layout_B.step). Параметры редактируются в Spreadsheet; сохранены выражения Part::Box/Part::Cylinder. В общих видах ограждения скрыты для обзора, но присутствуют в CAD и проверках.

Общие виды: [A](../build/frame_mount/A/isometric.png), [B](../build/frame_mount/B/isometric.png). До/после: [рама](../build/frame_mount/frame_before_after.png), [поперечины](../build/frame_mount/crossbar_before_after.png), [U-опора](../build/frame_mount/seat_before_after.png), [сервис](../build/frame_mount/service_before_after.png); соответствующие SVG рядом. Проекции не заменяют проверку положительного объёма в 3D.

Факты: 346 709 строк всех пар, 114 156 поддерживаемых строк новой группы без положительного объёма и 28 намеренно неизвестных строк INDETERMINATE. 18 native сравнений «до/после»; 58 положительных площадей условных сопряжений; 658 строк прежних целевых пар без регрессии; 3 672 строки цилиндровых сервисных пар; 14 непрерывных сервисных последовательностей с восстановлением позиций. Восемь limited исходов/strict cycle assertions, фактические FCStd/STEP/все QueryVolumes и повтор построения прошли. Все старые ID сохранены: A 70→79, B 68→77.

Конечный реестр [до](../../verification/r4_frame_mount/before/inventory.md) и [после](../build/frame_mount/inventory/inventory.md) различает нативное проникновение, предполагаемое геометрическое сопряжение, оболочки и INDETERMINATE. После остаётся **20 нативно подтверждённых пар проникновения**: монтаж дозатора/кармана/бункера, сервис дозатора и бак/мотор; полный перечень в JSON с фазами и нативными свидетельствами. Остальные непредписанные контакты и неизвестности не скрыты. Общий пресс BLOCKED оставшимися проникновениями, READY INDETERMINATE.

Проверенные **23 прежних Python-модуля неизменны** (frozen_tool.json), включая builder, actual-CAD validator, core, классификатор и strict cycle oracle на 66924ae. Дополнительные файлы этой папки — новые средства оркестрации, отчёта и supplementary self-check, требуют собственного review. Они не расширяют область принятого R5 акта. Старые входы, CAD, результаты, акты, RECHECK и независимые probes/evidence сохранены. Отдельное предупреждение об ограничении входных путей внутри ROOT сохраняется.

Из корня репозитория с FreeCAD 1.0.0/Part, `/usr/bin/python3` 3.13.5, PIL/reportlab и PySide2.QtSvg:

```bash
git lfs pull
/usr/bin/python3 -B cad/frame_mount/generate.py
/usr/bin/python3 -B cad/frame_mount/verify_output.py
/usr/bin/python3 -B cad/frame_mount/verify_output.py
```

FCStd и STEP нужно материализовать из LFS **до** проверки. `generate.py` — отдельная явная команда: run → geometry_evidence → figures → report → generation.json → publication_manifest.json. Run хэширует только собственные выходы, не предыдущий publication manifest и не файлы последующих стадий. Manifest версии 2 включает сохранённые исходники/входы/CAD/evidence; сам manifest исключён из собственного списка хэшей.

`verify_output.py` **ничего не записывает**: читает уже сохранённый manifest, проверяет полный каталог/хэши, actual CAD/STEP/все QueryVolumes, матрицы и доказательства, печатает детерминированный JSON в stdout и возвращает exit code. Два последовательных вызова должны дать одинаковый JSON/exit, сохранив байты и mtime проверяемых файлов. Missing/corrupt/stale файлы отклоняются без исправления. Старый `verification/r4_frame_mount/final_checks.json` — сохранённая история исходного C; verifier его больше не обновляет. При необходимости сохранять stdout внешним перенаправлением за пределами проверяемого каталога (например, `/tmp/verify-frame.json`).

После явной повторной генерации возможны отличия бинарных служебных данных FCStd/STEP и временных путей run.json. Проверяются неизменность геометрических/сценарных доказательств и native семантика, а не одинаковый бинарный сериализационный штамп. B01 входного акта `0b4788dd36f811e4acb202b96d6a76a6a06b63ad` остаётся OPEN до независимого RECHECK.

Полная регрессия процесса выпуска в отдельном локальном материализованном checkout (две генерации поверх существующего пакета, по два verifier, missing/corrupt/stale fixtures):

```bash
/usr/bin/python3 -B cad/frame_mount/regress_verifier.py
```

Результаты — `verification/r4_frame_fix/regressions/results.json`, команды/полные JSON stdout и снимки файлов рядом. Скрипт тестов сам вводит/восстанавливает faults в изолированной копии; verifier их не исправляет. Исходный probe R5 со старыми assertions сохранён: его exit 0 фиксирует дефект, а не исправление.

Прежние 83 теста сохранены и прошли; пять новых тестов supplementary inequality audit:

```bash
/usr/bin/python3 -m unittest discover -s cad/layout -p 'test_*.py'
/usr/bin/python3 -m unittest discover -s models/rev_linked_scene -p 'test_*.py'
/usr/bin/python3 -m unittest discover -s models/kinematic_press -p 'test_*.py'
/usr/bin/python3 -m unittest discover -s cad/layout_correction -p 'test_*.py'
/usr/bin/python3 -m unittest discover -s cad/frame_mount -p 'test_*.py'
```

Все размеры **ASSUMED**; реальные размеры, ходы, нагрузки и сырьё REV **UNKNOWN**. Геометрический торцевой контакт не подтверждает фланец, болты/швы, радиальную фиксацию, способность передачи усилия, безопасную расстыковку и подъём. Непроверенные посадки/крепёж/прочность/допуски остаются UNKNOWN. Архитектура и ТЗ не утверждены, физические испытания NOT_RUN, **G1 OPEN**. Независимая проверка NOT_RUN, задача не принята.
