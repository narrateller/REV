# STATE — панель проекта

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
