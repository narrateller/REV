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
Текущие блокеры приёмки: R5-IMPL-01 и R5-IMPL-02 OPEN; consecutive_rejections=2.
Q-R5-RECHECK-03 разрешён; корректирующая итерация допустима только по опубликованному
решению после фиксации его SHA и проверки owner/lease R4. Приёмка остаётся BLOCKED.
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
created_at_utc: '2026-11-10T17:42:58Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: 1283c9e6f3b14dbbe820dd06798399c611d34ce8
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T17:42:58Z'
subtask: Арбитраж Q-R5-RECHECK-03 опубликован до возобновления R4, контрпримеры воспроизведены
input_refs:
- commit: 36cda8132dcf9dbb7193b01e98bdfff2ba5e2a7b
  paths:
  - models/kinematic_press/model.py
  - models/kinematic_press/phase_plan.json
  - models/kinematic_press/phase_inputs_synthetic.json
- commit: 7e425a195bb8dd9b2609036a9333a196c71357a5
  paths:
  - verification/r5_recheck_03/review.md
  - verification/r5_recheck_03/arbitration.md
  - verification/r5_recheck_03/probe.py
  - reviews/cross_check_log.md
changed_files:
- decisions/ARB-R1-RECHECK-03.md
- verification/r1_arbitration_03/probe_results.json
- verification/r1_arbitration_03/reproduction.json
- ISSUES_AND_TASKS.md
completed_steps:
- Сверены main/claim/lease R1 и R4; получена опубликованная R5-история fast-forward без изменения кода
- 'Воспроизведён CE-01: неподвижное изделие получает SUFFICIENT_STROKE/CONSISTENT'
- 'Воспроизведён CE-02: matrix пропускает punch/channel_wall, прямой контакт [0,1]'
- Свежие данные probe совпали с отчётом R5; код/fixtures/результаты R4 неизменны
- Сохранена исходная область, выбран один параметризованный связный сценарий A/B
- Заданы четыре исхода, проверяемые контакты, READY/lifecycle и полный состав пар с доказательствами исключений
- Опубликовано решение R1 и критерии нового независимого RECHECK; блокеры не закрыты
unfinished_step:
  exact_expression_or_node: Корректирующая реализация r4-model-01 по опубликованному арбитражу, затем независимый
    RECHECK точного нового SHA
  last_successful_command: .venv/bin/python verification/r5_recheck_03/probe.py
  expected_result: Воспроизвести оба дефекта, не принять модель
  observed_result: Совпадение JSON с R5, оба контрпримера подтверждены
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
- Связь punch/product, полный жизненный цикл/READY и достаточность выдачи должны быть доказаны в исправленном
  synthetic сценарии
- Полнота пар должна следовать из независимого состава сцены; CE-02 обязан ловиться самой матрицей
blocker_ids: []
review_refs:
- 'REV-R5-RECHECK-03-001: REJECT_WITH_BLOCKER на 36cda813…; R5-IMPL-01/02 OPEN, consecutive_rejections=2'
- ARB-R1-RECHECK-03 решает вопрос плана, не заменяет RECHECK и не выбирает архитектуру
uncommitted_or_unsaved: []
next_action: R4 fetch опубликованное решение 1283c9e6f3b14dbbe820dd06798399c611d34ce8, сверяет main/owner/lease
  и фиксирует его SHA в своей капсуле; затем начинает только corrective iteration SYN-LINKED-EJECTION A/B и
  полной матрицы пар
next_action_success_criterion: Публикация решения и критериев предшествует началу R4; исправления/новые результаты
  имеют отдельный SHA и предъявляются независимому R5; приёмка остаётся BLOCKED до снятия R5-IMPL-01/02
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
