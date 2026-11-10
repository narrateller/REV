# Капсула T-INIT — codex-01, ревизия 2

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

C уже опубликован, удалённый ref сверён. Этот H обновляет STATE, NEXT_MODEL и
капсулу после C. G1 открыт; ТЗ, архитектура и численная база не утверждены.
Предыдущая эстафета сохраняется в истории Git; действующая — эта ревизия.
