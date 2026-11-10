# Капсула T-INIT — схема приёма/дозирования

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
created_at_utc: '2026-11-10T14:25:26Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: 5adaa8e9945176e07fbabcc96ab09bced56716ff
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T14:25:26Z'
subtask: Схема приёма/дозирования и отдельного взвешивания для TEST-F-01/02 подготовлена
input_refs:
- commit: b408f9d329e00a67621962888429b9223497ddb7
  paths:
  - NEXT_MODEL.md
  - requirements/system_requirements.md
  - requirements/verification_matrix.md
  - verification/press_function_test_plan.md
  - process/feedstock.md
  - process/sampling_plan.md
- source: Прямое поручение пользователя 2026-11-10
  scope: Схема пути до отдельной дозы, независимые L/F/M, шнек/шибер, пустая серия, входная роль TEST-F-02
    для VAL-REV-03; без испытаний
changed_files:
- verification/feed_dosing_rig_scheme.md
- verification/press_function_test_plan.md
- requirements/system_requirements.md
- requirements/verification_matrix.md
- ISSUES_AND_TASKS.md
- reviews/input_inventory_codex_01.md
completed_steps:
- Проверены main, owner и срок claim
- Подготовлена схема сырьё/подпробы → бункер → сменный модуль A/B → зона движения → сбор отдельной дозы → весы
- Разделены наблюдения L/F/M и команды/обратная связь привода
- Описаны дозовые границы, тара, досып/потери, события и сравнение на сопоставимых подпробах
- Добавлены пустые формы серии/дозы/журнала событий, результаты отсутствуют
- 'Уточнено: TEST-F-02 даёт вход для VAL-REV-03; изделие проверяют TEST-F-03/04'
- Документальные проверки прошли; C опубликован; фактические испытания не запускались
unfinished_step:
  exact_expression_or_node: Требования к наблюдаемости/метрологии каналов и независимый review схемы; численные
    диапазоны не обоснованы
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS документов, формы пусты, испытания NOT_RUN
  observed_result: PASS; 22 REQ ↔ 22 VAL, две корректные пустые YAML-формы
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
- Модуль A шнек и модуль B объёмный шибер — варианты сравнения, не выбранная архитектура
- Общий бункер/сборник/платформа требуют конструктивной и метрологической проверки
- Результаты автономного узла не доказывают заполнение прессовой камеры или повторяемость брикета
blocker_ids: []
review_refs:
- reviews/input_inventory_codex_01.md — авторский self-check; независимый review NOT_RUN
uncommitted_or_unsaved: []
next_action: 'Подготовить verification/feed_dosing_measurement_requirements.md: паспорт каналов L/F/M и команды/обратной
  связи, схема синхронизации, критерии валидности/отказов и перечень входов для обоснования диапазонов без
  запуска стенда'
next_action_success_criterion: Каждое измерение/событие связано с каналом и независимым подтверждением; определены
  незаданные диапазоны/погрешности/окна и способ их последующего обоснования; схема готова к независимому review;
  численные значения не выдуманы
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: 7377c9863cb24e6cca754887eab7a90d69b86e60
```

C опубликован. Этот H сохраняет STATE/NEXT_MODEL/капсулу. Работа остаётся
документальной, испытания не запускались; все целевые значения UNKNOWN,
G1 открыт. Масса дозы не является проверкой готового брикета.
