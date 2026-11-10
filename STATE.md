# STATE — панель проекта

## Паспорт

| Поле | Значение |
|---|---|
| project_id / изделие | REV / Hydraulic briquetting press |
| Назначение аналога | UNKNOWN |
| Владелец и утверждающий инженер | narrator; утверждающий инженер назначается отдельно |
| Источники прототипа | UNKNOWN; см. входные задачи |
| Принятое ТЗ / базовая линия | NONE / NONE |
| Режим | PROJECT; исходные требования ещё не утверждены |
| Текущая ветка / база | Заполняются при назначении сессии |
| Последнее обновление UTC / session_id | 2026-11-10T10:06:11Z / OPERATOR_INIT |
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
| NONE | NONE | NONE | NONE | NONE | NONE |

## Active Handoff Capsule

```yaml
capsule_version: '1.0'
status: NONE # ACTIVE, BLOCKED, RESUMED, ARCHIVED
task_id: null
role: null
session_id: null
model_label: null
author_sessions: []
assignment_evidence: null
created_at_utc: null
base_commit: null
work_commit: null # C с рабочими файлами; капсула находится в следующем H
branch: null
availability: NONE # REMOTE, LOCAL_ONLY, UNSAVED
claim_record: null
subtask: null
input_refs: [] # path, commit/hash, parameter_id, revision
changed_files: []
completed_steps: [] # выражение/узел, результат, единицы, evidence
unfinished_step:
  exact_expression_or_node: null
  coordinate_system: null
  intermediate_values: [] # только ID@revision и пути сохранённых данных
  last_successful_command: null
  expected_result: null
  observed_result: null
environment: {tool_versions: [], dependency_lock: null, seeds: []}
running_jobs: [] # job_id, tool, output_path, state, resume_command
open_hypotheses: []
blocker_ids: []
review_refs: []
uncommitted_or_unsaved: []
next_action: null # одна точная команда или одно действие с узлом
next_action_success_criterion: null
stop_conditions: []
```

## Очередь следующей модели

| Порядок | task_id | Адресат | Действие | Условие начала |
|---|---|---|---|---|
| 1 | T-INIT | @R1 | Инвентаризация данных и проект ТЗ | Подтверждение роли R1 |

После назначения сначала читать запись T-INIT. Если входов нет, фиксировать UNKNOWN и готовить структуру требований; не выдавать проект ТЗ за утверждённое ТЗ.

## Оператор и автоматические проверки

Версия шаблона: 1.2.1-candidate. Регламент: OPERATOR_GUIDE.md.
Workflow подготовлен; его выполнение и настройки GitHub не подтверждены.
Форма решения: templates/gate_decision.md; форма арбитража: templates/arbitration.md.

## Переход к следующей модели

Действующая инструкция для нового участника: NEXT_MODEL.md. После завершения задачи исполнитель обновляет её вместе с капсулой; см. AGENT_PROTOCOL.md, раздел 10.
