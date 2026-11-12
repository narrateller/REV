# Исправление оркестрации и классификатора по R5

2026-11-11T21:32:34Z, R4 r4-linked-20261111, T-r4-layout-build-01. Входной акт REV-R5-LAYOUT-CORRECTION-01-001 на 04b9f2950a34492b15e1d7c893f680b82f9183b9 проверил C 120a9582f4835e81cdf324605a14f632ce7db2cb: целевые проникновения устранены в его области, новая аналитика REJECT_WITH_BLOCKER. R5-LAYOUT-NEW-B01/B02 OPEN до независимого RECHECK; автор не закрывает их.

Геометрия inputs rev6, builder, 15 frozen файлов, все native manifest.objects и 8 PNG неизменны от C 120a958. Рабочие raw matrices, service_scenes и before_after_native совпали с исходным C по SHA-256. Пересобранные FCStd/STEP/PDF могут менять служебные timestamps/hashes, не формы. Геометрические результаты прежнего независимого review сохраняются; новая проверка не утверждает работоспособность REV.

## Фактические проверки

Основные команды:

```sh
/usr/bin/python3 cad/layout_correction/run_revision.py
/usr/bin/python3 cad/layout_correction/verify_output.py
```

Обе exit 0, 10 subprocess-команд run_revision exit 0. Пройдены 83 unit tests (73 прежних + 10 новых/сохранённых analysis tests), в них 15 записанных method/evidence-контрпримеров и 40 cycle-контрпримеров, включая составные. Данные — regressions/classifier_regressions.json и cycle_regressions.json. Исходный analysis_probe.py R5 прочитан и повторён до правки; его старые assertions фиксировали ошибки, исходный результат сохранён в verification/r4_analysis_fix/baseline_counterexamples.json. После исправления критерий — новые ожидаемые INDETERMINATE/rejection, не успешный старый probe.

Full CAD контрпример R5: использован неизменный evidence/unlinked_inputs.json с десятичным смещением продукта на 0.01 м в A/B, отдельный output-каталог. Native builds/check_layout exit 0; новая orchestration завершилась exit 1 с execution=COMPLETED/test_evaluation=FAIL, sufficient A/B BLOCKED, actual LINK_ABSENT, limited_cycle_success=false. Verify_output также exit 1. Regression PASS означает именно ожидаемый отказ обеих команд, а не положительный исход sufficient. Команды/exit codes/сводки и полный отрицательный run — verification/r4_analysis_fix/negative_full_*.json/log. Штатный input не изменялся.

Повторён оригинальный R5 geometry_probe.py: 130453 рабочих + 121470 сервисных = 251923 строки без пропусков/дубликатов; 618 target rows без strict overlap, 58 native start/mid/end checks без положительного объёма. Все 12 сервисных последовательностей непрерывны и восстановлены. Сохранены остальные положительные native/frame/service witnesses. Результат verification/r4_analysis_fix/geometry_reproduced.json — воспроизведение скрипта reviewer автором, не новый независимый акт.

## Изменение B01

CLEAR допускается только после проверки полного линейного метода/входов и complete supported evidence всех point/open интервалов. Проверяются motion, exact-rational vectors/time, экстенты, присутствие тел, SUPPORTED input_status, состав и последовательность регионов без пропусков, допустимые статусы и согласованность raw CLEAR. Rotation/spline/пропущенное движение/неизвестный delta/пустое или неполное evidence дают INDETERMINATE с reason и NOT_ESTABLISHED coverage. box_at и NativeWitness не экстраполируют неподдерживаемое движение линейно.

Raw evidence сохраняется; доказанный PENETRATION другой поддержанной пары сохраняет BLOCKED при одновременном unsupported/UNKNOWN. Пересечение conservative envelopes не превращается в native penetration; отсутствие native witness в одной точке не доказывает весь BRep-ход.

## Изменение B02 и схема результата

Sufficient требует одновременно geometry sufficient, NO_COLLISION, actual и reported LINK_CONFIRMED, ALLOWED_FOR_PATH_SUBSET, CONTINUOUS и RESTORED_FOR_PATH_SUBSET. Повторно вычисляются обязательная связь/выход/ограниченный path, покрытие пар, стадии, actual continuity/lifecycle и конечная геометрия. Нужны корректный REMOVE только после выхода, обязательные RETURN/RESET/READY-RETURNED и восстановленный реестр/позы. Любой отсутствующий, неизвестный, BLOCKED/отрицательный обязательный результат исключает success. Критерий sufficient не ослаблен и не переименован в негативный тест.

verify_output имеет отдельные assertions по raw сценам, не вызывает oracle outcomes.assess_scene: проверяет все шесть обязательных полей, actual link и выход, стадии, motion/парное покрытие, смежность времени/координаты, lifecycle и восстановленную READY-геометрию. Полный неподтверждённый run не может пройти по одному совпадению geometry/collision.

| Уровень | Поле | Значение/смысл |
|---|---|---|
| Выполнение команды | execution.status / exit_code | COMPLETED/0 штатно; COMPLETED/1 при явном validation rejection; FAILED/1 при ошибке выполнения |
| Совпадение с тестом | test_evaluation.status; matches_expectation | PASS/FAIL по полному строгому контракту, не физическая готовность |
| Исход сцены | limited_outcomes.geometric_scene_outcome | LIMITED_READY_CONFIRMED только у достаточных подтверждённых limited cycles; BLOCKED/INDETERMINATE у отрицательных/неизвестных |
| Целевые объёмы | geometric_result.target_status | NO_STRICT_TARGET_PENETRATION после фактической проверки; NOT_EVALUATED_IN_THIS_RUN при раннем отказе |
| Вся установка | whole_assembly_READY | INDETERMINATE, полный пресс не принят |

Short/collision/unknown могут совпасть с ожиданием теста, сохраняя BLOCKED/INDETERMINATE и limited_cycle_success=false. Штатные sufficient A/B имеют LIMITED_READY_CONFIRMED только для заданного подмножества. Положительная геометрия чужой пары не скрывает отрицательный link/return; известная коллизия не скрывается неизвестной связью другого результата.

Неизменные прочие проникновения и физические UNKNOWN перечислены в assessment.json/classifications.jsonl.gz и исторической оценке ниже. Архитектура/ТЗ не утверждены, реальные параметры/работоспособность/прочность/безопасность UNKNOWN, физические испытания NOT_RUN, G1 открыт. Задача IN_REVIEW, новый независимый RECHECK NOT_RUN. Точный C кода и результатов записывается следующим H в эстафету.

---

## История оценки C 120a958 (до исправления новой аналитики)

# Геометрическая корректировка исследовательских A/B

2026-11-11T20:29:56Z, R4 r4-linked-20261111, T-r4-layout-build-01. Исходный инструмент de377f012da08f34796b2e59aee663ba0b2b3d2b, акт R5 214b055f04d5b061a68dfd744afb6c956ac9a9d1 (WARNING). Задача IN_REVIEW, независимый OUTPUT review новой геометрии и нового анализатора NOT_RUN. Проверенные модули не изменялись; точный C результата фиксируется следующим H в NEXT_MODEL/капсуле.

Все 15 файлов инструмента из frozen_tool.json побайтно совпали до/после прогона с de377f0. Исходные данные/базовые CAD и независимые reviews/probes/evidence сохранены. Менялись только отдельные ASSUMED-входы rev6; 490 записей, все с ID/единицей/revision/source/uncertainty. Новая оркестрация и классификатор cad/layout_correction требуют отдельного независимого review; прежний акт не является проверкой их кода.

Команда из корня: `/usr/bin/python3 cad/layout_correction/run_revision.py`. Exit 0, все 10 subprocess-команд exit 0: 73 прежних unit tests и 6 новых tests анализатора, построение A/B, frozen check_layout, чистый семантический повтор A/B и фигуры. Итого 79 tests. Native FCStd/recompute/edit probe, STEP, все четыре canonical QueryVolumes и повтор — PASS в области новых условных примитивов. Восемь ограниченных исходов A/B сохранены. Полный лог/команды/hashes — run.json.

## Изменения и функции

Все координаты/размеры ниже — **ASSUMED, м**, не параметры REV; полные стабильные ID и before/after находятся в cad/layout_correction/change_inputs.json, inputs.assumed.json и changes.json. Расчётные зазоры/площади — номинальные производные этих гипотез, не реальные допуски.

| Узел | До | После | Причина и функция |
|---|---|---|---|
| pocket_R A/B | Z=[0.24,0.64], сплошная стенка поперёк хода заслонки | pocket_R Z=[0.30,0.64] плюс сохранённая нижняя часть pocket_R_lower Z=[0.24,0.255] | Явный паз Z=[0.255,0.30] вокруг gate Z=[0.26,0.295], а не исключение пары. Верх/низ стенки и отдельный закрытый retract-карман сохраняют геометрический контур подачи; удержание частиц/уплотнение щелей физически UNKNOWN |
| gate_support и retract-карман | Плита Y=[0.28,0.93], без верхней/боковых стенок и сервисной крышки | Плита Y=[0.26,0.72], верх, две боковые стенки и cap Y=[0.72,0.74] | Направляющий корпус позволяет slide через паз и закрывает наружную полость. Все исходные тела/ID сохранены, добавлено 5 общих тел. Gate не менялся, рабочий ход -0.48 не уменьшен |
| lock B | Y=[-0.12,0.12] | Y=[-0.32,0.32], X/Z и ход +0.85 прежние | Расширен контакт с двумя опорными стойками за пределами выходного сечения. В открытом положении Y=[0.53,1.17], путь продукта свободен |
| stop_support B | X=[1.08,1.24], Y=[0.55,0.79], Z=[-0.5,0.4] в swept-объёме end_stop | Правая стойка X=[1.35,1.51], Y=[0.20,0.32], Z=[-0.24,0.4]; добавлены левая стойка и нижняя перемычка | Опорный портал за lock с открытым центральным сечением Y=[-0.20,0.20]. Product/punch Y=[-0.16,0.16] не пересекают стойки; bridge top Z=-0.24 ниже product/punch bottom Z=-0.16 |
| guard_right A/B | Y=[0.91,0.95] пересекал рабочие lock/end_stop B | Вся исходная панель Y=[1.75,1.79], её X/Z/длина/высота сохранены | За полным рабочим ходом и габаритом гидроагрегата. Не укорочена/не удалена. Расширенный условный footprint, крепления, реальные нормы ограждения/площадки и доступы UNKNOWN |
| bridge/стойки, уточнение после trial | Пробная перемычка Z=[-0.4,-0.26] заходила в output_support Z=[-0.5,-0.38] | Bridge Z=[-0.38,-0.24], стойки начинаются Z=-0.24 | Положительное проникновение заменено точно заданным номинальным касанием основания; связь с боковыми рельсами сохранена. Исходный контрпример сохранён в history |

Первый вариант guard Y=1.30 попал в pump_motor при проверке остальных нативных пар; панель вынесена целиком дальше. История trial1/trial2 и незавершённая ранняя ошибка собственного анализатора для scenario-only препятствия сохранены в history. Эти промежуточные результаты не объявлялись принятыми. Все новые значения зафиксированы отдельными commits до повторных построений: 8c0cb7c, f81d873, 20c56d7 (полные SHA доступны в истории).

Геометрические свидетели функций: открытая заслонка не перекрывает загрузочное окно X=[0.2,0.6], Y=[-0.2,0.2]; закрытая покрывает всё это окно в обоих вариантах. Функция физической подачи/герметизации/удержания UNKNOWN. У A канал, clamp, punch, rod/cylinder и исходная рама не менялись; силовая гипотеза A сохранена, не подтверждена. У B номинальные контакты положительной площади замыкают end_stop → lock → две стойки → bridge → side rails; в function_witnesses сохранены пары, площади и native zero-volume/distance witnesses. Это топология условной реакции, а не расчёт усилий/прочности/креплений. Геометрическая выдача и ограниченный путь сохранены; реальные разгрузка/остаток/выдача UNKNOWN.

Сервис исправленных узлов: cap поднимается на ASSUMED 0.5, gate выдвигается по Y на ASSUMED 1.0, затем оба возвращаются. В B lock/end_stop и портал извлекаются/возвращаются по Z на ASSUMED 1.3 в отдельных условных сервисных последовательностях. Все тела остаются в реестре; не применяются удаления препятствий или новые разрешения core. Подготовка креплений, поддержка модуля, изоляция давления, строповка и безопасный доступ UNKNOWN. Допустимость сервиса в реальном прессе не подтверждена.

## Устранённые нативные контрпримеры

| Вариант | Пара | Было common volume, мм³ (R5) | Стало в том же witness, мм³ |
|---|---|---|---|
| A | inlet_gate / pocket_R | 560000.0 | 0.0 |
| B | inlet_gate / pocket_R | 560000.0 | 0.0 |
| B | guard_right / lock | 1620000.0 | 0.0 |
| B | lock / stop_support | 3024000.0 | 0.0 |
| B | end_stop / guard_right | 720000.0 | 0.0 |
| B | end_stop / stop_support | 9360000.0 | 0.0 |

Свидетели — before_after_native.json. Полный ход не выводится из этих шести точек: все изменённые тела — нативно сверенные axis-aligned boxes, непрерывная проверка строгого положительного объёма выполняется по всем точным event-регионам неизменного ядра. Прямой и обратный ходы входят в sufficient reference cycles A/B; остальные short/collision/unknown не получают разрешение зависимого возврата. Отдельные сервисные последовательности включают полный выход и возврат, время/геометрия непрерывны, позиции восстановлены.

Суммарно 618 строк целевых пар по фазам/сценариям: **0 положительных проникновений**, включая pocket_R_lower/вторую стойку. Это отдельный узкий результат, не разрешение всей сборки.

## Полный учёт остальных пар

130453 рабочих и 121470 сервисных строк, всего 251923. Исходная полная матрица неизменного checker — raw_checked_tool/all_pairs.json.gz; дополнительные полные сервисные состояния/матрицы — service_scenes.json.gz. Классификации каждой строки — classifications.jsonl.gz (gzip JSON Lines). Везде все неупорядоченные пары существующих тел, без выборочного удаления. A: 65 → 70 тел, B: 61 → 68, все исходные IDs присутствуют. QueryVolumes отдельно, в solid-матрицу не включены.

| Вариант/случай | Условно допустимое касание | Проникновение box | Native penetration witness | Пересечение оболочек | INDETERMINATE | CLEAR |
|---|---|---|---|---|---|---|
| A/sufficient | 80 | 133 | 14 | 0 | 696 | 15775 |
| A/short | 48 | 76 | 8 | 0 | 397 | 9131 |
| A/collision | 48 | 78 | 8 | 1 | 397 | 9408 |
| A/unknown | 47 | 76 | 8 | 0 | 466 | 9063 |
| B/sufficient | 238 | 247 | 26 | 0 | 1050 | 27718 |
| B/short | 152 | 152 | 16 | 0 | 645 | 17259 |
| B/collision | 152 | 154 | 16 | 1 | 645 | 17800 |
| B/unknown | 151 | 152 | 16 | 0 | 712 | 17193 |
| A/service_gate | 60 | 114 | 12 | 0 | 598 | 13706 |
| A/service_cylinder_barrel | 52 | 76 | 7 | 1 | 392 | 9132 |
| A/service_rod | 52 | 76 | 8 | 0 | 392 | 9132 |
| A/service_doser_slide | 52 | 82 | 8 | 0 | 396 | 9122 |
| A/service_clamp_L | 52 | 76 | 8 | 0 | 392 | 9132 |
| B/service_gate | 108 | 114 | 12 | 0 | 490 | 12944 |
| B/service_cylinder_barrel | 84 | 76 | 7 | 1 | 320 | 8624 |
| B/service_rod | 84 | 76 | 8 | 0 | 320 | 8624 |
| B/service_doser_slide | 84 | 82 | 8 | 0 | 324 | 8614 |
| B/service_lock | 78 | 76 | 8 | 0 | 326 | 8624 |
| B/service_end_stop | 82 | 76 | 8 | 0 | 322 | 8624 |
| B/service_portal | 76 | 76 | 8 | 0 | 330 | 8622 |

Счётчики повторяют пары по фазам, это не количество уникальных физических соединений. `ALLOWED_SYNTHETIC_TOUCH` требует нулевого положительного объёма, положительной площади face и явной поимённой политики назначенного guide/abut/reaction интерфейса; её основания ещё проверяет независимый R5. Ни одна positive-volume строка не превращается этим списком в касание; core продолжает выдавать свои COLLISION на нулевых касаниях. Новых исключений/контактов в checked tool не внесено. Необоснованные/реберные/точечные контакты — INDETERMINATE. Род/гильза/другие curved primitives: CLEAR допустим только по раздельным консервативным bounds; overlap оболочек не доказывает native solid penetration. Положительный нативный witness доказывает отдельное проникновение, отсутствие в пробе не доказывает весь BRep-ход.

Оставшиеся рамные/cylinder_mount_front и hydraulic_tank/pump_motor пересечения сохранены как penetration/native witness; их возможная роль условных габаритов или будущих соединений не является разрешением. Коррекция не добавила penetration с новыми телами; перенос guard не пересекает powerpack. Старые сервисные проблемы дозатора (ход вверх/обратно через hopper_R/hopper_floor_right/receiving_rim_right) и cylinder_barrel/cylinder_mount_front/криволинейная неизвестность сохранены в полном отчёте. Для изменённых gate/lock/end_stop/portal новых moving penetration/envelope-conflict строк нет; прочие сервисы не объявлены свободными/безопасными. Реальные вращения ограждений, гибкие трассы, вставки, подъём/изоляция UNKNOWN.

## Границы и provenance

Frozen tool сохранён; новая оркестрация/классификатор и их 6 tests — авторская самопроверка, самостоятельный объект независимого review. Исходный run_all неизменно содержит assertions сохранения старой геометрии, поэтому для rev6 применяется новый run_revision с публичными build/check entrypoints и новыми inputs/output paths. Hardcoded source_commit_inputs, known_native_penetrations, tool_blockers строки frozen check_layout относятся к старой baseline: сохранены как raw metadata, не выдаются за provenance/review новой геометрии. Текущие входные hashes, команды и source hashes — run.json.

Все реальные размеры/ходы/нагрузки/свойства сырья и безопасность REV UNKNOWN; registry/COTS/models не менялись. Геометрические результаты — условные ASSUMED-исследования и производные вычисления, не конструкция REV. Весь пресс **не принят**, whole_assembly_READY=INDETERMINATE. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Инструментальные B01/B02 CLOSED только в ранее проверенных областях; текущая геометрия и новый анализатор требуют независимого R5 review, автор не переводит задачу в DONE.

Дополнительная самопроверка `/usr/bin/python3 cad/layout_correction/verify_output.py`: PASS. Проверены все hashes и 216 полных строк двух новых контрпримеров (guard/pump_motor, bridge/output_support), отсутствие положительных/envelope-пересечений с новыми телами и восстановление всех сервисных позиций. Фактический результат verification/r4_layout_correction/final_checks.json; это новый авторский verifier для отдельного независимого review.
