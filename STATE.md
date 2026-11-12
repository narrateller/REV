# Ожидает принятия: отдельный claim условного расчёта R3

T-r3-parametric-sizing-01 READY / PROPOSED_PENDING_MAIN; owner_session NONE, proposed owner r3-sizing-20261112 / R3 / Codex. Постановка и claim C `5fdc50bbc8e83241ad2f8754860a503f5de9f418`; main при сверке `680946b8abba9d921c5723b523be573554c15eca`. Входы R2 `4fd6f32b4df3186a805ac7e654be6c4c9e1c6a50`, R5 `81e5dba4bb47cf8a552b3eb55733454ac4f9742d` (ACCEPT_WITH_WARNING) доступны в Git, в main ещё не интегрированы.

Следующий шаг — последовательное принятие claim оператором/координатором в main; затем fetch, проверка вхождения C/owner/lease/конкуренции/входов, входной аудит и расчёт по полной постановке в ISSUES_AND_TASKS.md. Модель/сценарии NOT_STARTED; это не результат для инженерной приёмки. Чужие назначения и сроки не изменены. Подробности: verification/r3_parametric_sizing/claim.md, хэши preflight.json; капсула handoffs/T-r3-parametric-sizing-01/r3-sizing-20261112.md.

G1 OPEN; архитектура/ТЗ и конкретное оборудование не утверждены; физические испытания NOT_RUN. Предыдущие инженерные сводки и handoffs сохранены ниже, текущая запись не отменяет их ограничений.

---

# Предложение интеграции исследовательского CAD-пакета

R1: решение `decisions/R1-RESEARCH-LAYOUT-ACCEPTANCE.md`, финальный C `7d1bd1c92c7cedc4282e3a903463e88205b86fa3`, независимый RECHECK `05f149332bc173eaa008250e1a5ab21e4d7611cf`. До merge IN_REVIEW. Приёмка предлагается только как исследовательского результата с WARNING, не геометрически/физически готового пресса. 6 legacy UP-пар BLOCKED, физическая выполнимость L-пути INDETERMINATE; G1 OPEN.

## Предыдущая сводка (история)

# STATE — панель проекта

## Текущий результат R4 — сервисный semantic fix (2026-11-12T03:05:59Z)

T-r4-layout-build-01 IN_REVIEW, **C `7d1bd1c92c7cedc4282e3a903463e88205b86fa3`**, REMOTE. Входной R5 2592b47: исходная геометрия/условный L-path с WARNING подтверждены, новый adapter REJECT_WITH_BLOCKER R5-FP-NEW-B01. Исправление требует независимого RECHECK (NOT_RUN), B01 OPEN, не самоприёмка.

Fresh service calculation учитывает все registered phases/participants/pairs/метод/план/continuity/return; все cached matrices/interval/classification/assessment/report сверяются по значениям. Command execution/test expectation/actual path/physical feasibility разделены. 110 tests; 5 original исправленных verifier exits1 (4 BLOCKED/1 INDETERMINATE), 25 цепочечных command records и compounds PASS. Два restored readonly verifier идентичны/без записи. Все 638919 matrices/classifications и 593931 interval rows пересчитаны.

34 frozen модуля, 46 source/native/input/scene/classification preservation files unchanged; CAD/STEP не сохранялись. Исходный L геометрически сохраняется; 14 static fixes/6 legacy native BLOCKED сохранены. 20 model geometric paths confirmed /2 BLOCKED, но overall physical service 20 INDETERMINATE/2 BLOCKED. Expected negative не означает пригодность. Весь пресс READY INDETERMINATE, сборка/задача не приняты.

Main/owner/claim/lease проверены, срок/область не расширены; исторический учёт main координатор сверяет до интеграции. Текущие данные/команды verification/r4_fp_fix/, запрос recheck_request.md, source cad/feed_power/, капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md и NEXT_MODEL.md. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, размеры ASSUMED/реальные UNKNOWN, G1 OPEN, merge не выполнялся.

## История результата R4 — дозатор/гидростанция (2026-11-12T01:34:06Z)

T-r4-layout-build-01 IN_REVIEW, **C `8fbbef00023e146e32cb6ff290a0c19408ca13b5`**, REMOTE. База a5d5bad, RECHECK c2e96a5 закрывает прежний B01 только в его области. Новый FP OUTPUT review NOT_RUN; весь пресс не принят.

ASSUMED rev8 заморожен до построения на 450e869. 14 static native пар устранены; 6 legacy doser-UP native пар остаются BLOCKED, предложенный side/lift path геометрически свободен, реальный дополнительный ход/подъём INDETERMINATE из-за UNKNOWN данных. R4-FP-SERVICE-01 OPEN. Не заявлять все 20 устранёнными. Сохранены все old ID, A91/B89; 62 новых и 58 прежних conditional interfaces, реальные силы/крепления UNKNOWN.

638919 all-pair/507043 critical rows, 878 прежних target rows без регрессии. 22 continuous/restored сервиса, 8 новых без positive overlap; 102 tests/18 package-regression cases PASS, 16 faults rejected без записи/auto repair. Actual native/STEP/канонические queries/repeat проверены; старый DoserRemoval всё ещё blocked UP. 34 прежних Python-модуля и old CAD/review/probes неизменны; новые FP wrappers отдельно для review. Генерация и readonly verifier отдельно.

Конечный список 557 non-CLEAR пар с 6 native legacy penetrations и всеми INDETERMINATE/оболочками сохранён. **Whole press READY INDETERMINATE**. Main/claim/lease проверены, scope/срок не расширены, нормализация исторического учёта main координатором до интеграции. Файлы/команды cad/feed_power/, cad/build/feed_power/, verification/r4_feed_power/. Текущая капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md, NEXT_MODEL.md. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, реальные UNKNOWN/условные ASSUMED, G1 OPEN; merge не выполнялся.

## История результата R4 — readonly verifier (2026-11-12T00:36:54Z)

T-r4-layout-build-01 IN_REVIEW, **C `a5d5bad6dd8928045512bca16836fd1d2544b7ca`**, REMOTE. Входной акт R5 0b4788d: ограниченная геометрическая группа принята с WARNING, новый процесс выпуска отклонён по R5-FRAME-NEW-B01. Исправление передано на независимый RECHECK (NOT_RUN), B01 OPEN.

Verifier больше не пишет manifest/входы/evidence/diagnostic reports, результат только stdout/exit. Явная генерация generate.py отдельно; односторонние хэши стадий. 95 tests и 18 регрессионных случаев/23 команды PASS: две отдельные генерации, по два неизменяющих verifier, 15 missing/corrupt/stale отказов без auto repair. Два verifier текущего пакета также идентичны, 92 файла без изменения байтов/mtime. Все 23 frozen модуля неизменны; необходимый release diff выделен для review.

Геометрический scope не менялся: 35 исходных deterministic evidence/source хэшей сохранены, native семантика A79/B77 одинакова, 18 устранённых и 20 оставшихся native-пар сохранены. Остальные UNKNOWN/оболочки/непредписанные контакты видимы, **whole press READY INDETERMINATE**. Пересохранение native служебных metadata при явном build не является изменением геометрии.

main/owner/claim/lease проверены 12 ноября, срок без продления; историческую нормализацию учёта main сверяет координатор до интеграции. Текущие команды/доказательства verification/r4_frame_fix/, текущий пакет cad/build/frame_mount/, капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md и NEXT_MODEL.md. Старые review/RECHECK/probes сохранены. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, реальные UNKNOWN/условные ASSUMED, G1 OPEN; merge не выполнялся.

## История результата R4 — рамная/монтажная коррекция (2026-11-11T22:56:14Z)

T-r4-layout-build-01 IN_REVIEW, **C `5198e0184b35978701ed1ce762d9e4fcd44997b3`**, REMOTE в work-r4/build-layout/r4-linked-20261111. Входной R5 04efe57 закрыл B01/B02 только в проверенной программной области. Новая коррекция/дополнительный код требуют независимого OUTPUT review, NOT_RUN. Задача и компоновки не приняты.

ASSUMED rev7 заморожен до построения на 17501de. Поперечины/рельсы/опоры цилиндра/выхода исправлены, открытый U-коридор и связи к основанию; старые ID сохранены A79/B77. 18 native before/after пар zero volume, 58 условных positive-area интерфейсов, крепёж/реальные силы UNKNOWN. Все 23 reviewed Python-модуля неизменны.

346709 all-pair строк, 114156 поддерживаемых строк новой группы без positive overlap +28 INDETERMINATE unknown-control. 658 прежних target строк без регрессии, 3672 строки цилиндровых сервисов, 14 continuous/restored сервисных последовательностей; actual CAD/STEP/all QueryVolumes/repeat/8 limited outcomes/83+5 tests PASS. Осталось 20 native penetration пар и прочие неопределённости; конечный inventory 463 пары. Дозаторный монтаж/извлечение и бак/мотор OPEN, **whole press READY INDETERMINATE**.

Owner/claim/lease/main сверены, срок не расширен; историческую нормализацию учёта main сверяет координатор перед интеграцией. Код/результаты cad/frame_mount/, cad/build/frame_mount/; команды README и independent review request. Текущая R4 капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md, NEXT_MODEL.md. Старые исходники/модели/акты/RECHECK/probes сохранены. Реальные параметры UNKNOWN, все исследовательские размеры ASSUMED; архитектура/ТЗ не утверждены, испытания NOT_RUN, G1 OPEN. Merge не выполнялся.

## История результата R4 — исправление аналитики (2026-11-11T21:37:52Z)

T-r4-layout-build-01 IN_REVIEW, C `66924aed1cb2d193b9883d2140d85560b1e4b0cb`, ветка work-r4/build-layout/r4-linked-20261111. Вход R5 04b9f2950a34492b15e1d7c893f680b82f9183b9: целевая геометрия C 120a958 подтверждена в её области, новый classifier/orchestration REJECT_WITH_BLOCKER. Представлены method/evidence gate и строгий sufficient contract с отдельными verifier assertions. R5-LAYOUT-NEW-B01/B02 OPEN до независимого RECHECK (NOT_RUN).

Execution/test/scene outcomes разделены. 83 unit tests, 15 classifier и 40 cycle regressions PASS; штатные обе CLI exit 0. Full-unlinked CAD counterexample теперь rejected обеими CLI exit 1, actual LINK_ABSENT/BLOCKED/false у sufficient A/B. Inputs/native geometry/PNG/15 frozen core/evidence неизменны; R5 geometry_probe воспроизвёл 251923 строк, 618 target/58 native без positive, сервисы restored. Прочие проникновения и UNKNOWN не скрыты, whole press READY INDETERMINATE.

Owner/claim/lease/main сверены до C; срок не расширялся, предварительный учёт main требует сверки координатором перед интеграцией. Registry/COTS/models неизменны, реальные параметры UNKNOWN, условные ASSUMED отдельно; архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Текущая эстафета NEXT_MODEL.md, капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md; результаты cad/build/layout_correction/ и verification/r4_analysis_fix/.

## История результата R4 — геометрическая корректировка (2026-11-11T20:34:47Z)

T-r4-layout-build-01 IN_REVIEW, C `120a9582f4835e81cdf324605a14f632ce7db2cb`, ветка work-r4/build-layout/r4-linked-20261111. На базе checked tool de377f0/review 214b055 целевые gate/pocket и B lock/stop/guard/support positive-volume пересечения устранены в поддержанной исследовательской геометрии по всему ходу/возврату/сервисам. Все исходные ID сохранены; 70/68 тел. 15 checked-tool файлов не менялись. Отдельные новые orchestration/classifier/face-touch policy требуют независимого review вместе с геометрией.

73 прежних + 6 новых tests, 8 limited outcomes и CAD/STEP/query/repeat PASS; 130453 рабочих + 121470 сервисных строк, 618 target rows без strict penetration, 6 native before/after zero volume. 216 дополнительных design-контрольных строк и новые тела без положительных/envelope пересечений, 12 сервисных последовательностей восстановлены. Показаны геометрические feed/isolation/reaction witnesses; реальные усилия/физика/безопасность UNKNOWN. Прочие проникновения/сервисы/неопределённость не скрыты, whole-press READY INDETERMINATE, весь пресс не принят. Геометрический OUTPUT review NOT_RUN.

Owner/lease/claim/main сверены до C, scope исходной задачи покрывает исправление геометрии, срок не продлён. Историческое расхождение NONE/PENDING main требует сверки координатором перед интеграцией. Реальный registry/COTS/models неизменны, все числа отдельно ASSUMED. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Актуальная эстафета NEXT_MODEL.md, handoffs/T-r4-layout-build-01/r4-linked-20261111.md; результаты cad/build/layout_correction/, навигация cad/layout_correction/README.md.

## История результата R4 — B02 QueryVolumes (2026-11-11T19:31:43Z)

T-r4-layout-build-01 IN_REVIEW, C `de377f012da08f34796b2e59aee663ba0b2b3d2b`, ветка work-r4/build-layout/r4-linked-20261111. Входной акт 8f381c4b080d902cb023429c54d518bfd6fab681 закрыл B01 в проверенной области и оставил B02 OPEN/Q01. Исправлена проверка всех канонических нативных зон по входам; новый независимый RECHECK B02 NOT_RUN, автор не закрывает блокер. Lifecycle неизменен, B01 не переоткрывается. 73 unit tests / 64 query-negative / 14 прежних CAD-negative / 33 lifecycle / 20 независимых lifecycle / 8 limited outcomes PASS, 14 команд exit 0.

Геометрия зон и компоновок сохранена, 107486 записей фаз/пар и нативные проникновения R5 совпали. Полная сборка не принята, READY INDETERMINATE. Main/claim/owner/lease прежние и сверены до C; предварительный учёт main требует отдельной сверки координатором перед интеграцией. Реальные параметры UNKNOWN, условные ASSUMED отдельно, registry/COTS/models неизменны. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Актуальные пути — NEXT_MODEL.md, handoffs/T-r4-layout-build-01/r4-linked-20261111.md, cad/build/research_layout/assessment.md и validation.json.

## История RECHECK-пакета инструмента R4 (2026-11-11T19:07:56Z)

T-r4-layout-build-01 IN_REVIEW, C `5449fb9bc4c20fcbc40fdec932876dcecc90ef4d`, ветка work-r4/build-layout/r4-linked-20261111. Входной акт R5 e939b41d0139b0a3a08a5950eeeec6e92324cf9b на исходный C 6bb66a5: REJECT_WITH_BLOCKER. Исправления lifecycle и actual-CAD validation представлены; R5-CAD-TOOL-B01/B02 OPEN до независимого RECHECK (NOT_RUN). 69 unit tests, 33 lifecycle, 14 CAD-negative и 8 limited outcomes PASS; код/команды/результаты в BUILD_README/assessment/validation/checks. Пробы независимого R5 и история сохранены.

Геометрия и все 107486 записей фаз/пар неизменны, проникновения подтверждены повторными native probes; полная сборка не принята, READY INDETERMINATE. Owner/claim/lease прежние, main 06d68b0 повторно сверена; нормализация предварительного учёта main требует последовательной интеграции координатором. Registry/COTS/models неизменны, реальные данные UNKNOWN, условные ASSUMED отдельно. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Актуальная эстафета NEXT_MODEL.md, капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md.

## История результата R4 — T-r4-layout-build-01 (2026-11-11T18:33:56Z)

Code/results `6bb66a566719593a59935e341b1b5c80a1cbc9a7`, ветка `work-r4/build-layout/r4-linked-20261111`; IN_REVIEW, независимый OUTPUT review NOT_RUN. Claim принят PR #35 на main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53, owner r4-linked-20261111, lease до 2026-11-12T18:06:24Z. Предварительный учёт NONE/PENDING нормализован по принятому claim, история сохранена. Эстафета: NEXT_MODEL.md и handoffs/T-r4-layout-build-01/r4-linked-20261111.md.

Редактируемые условные A/B, виды, STEP, код/отчёты опубликованы для независимой проверки; 60 тестов и 8 исходов ограниченного пути PASS. Полная сборка не принята: условные пересечения и неподдержанные условия сохранены, READY всей установки INDETERMINATE. Все численные входы ASSUMED отдельно, реальные параметры REV UNKNOWN; registry/COTS/старые модели неизменны. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Детали: cad/layout/BUILD_README.md, cad/build/research_layout/assessment.md. Старые сводки ниже — история, включая капсулу R1; она не заменяет текущую эстафету R4.

## Паспорт

| Поле | Значение |
|---|---|
| project_id / изделие | REV / Hydraulic briquetting press |
| Подтверждённая цель | Собственный функциональный аналог BP500 с возможностью изготовления в РФ; F-REV-01…04 |
| Сырьё / подготовка | Отсортированная древесная фракция строительного мусора после металлоудаления; до пресса: сортировка, металлосепарация, дробление/просев |
| Функции / критерии | Приём, дозирование, уплотнение, выдача; размеры/производительность/пороги UNKNOWN; выбор покупателя не является условием T-INIT |
| Контекст компании | Выпуск пеллет и расширение ассортимента; не определяет требования к прессу |
| Владелец и утверждающий инженер | narrator; утверждающий инженер назначается отдельно |
| Источники прототипа | Четыре PDF инвентаризированы: sources/index.md; достоверность инженерных заявлений не принята |
| Принятое ТЗ / базовая линия | NONE / NONE |
| Режим | PROJECT; цель подтверждена, проект требований rev6 не утверждён |
| Текущая ветка / база | work/T-INIT/codex-01 / 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17 |
| Последнее обновление UTC / session_id | 2026-11-10T17:42:58Z / codex-01 |
| enforcement | PROCEDURAL; серверные ограничения не проверены |
| Численная база | params/registry.yaml |
| Задачи / проверки | ISSUES_AND_TASKS.md / reviews/cross_check_log.md |

## Ворота V-модели

| Ворота | Этап / ветвь | Статус | Обязательное доказательство | Ответственный / проверка / утверждение |
|---|---|---|---|---|
| G1 | Анализ и ТЗ / левая | NOT_STARTED | Измеримые требования, границы, источники, неопределённости, план валидации | R1 / R2+R5 / пользователь |
| G2 | Архитектура / левая | NOT_STARTED | Физика, силовой путь, схемы, балансы, цикл, проверенный COTS-каталог, интерфейсы, риски | R2+R3 / R1+R5 / назначенный R1 |
| G3 | CAD / основание V | NOT_STARTED | Сборка, сопряжения, материалы, массы, движения, экспорт, входы CAE | R4 / R3+R5+R6 / назначенный R1 |
| G4 | Верификация и валидация / правая | NOT_STARTED | Матрица требований и тестов, воспроизводимые прогоны, сходимость, границы применимости | R5+R1 / независимые R2+R3+R4 по области / пользователь |
| G5 | DFM/CAM и РКД / выпуск | NOT_STARTED | РКД, спецификации, допуски, маршрут, контроль, закрытые замечания, решение о выпуске | R6 / R4+R5 / инженер, назначенный пользователем |

Здесь указаны функции; конкретные проверяющие не могут быть авторами проверяемых версий.
Для каждого решения о воротах создать запись в `decisions/<decision_id>.md`: baseline commit, scope, evidence, exclusions, blocker_ids, approver, основание полномочий, UTC.
Текущее решение по плану: ARB-R1-RECHECK-03 (не gate decision).
По предоставленному дополнению RECHECK-05 R5-IMPL-01 CLOSED и регрессия R5-IMPL-02 PASS только в synthetic области на debfd085; probe и ID сессии не представлены. Задача остаётся IN_REVIEW, G1 открыт. История consecutive_rejections=2 сохраняется; Q-R5-RECHECK-03 разрешён.
Независимый review эскизов REV-R5-REVIEW-01-001: WARNING, допускает лишь
ограниченную документальную проработку; четыре замечания OPEN. Новые циклы
и задание этим старым актом не проверены; отдельный акт REV-R5-MODEL-REVIEW-01-001
на постановку rev2/циклы даёт WARNING без обязательных исправлений и допускает
исследовательскую передачу R4 на synthetic данных после назначения/claim.
Открытые технические вопросы: собственная входная спецификация, состав партий/покрытий/клеёной
древесины/примесей, остаточный металл, влажность и фракция по стадиям, состояние
входа и границы поставки. Происхождение сырья и имеющиеся операции известны
со слов оператора; реальные пробы и журналы пока отложены;
цель изготовления в РФ подтверждена, фактическая изготовимость и локализация
ещё исследуются. BP500-ANALOG не используется; OBS/HYP не являются архитектурой REV.

## Активные назначения

| task_id | Роль | session_id / model_label | База | Claim / heartbeat / lease | Капсула |
|---|---|---|---|---|---|
| T-INIT | R1 | codex-01 / Codex | 2e479849cea10dab9376a68cb44d2ff716c215da | ACCEPTED_MAIN (PR #1); claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a; heartbeat: 2026-11-10T17:42:58Z; lease_expires_at: 2026-11-11T12:06:09Z | handoffs/T-INIT/codex-01.md |
| T-r4-layout-build-01 | R4 | r4-linked-20261111 / Codex | 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 | ACCEPTED_MAIN PR #35; heartbeat 2026-11-11T21:38:17Z; lease 2026-11-12T18:06:24Z; IN_REVIEW | handoffs/T-r4-layout-build-01/r4-linked-20261111.md |

## Active Handoff Capsule

```yaml
capsule_version: '1.0'
status: ACTIVE
task_id: T-INIT
role: R1
session_id: codex-01
model_label: Codex
author_sessions:
- codex-01
assignment_evidence: 'Подтверждение пользователя; T-INIT; claim принят через PR #1'
created_at_utc: '2026-11-10T18:33:57Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: 791d0ce8ccb31373b221d0b69063e2f835b442c0
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T17:42:58Z'
subtask: 'Историческая капсула RECHECK-04; актуальный следующий шаг в NEXT_MODEL.md по дополнению RECHECK-05'
input_refs:
- commit: 576a17fc0b127cb7d377992c01d645a77bed42d4
  paths:
  - models/kinematic_press/linked.py
  - models/kinematic_press/run_linked.py
  - models/kinematic_press/test_linked.py
  - models/kinematic_press/results/linked_report.json
- path: verification/r5_recheck_04/submitted_review.md
  source: акт предоставлен пользователем, reviewer session UNKNOWN
changed_files:
- verification/r5_recheck_04/submitted_review.md
- verification/r5_recheck_04/disposition.md
- ISSUES_AND_TASKS.md
- STATE.md
completed_steps:
- Сохранён акт пользователя; сверены пять SHA256 с Git blobs
- Во временной копии выполнены восемь существующих test_linked, все прошли; дефект в сохранённом отчёте подтверждён
- Зафиксированы CLOSED R5-IMPL-02 только synthetic на указанном SHA, OPEN R5-IMPL-01
- Подготовлены три исправления R4 и план независимого recheck; новый независимый review не проводился
unfinished_step:
  exact_expression_or_node: R4 исправляет три пункта раздела 5, затем независимый R5 проверяет новый SHA
  last_successful_command: python3 -m unittest test_linked в изолированной temp-копии 576a17fc
  expected_result: Сверить существующие тесты и сохранённый разрыв
  observed_result: 8 tests OK; B/collision содержит output_obstacle mismatch при matches_expected true
environment:
  tool_versions:
  - Python 3.12.14
  - PyYAML 6.0.3
  - pdftotext 25.03.0
  - Tesseract — см. JSON
  dependency_lock: requirements.txt
  seeds: []
running_jobs: []
open_hypotheses:
- Непрерывность и её влияние на статусы требуют исправления и повторной проверки
blocker_ids: []
review_refs:
- 'REV-R5-RECHECK-04-001: предоставлен пользователем, reviewer session UNKNOWN; текст сохранён без изменений'
- Независимый review исправления NOT_RUN
uncommitted_or_unsaved: []
next_action: R4 получает commit решения 791d0ce8ccb31373b221d0b69063e2f835b442c0, проверяет owner/lease и в
  своей ветке вносит три исправления; затем передаёт новый SHA независимому R5
next_action_success_criterion: Все исходы/мутации и регрессии проверены независимым R5 на новом code/results
  SHA; только тогда возможно закрытие R5-IMPL-01
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: 7e99ecf87874b3bc53b1c08f115b2b5ee2ad4c3c
```

## Очередь следующей модели

| Порядок | task_id | Адресат | Действие | Условие начала |
|---|---|---|---|---|
| 1 | T-INIT | @R1 | Исправление SYN-LINKED-EJECTION A/B и полного состава пар у R4 | Решение арбитража опубликовано; сначала фиксация SHA/owner/lease, приёмка BLOCKED до RECHECK |

После назначения сначала читать запись T-INIT. Если входов нет, фиксировать UNKNOWN и готовить структуру требований; не выдавать проект ТЗ за утверждённое ТЗ.

## Оператор и автоматические проверки

Версия шаблона: 1.2.1-candidate. Регламент: OPERATOR_GUIDE.md.
Workflow подготовлен; его выполнение и настройки GitHub не подтверждены.
Форма решения: templates/gate_decision.md; форма арбитража: templates/arbitration.md.

## Переход к следующей модели

Действующая инструкция для нового участника: NEXT_MODEL.md. После завершения задачи исполнитель обновляет её вместе с капсулой; см. AGENT_PROTOCOL.md, раздел 10.

Назначение R1 подтверждено; claim принят в main. Паспорт и проект требований/матрицы/нормативной области подготовлены, требуется
независимая проверка и ответы на вопросы. T-INIT не завершена; G1 остаётся NOT_STARTED.
Текущий результат: постановка модели rev2 на 3aebae606011ded0f6d6e0a8d6ccc15094d88feb; акт её независимой проверки в commit 7e99ecf87874b3bc53b1c08f115b2b5ee2ad4c3c.
Операторские OP-данные сохранены; требования и испытания относятся к прессу.
Товарные предложения — только архивный контекст, не условие продолжения.
Исследование: sources/functional_analysis_r2.md; подтверждённая цель отделена от OBS/HYP.
Выбор архитектуры, расчёты и утверждение G1 не выполнялись.

## Предложение назначения R4

T-codex-01-01: пользователь назначил r4-model-01 / Codex / R4; claim ACCEPTED_MAIN, owner_session: r4-model-01. Координация Q-r4-model-01-01, капсула handoffs/T-codex-01-01/r4-model-01.md. Код NOT_STARTED; G1 открыт. Принятый владелец T-INIT не меняется.

## Частичный результат R4

T-codex-01-01 HANDOFF, owner r4-model-01. Код и результаты synthetic на b3ba802fb1bad642338a18ef82493f44ac069067; акт входа models/kinematic_press/input_audit.md. Пять случаев соответствуют ожидаемым статусам, независимый review NOT_RUN. Полная фазовая модель обеих альтернатив и все необходимые пары отсутствуют; завершение задачи не заявлено. G1 открыт.

## Передача R4 на R5

T-codex-01-01 IN_REVIEW: код/результаты 5cb3e8ab274ae4d746ec016ecd11b6c2acd14edb; запрос независимому R5 в ISSUES_AND_TASKS.md, ревью NOT_RUN. 13 фаз: synthetic 2 проверенные пары, 60 непроверенных; REV 0/62. UNKNOWN REV и G1 сохранены.

Независимый OUTPUT review REV-R5-IMPL-02-001 на 5cb3e8ab274ae4d746ec016ecd11b6c2acd14edb: вычислительное ядро PASS только для линейных AABB; фазовая модель REJECT_WITH_BLOCKER (R5-IMPL-01/02). 2/62 synthetic пары, REV 0/62. Силовая топология WARNING. Отчёт verification/r5_model_02/review.md; задача IN_REVIEW, G1 открыт, прежние R5-OBS не закрыты.

## Повторная проверка R5 — REV-R5-RECHECK-03-001

Проверенный SHA: 36cda8132dcf9dbb7193b01e98bdfff2ba5e2a7b.
Commit результата: 9e12e8bd4f2325ae0e887d3f2e28eaa85c55205f.
R5-IMPL-01 и R5-IMPL-02 остаются OPEN; T-codex-01-01 BLOCKED,
consecutive_rejections=2. Более раннее NONE в панели блокеров историческое:
актуальные блокеры — эти два. Владелец реализации r4-model-01 не меняется.
R1 должен рассмотреть Q-R5-RECHECK-03 (verification/r5_recheck_03/arbitration.md)
до новой итерации. G1 остаётся NOT_STARTED; архитектура не выбрана.
Капсула: handoffs/T-codex-01-01/r5-recheck-03.md; независимые контрпримеры
и минимальный сценарий: verification/r5_recheck_03/review.md.

## Текущий итог арбитража Q-R5-RECHECK-03

Решение 1283c9e6f3b14dbbe820dd06798399c611d34ce8 опубликовано в work/T-INIT/codex-01; полный
текст decisions/ARB-R1-RECHECK-03.md. Исходная область сохранена, CE-01/02
воспроизведены (verification/r1_arbitration_03/). Код R4 не менялся. Старые
записи NOT_STARTED/IN_REVIEW и ожидания решения выше — история, актуальны
BLOCKED приёмки и разрешение только корректирующей итерации по условиям решения.
Независимый RECHECK исправленной реализации ещё NOT_RUN; G1 открыт.


## Текущий итог REV-R5-RECHECK-04-001

По акту пользователя `verification/r5_recheck_04/submitted_review.md` блокер
R5-IMPL-02 закрыт в указанной synthetic области, R5-IMPL-01 OPEN; общий
результат REJECT_WITH_BLOCKER. Ранее указанные два OPEN — история RECHECK-03.
Поручение R4 и план независимого recheck: verification/r5_recheck_04/disposition.md.
Геометрия REV, физическая выдача, безопасность и G1 не подтверждены.

Текущий C решения по RECHECK-04: 791d0ce8ccb31373b221d0b69063e2f835b442c0; подробная эстафета в NEXT_MODEL.md.

## Предоставленный акт RECHECK-05

Заявлены PASS/CLOSED R5-IMPL-01 и PASS регрессии R5-IMPL-02 на `debfd085`, но подтверждение достаточности независимой проверки ожидает дополнения R5: пакет был усечён, а команды и результаты обязательных негативных мутаций в акте отсутствуют. R5-IMPL-01 OPEN/HOLD, задача BLOCKED; G1 OPEN. См. verification/r5_recheck_05/disposition.md.

## Дополнение RECHECK-05 — заявлено воспроизведение

На основании предоставленного пользователем дополнения R5-IMPL-01 CLOSED synthetic на `debfd085`, регрессия R5-IMPL-02 PASS synthetic. Код независимого probe и ID сессии пока недоступны; T-codex-01-01 IN_REVIEW, не DONE; G1 OPEN. См. verification/r5_recheck_05/disposition.md. Предыдущие статусы ниже по истории не являются текущими.

## Оценка R1 приёмки модели

См. verification/t_codex_01_01_acceptance/r1_assessment.md: кандидат на ограниченную synthetic приёмку, задача IN_REVIEW; отсутствуют идентификатор reviewer-сессии и артефакт независимых мутаций. G1 остаётся OPEN.

## Решение R1: приёмка synthetic результата

R1 принял `debfd085` в ограниченной области synthetic AABB; независимый R5 `r5-implementation-02`, акт и probe сохранены и зарегистрированы. Задача IN_REVIEW до последовательной интеграции с моделью и доказательствами; G1 OPEN. См. verification/t_codex_01_01_acceptance/r1_assessment.md.

## Повторная передача R5

T-codex-01-01: исправления на 36cda8132dcf9dbb7193b01e98bdfff2ba5e2a7b, запрос RECHECK к REV-R5-IMPL-02-001; R5-IMPL-01/02 OPEN до независимого акта. 127/127 пар лишь в разнесённой синтетической геометрии, REV 0/127; физическая связность не подтверждена. G1 открыт.

## Исправление по арбитражу R1

SYN-LINKED-EJECTION: code/results 576a17fc0b127cb7d377992c01d645a77bed42d4; ARB-R1-RECHECK-03 1283c9e6f3b14dbbe820dd06798399c611d34ce8; независимый R5 RECHECK NOT_RUN. R5-IMPL-01/02 OPEN, consecutive_rejections=2; G1 открыт. Синтетический READY не подтверждает реальные условия REV.

## Принятие модели после PR #2

`main` `672c835e201766a943927917f12875a9204b0b34` содержит model `debfd085` и review/probe `b4d4af9`; задача T-codex-01-01 DONE только в синтетической AABB области после принятия этой записи. G1 OPEN; следующая работа — проверка полноты требований/матрицы и подготовка независимого review ТЗ. Текущая эстафета — NEXT_MODEL.md.

Независимый OUTPUT-review проекта ТЗ REV-R5-TZ-REVIEW-01-001 на bff66903c4588321faf3b86bf0abb501c8a7c881: REJECT_WITH_BLOCKER для утверждения ТЗ/G1; R5-TZ-B01…03 OPEN, R5-TZ-W01…04 требуют обработки. Отчёт verification/r5_requirements_review/review.md; G1 NOT_STARTED/OPEN, архитектура не утверждена.

## Ответ R1 на review проекта ТЗ

На базе `b527c62ba9f1f37a5176dc9ed45b4b245bcdb49d` подготовлены документальные исправления W01…04 и план по B01…03; все ожидают независимого RECHECK, три блокера остаются OPEN. Физические данные UNKNOWN/NOT_RUN, G1 OPEN. См. verification/requirement_criteria_development.md и NEXT_MODEL.md.

Ограниченный RECHECK REV-R5-TZ-RECHECK-01-001 на a02420fd3b100447550740a417d75c8608206cd7: W01…04 CLOSED документально; B01…03 OPEN, вердикт REJECT_WITH_BLOCKER для утверждения ТЗ/G1. См. verification/r5_tz_recheck_01/review.md. G1 OPEN, архитектура не утверждена.

## Независимый RECHECK и дальнейшая работа по ТЗ

`f1edde47c580308aed7c1308281fc3069e25ccd7`: W01…04 CLOSED документально, B01…03 OPEN; G1 OPEN, испытания/пробы NOT_RUN. Исправлены исторические ссылки на rev3 схемы; проверенный акт STALE относительно этих редакционных изменений, W01…04 не переоткрыты. Порядок доработки — verification/g1_blocker_workplan.md, текущая эстафета — NEXT_MODEL.md.

## Кандидатные границы поставки

R1 подготовил process/supply_boundary_options.md для согласования с оператором; D-REV-04 и B01…03 остаются OPEN, G1 OPEN. Пробы и журналы отложены.

## Предварительный ориентир точки передачи

OP-REV-07: оператор предварительно ориентируется на передачу после существующих дробления и просева. Это кандидат IN-REV-A; пригодность, точное место и ответственность UNKNOWN. См. process/supply_boundary_options.md. G1 OPEN.

## Уточнение по транспортировке и буферу

OP-REV-08: оператор оставил транспортировку от просева к прессу и промежуточный буфер UNKNOWN; поставка и ответственность не распределены. G1 OPEN.

## Уточнение по контролю включений

OP-REV-09: предварительная ответственность за проверку остаточного металла и других включений перед прессом — существующая линия; методы/пределы/эффективность UNKNOWN. G1 OPEN.

## Ориентир по возможной доподготовке

OP-REV-10: если доподготовка понадобится по исследованию, предварительно рассматривать её на существующей линии. Её необходимость, операции и оборудование UNKNOWN; G1 OPEN.

## Ориентир границы выхода

OP-REV-11: предварительный конец поставки по выданному брикету — выход пресса. Параметры выдачи и дальнейшее обращение UNKNOWN; G1 OPEN.

## Паспорт групп измерений

R1 подготовил process/input_material_measurement_passport.md для будущей документальной оценки R2. Методы и значения UNKNOWN; пробы/испытания NOT_RUN, B01…03 и G1 OPEN.

## Принятие claim R2

PR #6 принят в main `6ccc31bef5a49a600d162cb7ab99fd0aed40d457`, claim `dd57126ae68fccddcfaeeef087efe07e995d0e60` для `r2-material-01`, lease до 2026-11-11T23:45:21Z. Учётное исправление трекера в этой ветке ещё требует интеграции. Пробы/испытания NOT_RUN, G1 OPEN.


## Сравнение методов R2 — ожидает независимого review

T-r2-material-01 / r2-material-01 IN_REVIEW: входной акт и сравнение пяти групп в verification/r2_material_methods/. Исходные три документа сохранены на базе 47511c3f7f3eebe69e2c8f8e4863d68c74d36b72; внешние нормативные редакции не подтверждены. Пять групп — кандидаты, методы/пределы не утверждены, пробы и испытания NOT_RUN; B01–B03 OPEN, G1 OPEN. Точный SHA результата передаётся отдельно после фиксации.

OUTPUT-review REV-R5-R2-MATERIAL-01-001 на c78a745fb431b459bf6272b585d17a7fad977845: WARNING только на документальное сравнение пяти групп; R5-MAT-W01…04 для дальнейшей программы, методики и стандарты не утверждены. См. verification/r5_r2_material_review/review.md; B01–B03 и G1 OPEN, пробы/испытания NOT_RUN.


## Ответ R2 на замечания R5 к методам сырья

R2 подготовил verification/r2_material_methods/response_r5_material_01.md к акту 08d75ec9bc86afae14663a6037958e384b1965e0. T-r2-material-01 IN_REVIEW; W01–W04 OPEN до независимого RECHECK. Источники и пригодность NOT_RUN, пределы UNKNOWN; пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

Ограниченный RECHECK REV-R5-R2-MATERIAL-RECHECK-01-001 на fcbeefae46b4fd999c194bd214b5dda7c476b0ec: W01–W04 CLOSED только документально; WARNING, применимость методов и источники не подтверждены. verification/r5_r2_material_recheck_01/review.md; B01–B03 и G1 OPEN.

## Документальное сравнение методов R2

Результат R2 принят R1 в ограниченной документальной области с WARNING; W01…04 CLOSED только для ответа, последующая проверка источников и пригодности остаётся обязательной. T-r2-material-01 IN_REVIEW до интеграции; B01–B03 и G1 OPEN. См. verification/r2_material_methods/r1_acceptance.md.

## Интеграция документального результата R2

PR #8 вошёл в main `3a725f82ae93c82c39ed7bb554d6f2449f47d92e`. T-r2-material-01 DONE только как ограниченное документальное сравнение с WARNING после принятия этой записи. Проверка первоисточников/применимости остаётся отдельной работой; B01–B03 и G1 OPEN.

## Принятие claim R2 для первоисточников

PR #10 принят в main `123240e20604eec9f497ad8eb3bc29d46539905a`; claim `295ec1e3549a597a76619465eaa58b1746bcefb1`, owner `r2-material-01`, lease до 2026-11-12T00:36:14Z. Учётная запись об этом подготовлена в отдельной ветке; G1 OPEN.


## Реестр первоисточников R2

T-r2-sources-01 IN_REVIEW: входной акт и реестр в verification/r2_primary_sources/. Прочитаны указанные разделы доступных материалов; полнота текстов, актуальность редакций и применимость NOT_RUN, подходящий источник по физическому остатку металла не установлен. NREL 42621/42620 CONNECT 403; пределы UNKNOWN, пробы и испытания NOT_RUN, B01–B03 и G1 OPEN.

OUTPUT-review REV-R5-R2-SOURCES-01-001 на 25745de1c69d2f0dd6adf8a6f10e8f7af59305a9: REJECT_WITH_BLOCKER для независимой сверки источников, CONNECT 403; R5-SRC-B01 OPEN. Реестр допустим как навигация с непроверенными выводами R2; см. verification/r5_r2_sources_review/review.md. B01–B03 и G1 OPEN.


## Копии источников для R5

SRC-01…04 сохранены в verification/r2_primary_sources/copies/ с URL и SHA-256, совпадающими с реестром. Независимая проверка NOT_RUN, R5-SRC-B01 OPEN; LAP 42620/42621/42622 NOT_RUN. Пробы/испытания NOT_RUN; B01–B03 и G1 OPEN.

RECHECK REV-R5-R2-SOURCES-RECHECK-01-001: четыре LFS копии на d9bc2f101ca001de763b5418dbe7cb2ad2ca5ab2 получены и сверены с реестром; R5-SRC-B01 частично устранён, OPEN по трём отсутствующим LAP и непроверенным атрибутам. SRC-03 требует уточнения разделов. См. verification/r5_r2_sources_recheck_01/review.md; B01–B03 и G1 OPEN.


## Уточнение реестра источников после RECHECK R5

R2 уточнил SRC-02…04 и повторил запросы NREL 42620/42621/42622: CONNECT 403, тексты NOT_RUN; R5-SRC-B01 OPEN до независимой оценки. Методы не утверждены; пробы и испытания NOT_RUN; B01–B03 и G1 OPEN.

Ограниченный RECHECK REV-R5-R2-SOURCES-RECHECK-02-001: SRC-03/04 документально исправлены, SRC-02 корректно отделяет источники атрибутов; R5-SRC-B01 OPEN по отсутствующим LAP и непроверенным атрибутам. См. verification/r5_r2_sources_recheck_02/review.md; B01–B03 и G1 OPEN.


## Передача LAP и карточки OSTI для R5

Получены копии NREL 42620/42621/42622 и JSON OSTI 1328338: verification/r2_primary_sources/lap_evidence/. Полный методический review, действительность и применимость NOT_RUN; R5-SRC-B01 OPEN. Пробы/испытания NOT_RUN; B01–B03 и G1 OPEN.

RECHECK REV-R5-R2-LAP-RECHECK-01-001: пакет 3bc59174fb850e9cf818df23ec55f9bc9c8a23f6 прочитан в указанной области, хэши совпали; R5-SRC-B01 OPEN из-за непроверенной связи карточки SRC-02 с PDF и дат 42620. См. verification/r5_r2_lap_recheck/review.md; B01–B03 и G1 OPEN.


## Происхождение LAP 42620 и аспектного отношения SRC-02

R2 подготовил verification/r2_primary_sources/version_inquiry/: расхождения установлены, но причина и версионная привязка UNKNOWN. R5-SRC-B01 OPEN, независимый review дополнения NOT_RUN; методы не утверждены, пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

REV-R5-R2-VERSION-REVIEW-01-001 на cec689d77087d912ebfe34425cb8d288768637c2: R5-SRC-B01 CLOSED в ограниченной документальной области при исключении неизвестных дат/AR; новый R5-VERSION-B01 OPEN из-за неверного SHA JSON, исследование REJECT_WITH_BLOCKER. verification/r5_r2_version_recheck/review.md; B01–B03 и G1 OPEN.


## Исправление SHA источника SRC-02

R2 исправил укороченный SHA openalex-src02.json и сохранил прежнее значение и локальные доказательства в version_inquiry/report.md. Исторический акт R5 STALE к новой редакции; R5-VERSION-B01 OPEN до независимой сверки. Даты/версия/значение AR UNKNOWN и исключены из проектного использования; пробы и испытания NOT_RUN, B01–B03 и G1 OPEN.

REV-R5-VERSION-HASH-RECHECK-01-001 на 4605f3435c5882550d540ff797e7322613723769: R5-VERSION-B01 CLOSED по Git и доступной копии, WARNING; временная исходная копия недоступна для независимого cmp. verification/r5_version_hash_recheck/review.md; B01–B03 и G1 OPEN.

## Документальная приёмка реестра источников R2

R1 принял ограниченную документальную карту с WARNING; источники/редакции/лабораторная применимость и R5-SRC-W01 остаются открытыми. T-r2-sources-01 IN_REVIEW до интеграции; B01–B03 и G1 OPEN. См. verification/r2_primary_sources/r1_acceptance.md.

## После PR #12

Реестр источников принят в ограниченной документальной области с WARNING; R5-SRC-W01 остаётся открытым. Подготовлен проект отдельной задачи verification/metal_detection_research_brief.md, без назначения и claim. B01–B03 и G1 OPEN.


## Документальное исследование контроля металла R2

T-r2-metal-01 IN_REVIEW: входной акт и исследование в verification/r2_metal_detection/. Заявления изготовителей не являются независимой валидацией, оборудование и методы не выбраны. R5-SRC-W01, B01–B03 и G1 OPEN; пробы, испытания и калибровки NOT_RUN.

OUTPUT-review REV-R5-R2-METAL-01-001 по 4dfcec6829fda861886aaa9a0e89cb63214cc894: REJECT_WITH_BLOCKER для независимой сверки M01–M06, все источники CONNECT 403; R5-METAL-B01 и R5-SRC-W01 OPEN. verification/r5_r2_metal_review/review.md. B01–B03 и G1 OPEN.


## Исходные HTML M01–M06

R2 нашёл все исходные ответы и сверил хэши; локальные копии и ограничения передачи описаны в verification/r2_metal_detection/source_access.md. Копии не опубликованы в Git, доступ R5 к локальным файлам NOT_RUN; R5-METAL-B01 и R5-SRC-W01 OPEN. Методы и приборы не выбраны; пробы, испытания и калибровки NOT_RUN, B01–B03 и G1 OPEN.


## Уточнение M01/M02 после независимой сверки

Акт R5 `2a8d43b3b7ef181fadc768363e36f4f04de21559` сохранён в истории. R2 уточнил формулировки в verification/r2_metal_detection/research.md; R5-METAL-B01 закрыт R5 только документально, документальная часть R5-SRC-W01 с WARNING, применимость и программа остаются OPEN. Независимая проверка новой редакции NOT_RUN; методы/приборы не выбраны, пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

## Документальное исследование контроля металла

Результат R2 принят R1 в ограниченной документальной области, R5-METAL-B01 CLOSED документально, применимость и программа R5-SRC-W01 OPEN. T-r2-metal-01 IN_REVIEW до интеграции; B01–B03 и G1 OPEN. См. verification/r2_metal_detection/r1_acceptance.md.

## После PR #15: анализ опасностей

Результат исследования металла интегрирован в `78f9d33061b55ea66e91e91f6f384b9e820a58bf`; T-r2-metal-01 DONE только документально после принятия этой записи. Проект задания по B03 — verification/press_risk_analysis_brief.md; назначение и claim не выполнены. G1 OPEN.


## R3: документальные опасности и нормативные вопросы

T-r3-safety-01-01: owner r3-safety-01; claim ACCEPTED_MAIN, PR #17,
`b28a99594e31bc6a34c35646e4717a2ccea5943a`; запись claim
`356b76a1a6711e31f04388ed5ab34cea55be5da1`; lease до 2026-11-12T04:14:00Z.
Документальный результат IN_REVIEW, независимая проверка NOT_RUN.
Капсула handoffs/T-r3-safety-01-01/r3-safety-01.md; документы verification/r3_press_safety/.
B01–B03, R5-OBS-01…04 и G1 OPEN; пробы и испытания NOT_RUN.


## R3: исправления по независимому OUTPUT-review

REV-R5-R3-SAFETY-01-001 (`ec5662a386aabbe894c94cb8b97897d182d55580`) — REJECT_WITH_BLOCKER результата `43c5a0f0e89b386fdf07600cc6ccf27c7e6fa63c`. Исправления передаются на независимый RECHECK; R5-SAFETY-B01 и W01–W05 остаются OPEN. T-r3-safety-01-01 IN_REVIEW; B01–B03, R5-OBS-01…04 и G1 OPEN. Испытания и пробы NOT_RUN.

## Предварительная карта опасностей R3

R1 принял документальную карту с WARNING после RECHECK; T-r3-safety-01-01 IN_REVIEW до интеграции. Это не законченный анализ риска и не подтверждение защит/нормативной применимости. B01–B03, R5-OBS-01…04 и G1 OPEN. См. verification/r3_press_safety/r1_acceptance.md.


## После PR #18: новая задача нормативных источников

PR #18 принят в main `2b26e56f0d35119631bba959da50b32cccaac621`: T-r3-safety-01-01 DONE только как документальная карта с WARNING. Предыдущие записи IN_REVIEW относятся к моменту до интеграции. Отдельная T-r3-norms-01 READY; claim r3-safety-01 PROPOSED / PENDING_MAIN, lease предложен до 2026-11-12T08:12:00Z; исследование NOT_STARTED до принятия. Капсула handoffs/T-r3-norms-01/r3-safety-01.md. Место эксплуатации UNKNOWN; B01–B03, R5-OBS-01…04 и G1 OPEN.


## Нормативные источники: claim принят

T-r3-norms-01 IN_REVIEW: claim `3345b050966fc4e52b317e64381c0dd7bc087b2a` принят PR #19 на `d499216856b3bdbd65f7f23584be80ab6108576a`; owner r3-safety-01, lease до 2026-11-12T08:12:00Z. Подготовлены входной акт и реестр кандидатов в verification/r3_normative_scope/; независимая проверка NOT_RUN. Прежние PENDING_MAIN — история до PR #19. Место эксплуатации, применимость и обязательность UNKNOWN; B01–B03 и G1 OPEN.

## Нормативные источники R3 — документальная карта

Реестр предварительно принят R1 с WARNING: verification/r3_normative_scope/r1_acceptance.md. R5-NORMS-B01 CLOSED только для заявленных фрагментов; действующие редакции и применимость UNKNOWN/NOT_RUN. T-r3-norms-01 IN_REVIEW до интеграции, B01–B03 и G1 OPEN.

## После PR #20 — инженерные входы формования

На базе `4b898c14338083deebc27d9d4ec45ba691b62808` R1 подготовил verification/engineering_input_map.md. Документальные зависимости требуют независимой профильной проверки; данные сырья, усилия и размеры UNKNOWN. T-r3-norms-01 завершена только как документальная карта после принятия этой записи; B01–B03 и G1 OPEN.

## Уточнения карты инженерных входов по R3

Акт R3 `59bdfeb0992645d4382070fa09c613c6de65901f` WARNING; R1 уточнил знаки, базы, баланс, измерения и сопоставимость A/B. W01–W04 открыты до независимого RECHECK; прежний акт STALE к изменённому файлу. UNKNOWN/NOT_RUN сохранены, G1 OPEN.

## Документальная приёмка инженерной карты

R1 принял карту по RECHECK R3 WARNING только как постановку будущих измерений; см. verification/engineering_input_map_acceptance.md. W01–W04 закрыты документально, реальная методика/данные UNKNOWN; интеграция ожидается. B01–B03 и G1 OPEN.

## Проект программы данных формования

После PR #21 R1 подготовил verification/compaction_measurement_program_draft.md для документальной проверки R2/R3/R5. Фактические данные и критерии UNKNOWN; пробы и испытания NOT_RUN, B01–B03 и G1 OPEN.

## Предварительные замечания R2 к программе формования

Результат `e939c146f51d4a40daba75b1bb21bd694e12bccc` не принят как review: claim R2 PENDING_MAIN, в предлагаемой записи нет явного heartbeat/lease. R1 подготовил документальные уточнения W01–W05 в verification/compaction_measurement_program_draft.md; они ожидают независимой проверки. B01–B03 и G1 OPEN, пробы/испытания NOT_RUN.

## Постановка данных формования R2

Claim T-r2-compaction-data-01 принят PR #24 на `6f22d966de85a7072cea43d2288d560edfb3b558`; owner `e98b8ef8-7302-453a-ac8d-1edbb7d8860c`, lease до 2026-11-12T11:36:00Z. Проект схем отбора, связей и материального баланса — verification/r2_compaction_data/specification.md, независимый review NOT_RUN, задача IN_REVIEW. R5-COMP-W01–W05, B01–B03 и G1 OPEN; методы и пределы UNKNOWN, пробы/испытания NOT_RUN.

## Постановка данных формования — проект интеграции

Постановка `146f17de0f9e06f590f97f191a431f77a0b1c176`, независимый акт R5 `9a6488a8673f6025f48e75e9081fafedaa067bd8` и проект решения verification/r2_compaction_data/disposition.md подготовлены к интеграции как документальный черновик с WARNING. До принятия PR задача IN_REVIEW. R5-COMP-W01–W05, B01–B03 и G1 OPEN; методы/пределы UNKNOWN, пробы и испытания NOT_RUN.


## Предложение R3 по измерениям и наблюдаемости

На базе PR #25 `461a9abcc4bb0011291f6f7a1747524713b371ec` задача T-r3-compaction-measure-01 READY; предлагаемый owner r3-safety-01, claim PENDING_MAIN, lease предложен до `2026-11-12T12:29:35Z`. Исполнение и входной аудит NOT_STARTED до принятия claim. Существующий claim T-INIT истёк, владелец не изменён. R5-COMP-W03/W04, B01–B03 и G1 OPEN; пробы/испытания NOT_RUN.


## R3: постановка измерений и наблюдаемости на review

T-r3-compaction-measure-01 IN_REVIEW; claim `5f046982b59376eb26d89541adb81955b27e6ffb` принят PR #26 на `adaf5593edb7c374c112bbcc58c802d35bd4ccd3`, owner r3-safety-01, lease до 2026-11-12T12:29:35Z. Постановка и входной акт: verification/r3_compaction_observability/. Независимая проверка NOT_RUN; прежний PENDING_MAIN — история до PR #26. R5-COMP-W03/W04, B01–B03 и G1 OPEN, пробы и испытания NOT_RUN.


## Проект интеграции R3 W03/W04

Постановка `026bd890d7957526bfbee5ffb2745e9fe7b0c43e` и R5 OUTPUT-review `644d74178fefb4cb40150276532b08c6a8381b98` подготовлены к интеграции как документальный черновик с WARNING, см. verification/r3_compaction_observability/disposition.md. До принятия PR задача IN_REVIEW; R5-COMP-W03/W04 остаются OPEN до разработки и проверки применимой методики. B01–B03 и G1 OPEN, пробы/испытания NOT_RUN.

## Проект сравнения A/B R2

Claim T-r2-compaction-comparison-01 принят PR #28 в `d5c7abcb13c24c31c41e9f8e257178429f7554f6`, owner `e98b8ef8-7302-453a-ac8d-1edbb7d8860c`, lease до 2026-11-12T13:21:00Z. Проект verification/r2_compaction_comparison/specification.md подготовлен для независимого review; задача IN_REVIEW. R5-COMP-W01–W05, B01–B03 и G1 OPEN; методы и численные пределы UNKNOWN, пробы и испытания NOT_RUN.

## Проект интеграции сравнения A/B

Постановка `61286a4b2f83696e4ed82b8486bd057b70cdaaac`, независимый акт R5 `1b4d34a98a18c3897fbbe4ec5b25b74a2862f6c4` и проект решения verification/r2_compaction_comparison/disposition.md подготовлены к интеграции только как документальный черновик с WARNING. До принятия PR задача IN_REVIEW; R5-COMP-W05 OPEN до разработки, независимой проверки и согласования применимой методики. W01–W04, B01–B03 и G1 OPEN; методы и пределы UNKNOWN, пробы/испытания NOT_RUN.

## R4 — связанные synthetic-сцены

T-r4-linked-01 IN_REVIEW в рабочей ветке; R5-LINKED-W01 OPEN, независимый OUTPUT review NOT_RUN. Контракт 7b519238; акт d2ab72f относится к предыдущей редакции bb31d82. Физика/безопасность REV UNKNOWN, G1 открыт.

## Исправления после OUTPUT R5

T-r4-linked-01: code/results 8896d70983648ccd33c0f861c9bc9d28327ff9eb; R5-LINKED-IMPL-B01…B03 и R5-LINKED-IMPL-W01 OPEN до независимого RECHECK. R5-LINKED-CLAIM-W01 OPEN до интеграции сверки. Физика REV UNKNOWN, G1 открыт.

## Документальная передача R1

T-r4-linked-01: R5-LINKED-FIX-W01 исправлен в README на 4ebf47a5f6f96708a65653acaf0cebeee1b84c26; код/fixtures/результаты 8896d70983648ccd33c0f861c9bc9d28327ff9eb неизменны. RECHECK 82d60717ed9621af7f9fee4e57135d12f22cfc32 сохранён с probe и историей; решение о приёмке и интеграции ожидает R1, задача не DONE. G1 открыт, физика/безопасность UNKNOWN.

## Предложение R4 после PR #33

T-r4-layout-01: отдельная документальная постановка параметрической компоновки всего пресса A/B; claim PROPOSED / PENDING_MAIN, owner новой задачи NONE, proposed_owner r4-linked-20261111. Проектная работа NOT_STARTED до принятия claim. Границы прежних synthetic результатов сохранены; G1 открыт.

## Постановка компоновки всего пресса R4

T-r4-layout-01: документальный черновик cad/layout/whole_press_layout_brief.md IN_REVIEW в рабочей ветке; claim принят PR #34, owner r4-linked-20261111. Независимый OUTPUT-review NOT_RUN. Реальные размеры/ходы/нагрузки UNKNOWN, CAD/расчёты/пробы/испытания NOT_RUN; архитектура и ТЗ не утверждены, G1 открыт.

## Подготовка построения R4

Пакет 79e9c3aa9aaca33778814957fafecd93a4adc392 отвечает W01/W02/W03, новая T-r4-layout-build-01 и claim PROPOSED/PENDING_MAIN. Геометрия и build/check код NOT_STARTED. Только импорт FreeCAD/Part проверен, физика/посадки/архитектура не приняты. PR без слияния; G1 открыт.
