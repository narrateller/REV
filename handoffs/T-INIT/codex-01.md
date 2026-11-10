# Капсула T-INIT — циклы, первая модель, review эскизов

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
created_at_utc: '2026-11-10T14:47:19Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: bacc5ff5e18819d8799c931d1091df7bce9bfe7a
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T14:47:19Z'
subtask: Краткие циклы A/B, задание первой цифровой модели и независимый review эскизов подготовлены
input_refs:
- commit: 6fe0a417ed2fde165e2fc01d625ec86ab810346e
  paths:
  - concepts/press_functional_alternatives.md
  - verification/feed_dosing_rig_scheme.md
  - sources/function_realization_comparison.md
  - NEXT_MODEL.md
- source: Прямое поручение пользователя 2026-11-10
  scope: Таблицы циклов, модель/опыты, задание первой модели и передача эскизов независимому reviewer
changed_files:
- controls/press_variant_state_tables.md
- models/first_digital_model_brief.md
- reviews/cross_check_log.md
- ISSUES_AND_TASKS.md
completed_steps:
- Проверены актуальная main, owner и срок claim
- 'Подготовлены краткие циклы A/B: движение, разрешение, подтверждение и сбой'
- Отделены геометрические/кинематические проверки от свойств сырья/сил/реальной выдачи
- Предложена READY-задача T-codex-01-01 с входами/выходами/критериями, owner NONE, реализация NOT_STARTED
- Эскизы immutable 6fe0a417… проверены отдельным R5 r5-review-01; WARNING, только документальное продолжение
- Хэши трёх reviewed artifacts перепроверены; замечания/план и срок зафиксированы
- C опубликован; модель/стенд/испытания не запускались
unfinished_step:
  exact_expression_or_node: Независимая проверка новой постановки модели/циклов и назначение исполнителя первой
    модели; открытые R5-OBS-01…04 не закрыты
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS документов и проверка immutable artifacts review; без инженерного PASS
  observed_result: PASS; акт WARNING корректен, артефакты unchanged
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
- Обе архитектуры сохраняются без выбора
- Геометрический запас/ход не подтверждает реальные силы/остаточную энергию/удержание и качество брикета
- 'R5-OBS-01…04: отсечение/опирание; разгрузка упора/выдача; старт/удержание канала; метрология F'
blocker_ids: []
review_refs:
- 'REV-R5-REVIEW-01-001: WARNING; R5 r5-review-01; reviewed_commit 6fe0a417ed2fde165e2fc01d625ec86ab810346e;
  только три listed artifacts'
- Новые циклы и задание модели в этом C независимым review ещё не проверены
uncommitted_or_unsaved: []
next_action: Независимо проверить постановку T-codex-01-01 и таблицы циклов, затем назначить/claim исполнителя
  первой параметрической модели с фиксацией текущего C; до реализации не подменять UNKNOWN числами
next_action_success_criterion: Проверены границы 2D/кинематики и отдельность свойств сырья/сил; есть назначение/claim
  и точные входы; незаданные параметры ведут к INDETERMINATE, архитектура не выбирается
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: 53a5dca0655144418833432e30db5d8313d2244c
```

C опубликован; H обновляет сводки. Reviewer r5-review-01 не участвовал в
авторстве трёх проверенных артефактов, не проверял новые циклы/задание.
WARNING не закрывает R5-OBS и не разрешает инженерную приёмку/запуск.
Требуется отдельная приёмка будущей модели; архитектура и G1 не утверждены.
