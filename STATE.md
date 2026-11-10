# STATE — панель проекта

## Паспорт

| Поле | Значение |
|---|---|
| project_id / изделие | REV / Hydraulic briquetting press |
| Назначение аналога | UNKNOWN |
| Владелец и утверждающий инженер | narrator; утверждающий инженер назначается отдельно |
| Источники прототипа | Четыре PDF инвентаризированы: sources/index.md; достоверность инженерных заявлений не принята |
| Принятое ТЗ / базовая линия | NONE / NONE |
| Режим | PROJECT; исходные требования ещё не утверждены |
| Текущая ветка / база | work/T-INIT/codex-01 / 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17 |
| Последнее обновление UTC / session_id | 2026-11-10T12:40:01Z / codex-01 |
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
Открытые риски: исходные данные и критерии изделия ещё не заданы.

## Активные назначения

| task_id | Роль | session_id / model_label | База | Claim / heartbeat / lease | Капсула |
|---|---|---|---|---|---|
| T-INIT | R1 | codex-01 / Codex | 2e479849cea10dab9376a68cb44d2ff716c215da | ACCEPTED_MAIN (PR #1); claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a; heartbeat: 2026-11-10T12:40:01Z; lease_expires_at: 2026-11-11T12:06:09Z | handoffs/T-INIT/codex-01.md |

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
created_at_utc: '2026-11-10T12:40:01Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: e8e6230a7df2c7e25b3edcaf61737f9ede7be694
branch: work/T-INIT/codex-01
availability: LOCAL_ONLY
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T12:40:01Z'
subtask: Проект требований, матрица и нормативная область подготовлены для обсуждения и независимого review
input_refs:
- commit: 170cc417f8c46afd8332cec5c33162a8f0d49c2a
  paths:
  - sources/index.md
  - STATE.md
  - NEXT_MODEL.md
  - params/registry.yaml
- commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  paths:
  - ISSUES_AND_TASKS.md
  - AGENT_PROTOCOL.md
changed_files:
- ISSUES_AND_TASKS.md
- reviews/input_inventory_codex_01.md
- requirements/system_requirements.md
- requirements/verification_matrix.md
- decisions/standards_scope.md
completed_steps:
- Проверены актуальная main, owner codex-01 и действующий lease
- Учтено прямое поручение пользователя продолжить документальную часть
- Подготовлены 20 кандидатов требований и 20 связанных плановых проверок, все NOT_RUN
- Подготовлены нормативные вопросы; инженерный реестр и PDF не изменены
- Проверены структура, уникальность ID и полное взаимное покрытие REQ/VAL
unfinished_step:
  exact_expression_or_node: Ответы Q-codex-01-01/02, независимый review паспорта/проекта, заполнение критериев
    и утверждение ТЗ
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS структуры без инженерной приёмки
  observed_result: PASS; покрытие 20 REQ ↔ 20 VAL, без результатов испытаний
environment:
  tool_versions:
  - Python 3.12.14
  - PyYAML 6.0.3
  - pdftotext 25.03.0
  - Tesseract — см. JSON
  dependency_lock: requirements.txt
  seeds: []
running_jobs: []
open_hypotheses: []
blocker_ids: []
review_refs:
- reviews/input_inventory_codex_01.md — self-check; независимого review нет
uncommitted_or_unsaved: []
next_action: Уточнить назначение/сырьё/продукт и площадку по Q-codex-01-01/02; независимый участник проверяет
  проект в C
next_action_success_criterion: Ответы с источниками зафиксированы; независимый акт ссылается на точный C, автор
  reviewer не codex-01; критерии не выдуманы
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: 9420968d34e47a6640672a0c339f200cb298739e
```

## Очередь следующей модели

| Порядок | task_id | Адресат | Действие | Условие начала |
|---|---|---|---|---|
| 1 | T-INIT | @R1 | Ответы на Q-codex-01-01/02 и независимый review документального проекта | Claim и lease проверять перед продолжением; критерии UNKNOWN |

После назначения сначала читать запись T-INIT. Если входов нет, фиксировать UNKNOWN и готовить структуру требований; не выдавать проект ТЗ за утверждённое ТЗ.

## Оператор и автоматические проверки

Версия шаблона: 1.2.1-candidate. Регламент: OPERATOR_GUIDE.md.
Workflow подготовлен; его выполнение и настройки GitHub не подтверждены.
Форма решения: templates/gate_decision.md; форма арбитража: templates/arbitration.md.

## Переход к следующей модели

Действующая инструкция для нового участника: NEXT_MODEL.md. После завершения задачи исполнитель обновляет её вместе с капсулой; см. AGENT_PROTOCOL.md, раздел 10.

Назначение R1 подтверждено; claim принят в main. Паспорт и проект требований/матрицы/нормативной области подготовлены, требуется
независимая проверка и ответы на вопросы. T-INIT не завершена; G1 остаётся NOT_STARTED.
Текущий результат документальной части: commit e8e6230a7df2c7e25b3edcaf61737f9ede7be694.
