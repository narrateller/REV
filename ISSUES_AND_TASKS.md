# ISSUES_AND_TASKS — задачи, вопросы, блокеры

Единственный межролевой трекер. Одна запись — одна проверяемая задача либо вопрос.
ID после создания не меняется. Для параллельного создания применять `T-<session_id>-<local_id>`, `Q-<session_id>-<local_id>`, `B-<session_id>-<local_id>`.

## Правила

- Адресаты: @R1…@R6; исполнителем является одна подтверждённая сессия. Несколько адресатов не означают несколько одновременных владельцев.
- P0 — недостоверная база/критическая ошибка, немедленная остановка зависимой работы; P1 — блокирует ворота; P2 — плановая работа; P3 — улучшение. Приоритет не заменяет анализ влияния.
- Типы: TASK, QUESTION, BLOCKER, CHANGE. Статусы: BACKLOG → READY → CLAIMED → IN_PROGRESS → IN_REVIEW → DONE. Дополнительные: BLOCKED, HANDOFF, CANCELLED. Возврат после review: IN_REVIEW → IN_PROGRESS/BLOCKED.
- READY требует перечисленных входов и критериев. CLAIMED требует принятого claim. IN_PROGRESS требует входного акта. DONE требует выходных доказательств и независимой приёмки. Для вопроса доказательством служит ответ с источником; для изменения — принятое решение.
- WARNING не закрывает обязательный критерий. REJECT_WITH_BLOCKER создаёт связанную запись BLOCKER и переводит зависимые задачи в BLOCKED. Блокер закрывает reviewer после проверки исправленной версии.
- Вопрос содержит предлагаемую гипотезу и последствия каждого ответа. Пользователю передавать только то, что нельзя разрешить данными/расчётом в пределах полномочий.
- Записи не удалять; завершённые переносить в `archive/tasks/` со ссылкой. Все времена — UTC ISO 8601. Lease выбирается под длительность подзадачи и записывается конкретным временем.

## Индекс

| ID | Тип | P | Адресат | Статус | Owner | Зависимости | Ворота |
|---|---|---|---|---|---|---|---|
| T-INIT | TASK | P1 | @R1 | READY | NONE | NONE | G1 |

## T-INIT

- Название: подготовить паспорт исходных данных и проект требований аналога.
- Автор: TEMPLATE. Адресат: @R1. Приоритет: P1. Статус: READY.
- owner_session / model_label / assignment_evidence: NONE / NONE / NONE.
- base_commit / claim_commit / heartbeat_utc / lease_expires_at: NONE / NONE / NONE / NONE.
- Входы: AGENT_PROTOCOL.md, STATE.md, roles/role_profiles_summary.md; пользовательские источники при их наличии.
- Параметры: проектные отсутствуют. DEMO_* запрещено переносить автоматически.
- Входной review: требуется до инженерных выводов; отсутствие источника фиксировать как ограничение.
- Результаты: sources/index.md, requirements/system_requirements.md, requirements/verification_matrix.md, decisions/standards_scope.md.
- Критерии DONE: источники инвентаризированы; известное отделено от UNKNOWN; для каждого требования заданы ID, величина/критерий или явный пробел, метод проверки, владелец; проект проверен независимой сессией.
- G1 при этом остаётся открытым до утверждения ТЗ пользователем.
- Зависимости / блокируемые задачи: NONE / NONE.
- Вопросы: назначение изделия и доступные исходные документы, если не заданы пользователем.
- Выходной review / решение / handoff: NONE / NONE / NONE.
- История: TEMPLATE_CREATED; утверждение роли и ТЗ отсутствует.

## Форма новой записи — копировать и заполнить

```yaml
id: null
type: TASK
title: null
author_session: null
to_roles: []
priority: P2
status: BACKLOG
owner_session: null
model_label: null
assignment_evidence: null
base_commit: null
claim_record_commit: null # заполняется последующей записью, не собственным SHA
heartbeat_utc: null
lease_expires_at: null
input_refs: [] # path + immutable commit/hash
parameter_refs: [] # ID@revision
depends_on: []
blocks: []
affected_gates: []
input_review_id: null
conflict_id: null
consecutive_rejections: 0 # второй возврат по тому же конфликту запускает арбитраж
arbitration_ref: null
question_or_change: null
proposed_answer_and_evidence: null
impact_if_wrong: null
expected_outputs: []
acceptance_criteria: []
output_review_id: null
resolution: null
decision_ref: null
handoff_ref: null
history: [] # UTC, session_id, from, to, reason, evidence
```
