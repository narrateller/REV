# RECHECK REV-R5-FRAME-NEW-B01-001

- **Проверенный code/results C: `a5d5bad6dd8928045512bca16836fd1d2544b7ca`.** Эстафета H: `0461181e9df0ceccb556edc91f70d51c6f5b8355`; исходный акт `0b4788dd36f811e4acb202b96d6a76a6a06b63ad`, геометрический C `5198e0184b35978701ed1ce762d9e4fcd44997b3`.
- Reviewer R5 / Codex, прямое поручение пользователя, **session ID `6af41aff-4210-8191-94a3-5d9c4bd75076`**, runtime `802a152c45064543a7b8be5ef13696fe`. Дата **2026-11-12 Europe/Moscow**; фактическая UTC-метка — evidence/source_check.json. Автор R4 r4-linked-20261111 — другая сессия. Организационная независимость/профильная квалификация не удостоверены.
- **R5-FRAME-NEW-B01: CLOSED в проверенной программной области C.** Исходный цикл хэшей устранён; verifier одинаково проверяет сохранённый пакет, ничего не перезаписывает и отклоняет проверенные missing/corrupt/stale/подменённые данные без auto repair.
- **Новый процесс выпуска: ACCEPT_WITH_WARNING как ограниченный исследовательский инструмент C.** Генерация отделена от проверки; прежнее отклонение нового кода по этому единственному блокеру снято в указанной области. Обязательных исправлений по B01 не осталось.
- Приёмка геометрической группы сохраняется **только с WARNING в конечной ASSUMED-области прежнего акта**. Оставшиеся **20 native-пар OPEN**, весь пресс не принят, whole press READY=INDETERMINATE. Реальные параметры UNKNOWN; физические испытания NOT_RUN; **G1 OPEN**.

## Точные объекты и порядок независимой проверки

C и исходный акт включены в ancestry H/C соответственно. H отличается от C только ISSUES_AND_TASKS, NEXT_MODEL, STATE, капсулой и cross_check_log; проверенные код/пакет одинаковы. Свежая main до и в конце работы — `06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53`. Claim автора `79e9c3aa9aaca33778814957fafecd93a4adc392` принят PR #35/пользователем; owner r4-linked-20261111, lease до 2026-11-12T18:06:24Z без продления. Историческое NONE/PENDING main остаётся предметом нормализации координатора перед интеграцией. R5 не присваивал claim R4 и не выполнял merge.

**Сначала проверен именно опубликованный пакет, без какой-либо генерации.** После materialize LFS сняты хэши файлов и выполнены два verifier. Оба exit 0 / PASS, stdout/stderr совпали; изменений файлов не было. `first_saved_verifier.json` и `first_saved_snapshot.json` сохраняют этот этап. Затем, всё ещё до генерации в исходном checkout, выполнена дополнительная пара с проверкой SHA-256, размера и mtime_ns **636 файлов репозитория**: before/middle/after одинаковы, exit `[0,0]`, результаты идентичны. Внутри публикации проверены **91 запись + сам manifest = 92 файла**, включая входы, CAD, доказательства и исторический `verification/r4_frame_mount/final_checks.json`.

Генерация и faults выполнялись **позже в отдельных материализованных Git checkout** `/tmp/rev-frame-fix-a5` и `/tmp/rev-frame-fault-a5`. Сохранённый пакет в `/workspace/REV` не перестраивался. Harness сам меняет и восстанавливает fixtures; это не действие verifier. Снимки перед каждым вызовом снимаются уже после внесённой подмены и сравниваются с состоянием после вызова, поэтому отказ не засчитывается при изменении/исправлении ошибочного пакета.

Среда: `/usr/bin/python3` 3.13.5, FreeCAD/Part 1.0.0, Git LFS, Pillow/reportlab/PySide2.QtSvg. В копиях установлен локальный LFS filter; Git-история и нативные файлы доступны. Генерация использует прежний frozen native builder/validator. Bytecode для verifier/его дочерних проверок отключён; снимки исключают .git/.venv/__pycache__, не исключают проверяемые CAD/отчёты/входы. Не заявляется неизменность всей ОС или времени доступа atime.

## Проверка исправления по коду

Необходимый diff: run.py ограничивает artifacts своими выходами; verify_output.py читает manifest и печатает JSON/stdout; report.py обновляет команды. Новые publication.py/generate.py разделяют seal и verify; семь новых unit tests и regress_verifier.py проверяют этот процесс. Геометрический solver/параметры этим diff не менялись.

Проверенный порядок зависимостей:

`исходники/входы → собственные выходы run → геометрические доказательства/виды/отчёт → generation.json → publication_manifest.json → stdout verifier`.

run.artifacts больше не включает предыдущий publication manifest, generation.json и файлы поздних стадий. Проверка manifest требует schema_version=2, точное равенство recorded/actual каталога и соответствие каждого SHA-256; не создаёт отсутствующий manifest и не заменяет ожидаемые хэши фактическими. Verifier сохранил прежние native FCStd/STEP/QueryVolumes, strict cycle, frozen/Git и geometric/inventory assertions. Запись final_checks/manifest убрана с путей успеха **и отказа**. Вывод verifier теперь следует сохранять за пределами проверяемого каталога.

## Исходный контрпример R5 и воспроизводимость генерации

Повторена именно исходная последовательность **построение поверх уже опубликованного output → первый verifier → второй verifier без изменений**, с актуальной отдельной командой generate.py. Ожидаемый исправленный исход — `[0,0]` и неизменный пакет, а не прежний `[0,1]`. Исторический manifest_probe.py с assertions старой ошибки сохранён; запуск его старых ожиданий не считается проверкой исправления.

В собственной копии две явные генерации завершились exit 0. После **каждой** выполнено по два verifier: все четыре exit 0, stdout/stderr одинаковы внутри пары и stdout одинаков между обеими генерациями. Каждый verifier сохранил SHA-256/размер/mtime_ns всех **633 файлов** повторного checkout. Manifest и run.json не изменялись проверкой; forbidden late-stage пути отсутствуют в run.artifacts. Таким образом, проверка больше не делает собственную ссылку на manifest устаревшей.

Между двумя явными генерациями сохранены **35 детерминированных geometry/evidence SHA-256** и native manifest semantics A/B: objects/input_sha256/reopen_recompute/edit_probe/spreadsheet_parameters/query_volumes. FCStd/STEP/PDF могут менять служебную сериализацию при явном построении; побайтная тождественность этих бинарных файлов между генерациями не является заявленным результатом. Их native соответствие заново проверено verifier после каждого выпуска. Стабильность manifest требуется внутри неизменённого выпуска, а не между двумя явными пересборками с новыми binary metadata.

Независимо воспроизведён author regress_verifier: **18 случаев / 23 команды PASS**, в том числе две генерации, шесть одинаковых readonly checks и 15 отрицательных случаев. Сохранены новые результаты этого запуска, не только исходные self-check документы C.

## Независимые подмены и отсутствие автоматического исправления

Собственный fault_probe выполнил **29/29 ожидаемых случаев**: два успешных контроля исходного/явно восстановленного fixture и **27 отказов exit 1**. Во всех случаях снимки SHA-256/size/mtime до/после verifier совпали; missing файлы не появились, повреждённые/устаревшие не были заменены, manifest и исторический final_checks не обновлялись.

| Независимая подмена | Факт |
|---|---|
| Missing и corrupt для A FCStd, B STEP, B PNG, geometry_evidence, inventory и generation.json | 12 отказов; catalog/hash diagnostics, без ремонта |
| Missing/corrupt manifest, schema v1, пустой recorded catalog, дополнительный unrecorded файл | 5 отказов; manifest не пересоздан |
| Валидный FCStd прежней редакции, прежний валидный assessment, input_revision=6 | 3 отказа по stale hash, не только по синтаксической порче |
| Одновременно отсутствующий A STEP и повреждённый inventory | 1 отказ, обе подмены сохранены |
| Удалённый исторический final_checks | 1 отказ; verifier не выпустил новый отчёт взамен |
| Удалена одна из 18 before/after native-записей, publication hashes обновлены harness | 1 отказ по semantic assertion |
| Скрыта одна OPEN native-пара, summary и run/publication hashes обновлены | 1 отказ по полноте non-CLEAR inventory |
| CylinderRemoval.Height изменена отдельно в A и B на тестовое +1 мм; FCStd export/run/publication hashes обновлены | 2 отказа **native CAD validation**, без восстановления геометрии |
| Валидная native модель A подставлена вместо B с обновлёнными хэшами | 1 отказ **native CAD validation** |

Последние пять случаев намеренно проходят внешний hash-контроль, чтобы не принимать обычное несовпадение SHA за доказательство работоспособности semantic/native assertions. Тестовое +1 мм — мутация fixture, не параметр/допуск конструкции. Полные JSON stdout/stderr и пустые file_changes для каждого случая — `evidence/independent_faults.json`.

Успешный exit fault_probe означает совпадение ожидаемого отказа с фактическим exit 1 проверяемой команды, **не успешную sufficient-сцену или геометрию**. Все fixtures восстанавливает только harness после сравнения снимков; генератор в fault_probe не вызывается.

## Сохранность 23 модулей, геометрии и открытого остатка

Все **23 frozen-модуля** побайтно совпали с Git-объектами C и `66924aed1cb2d193b9883d2140d85560b1e4b0cb` и указанными frozen SHA-256. Все **35** зафиксированных детерминированных geometry/evidence файлов совпали и по материализованным хэшам, и по Git-объектам C/5198e01. Неизменны ASSUMED inputs, geometry_evidence.py, inventory.py и figures.py. Точный input SHA-256 по-прежнему `79b190d8db24727120a76ec12704275c940b617fd0d100d79368576eedf7ef05`. Бинарная сериализация native документов менялась при выпуске; bodies/shapes/query-проверки сохранены.

Повторно выполнен независимый native_probe исходного акта **на фактических FCStd/STEP текущего C**, с тем же собственным rational partition solver и native adapter:

- 346 709 all-pair строк без ошибок покрытия;
- 1 044 строки девяти целевых пар A/B без положительного объёма; все 18 native before>0 / after=0;
- 114 156 поддержанных строк изменённой группы без положительного объёма и 28 сохранённых INDETERMINATE controls;
- 658 прежних target строк, 187 secondary control строк и шесть исторических R5 witness-позиций без регрессии;
- 3 672 цилиндровых service-строки, 14 continuous/restored последовательностей, 58 nominal native face interfaces;
- actual FCStd/STEP и все четыре QueryVolumes соответствуют входам; тела A79/B77 сохранены;
- 463 non-CLEAR пары/исходные классы/контексты не потеряны; **20 оставшихся native-пар** снова подтверждены и остаются OPEN.

Полнота хода по-прежнему опирается на точные интервальные неравенства и native соответствие примитивов, а не на одни выборки Part.common. Старый скрипт в JSON содержит историческое поле code_sha=5198e01; он не переписан ради нового акта. Проверяемый **текущий C**, входной хэш и фактические native file hashes зафиксированы в source_check.json и native_preservation.json/native_adapter. Это устранение неоднозначности provenance, не перенос проверки с плавающей ветки.

Сохранены прежние ограничения: 58 face contacts — условные геометрические сопряжения; крепёж, радиальная фиксация, силовая способность и фактический доступ UNKNOWN. Возврат координат doser_slide не делает его сервис успешным: OPEN-проникновения дозатора/бункера/кармана, его извлечения и tank/motor видимы. Два envelope control и прочие INDETERMINATE не объявлены подтверждёнными физическими коллизиями или CLEAR.

## Команды и доказательства

Первые два вызова выполнялись **до** любой генерации. Все команды запускаются из корня материализованного checkout, stdout следует перенаправлять вне publication-каталога:

```sh
/usr/bin/python3 cad/frame_mount/verify_output.py
/usr/bin/python3 cad/frame_mount/verify_output.py
# Только затем, в отдельной копии:
/usr/bin/python3 -B cad/frame_mount/generate.py
/usr/bin/python3 -B cad/frame_mount/verify_output.py
/usr/bin/python3 -B cad/frame_mount/verify_output.py
# Повторить generate + два verifier для второго выпуска.
/usr/bin/python3 -B cad/frame_mount/regress_verifier.py --evidence /tmp/r5-frame-b01-author-regressions
```

Собственные probes и фактические пути повторения:

```sh
/usr/bin/python3 -B verification/r5_frame_b01_recheck/readonly_probe.py /workspace/REV /tmp/r5-frame-b01-saved-mtime.json
/usr/bin/python3 -B verification/r5_frame_b01_recheck/fault_probe.py /tmp/rev-frame-fault-a5 /workspace/REV /tmp/r5-frame-b01-faults.json
# В /tmp/rev-frame-fix-a5 уже выполнена первая явная generate.py:
/usr/bin/python3 -B verification/r5_frame_b01_recheck/generation_probe.py /tmp/rev-frame-fix-a5 /workspace/REV /tmp/r5-frame-b01-generation.json
/usr/bin/python3 -B verification/r5_frame_mount_review/native_probe.py /workspace/REV /tmp/r5-frame-b01-native.json
```

Для копий использованы shared Git clone C, `git lfs install --local` и материализованные файлы оригинала. fault_probe требует локальный LFS object старого C=5198e01 для stale-valid FCStd fixture; в этой среде объект доступен. Старые/новые выходы не подменяются в основном checkout. generation_probe проверяет уже выполненную первую генерацию, выполняет вторую и обе пары verifier. JSON содержит команды, реальные exit/stdout/stderr и native/evidence сравнение.

Воспроизведены пять наборов unittest (`-B -m unittest discover -s … -p 'test_*.py'`) для cad/layout, models/rev_linked_scene, models/kinematic_press, cad/layout_correction, cad/frame_mount: **20+33+20+10+12=95**, все exit 0 / OK. Последние 12 включают пять прежних inequality tests и семь новых publication tests. Команды/выводы — evidence/unit_tests.json. Author replay — evidence/author_replay; собственные первые checks, mtime-снимки, подмены и generation replay сохранены отдельно.

## Решение и NOT_RUN

**B01 CLOSED только для C и указанного процесса выпуска/проверки.** Исправленный release-код пригоден в ограниченной исследовательской области с прежними WARNING. Область геометрической приёмки 18 пар не расширена; остальные конфликты/неопределённости и ограничения исходного акта сохранены. Интеграция в main и решение координатора остаются отдельными действиями.

**NOT_RUN:** исчерпывающее доказательство корректности программы/всех возможных подмен и платформ; произвольные неописанные состояния и движения; реальные крепления, монтажные зазоры, силы/прочность/ресурс, безопасное обслуживание/извлечение и нормативная применимость. Не проведены пробы и физические испытания. Архитектура и ТЗ не утверждены, реальные параметры UNKNOWN. Весь пресс не принят; проектные B01–B03 и другие прежние открытые замечания не закрываются; **G1 OPEN**.

История актов и исходных probes/evidence сохранена. SHA-256 новых скриптов, акта и доказательств — evidence/sha256.json (сам manifest исключён). Точный SHA коммита настоящего акта сообщается отдельно после публикации и проверки удалённой ветки, без самоссылки внутри коммита.
