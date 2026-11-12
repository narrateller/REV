# R5-FRAME-NEW-B01 — исправление процесса выпуска

Вход: независимый акт REV-R5-FRAME-MOUNT-01-001 на `0b4788dd36f811e4acb202b96d6a76a6a06b63ad`, проверенный геометрический C `5198e0184b35978701ed1ce762d9e4fcd44997b3`. Автор R4 r4-linked-20261111. Независимый RECHECK нового исправления NOT_RUN, **B01 OPEN** до решения R5. Ограниченная геометрическая приёмка с WARNING исходного акта сохраняется; весь пресс не принят.

## Изменение

Порядок зависимостей теперь односторонний:

`исходники → выходы run → геометрические доказательства/виды/отчёт → generation.json → publication_manifest.json → stdout verifier`.

- `cad/frame_mount/verify_output.py` читает уже сохранённый manifest версии 2, проверяет полноту каталога, все хэши и прежние semantic/native условия. Ни при PASS, ни при отказе он не пишет manifest, final_checks, входы, CAD или evidence. Результат — детерминированный JSON stdout и exit code. Создание bytecode отключено для verifier и дочернего native validator.
- `cad/frame_mount/publication.py` разделяет проверку и явное создание manifest. Проверка не вызывает запись. Отсутствующие/повреждённые/устаревшие manifest и файлы дают отказ; manifest не заполняется по фактическому состоянию автоматически.
- `cad/frame_mount/generate.py` — отдельная явная команда: выполняет четыре стадии построения/доказательств/видов/отчёта, сохраняет журнал generation.json и создаёт publication manifest. После этого verifier запускается отдельно.
- Необходимый diff `run.py`: хэшировать только собственные выходы; исключены зависимости от всех последующих стадий, а не только частный случай старого manifest. Необходимый diff `report.py` — актуальные команды/описание процесса. Геометрические методы/параметры не менялись.

**Все 23 прежних frozen Python-модуля неизменны.** Не менялись geometry_evidence.py, figures.py, inventory.py, rev7 ASSUMED-входы или графики движений. Новые release/helper/regression файлы и указанные три изменённых модуля — явная область RECHECK. Входной R5 review и его independent probes/evidence сохранены. Старый manifest_probe с assertions исходной ошибки сохранён; его успешный exit не является доказательством исправления.

## Воспроизведение

Из корня материализованного Git checkout:

```bash
git lfs install --local
git lfs pull
# Проверка опубликованного пакета без генерации:
/usr/bin/python3 -B cad/frame_mount/verify_output.py
/usr/bin/python3 -B cad/frame_mount/verify_output.py
# Отдельная ЯВНАЯ повторная генерация:
/usr/bin/python3 -B cad/frame_mount/generate.py
/usr/bin/python3 -B cad/frame_mount/verify_output.py
/usr/bin/python3 -B cad/frame_mount/verify_output.py
# Полная регрессия в локальной временной копии:
/usr/bin/python3 -B cad/frame_mount/regress_verifier.py
```

Не перегенерировать опубликованное evidence перед его первичной проверкой; сначала сохранить исходный C. По умолчанию regression evidence пишется вне проверяемого publication-каталога в verification/r4_frame_fix/regressions/. При желании указать `--evidence /tmp/rev-frame-regressions`. В проверяемом каталоге не сохранять перенаправленный stdout: это будет новый незарегистрированный файл и даст ожидаемый отказ. Внешние логи можно сохранять, например, в /tmp.

`verify_output.py` проверяет actual FCStd/STEP и все QueryVolumes прежним native adapter с выводом временного результата в отдельный TemporaryDirectory. Исходные модели не сохраняются этим адаптером. Исторический verification/r4_frame_mount/final_checks.json остаётся неизменным доказательством первоначального C; текущие два stdout — verify-1.json и verify-2.json в этой папке.

## Доказательства и предел

- `input_audit.md`, `preservation.json`: база/claim/lease и сохранённые до исправления хэши геометрии/доказательств, native manifest.objects A/B.
- `unit_tests.json`: полные команды/выводы пяти наборов — 20+33+20+10+12 = **95 tests**, все exit 0.
- `read_only_repeat.json`: два verifier опубликованного пакета, идентичные stdout/exit, все 92 файла неизменны по байтам, размеру и mtime; снимок и полные результаты сохранены.
- `regressions/commands.json`, `results.json`: две явные полные генерации поверх существующего output в изолированном LFS-materialized checkout, два verifier после каждой; faults missing/corrupt/stale без восстановления самим verifier; после явного восстановления fixtures снова два успешных verifier.
- `regressions/semantic_repeat.json`: повторяемость нативной семантики и детерминированных геометрических доказательств между генерациями. FCStd/STEP, PDF и временные пути run.json могут менять служебные данные при явном перестроении; byte-identical повтор этого сериализационного metadata не заявлен. Проверяется повторяемость геометрии, доказательств и исходов; byte/mtime инвариант обязателен для verifier.

Геометрическая область остаётся прежней: устранены **18** целевых native-пар проникновения, **20** остаточных native-пар OPEN. 346709 all-pair строк; 658 прежних целевых строк без регрессии, 14 continuous/restored сервисных последовательностей, eight limited outcomes не расширяются до сборки. Все хэши preservation.json сохранены, native manifest.objects совпадают с исходным C. Пересохранённые native файлы соответствуют тем же ASSUMED-параметрам. Конечный перечень — cad/build/frame_mount/inventory/inventory.json/md, остальная неопределённость видима.

Размеры ASSUMED, реальные параметры/нагрузки/крепёж/физика/безопасность UNKNOWN; архитектура/ТЗ не утверждены, физические испытания NOT_RUN. **G1 OPEN, whole press READY INDETERMINATE.**
