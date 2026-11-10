# STATE — панель проекта

## Паспорт

| Поле | Значение |
|---|---|
| project_id / изделие | REV / Hydraulic briquetting press |
| Подтверждённая цель | Собственный функциональный аналог гидравлического брикетировочного пресса с возможностью изготовления в РФ; U-REV-01 |
| Товар / сырьё / подготовка | Топливный брикет — кандидат нового товара; древесная фракция строительного мусора; сортировка, металлосепарация, дробление/просев подтверждены оператором |
| Годность / покупатель / вход пресса | BUY на согласовании; показатели/кондиция UNKNOWN; process/feedstock.md и fuel_product_candidate.md |
| Владелец и утверждающий инженер | narrator; утверждающий инженер назначается отдельно |
| Источники прототипа | Четыре PDF инвентаризированы: sources/index.md; достоверность инженерных заявлений не принята |
| Принятое ТЗ / базовая линия | NONE / NONE |
| Режим | PROJECT; цель подтверждена, проект требований rev3 не утверждён |
| Текущая ветка / база | work/T-INIT/codex-01 / 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17 |
| Последнее обновление UTC / session_id | 2026-11-10T14:02:04Z / codex-01 |
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
Текущие решения: NONE. Текущие блокеры: NONE; отсутствие блокеров не означает прохождение ворот.
Открытые вопросы: конечный BUY и спецификация, состав партий/покрытий/клеёной
древесины/примесей, остаточный металл, влажность и фракция по стадиям, состояние
входа и границы поставки. Происхождение сырья и имеющиеся операции известны
со слов оператора; реальные пробы и журналы пока отложены;
цель изготовления в РФ подтверждена, фактическая изготовимость и локализация
ещё исследуются. BP500-ANALOG не используется; OBS/HYP не являются архитектурой REV.

## Активные назначения

| task_id | Роль | session_id / model_label | База | Claim / heartbeat / lease | Капсула |
|---|---|---|---|---|---|
| T-INIT | R1 | codex-01 / Codex | 2e479849cea10dab9376a68cb44d2ff716c215da | ACCEPTED_MAIN (PR #1); claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a; heartbeat: 2026-11-10T14:02:04Z; lease_expires_at: 2026-11-11T12:06:09Z | handoffs/T-INIT/codex-01.md |

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
created_at_utc: '2026-11-10T14:02:04Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: d00f2023d0472277aeddd8835bcb0929b46e6d59
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T14:02:04Z'
subtask: Операторские данные древесного строительного потока, топливный товар-кандидат, паспорт/план SP и rev3
input_refs:
- commit: 55484dd220a624a50f545c3cc3c64039645229b6
  paths:
  - requirements/system_requirements.md
  - requirements/verification_matrix.md
  - sources/functional_analysis_r2.md
  - STATE.md
- source: Сообщения оператора в текущей беседе 2026-11-10, записаны в T-INIT и process/feedstock.md
  ids:
  - OP-REV-01
  - OP-REV-02
  - OP-REV-03
  - OP-REV-04
  - OP-REV-05
  - OP-REV-06
changed_files:
- ISSUES_AND_TASKS.md
- requirements/system_requirements.md
- requirements/verification_matrix.md
- requirements/fuel_product_candidate.md
- process/feedstock.md
- process/sampling_plan.md
- decisions/standards_scope.md
- reviews/input_inventory_codex_01.md
- sources/index.md
completed_steps:
- Проверены актуальная main, owner codex-01 и срок claim
- OP-REV-01…06 зафиксированы как данные оператора, без измеренных численных значений
- Подготовлены BUY-кандидаты и QF-методы, паспорт сырья, SP-план и IN-границы
- Подтверждены имеющиеся операции без предположения сушки/кондиции
- 'Проект требований/матрицы обновлён до rev3: 22 REQ ↔ 22 VAL, все NOT_RUN'
- Результат C опубликован в рабочей ветке; исходные PDF/registry не изменены
unfinished_step:
  exact_expression_or_node: Выбор BUY-REV-* и требований потребителя; параметры/фактические результаты не получены
    по указанию оператора
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS структуры без результатов испытаний
  observed_result: PASS; 22 согласованных по ID пары REQ/VAL
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
- BUY-REV-01…03 — покупатели/сценарии
- IN-REV-A/B/C — границы подготовки/входа
- Ранее описанные HYP архитектуры остаются вариантами
blocker_ids: []
review_refs:
- reviews/input_inventory_codex_01.md — self-check; независимый review NOT_RUN
uncommitted_or_unsaved: []
next_action: Получить согласование первого BUY-REV-* по предложению fuel_product_candidate.md; затем составить
  карточку требований конкретного типа установки и выбрать применимые QF без назначения вымышленных пределов
next_action_success_criterion: Выбор покупателя/сценария либо явное отложенное решение записан в D-REV-01/Q-codex-01-01;
  подготовлена адресная спецификация с UNKNOWN; пробы/журналы пока не требовать
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: 030a348eb11832999faf5710379e11f4b530ff7a
```

## Очередь следующей модели

| Порядок | task_id | Адресат | Действие | Условие начала |
|---|---|---|---|---|
| 1 | T-INIT | @R1 | Согласовать первый BUY-REV-*, затем адресовать QF и IN | Пробы/журналы отложены; критерии UNKNOWN; независимый review и G1 открыты |

После назначения сначала читать запись T-INIT. Если входов нет, фиксировать UNKNOWN и готовить структуру требований; не выдавать проект ТЗ за утверждённое ТЗ.

## Оператор и автоматические проверки

Версия шаблона: 1.2.1-candidate. Регламент: OPERATOR_GUIDE.md.
Workflow подготовлен; его выполнение и настройки GitHub не подтверждены.
Форма решения: templates/gate_decision.md; форма арбитража: templates/arbitration.md.

## Переход к следующей модели

Действующая инструкция для нового участника: NEXT_MODEL.md. После завершения задачи исполнитель обновляет её вместе с капсулой; см. AGENT_PROTOCOL.md, раздел 10.

Назначение R1 подтверждено; claim принят в main. Паспорт и проект требований/матрицы/нормативной области подготовлены, требуется
независимая проверка и ответы на вопросы. T-INIT не завершена; G1 остаётся NOT_STARTED.
Текущий результат: ревизия 3, commit d00f2023d0472277aeddd8835bcb0929b46e6d59.
Операторские OP-данные, паспорт/план проб, покупатели/методы и границы подготовки сохранены.
Исследование: sources/functional_analysis_r2.md; подтверждённая цель отделена от OBS/HYP.
Выбор архитектуры, расчёты и утверждение G1 не выполнялись.
