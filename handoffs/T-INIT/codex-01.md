# Капсула R1 — арбитраж Q-R5-RECHECK-03

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

C решения уже опубликован; этот H сохраняет эстафету и сводки. Q разрешён
только по плану. Блокеры OPEN, счётчик 2, код R4 не исправлялся, приёмка/G1
не утверждены. R4 должен взять точный SHA C до начала разрешённой итерации.
