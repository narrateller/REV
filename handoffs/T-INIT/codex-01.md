# Капсула T-INIT — codex-01, операторские данные и rev3

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

C опубликован в рабочей ветке; этот H сохраняет сводки. Пробы, лабораторные
журналы и испытания по указанию оператора пока отложены. Наличие окрашенной
древесины и сообщение «с ней нет проблем» — OP-данные, не лабораторный verdict.
Выбор BUY вынесен на согласование; независимый review и G1 остаются открытыми.
