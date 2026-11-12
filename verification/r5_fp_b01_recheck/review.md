# RECHECK REV-R5-FP-NEW-B01-001

- **Проверенный code/results C `7d1bd1c92c7cedc4282e3a903463e88205b86fa3`.** Эстафета H `4bde1194a07244445364a1358678d1d07bd99a0c`; исходный акт `2592b470940cea886e033a999c889c15a92889f6`, геометрический baseline `8fbbef00023e146e32cb6ff290a0c19408ca13b5`.
- Reviewer R5 / Codex, прямое поручение пользователя; **session ID `6af41aff-4210-8191-94a3-5d9c4bd75076`**, runtime `802a152c45064543a7b8be5ef13696fe`; **2026-11-12 Europe/Moscow**, UTC-метки — evidence/source_check.json. Автор R4 r4-linked-20261111 — другая сессия; организационная независимость/профильная квалификация не удостоверены.
- **R5-FP-NEW-B01: CLOSED в проверенной области C.** Пять прежних false PASS исправлены. Текущие state/time, состав и метод движения, полный путь и derived evidence проверяются заново; негативное тестовое ожидание не превращается в успешный путь.
- **Пригодность нового кода: ACCEPT_WITH_WARNING как ограниченного исследовательского инструмента C**, для проверенных сохранённых пакетов и явной semantic reanalysis. Обязательных исправлений по B01 не осталось. Это не исчерпывающее доказательство программы или утверждение физического метода.
- Допустимый исходный L-путь сохраняет limited geometric success, **физическая выполнимость INDETERMINATE**. Все шесть native-пар прямого UP остаются **BLOCKED / OPEN**. Прежняя приёмка 14 fixes и конечного L-пути с WARNING не расширена. **Весь пресс не принят, G1 OPEN**, архитектура/ТЗ не утверждены; физические испытания не проводились.

## Точные входы и сохранённый пакет

C — предок H, исходный акт — предок C. H меняет только учёт, STATE/NEXT_MODEL, капсулу и cross_check_log, не проверяемый пакет. Main до/после — `06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53`; accepted claim `79e9c3aa9aaca33778814957fafecd93a4adc392`/PR #35/подтверждение пользователя, owner r4-linked-20261111, lease до 2026-11-12T18:06:24Z без расширения. Исторический NONE/PENDING main координатор сверяет до интеграции; R5 не присваивал claim и не выполнял merge.

Прочитаны новый recheck_request/input_audit/README/causes, необходимый diff common/generate/present/verify и новые service_semantics/service_evidence/service_fixtures/tests. Старые акты и независимые probes сохранены. **Все 34 frozen-модуля** совпали по Git-объектам reference/C, материализованным байтам и SHA-256. **Все 46** файлов native/input/scene/classification/геометрических доказательств из geometry_preservation совпали по байтам с baseline, а не только с декларацией preservation.json. Реальные registry/COTS не изменены. Вход по-прежнему SHA-256 `8332b00f141e8b5a047ea81213c29c49f6467f99e039e3c3e661cae7edccf6b9`.

**Первой выполнена проверка сохранённого C/H, без генерации.** После LFS materialization два verifier дали exit `[0,0]`, одинаковые stdout/stderr; SHA-256/size/mtime_ns **798 файлов** before/middle/after одинаковы. Все **80** publication-записей соответствовали байтам пакета. Verifier ничего не пересоздавал. Снимки включают source/inputs/native/evidence, исключают .git/.venv/__pycache__, не претендуют на неизменность atime/всей ОС.

Изменения fixtures, отчётов и явная reanalysis выполнялись в отдельных materialized Git checkout `/tmp/rev-fpfix-chain`, `/tmp/rev-fpfix-independent`, `/tmp/rev-fpfix-reanalysis`. Исходный пакет `/workspace/REV` не генерировался и не исправлялся. Среда: Linux, `/usr/bin/python3` 3.13.5, FreeCAD/Part 1.0.0, Git LFS. Отрицательные CLI снимались до/после уже внесённой подмены; изменять/восстанавливать fixture разрешено только harness.

## Что теперь связано в коде

service_semantics строит обязательные протоколы из inputs, проверяет registry/форму/метод, фактические позы/delta и времена, все pair-матрицы и полный affine interval; отдельно пересчитывает continuity/return. Подтверждённая коллизия или известное нарушение пути блокируют путь; неизвестный обязательный метод/участок без доказанного блокирующего дефекта даёт INDETERMINATE. Неизвестность не стирает известную коллизию. Descriptor group не может объявить registered solid оболочкой и скрыть его проникновение.

service_evidence выводит changed-set из inputs и включает **все пары сервисов** в обязательную область; сравнивает значения matrices/interval/classification, их counts, assessment, service_semantics/service_report и две копии service source с текущим расчётом. Это устраняет прежнюю проверку лишь ID/порядка/хэшей. Native CAD/все canonical QueryVolumes и strict work-cycle проверки сохранены.

На исходном пакете verifier реально пересчитал **638 919 matrix rows, 593 931 обязательную interval row и 638 919 classification rows**, сравнив сохранённые агрегаты. Mandatory interval-область расширена относительно прежних 507 043 critical rows, геометрический путь и исходные сцены не менялись.

Поля execution/calculation_execution, test_evaluation/matches_test_expectation, interval_geometry_outcome, geometric_path_outcome/limited_geometry_success, overall_service_outcome и physical_feasibility разделены. PASS проверки пакета означает совпадение обязательных ожиданий, включая ожидаемый legacy BLOCKED, а не пригодность всех сервисов.

## Пять исходных независимых контрпримеров

**Неизменённый R5 service_counterexamples.py** исходного акта повторён в копии C. Он изменяет обе source-копии сцены и manifest hashes, сохраняет код/inputs/native CAD и пересчитывает фактические pair-матрицы. Native positive witnesses исходного probe повторены. Все пять actual verifier exits теперь **1**, записи verifier не изменяют пакет:

| Исходная подмена | Геометрический / общий сервисный исход | Proven collision записей | limited_geometry_success |
|---|---|---:|---|
| A: убрать retract перед UP/DOWN | BLOCKED / BLOCKED | 6 | false |
| B: убрать retract перед UP/DOWN | BLOCKED / BLOCKED | 6 | false |
| A: UP перед боковым выводом | BLOCKED / BLOCKED | 4 | false |
| A: front plate неподвижна при подъёме powerpack | BLOCKED / BLOCKED | 2 | false |
| A: unsupported rotation мотора | INDETERMINATE / INDETERMINATE | 0; unknown method явно сохранён | false |

У всех physical_feasibility=INDETERMINATE, matches_test_expectation=false. Первые четыре не переименованы в uncertainty; последний не превращён в CLEAR или BLOCKED по недоказанному вращательному пересечению. `defect_reproduced` старого probe стал false; его собственный exit 0 означает выполнение harness, смотреть нужно actual verifier exit/outcome.

Свежий запуск `verification/r4_fp_fix/recheck_cases.py` дал PASS: **25 внешних command records**, включая original R5 probe (внутри него пять verifier), расчёт/отчёт/reanalysis первых пяти и одного compound случая, ещё четыре compound/unknown verifier, восстановленные baseline verifier `[0,0]`. Во всей проверенной цепочке первые четыре исходных случая остались BLOCKED, rotation — INDETERMINATE. Report JSON/Markdown содержат фактический исход, CLI отчёта/reanalysis возвращают 1 при неожидаемо плохом пути. Failed reanalysis не заменяет его каноническим и не заверяет пакет.

## Независимые составные случаи через всю цепочку

Собственный chain_probe **не импортирует авторские service_fixtures**. Мутации строятся из сохранённых сцен; pair evidence обновляется frozen public API. Для каждого случая проверены direct calculation/aggregation, calculation CLI, report JSON/Markdown, verifier CLI и `generate.py --reanalyze`. Обе source-копии согласованы; hashes явно обновляет harness, включая report hashes перед verifier, чтобы отказ не объяснялся одним SHA mismatch.

| Независимый случай (B) | interval_geometry_outcome | geometric_path / overall_service |
|---|---|---|
| Нет retract + вращение постороннего motor | BLOCKED | BLOCKED / BLOCKED |
| Нет retract + неизвестный delta постороннего motor | BLOCKED | BLOCKED / BLOCKED |
| Unsupported rotation + пропуск pair evidence | INDETERMINATE | INDETERMINATE / INDETERMINATE |
| Collision-free интервалы + временной разрыв | CONFIRMED_NO_POSITIVE_VOLUME | BLOCKED / BLOCKED |
| Collision-free интервалы + скачок/невосстановленный nominal return | CONFIRMED_NO_POSITIVE_VOLUME | BLOCKED / BLOCKED |
| Отсутствует обязательная последняя фаза | INDETERMINATE | INDETERMINATE / INDETERMINATE |
| Отсутствует обязательное тело registry | INDETERMINATE | INDETERMINATE / INDETERMINATE |
| Collision + forged group=routes + unsupported motor | BLOCKED | BLOCKED / BLOCKED |

Все **32 прямых CLI-вызова** этих восьми цепочек дали ожидаемый exit **1**. Calc/verifier/failed reanalysis сохранили SHA/size/mtime пакета; report — отдельная явная команда записи отчёта, не auto repair verifier. У всех случаев limited_geometry_success=false, matches_test_expectation=false, physical_feasibility=INDETERMINATE. В collision+unknown сохранены **и** proven_collisions, **и** unknown_mandatory_conditions. Отсутствие коллизии внутри отдельных интервалов не выдано за корректный целый путь при разрыве/неверном возврате.

После явного восстановления fixture агрегатор вновь дал 20 геометрически допустимых / 2 BLOCKED и 20 общих INDETERMINATE / 2 BLOCKED. Команда самого harness завершается exit 0 после проверки ожидаемых отказов; это не PASS плохого сервисного пути.

## Подмены derived evidence при допустимых исходных позах

Дополнительно обновлялись publication hashes, сохраняя текущую геометрию/позы допустимыми и количество/идентичность строк:

- Положительный legacy interval result заменён на NO_POSITIVE_VOLUME без удаления строки: **отказ `stale interval result`** при fresh value comparison.
- Одна legacy PENETRATION classification заменена на CLEAR без изменения порядка/числа строк: **отказ `stale classification`**.
- В service_report ожидаемый legacy negative превращён в limited_geometry_success=true/CONFIRMED: **отказ `saved report differs from fresh service calculation`**.

В этих трёх случаях свежая service test_evaluation сама по себе PASS, поскольку actual baseline включает ожидаемый BLOCKED. Пакет всё равно отклонён из-за ложного derived evidence/report; verifier их не ремонтирует.

Также удалён **один обязательный B/service_fp_motor** из обеих source-копий: calculation→report→verifier→reanalysis дали `[1,1,1,1]`, complete_required_service_set=false и явную missing_required_services запись, без подстановки отсутствующего сервиса. Всего derived_probe — **четыре случая / семь CLI**, все ожидаемые отказы; снимки readonly команд неизменны.

## Допустимый L, legacy UP и геометрическая сохранность

Базовый набор имеет **20 CONFIRMED_NO_POSITIVE_VOLUME геометрических путей и 2 BLOCKED legacy paths**. По общему сервисному исходу — **20 INDETERMINATE / 2 BLOCKED**, physical_feasibility=INDETERMINATE. Для A/B L: limited_geometry_success=true, matches_test_expectation=true, overall_service_outcome=INDETERMINATE. Для A/B legacy UP: matches_test_expectation=true, но **limited_geometry_success=false**, interval/path/overall BLOCKED, negative_test_is_path_success=false. Наборы proven_collision_pairs ровно три doser/hopper пары на вариант — шесть native-пар.

В отдельной копии допустимая `generate.py --reanalyze` завершилась exit 0 / test_evaluation PASS. Она пересчитала derived evidence/report из сохранённых поз и не сохраняла CAD. Все **46** геометрических/native/input/scene/classification файлов после неё сохранили прежние байты. Следующие два verifier дали одинаковые exit `[0,0]` и stdout/stderr, сохранив SHA/size/mtime всех 798 файлов копии. Это отдельно подтверждает исправленный положительный путь, не только отрицательные fixtures.

Повторён независимый native_probe исходного акта на фактических моделях текущего C: 638 919 pair rows, 14 static before>0/after=0, все шесть legacy native-пар положительны в тех же witness состояниях; 12 legacy UP/DOWN positive rows, ни одного нового positive moving overlap. Восемь новых service sequences сохранили состав/непрерывность/возврат; регрессий прежних 878 gate/portal и 1 440 frame/mount target rows нет. Native FCStd/STEP и все четыре canonical QueryVolumes соответствуют inputs, тела A91/B89, 62 новых и 58 прежних номинальных face interfaces сохранены. Полный inventory — прежние 557 non-CLEAR пар, 6 native legacy / 2 envelope controls / 15 policy contacts / 534 INDETERMINATE.

Старый native_probe содержит историческое поле C=8fbbef0; он не переписан. Текущий проверенный SHA и фактические native hashes отражены в source_check.json и native_preservation.json/native_adapter. Независимый exact partition solver проверяет все границы и открытые интервалы; native samples не выданы за доказательство всего произвольного BRep-движения.

Канонический DoserRemoval остаётся старым BLOCKED UP, новый L не становится реальной сервисной зоной из-за успешного геометрического расчёта. Дополнительный ход/привод, отсоединение коммуникаций/креплений, временные опоры, масса/оснастка/подъём, реальные зазоры/площадка остаются UNKNOWN. **R4-FP-SERVICE-01 OPEN; физическая выполнимость L INDETERMINATE.**

## Воспроизведённые команды и файлы

Сначала два readonly checks сохранённого C, затем только копии/fixtures:

```sh
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B verification/r4_fp_fix/recheck_cases.py
/usr/bin/python3 -B cad/feed_power/generate.py --reanalyze
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
```

Собственные probes и фактические пути (stdout/evidence за пределами проверяемого publication-каталога):

```sh
/usr/bin/python3 -B verification/r5_fp_b01_recheck/readonly_probe.py /workspace/REV /tmp/r5-fpfix-saved.json
/usr/bin/python3 -B verification/r5_fp_b01_recheck/chain_probe.py /tmp/rev-fpfix-independent /tmp/r5-fpfix-chain.json
/usr/bin/python3 -B verification/r5_fp_b01_recheck/derived_probe.py /tmp/rev-fpfix-chain /tmp/r5-fpfix-derived.json
/usr/bin/python3 -B verification/r5_feed_power_review/native_probe.py /workspace/REV /tmp/r5-fpfix-native.json
/usr/bin/python3 -B verification/r5_fp_b01_recheck/readonly_probe.py /tmp/rev-fpfix-reanalysis /tmp/r5-fpfix-reanalyzed-readonly.json
```

Копии получены shared Git clone точного C, `git lfs install --local`, материализацией исходных файлов; generation/faults не запускаются параллельно в одном mutable checkout. Источник C и старые акты/probes не переписывались. Calculation/aggregation и actual outcomes всех звеньев записаны в independent_chain.json, raw stdout/stderr — в commands. Author replay с пятью исходными случаями — evidence/author_replay; stale-value/missing-service — derived_faults.json; readonly снимки и native/preservation — отдельно.

Воспроизведены **110 unittest**: 20+33+20+10+12+15, все OK/exit 0. Полные команды `-B -m unittest discover -s <dir> -p 'test_*.py'` для cad/layout, models/rev_linked_scene, models/kinematic_press, cad/layout_correction, cad/frame_mount, cad/feed_power — evidence/unit_tests.json. Эти тесты дополняют реальные пакетные контрпримеры, не заменяют их.

## Решение и NOT_RUN

**B01 CLOSED только для C и проверенной ограниченной semantic/service цепочки. Новый код пригоден как исследовательский инструмент с WARNING.** Прежняя геометрическая приёмка 14 fixes/L-path не расширяется до пресса; другие открытые замечания не закрываются. Интеграция и нормализация учёта — отдельно координатором, задача не становится DONE автоматически.

**NOT_RUN:** полная новая CAD-пересборка в этом RECHECK (native файлы сохранены побайтно и фактически проверены); исчерпывающее доказательство программы/всех подмен/платформ, произвольные неописанные движения и curved/deformable BRep; реальные крепления/энергоизоляция/расстыковка/оснастка/площадка/подъём, силы/прочность/ресурс/допуски/нормативная применимость/безопасность. Пробы и физические испытания не проводились. Архитектура/ТЗ не утверждены, реальные параметры UNKNOWN. Весь пресс не принят; **G1 OPEN**.

История сохранена. SHA-256 акта, новых скриптов и доказательств — evidence/sha256.json (сам manifest исключён). Точный commit SHA публикации акта сообщается отдельно после проверки удалённой ветки, без самоссылки внутри коммита.
