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
created_at_utc: '2026-11-10T12:21:05Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: 9420968d34e47a6640672a0c339f200cb298739e
branch: work/T-INIT/codex-01
availability: LOCAL_ONLY
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
subtask: Инвентаризация четырёх PDF и паспорт источников — подготовлены к независимой проверке
input_refs:
- commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  paths:
  - project/source_manifest.json
  - sources/raw/
  - AGENT_PROTOCOL.md
  - params/registry.yaml
changed_files:
- sources/index.md
- evidence/source_inventory_codex_01.json
- reviews/input_inventory_codex_01.md
- ISSUES_AND_TASKS.md
completed_steps:
- Проверены main, владелец и lease
- Проверены размеры и SHA256 четырёх PDF
- Подготовлены карта содержания, ограничения OCR и пробелы
unfinished_step:
  exact_expression_or_node: Независимый review паспорта; оставшиеся результаты T-INIT не созданы
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS структуры, без инженерной приёмки
  observed_result: PASS
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
- reviews/input_inventory_codex_01.md — self-check, не независимый review
uncommitted_or_unsaved: []
next_action: Независимый участник проверяет sources/index.md по PDF в commit C, фиксирует review отдельно;
  R1 готовит структуру требований с UNKNOWN
next_action_success_criterion: Review имеет точные commit/страницы и границы; никакие рекламные числа не приняты
  за требования REV
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
```

C содержит документальную инвентаризацию. Этот H содержит сводки и капсулу.
При записи доступность C — LOCAL_ONLY; после push проверять удалённый ref.
Исходные PDF, source_manifest.json и параметрический реестр не изменены.
Независимый review NOT_RUN; T-INIT не завершена, G1 не закрыты.
