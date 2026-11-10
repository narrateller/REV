# STATE — панель проекта

## Паспорт

| Поле | Значение |
|---|---|
| project_id / изделие | REV / Hydraulic briquetting press |
| Подтверждённая цель | Собственный функциональный аналог гидравлического брикетировочного пресса с возможностью изготовления в РФ; U-REV-01 |
| Назначение брикета / сырьё / годность / поставка | UNKNOWN; решения D-REV-01…04 |
| Владелец и утверждающий инженер | narrator; утверждающий инженер назначается отдельно |
| Источники прототипа | Четыре PDF инвентаризированы: sources/index.md; достоверность инженерных заявлений не принята |
| Принятое ТЗ / базовая линия | NONE / NONE |
| Режим | PROJECT; цель подтверждена, проект требований rev2 не утверждён |
| Текущая ветка / база | work/T-INIT/codex-01 / 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17 |
| Последнее обновление UTC / session_id | 2026-11-10T13:38:08Z / codex-01 |
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
Открытые риски: назначение брикета, сырьё, годность и поставка не заданы;
цель изготовления в РФ подтверждена, фактическая изготовимость и локализация
ещё исследуются. BP500-ANALOG не используется; OBS/HYP не являются архитектурой REV.

## Активные назначения

| task_id | Роль | session_id / model_label | База | Claim / heartbeat / lease | Капсула |
|---|---|---|---|---|---|
| T-INIT | R1 | codex-01 / Codex | 2e479849cea10dab9376a68cb44d2ff716c215da | ACCEPTED_MAIN (PR #1); claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a; heartbeat: 2026-11-10T13:38:08Z; lease_expires_at: 2026-11-11T12:06:09Z | handoffs/T-INIT/codex-01.md |

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
created_at_utc: '2026-11-10T13:38:08Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: 030a348eb11832999faf5710379e11f4b530ff7a
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T13:38:08Z'
subtask: 'Ревизия 2 постановки: подтверждённая цель, исследование OBS/HYP и проект REQ/VAL'
input_refs:
- commit: 453281f07cfc88da84d13ddd429b7415a3dcf13c
  paths:
  - AGENT_PROTOCOL.md
  - STATE.md
  - NEXT_MODEL.md
  - sources/index.md
  - project/source_manifest.json
  - sources/raw/
  - params/registry.yaml
- source: Прямое поручение пользователя 2026-11-10, зафиксировано в T-INIT
  ids:
  - U-REV-01
  - U-REV-02
  - U-REV-03
changed_files:
- sources/functional_analysis_r2.md
- evidence/source_research_r2_codex_01.json
- sources/index.md
- requirements/system_requirements.md
- requirements/verification_matrix.md
- decisions/standards_scope.md
- ISSUES_AND_TASKS.md
- reviews/input_inventory_codex_01.md
completed_steps:
- Проверены main, владелец и lease
- Зафиксирована собственная цель REV для изготовления в РФ; BP500-ANALOG не использовался
- Прочитаны адресные PDF и визуально сверены ключевые схемы/рисунки
- Подготовлены 11 наблюдений OBS с HYP-вариантами и условиями проверки
- 'Подготовлены rev2: 21 REQ и 21 VAL; все VAL NOT_RUN; параметры не перенесены'
- Результат C опубликован в origin/work/T-INIT/codex-01, SHA проверен
unfinished_step:
  exact_expression_or_node: D-REV-01…06, независимый review; численная и архитектурная база не выбраны
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS структуры; независимая приёмка NOT_RUN
  observed_result: PASS; 21 REQ ↔ 21 VAL, 11 OBS; документы rev2
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
- HYP-BP-01…03
- HYP-W-01…03
- HYP-P-01…02
- HYP-A-01…03
blocker_ids: []
review_refs:
- reviews/input_inventory_codex_01.md — авторский self-check; независимый review NOT_RUN
uncommitted_or_unsaved: []
next_action: 'R1 получает ответы по D-REV-01…04: назначение брикета/потребитель, доступное сырьё/пробы, критерии
  годности, состав поставки; записывает ответы в T-INIT без выбора архитектуры'
next_action_success_criterion: Есть явные ответы/UNKNOWN по каждому полю с источником пользователя; затем можно
  составить паспорт выбранного сырья и программу проверки годности
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: e8e6230a7df2c7e25b3edcaf61737f9ede7be694
```

## Очередь следующей модели

| Порядок | task_id | Адресат | Действие | Условие начала |
|---|---|---|---|---|
| 1 | T-INIT | @R1 | Уточнить D-REV-01…04 и независимо проверить rev2 | Claim/lease действительны; ответы и критерии UNKNOWN, G1 открыт |

После назначения сначала читать запись T-INIT. Если входов нет, фиксировать UNKNOWN и готовить структуру требований; не выдавать проект ТЗ за утверждённое ТЗ.

## Оператор и автоматические проверки

Версия шаблона: 1.2.1-candidate. Регламент: OPERATOR_GUIDE.md.
Workflow подготовлен; его выполнение и настройки GitHub не подтверждены.
Форма решения: templates/gate_decision.md; форма арбитража: templates/arbitration.md.

## Переход к следующей модели

Действующая инструкция для нового участника: NEXT_MODEL.md. После завершения задачи исполнитель обновляет её вместе с капсулой; см. AGENT_PROTOCOL.md, раздел 10.

Назначение R1 подтверждено; claim принят в main. Паспорт и проект требований/матрицы/нормативной области подготовлены, требуется
независимая проверка и ответы на вопросы. T-INIT не завершена; G1 остаётся NOT_STARTED.
Текущий результат: ревизия 2, commit 030a348eb11832999faf5710379e11f4b530ff7a.
Исследование: sources/functional_analysis_r2.md; подтверждённая цель отделена от OBS/HYP.
Выбор архитектуры, расчёты и утверждение G1 не выполнялись.
