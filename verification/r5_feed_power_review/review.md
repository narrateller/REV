# OUTPUT-review REV-R5-FEED-POWER-01-001

- **Проверенный code/results C `8fbbef00023e146e32cb6ff290a0c19408ca13b5`.** Эстафета H `84251bf4dca6c8ebe1721ee5d26858a14715f868`; область — verification/r4_feed_power/review_request.md на C.
- Reviewer R5 / Codex, прямое поручение пользователя; **session ID `6af41aff-4210-8191-94a3-5d9c4bd75076`**, runtime `802a152c45064543a7b8be5ef13696fe`; **2026-11-12 Europe/Moscow**, UTC-метки в evidence/source_check.json. Автор R4 r4-linked-20261111 — другая сессия; организационная независимость/профильная квалификация не удостоверены.
- **14 статических исправлений: ACCEPT_WITH_WARNING в конечной ASSUMED-области C.** Все 14 положительных native-объёмов устранены; регрессии прежних исправлений в проверенных сценах нет.
- **Новый условный сервисный путь: геометрически подтверждён для опубликованных поз/ходов/состава C, WARNING.** Физическая выполнимость **INDETERMINATE**, R4-FP-SERVICE-01 OPEN. Шесть прежних пар прямого подъёма остаются доказанными **BLOCKED / OPEN**.
- **Новый код cad/feed_power: REJECT_WITH_BLOCKER — R5-FP-NEW-B01 OPEN.** Verifier принимает изменённую столкновительную/неподдерживаемую сервисную сцену при обновлённом manifest, не пересчитывая её геометрическое доказательство. Это не отменяет отдельную независимую проверку исходного C.
- **Весь пресс не принят, READY=INDETERMINATE; G1 OPEN.** Архитектура/ТЗ не утверждены; физические испытания не проводились. Все реальные параметры UNKNOWN.

## База, входы и сохранённый пакет

База a5d5bad6dd8928045512bca16836fd1d2544b7ca и независимый RECHECK c2e96a58d7efd64ea3364b2bcbfb3f0642bbc430 сохранены в ancestry C. Закрытие R5-FRAME-NEW-B01 не распространяется автоматически на новый adapter и здесь не переоткрывается. C — предок H; H меняет только учёт/STATE/NEXT_MODEL/капсулу/cross_check_log, не проверенные FP-файлы.

Свежая main в начале и конце: `06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53`. Claim `79e9c3aa9aaca33778814957fafecd93a4adc392` — её предок, принят PR #35/подтверждён пользователем; owner r4-linked-20261111, lease до 2026-11-12T18:06:24Z без продления. Историческое NONE/PENDING main не исправляется этим review; нормализацию координатор сверяет до интеграции. R5 не присваивал claim автора и не выполнял merge.

Прочитаны запрос, input_audit, change_plan, README, before/after/inventory, новые Python-модули и self-check документы. ASSUMED rev8 зафиксирован **до построения** на `450e869f28c8fdb327b76abbde04891931cec533`. SHA-256 входа: **`8332b00f141e8b5a047ea81213c29c49f6467f99e039e3c3e661cae7edccf6b9`**. Условные новые service retract/park отделены от прежних рабочих ходов и реальных неизвестных данных.

Все **34 checked-модуля** сравнены побайтно с Git-объектами базы/C и frozen SHA-256: неизменны. Protected старые code/inputs/CAD/reviews/probes, реальные registry/COTS не изменены относительно предшествующего RECHECK. Все прежние body ID сохранены: A79→**91**, B77→**89**; 12 добавленных ID на вариант присутствуют в native документах. Менялись формы/положения отдельных старых ID; сохранение ID не означает сохранения их старой формы.

**До любой генерации** материализован LFS и дважды выполнен verifier на опубликованном C/H. Оба exit 0 / PASS, одинаковые stdout/stderr; SHA-256, размер и mtime_ns **746 файлов** before/middle/after одинаковы. **74 записи publication manifest** совпали с сохранёнными байтами. В основном checkout исходные FP-модели/доказательства не перестраивались.

Среда: Linux, `/usr/bin/python3` 3.13.5, FreeCAD/Part 1.0.0, Git LFS, Pillow/reportlab/PySide2.QtSvg. Повторная сборка и faults — в отдельных materialized Git checkout `/tmp/rev-fp-build-8fb`, `/tmp/rev-fp-fault-8fb`; локальные LFS filters настроены. Verifier не изменял проверяемые файлы на успехе или в контрпримерах. Ошибочная геометрическая приёмка новым verifier — другой дефект, не регрессия прежней readonly-проверки.

## Воспроизведение и соответствие артефактов

Явная `cad/feed_power/generate.py` завершилась exit **0**, включая обе native сборки, core check, повторные A/B build и present — шесть дочерних команд exit 0. Затем **отдельно** дважды вызван verifier: exit `[0,0]`, одинаковый результат и неизменность SHA-256/size/mtime всех 746 файлов копии. Снимок выполнен после завершения author regression harness; ранее замеченная запись его commands.json была действием параллельного harness, не verifier, и не засчитана как изменение продукта.

Воспроизведены **102 unittest**: 20+33+20+10+12+7, все OK/exit 0. Последние семь проверяют новую геометрию/планы и каталог; они не доказывают достаточность нового semantic verifier. Отдельно author regressions дали **18 случаев / 20 команд PASS**, включая 16 отказов missing/corrupt/stale и updated-hash fixtures без auto repair. Это свежий запуск в копии, не только чтение опубликованной самопроверки.

Независимый artifact_probe открыл/пересчитал **сохранённые** FCStd A/B и заново отрисовал восемь PNG с побайтным совпадением. Повторная генерация воспроизвела native objects/input/edit/reopen/query semantics, восемь PNG и все шесть новых detail SVG/PNG. Выполнены шесть Spreadsheet-редактирований motor_mount_rear/doser_tray_inner/tank_arm_0 с восстановлением размеров без записи моделей C. Фактически проверены сохранённые и rebuilt FCStd/STEP, роли/геометрия/положения всех четырёх canonical QueryVolumes. Native solids валидны, A91/B89. Служебные binary metadata FCStd/STEP/PDF после явной пересборки могут отличаться; они не приняты за изменение формы.

DoserRemoval по-прежнему описывает **старый прямой UP**, который остаётся BLOCKED. Новый L-route проверен позами физических примитивов и точными интервалами, **не новым нативным QueryVolume**. Из этого нельзя делать вывод о достаточности сервисной зоны или доступе реального персонала. Визуально сверены общий вид A и detail сервиса: красный ghost отмечает заблокированный UP, синий — условный L-route; проекция не названа доказательством коллизии. Ограждения скрыты только на общих видах и сохранены в native телах/STEP/матрицах.

## 20 прежних пар в одинаковом состоянии: 14 устранены, 6 остаются

Каждый native witness независимо повторён **на том же case/phase/time** до и после. Не сравнивались исходный конфликтный подъём и новая свободная поза как будто это одно состояние.

| Пара, по A и B | До, мм³ на вариант | После, мм³ | Решение |
|---|---:|---:|---|
| doser_floor_front / pocket_front | 416 000 | 0 | STATIC_REMOVED |
| doser_floor_left / pocket_L | 320 000 | 0 | STATIC_REMOVED |
| doser_floor_rear / pocket_rear | 416 000 | 0 | STATIC_REMOVED |
| doser_floor_right / pocket_R | 320 000 | 0 | STATIC_REMOVED |
| doser_front / hopper_floor_front | 1 100 000 | 0 | STATIC_REMOVED |
| doser_rear / hopper_floor_rear | 1 100 000 | 0 | STATIC_REMOVED |
| hydraulic_tank / pump_motor | ≈7 248 108.067 | 0 | STATIC_REMOVED |
| doser_slide / hopper_R | 480 000 | 480 000 | BLOCKED_LEGACY_UP |
| doser_slide / hopper_floor_right | 6 200 000 | 6 200 000 | BLOCKED_LEGACY_UP |
| doser_slide / receiving_rim_right | 240 000 | 240 000 | BLOCKED_LEGACY_UP |

Объёмы — вычисленные nominal native результаты, не критерии/допуски изделия. Уменьшение остатка 20→6 означает устранение **семи статических пар на вариант**, а не устранение всех прежних конфликтов. Шесть legacy-пар подтверждены положительными Part.common, OPEN, disposition=BLOCKED_LEGACY_STRAIGHT_UP. В полном ходе UP/DOWN сохраняются **12 положительных строк**, включая обратные участки; они не переименованы в неопределённость и не скрыты новой политикой.

Независимый native_probe **не импортирует cad/feed_power**. Для всех пар он строит точные рациональные нули шести аффинных выражений перекрытия, проверяет границы и внутренность каждого открытого интервала. Native adapter и дополнительная проверка **224** уникальных body-state размеров связывают эти границы с фактическими native примитивами. Для содержащихся цилиндров отсутствие объёмного пересечения консервативных границ достаточно; выборки Part.common не используются для объявления непрерывного CLEAR curved solid.

Итоги исходного C:

| Подмножество | Независимый результат |
|---|---|
| Полные pair-матрицы всех фаз | **638 919**, без пропусков/дубликатов |
| Critical subset | **507 043**: 506 934 без положительного объёма, 97 INDETERMINATE, 12 положительных legacy UP/DOWN |
| Прежние gate/portal targets | **878** строк без положительного объёма |
| Прежние frame/mount targets | **1 440** строк без положительного объёма |
| Moving пары восьми новых services | **4 936** строк без положительного объёма |
| Сервисные последовательности | **22**, непрерывны, реестр тел сохранён, координаты/нулевые delta восстановлены |
| Native interfaces | **62 новых + 58 прежних frame**, положительная площадь противоположных coplanar граней, нулевой общий solid volume |

Выполнены 42 уникальных cached native pose-common вычисления плюс native face-проверки интерфейсов; весь интервал доказывает собственный exact solver, не это число выборок. Восемь limited cycle outcomes сохранены: sufficient — только LIMITED_READY_CONFIRMED подмножества; short/collision BLOCKED, unknown INDETERMINATE. Их успешное тестовое ожидание не является готовностью пресса.

**Вердикт 14 исправлений: подтверждены в конечной ASSUMED-геометрии и заданных движениях C, WARNING.** Прежние corrections/крепёжные UNKNOWN не пересмотрены в сторону физической приёмки.

## Новый путь и состав сервисных узлов

Для обоих вариантов независимо проверены четыре последовательных перемещения **только тела doser_slide**: Y retract → Z UP → Z DOWN → −Y return, с начальной/конечной неподвижными фазами. Каждая промежуточная поза входит в точное интервал-доказательство, времена смежных фаз совпадают; нет телепортации, CREATE/REMOVE, потери или добавления тела. Неподвижны hopper, trays, guides, collar, frame, guards и прочее окружение. Это путь моделируемого ползуна, **не всего реального дозатора с приводом и коммуникациями**.

Длины читаются из ASSUMED-ID входа, а не утверждаются как реальные ходы. Дополнительный Y retract в C — 7/10 м, lift — прежний 13/10 м; это зафиксированные nominal входы исследования, не подтверждённые возможности COTS. Рабочий doser_slide, оси/ходы punch/rod/cylinder/gate/lock/stop и прежние config не изменены. Горизонтальные retract/return имеют положительное геометрическое нижнее опирание и площади обеих coplanar направляющих на всех support-edge событиях/между ними. Вычисленные минимумы именно этих двух участков: 3/25 м² снизу, 9/250 м² с каждой стороны; это не несущая способность/норматив площади. Slot между split tray/guides сохраняет cap UP corridor; соответствующие пары входят в полную проверку.

Также независимо сверен состав других новых движений:

- motor: только pump_motor UP/DOWN;
- powerpack_module: hydraulic_tank + pump_motor + обе motor_mount плиты UP/DOWN;
- tank_after_motor_park: motor + обе плиты UP, затем park Y; tank UP/DOWN; обратный park и DOWN motor/плит.

У всех восьми новых сцен нет positive moving overlap в исходном C. Условные 62 face interfaces и сохранённые 58 frame interfaces не образуют новой blanket allow-list: raw неопределённости сохранены. Положительное номинальное окно hopper→doser→pocket сохранено; оно не доказывает перемещение/дозирование реального сырья. Новый блок опор/плит не подтверждает tank wall, болты/швы/фланцы или способность держать массу/момент.

**До реального сервиса необходимы:** фактический состав отсоединяемого узла и его привода; доступный ход и последовательность расстыковки креплений/гидравлики/электрики/прочих коммуникаций; изоляция энергии; временные опоры, удержание и устойчивость; масса/центр тяжести, подъёмные точки и оснастка; реальные зазоры/допуски/наклоны и пространство площадки/крана/персонала. Эти тела, гибкие связи и препятствия площадки в модели не определены. Контакт/геометрическая раздельность не обосновывают безопасный подъём или силовую фиксацию.

**Вердикт пути: годен как условная геометрическая исследовательская последовательность C с WARNING; физическая применимость INDETERMINATE, R4-FP-SERVICE-01 OPEN.** Legacy UP остаётся BLOCKED. Весь пресс и физический метод обслуживания не приняты.

## R5-FP-NEW-B01 — OPEN: verifier доверяет устаревшему service evidence

Новый verifier пересчитывает continuity и проверяет наличие всех pair ID/порядок critical rows, но **не пересчитывает их геометрический статус из текущих service state/time**. Не сверяет фактический порядок/состав движений с планом входа. Затем принимает старые classifications, interval_rows и assessment.service_moving_penetrations как доказательство отсутствия новых коллизий. Эти утверждения могут относиться к другой траектории.

Независимые fixtures сохраняют код, входы и native FCStd/STEP исходными. Harness изменяет сцену **в обеих** копиях `service_scenes.json.gz` и `work_and_extra.json.gz`, пересчитывает её реальные pair-матрицы frozen API и обновляет только соответствующие SHA-256 publication manifest. Остальные отчёты/interval evidence остаются прежними, что verifier обязан обнаруживать как stale semantic evidence. Межфазная непрерывность, возврат, IDs и количество/порядок pair-строк сохранены. Verifier не переписывает файлы, но выдаёт ложный PASS:

| Независимый контрпример | Требуемый исправленный исход | Фактический C |
|---|---|---|
| A: убрать retract, выполнить прямой UP/DOWN под именем нового сервиса | FAIL/BLOCKED; шесть положительных stage/pair witnesses | exit **0**, PASS |
| B: тот же случай | FAIL/BLOCKED; шесть положительных witnesses | exit **0**, PASS |
| A: сначала UP, затем Y, DOWN и возврат Y | FAIL/BLOCKED; четыре native witnesses | exit **0**, PASS |
| A: powerpack_module поднимает tank/motor/rear plate, front plate остаётся на месте | FAIL/BLOCKED; два native tank/front-plate witnesses | exit **0**, PASS |
| A: motion=rotation у motor на UP; raw матрица пересчитана с unsupported result | отклонить подтверждённый сервис; INDETERMINATE по методу | exit **0**, PASS |

Native положительные объёмы в первых четырёх случаях заново получены отдельным Part.common в собственных рациональных witness-позах, не выведены из одного старого текстового статуса. В пятом frozen engine прямо отклоняет motion как неподдержанный. Подмены не являются изменениями проекта; это отрицательные fixtures. Exact expected/actual exit, stdout, native volumes и отсутствие записи verifier — evidence/service_counterexamples.json. Успешный exit самого harness означает воспроизведение дефекта; ожидаемый правильный exit проверяемого verifier записан как **1**, фактический — **0**.

**Обязательные исправления:** readonly verifier должен связать актуальные входы/планы, фактические state/time/состав движущихся тел и полные интервальные геометрические результаты. Derived critical/changed/moving sets и исходы нужно вычислять из проверяемых входов/сцен, а не доверять сохранённому списку/статусу. Сверять текущие matrices, interval_rows/evidence, classifications и assessment, сохраняя все границы фаз, positive/UNKNOWN и legacy BLOCKED. Не чинить пакет в verifier и не ослаблять 34 frozen модуля. Добавить все пять updated-hash регрессий с ожидаемыми отказами и отдельный RECHECK исправленного SHA.

Этот дефект относится к **новому adapter**, не к неизменённому engine или прежнему R5-FRAME-NEW-B01. Генерация текущего C и readonly/hash-свойства воспроизведены, но 102 проходящих теста/16 author faults не покрывают найденную stale-semantic ошибку. **Вердикт нового кода: REJECT_WITH_BLOCKER R5-FP-NEW-B01.**

## Конечный остаток и отчётность

Независимо сопоставлены все **557 non-CLEAR пар**, их исходные class-счётчики и все case/phase контексты между classifications stream и inventory. Состав: **6 native BLOCKED legacy UP, 2 envelope controls, 15 old-policy nominal contacts, 534 INDETERMINATE**. Все сохранённые native positive пары совпали с независимым сканированием поддержанных поз; иных positive native-пар в исходных сценах C не найдено. Новые 62 nominal mating interfaces не переписывают эти классы и не являются разрешёнными реальными креплениями.

Две оболочечные пары research_obstacle/rod — отрицательные synthetic controls без сохраняемого native obstacle; они не доказанные реальные столкновения. Непредписанные/curved/численно неоднозначные контакты и unknown-control не объявлены CLEAR. Шесть фактических legacy проникновений не подменены неопределённостью физической реализуемости альтернативы. В исходном отчёте эти ограничения представлены корректно. Однако автоматический verifier способен выдать ту же успешную сводку для повреждённой сервисной сцены, поэтому принимать новый код только по его отчёту нельзя.

## Команды и доказательства

Фактические основные команды из корня материализованного checkout:

```sh
# Сначала сохранённый C, до генерации:
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
# Затем только в отдельной копии:
/usr/bin/python3 -B cad/feed_power/generate.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B verification/r4_feed_power/regressions.py
```

Независимые воспроизводимые probes, оригинал и копии должны оставаться раздельными:

```sh
/usr/bin/python3 -B verification/r5_feed_power_review/readonly_probe.py /workspace/REV /tmp/r5-fp-saved.json
/usr/bin/python3 -B verification/r5_feed_power_review/native_probe.py /workspace/REV /tmp/r5-fp-native.json
/usr/bin/python3 -B verification/r5_feed_power_review/artifact_probe.py /workspace/REV /tmp/rev-fp-build-8fb /tmp/r5-fp-artifacts.json
/usr/bin/python3 -B verification/r5_feed_power_review/service_counterexamples.py /tmp/rev-fp-fault-8fb /tmp/r5-fp-semantic.json
```

Шесть unittest discover команд (`-B -m unittest discover -s <directory> -p 'test_*.py'`) и их полные выводы — evidence/unit_tests.json; directories: cad/layout, models/rev_linked_scene, models/kinematic_press, cad/layout_correction, cad/frame_mount, cad/feed_power. Generation command log, semantic/native repeat, readonly snapshots, author regressions и собственные counterexamples сохранены рядом. Immutable исходные результаты C и старые акты/probes не переписаны.

## Ограничения и дальнейшая передача

14 исправлений и исходный условный путь можно передать координатору как независимо проверенную **конечную геометрическую область с WARNING**. Новый code adapter не принимать до исправления R5-FP-NEW-B01 и независимого RECHECK точного SHA. Интеграция и нормализация учёта отдельно координатором; задача не становится DONE этим актом.

**NOT_RUN:** физическая подача/дозирование, реальный привод/extra stroke, крепления/расстыковка/энергоизоляция, временные опоры/подъём/площадка, прочность/жёсткость/ресурс, реальные зазоры/допуски/наклоны, неописанные движения/гибкие коммуникации, нормативная применимость и безопасность. Не заявлены полнота анализа рисков или исчерпывающее доказательство программы. Пробы и физические испытания не проводились. Архитектура/ТЗ не утверждены, реальные параметры UNKNOWN. Прежние открытые проектные B01–B03/замечания не закрываются; **G1 OPEN**.

SHA-256 новых скриптов, акта и доказательств — evidence/sha256.json (сам manifest исключён). Точный commit SHA публикации акта сообщается отдельно после проверки удалённой ветки, без самоссылки в коммит.
