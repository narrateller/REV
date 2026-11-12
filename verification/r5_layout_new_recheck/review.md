# RECHECK REV-R5-LAYOUT-NEW-RECHECK-01-001

- Проверенный code/results **C `66924aed1cb2d193b9883d2140d85560b1e4b0cb`**; эстафета **H `be5e97360fc6b875df9cd249889653629be552e2`**. Исходный акт `04b9f2950a34492b15e1d7c893f680b82f9183b9`, блокеры R5-LAYOUT-NEW-B01/B02.
- Reviewer: R5 / Codex; **session_id `6af41aff-4210-8191-94a3-5d9c4bd75076`**; дата проверки 2026-11-11 UTC; прямое поручение пользователя. Runtime session `802a152c45064543a7b8be5ef13696fe`. Автор R4 `r4-linked-20261111` — другая сессия. Организационная независимость и профильная квалификация не удостоверены.
- **B01: CLOSED в проверенной программной области** — неподдерживаемые/неизвестные движения и неполное evidence не дают ложного CLEAR.
- **B02: CLOSED в проверенной программной области** — потерянная обязательная связь и недостающие условия limited sufficient отклоняются; исходный полный unlinked-контрпример больше не принимается.
- **Новый код: ACCEPT_WITH_WARNING как ограниченный исследовательский инструмент** для объявленных условных линейных сцен и проверенных входов. Исправления не означают устранения остальных пересечений или готовности A/B. Целевое геометрическое доказательство прежнего акта сохранено и независимо повторено.
- **Компоновки A/B в целом не приняты; whole press READY=INDETERMINATE. G1 OPEN.** Архитектура и ТЗ не утверждены; физические испытания не проводились.

## Точные входы и основание работы

Проверены Git-объекты C, H и исходного акта; акт — предок C, C — предок H. Diff C→H затрагивает только NEXT_MODEL.md, STATE.md, review_request.md и капсулу передачи, не код или геометрию. Результаты относятся к C, а не к произвольному последующему HEAD. Свежий `git ls-remote origin refs/heads/main` до и после запусков показал `06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53`.

Назначение R5 — прямое поручение пользователя. Claim автора `79e9c3aa9aaca33778814957fafecd93a4adc392` принят PR #35; H сохраняет owner r4-linked-20261111 и lease до 2026-11-12T18:06:24Z, заявляет подтверждение пользователем. Историческое противоречие READY/NONE/PENDING в общей сводке и рабочей нормализации этим RECHECK не исправляется. Координатор должен согласовать учёт перед интеграцией; R5 не присваивал себе claim R4 и не интегрировал результат в main.

Новая область кода: assess.py, outcomes.py, run_revision.py, verify_cycles.py, verify_output.py и test_review_regressions.py. Старый `analysis_probe.py` намеренно утверждает прежнее ошибочное поведение и не использовался как тест исправления. Новый независимый `probe.py` содержит противоположные ожидаемые исходы. Общие модули frozen engine используются в обеих авторских проверках; два модуля не объявляются независимыми геометрическими методами.

Среда: Linux, `/usr/bin/python3` 3.13.5, FreeCAD/Part 1.0.0 из `/usr/lib/freecad-python3/lib`. Git LFS материализован. Сборки выполнялись в отдельной копии `/tmp/rev-analysis-fix-669` без .git/.venv; источники C и опубликованные модели в checkout не перезаписаны. Данные ASSUMED не превращены в реальные параметры REV.

## Команды и фактическое воспроизведение

Пути ниже — фактические пути этого запуска. Для повторения нужен материализованный checkout опубликованной ветки с кодом C и этим актом. Копия создавалась `tar` с исключением .git, .venv и __pycache__. Её нельзя помещать внутрь исходного checkout.

```sh
# Из /tmp/rev-analysis-fix-669:
/usr/bin/python3 cad/layout_correction/run_revision.py
/usr/bin/python3 cad/layout_correction/verify_output.py

# Исходный полный R5-контрпример: тот же JSON, только иной путь внутри копии.
mkdir -p cad/layout_correction/unlinked
cp verification/r5_layout_correction_review/evidence/unlinked_inputs.json cad/layout_correction/unlinked/inputs.assumed.json
/usr/bin/python3 cad/layout_correction/run_revision.py --inputs cad/layout_correction/unlinked/inputs.assumed.json --out /tmp/rev-analysis-unlinked-669-rerun
/usr/bin/python3 cad/layout_correction/verify_output.py --out /tmp/rev-analysis-unlinked-669-rerun

# Из /workspace/REV:
/usr/bin/python3 verification/r5_layout_new_recheck/probe.py /workspace/REV verification/r5_layout_new_recheck/evidence/independent_cases.json
/usr/bin/python3 verification/r5_layout_new_recheck/cli_probe.py /tmp/rev-analysis-fix-669 /tmp/rev-analysis-unlinked-669-rerun verification/r5_layout_new_recheck/evidence/cli_cases.json
/usr/bin/python3 verification/r5_layout_correction_review/geometry_probe.py /workspace/REV verification/r5_layout_new_recheck/evidence/geometry_independent.json
/usr/bin/python3 verification/r5_layout_correction_review/function_probe.py /workspace/REV verification/r5_layout_new_recheck/evidence/functions.json
/usr/bin/python3 verification/r5_layout_correction_review/artifact_probe.py /workspace/REV verification/r5_layout_new_recheck/evidence/artifacts.json
/usr/bin/python3 verification/r5_layout_new_recheck/preservation.py /workspace/REV /tmp/rev-analysis-fix-669 verification/r5_layout_new_recheck/evidence/preservation.json
```

| Проверка | Exit | Факт |
|---|---:|---|
| Штатный run_revision | 0 | execution COMPLETED; test_evaluation PASS; 10 дочерних команд exit 0 |
| Штатный verify_output | 0 | strict limited cycles и сохранённая геометрия PASS |
| Четыре набора unittest внутри сборки | 0 | 20 + 33 + 20 + 10 = **83 теста**, все OK |
| Авторские записи регрессий | 0 в unittest | **15 classifier + 40 cycle** случаев, все совпали с ожиданиями |
| Независимый probe.py | 0 | **116/116** ожидаемых исходов; включая все непустые сочетания пяти условий в A/B |
| Полный unlinked run_revision | **1** | **VALIDATION_FAILED**, execution COMPLETED, test_evaluation FAIL; 7 дочерних команд exit 0, затем строгий oracle отклоняет sufficient |
| Полный unlinked verify_output, свежий каталог | **1** | FAIL: assessment.json не создан после отклонения цикла |
| Независимый cli_probe.py | 0 | **9/9** ожидаемых отказов CLI, внутренние вызовы verify_output имеют exit **1** |
| Geometry/function/artifact/preservation probes | 0 | Геометрические доказательства, native CAD и функциональные условные связи сохранены |

Дочерние команды, stdout/stderr, версии и хэши записаны в `evidence/default_run.json`, `default_verification.json`, `source_check.json` и логах. `author_*_regressions.json` получены новым запуском, а не просто скопированы из заявленных результатов C.

**Три разных результата:** exit 0 означает успешное выполнение соответствующей команды; matches_expectation означает совпадение сцены с тестовым ожиданием; geometric_scene_outcome характеризует сцену. Совпавший отрицательный тест не превращается в CLEAR или READY. В штатных восьми сценах A/B:

| Case | matches_expectation | limited_cycle_success | geometric_scene_outcome |
|---|---|---|---|
| sufficient | true | true | LIMITED_READY_CONFIRMED только для проверенного подмножества |
| short | true | false | BLOCKED |
| collision | true | false | BLOCKED |
| unknown | true | false | INDETERMINATE |

Для всех восьми whole assembly READY остаётся INDETERMINATE. Независимый тест, ожидающий отказ CLI, сам завершает работу exit 0 после наблюдаемого exit 1 проверяемой команды; это не успешный sufficient.

## B01 — неподдерживаемый метод, неизвестность и границы

Проверены rotation, spline, nonlinear и отсутствующий motion при совпадающих, касающихся и раздельных начальных коробках, в интервале [2,5]. Конечный delta больше не легализует неподдерживаемое движение. Получены INDETERMINATE, непустая причина и `exact_box_sign_coverage=NOT_ESTABLISHED`; исходный raw evidence сохранён. `box_at` не экстраполирует эти движения как линейные.

Отдельно проверены неизвестный delta, неверный extent, пропущенная конечная точка, разрыв evidence, неизвестный статус сегмента, противоречащий сегментам CLEAR, отсутствующее тело пары и обратный интервал. Ложного CLEAR нет. У составной сцены с доказанным проникновением одной поддержанной пары и двумя неизвестными парами результат BLOCKED; PENETRATION=1 и INDETERMINATE=2 сохранены раздельно. Неизвестность не скрывает установленный дефект.

По коду `support_failure` теперь предшествует классификации: проверяются область motion, координаты/delta, объявление формы, SUPPORTED, чередование point/open регионов, включение обеих границ и отсутствие разрывов. Это не доказательство корректности произвольного внешнего/поддельного evidence или произвольной кинематики; неподдержанные движения остаются вне метода.

**Решение: R5-LAYOUT-NEW-B01 CLOSED только для указанной области C.**

## B02 — обязательные условия достаточного ограниченного цикла

Для A и B проверены по отдельности и во всех **31 непустом сочетании** пяти условий: required_link, path_transition, continuity_status, lifecycle и path_ready. Во всех 62 случаях оба модуля отвергают успешный sufficient. Это включает отсутствие REMOVE отдельно от меток непрерывности и READY.

Кроме сводных полей изменялись сами доказательства при сохранённых успешных метках: фактическая потеря связи, скачок координат на границе, временной разрыв, ранний/двойной REMOVE, неверный ID/конечная координата удаления, добавленные CREATE/SPLIT, отсутствие RETURN/READY, ложное имя READY, невосстановленная позиция, неполная матрица пар и unsupported motion на возврате. Составной случай соединяет потерю контакта, пропущенный RETURN, неизвестную непрерывность и лишний CREATE. Оба проверяющих модуля отвергли эти случаи A/B. Неизвестность не дала успешного dependent transition.

`outcomes.assess_scene` пересчитывает связь и ограниченный путь, сверяет исходную геометрию с входом, полную матрицу пар, последовательность фаз, непрерывность/lifecycle и восстановление реестра и положений. Sufficient требует подтверждённый REMOVE изделия на разрешённой границе и последний READY-RETURNED; одних GEOMETRY_SUFFICIENT/NO_COLLISION недостаточно. `verify_cycles` отдельно проверяет обязательные поля, фактический контакт, фазы, пары, межфазные времена/координаты, удаление и возврат; не вызывает outcomes.

### Исходный полный unlinked-контрпример

Использован **точно сохранённый** JSON исходного акта; его SHA-256 и diff параметров — `source_check.json`. Отличаются только ASSUMED-LAYOUT-PRODUCT-A-PX и ASSUMED-LAYOUT-PRODUCT-B-PX: тестовый сдвиг с 0.15 на 0.16 м. Это синтетическая мутация, не изменение параметров изделия. Десятичная запись сохранена; прежний неудачный вариант с Fraction-строкой не используется.

Native A/B построены, frozen core check завершился exit 0. Затем для обоих sufficient пересчитаны:

- GEOMETRY_SUFFICIENT и NO_COLLISION;
- **LINK_ABSENT, BLOCKED, CONTINUOUS, NOT_CONFIRMED**;
- geometric_scene_outcome=BLOCKED, limited_cycle_success=false, matches_expectation=false.

RETURN/READY-RETURNED после неподтверждённой выдачи нет. Новый run_revision не принимает эти сцены, пишет VALIDATION_FAILED/FAIL и возвращает 1. Здесь сборка завершена, но заявленная достаточность не подтверждена. Анализ целевых проникновений этой отрицательной сборкой не выполнен: suite останавливает pipeline раньше analyze.

Для verify_output свежий отрицательный каталог сначала даёт отказ по отсутствующему assessment.json. **Этот отказ сам по себе не засчитан как независимая проверка контакта.** Поэтому cli_probe дополнительно создаёт отдельные fixtures с assessment и:

1. С реальным failed run — отказ по strict test evaluation.
2. С поддельным успешным run над unlinked raw — отказ по mandatory outcome.
3. С поддельными успешными полями самого raw и добавленными возвратными фазами — отказ по **actual required link**, пересчитанному из тел.
4. С потерей transition, continuity, lifecycle, READY и составным дефектом — отказы по соответствующим ранним assertions.

Fixtures обновляют хэш изменённого raw, чтобы отказ не объяснялся одним несовпадением хэша. Они не используются как геометрические доказательства и не публикуются как результаты установки. Для lifecycle без сообщения AssertionError сохранён именно пустой reason; это диагностическое ограничение, не успешный исход. По A и B отдельно те же условия покрыты независимым probe.py; CLI прекращается на первом дефектном A.

**Решение: R5-LAYOUT-NEW-B02 CLOSED только для проверенной limited synthetic-области C.**

## Сохранность геометрии и целевого доказательства

Независимый `preservation.py` сравнил реальные Git-объекты **всех 15 frozen файлов C с de377f012da08f34796b2e59aee663ba0b2b3d2b**, а также материализованные байты и SHA-256: совпали. Все исходные ID сохранены: A 65→70, B 61→68, удалённых ID нет. Относительно 120a958 неизменны 16 файлов геометрических входов/PNG/исходных сцен/доказательств, перечисленных в geometry_baseline.json; сравнение выполнено и с Git-объектами, а не только с декларацией manifest.

Повторная сборка воспроизвела objects, input_sha256, reopen_recompute, edit_probe, spreadsheet_parameters и QueryVolumes обоих manifest; распакованные рабочие и сервисные сцены совпали; все восемь PNG совпали побайтно. Бинарные FCStd/STEP не объявляются побайтно неизменными: пересохранение меняет служебные данные. Native adapter независимо прошёл для сохранённых и заново собранных FCStd/STEP, включая QueryVolumes; сохранённые модели валидны, 70/68 тел. Дополнительный artifact_probe заново отрисовал восемь PNG из FCStd с точным совпадением и проверил редактирование gate_house_top в Spreadsheet и восстановление исходного размера. Все опубликованные source/artifact хэши C совпали.

`geometry_probe.py` повторяет независимый Fraction-решатель строгих линейных неравенств перекрытия на всём нормированном ходе [0,1], включая границы; это не только дискретные кадры нового классификатора. В 251 923 строках рабочих/возвратных/сервисных пар нет ошибок покрытия; **618 целевых строк** без положительного объёма. Dimensions целевых native примитивов сверены с точными коробками; **58 уникальных native Part.common** на началах/серединах/концах дают нулевые целевые объёмы. В 12 сервисных последовательностях независимо подтверждены непрерывность и возврат. Старый geometry_probe содержит историческое сравнение frozen C=120a958; актуальное сравнение именно C=66924ae отдельно выполнено preservation.py.

Сохранено устранение inlet_gate/pocket_R в A/B и lock/end_stop с guard_right/stop_support в B, включая нижний pocket и вторую опору. Не появилось положительного пересечения новых функциональных gate/cap/portal тел в проверенных точных линейных сценах. Function probe повторно подтвердил условное открытие/закрытие окна заслонкой, исходные рабочие ходы и семь положительных площадей контакта условной реакционной цепи B. Это геометрическая топология, не фактическое силовое замыкание, удержание или безопасное обслуживание.

## Открытые ограничения и замечания

**Остальные пересечения OPEN.** Независимо снова получены native common volumes A/B: cylinder_barrel/cylinder_mount_front ≈15 205 308 мм³; hydraulic_tank/pump_motor ≈7 248 108 мм³; crossbar0/side_rail_L =2 016 000 мм³. Сохраняются прочие рамные/монтажные дефекты, сервис дозатора через hopper/receiving rim и неопределённости извлечения цилиндра/сопряжений. Их исправление в задачу B01/B02 не входило. Касания по ASSUMED policy не утверждены для реальной конструкции; envelope overlap для curved solids не равен доказанной native-коллизии. Новая диагностика не устраняет физическую геометрию.

Два эксплуатационных замечания к исследовательскому коду, не возобновляющих B01/B02 в проверенной области:

- `--inputs` фактически ограничен путём внутри ROOT: первая попытка передать файл из другого checkout дошла до native build, но frozen check_layout завершился ValueError при relative_to(ROOT). Она **не считается** воспроизведением исправленного semantic oracle. Сохранены `external_input_path_failure.json` и `unlinked.log`; решающий повтор с тем же JSON внутри ROOT дошёл до suite и отклонён по связи. Для повторения пользоваться приведённым внутренним путём. Произвольные внешние пути не подтверждены.
- Свежий failed output не содержит assessment, а некоторые assertion-причины пусты. Диагностика отказа может быть точнее; отсутствие файла не заменяет semantic evidence. Дополнительные CLI-fixtures выше закрывают именно этот пробел доказательств review.

Обязательных исправлений **по B01/B02 в проверенной области не осталось**. Приёмка исследовательского инструмента ограничена указанным SHA, входами и линейной моделью. Интеграция и решение координатора остаются отдельными действиями; этот акт не принимает компоновки A/B и не меняет проектную базовую линию.

**NOT_RUN:** исчерпывающее доказательство корректности программы, враждебная согласованная подмена всех файлов/отчётов, произвольные сторонние входы и внешние пути, произвольные вращения/деформации и непрерывный BRep-анализ curved solids; реальные заполнение, трение, удержание A, разгрузка/выдача B, остатки, прочность, ресурс и безопасный сервис; физические пробы/испытания, нормативная применимость. Реальные параметры UNKNOWN. Архитектура и ТЗ не утверждены. Проектные B01–B03, R5-OBS-01…04, R5-COMP-W01–W05 и **G1 OPEN**. Закрытия настоящего акта относятся только к R5-LAYOUT-NEW-B01/B02.

История исходного акта и его доказательства сохранены. SHA-256 скриптов, акта и новых доказательств — `evidence/sha256.json` (сам manifest исключён). Точный SHA публикации акта сообщается отдельно после коммита и проверки удалённой ветки; самоссылка SHA в акт не встраивается.
