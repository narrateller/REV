# Капсула T-INIT — codex-01

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

C содержит документальный проект. Этот H сохраняет STATE, капсулу и NEXT_MODEL.
До push доступность C — LOCAL_ONLY, после push проверять удалённый SHA.
Акт R5 не принят: codex-01 является автором паспорта и не может сам подтвердить независимость.
Остались ответы пользователя, критерии, независимая проверка и утверждение ТЗ.
