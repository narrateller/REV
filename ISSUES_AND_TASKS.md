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
| T-INIT | TASK | P1 | @R1 | CLAIMED | codex-01 | NONE | G1 |

## T-INIT

- Название: подготовить паспорт исходных данных и проект требований аналога.
- Автор: TEMPLATE. Адресат: @R1. Приоритет: P1. Статус: CLAIMED (предложение в рабочей ветке; вступает в силу только после принятия claim в main).
- owner_session / model_label / assignment_evidence: codex-01 / Codex / прямое подтверждение пользователем в текущей беседе: «Подтверждаю назначение Codex на роль R1 — системный анализ и валидация. Сессия codex-01, задача T-INIT»; зафиксировано 2026-11-10T12:06:09Z.
- session_id / role / assignment_utc: codex-01 / R1 / 2026-11-10T12:06:09Z.
- capabilities: Git read и локальные commits; Python 3.12.14, PyYAML 6.0.3; проверка реестра и 71 тест выполнены при настройке среды; четыре PDF доступны для чтения. Git push проверяется отдельно; GitHub API недоступен (CONNECT 403); CAD/CAE — UNAVAILABLE (не проверены запуском).
- base_commit / claim_commit / heartbeat_utc / lease_expires_at: 2e479849cea10dab9376a68cb44d2ff716c215da / см. последующую запись claim_record_commit в STATE.md и NEXT_MODEL.md / 2026-11-10T12:06:09Z / 2026-11-11T12:06:09Z.
- branch: work/T-INIT/codex-01.
- claim_scope: ближайшая атомарная подзадача — инвентаризация четырёх исходных PDF и паспорт источников; до принятия claim в main анализ не начинать.
- claim_acceptance: PENDING_MAIN_MERGE; запись в этой ветке не является действующим захватом. Перед merge повторно проверить main, owner_session, lease и входы; при истечении lease оформить продление, не начинать работу по просроченному claim.
- input_refs: AGENTS.md, AGENT_PROTOCOL.md, STATE.md, NEXT_MODEL.md, roles/role_profiles_summary.md, params/registry.yaml, reviews/cross_check_log.md, project/source_manifest.json, sources/raw/ — версии из commit 2e479849cea10dab9376a68cb44d2ff716c215da.
- lease_basis: 24 часа для принятия claim и ближайшей подзадачи; продление оформляется отдельной принятой записью.
- Входы: AGENT_PROTOCOL.md, STATE.md, roles/role_profiles_summary.md; пользовательские источники при их наличии.
- Параметры: проектные отсутствуют. DEMO_* запрещено переносить автоматически.
- Входной review: требуется до инженерных выводов; отсутствие источника фиксировать как ограничение.
- Результаты: sources/index.md, requirements/system_requirements.md, requirements/verification_matrix.md, decisions/standards_scope.md.
- Критерии DONE: источники инвентаризированы; известное отделено от UNKNOWN; для каждого требования заданы ID, величина/критерий или явный пробел, метод проверки, владелец; проект проверен независимой сессией.
- G1 при этом остаётся открытым до утверждения ТЗ пользователем.
- Зависимости / блокируемые задачи: NONE / NONE.
- Вопросы: назначение изделия и доступные исходные документы, если не заданы пользователем.
- Выходной review / решение / handoff: NONE / NONE / NONE.
- История: TEMPLATE_CREATED; 2026-11-10T12:06:09Z / codex-01 / роль R1 утверждена пользователем; READY → CLAIMED предложено для последовательного принятия в main; анализ источников не начат; ТЗ не утверждено.

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
