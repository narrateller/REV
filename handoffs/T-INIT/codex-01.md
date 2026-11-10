# Капсула T-INIT — измерения и эскизы всего пресса

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
created_at_utc: '2026-11-10T14:33:09Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: 53a5dca0655144418833432e30db5d8313d2244c
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T14:33:09Z'
subtask: Таблица измерений и два функциональных эскиза всего пресса подготовлены
input_refs:
- commit: f154a1444bbd75040b3be8c515dedc873ff611c2
  paths:
  - NEXT_MODEL.md
  - verification/feed_dosing_rig_scheme.md
  - sources/function_realization_comparison.md
  - requirements/system_requirements.md
  - requirements/verification_matrix.md
- source: Прямое поручение пользователя 2026-11-10
  scope: Краткая таблица, различение отсутствия движения/потери F; два эскиза, силовой контур, стык дозатора,
    данные выбора; без испытаний
changed_files:
- verification/feed_dosing_rig_scheme.md
- concepts/press_functional_alternatives.md
- requirements/system_requirements.md
- requirements/verification_matrix.md
- verification/press_function_test_plan.md
- sources/function_realization_comparison.md
- ISSUES_AND_TASKS.md
- reviews/input_inventory_codex_01.md
completed_steps:
- Проверены main, owner и действующий lease
- Добавлена таблица сигнал/точка/время/недостоверность для L/F/M, команды/положения и синхронизации
- NO_MOTION_CONFIRMED отделён от SIGNAL_LOSS/INVALID; потеря F не считается пропуском потока
- Подготовлены два эскиза всего пресса с материалом, движениями, силовыми контурами и стыком дозатора/камеры
- Собраны данные выбора и непроверенные функции запуска/удержания/разгрузки/выдачи
- Документальные проверки прошли; C опубликован, испытания не запускались
unfinished_step:
  exact_expression_or_node: Состояния/разрешения движений и критерии наблюдаемости/разгрузки для обоих вариантов;
    геометрия/усилия не обоснованы
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS документов, без инженерной приёмки
  observed_result: PASS; 22 REQ ↔ 22 VAL, две Mermaid-схемы и пустые YAML-формы
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
- 'Канал с зажимом: стартовое сопротивление и удержание столба ещё не доказаны'
- 'Закрытая камера: механическое замыкание/разгрузка двери и ход главного пуансона для выдачи ещё не доказаны'
- Стык дозатора/силовой камеры требует собственного опирания/отсечения, привод подачи не является проверенным
  силовым затвором
blocker_ids: []
review_refs:
- reviews/input_inventory_codex_01.md — авторский self-check; независимый review NOT_RUN
uncommitted_or_unsaved: []
next_action: 'Создать controls/press_variant_state_tables.md: для каждой фазы A/B указать команды, физические
  разрешения, независимые подтверждения и реакцию на недостоверные сигналы/неполное заполнение/выход; не запускать
  стенд'
next_action_success_criterion: Учтены изоляция загрузочного окна, старт пустого канала/удержание при возврате,
  замыкание и разгрузка упора перед открытием, свободная траектория выдачи; численные условия UNKNOWN с методом
  будущего обоснования
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: 5adaa8e9945176e07fbabcc96ab09bced56716ff
```

C опубликован; этот H сохраняет STATE/NEXT_MODEL/капсулу. Эскизы не являются
проверенными силовыми конструкциями, ни один вариант не выбран. Размеры,
усилия и пороги UNKNOWN. Испытания NOT_RUN, G1 открыт.
