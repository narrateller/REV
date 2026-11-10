# Капсула T-INIT — codex-01, функции пресса и rev4

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
created_at_utc: '2026-11-10T14:15:07Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: 7377c9863cb24e6cca754887eab7a90d69b86e60
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T14:15:07Z'
subtask: 'Rev4: требования и проверка функций аналога BP500; выбор покупателя исключён из условий T-INIT'
input_refs:
- commit: ad58c4e817d5eecf6896b00cf6fbaa53d8b594f0
  paths:
  - sources/functional_analysis_r2.md
  - sources/index.md
  - process/feedstock.md
  - process/sampling_plan.md
  - AGENT_PROTOCOL.md
- source: Текущее уточнение пользователя 2026-11-10, зафиксировано в T-INIT
  scope: Разрабатывать пресс F-REV-01…04; пеллеты/ассортимент — контекст; выбор покупателя не требуется
changed_files:
- requirements/system_requirements.md
- requirements/verification_matrix.md
- sources/function_realization_comparison.md
- verification/press_function_test_plan.md
- process/feedstock.md
- process/sampling_plan.md
- ISSUES_AND_TASKS.md
- decisions/standards_scope.md
- archive/context/fuel_product_candidate_rev3.md
- reviews/input_inventory_codex_01.md
- sources/functional_analysis_r2.md
- sources/index.md
completed_steps:
- Проверены main, owner и действующий lease
- Отменено условие выбора покупателя; товарное предложение перенесено в архив контекста
- Сопоставлены BP500/WEIMA/E55/ARS по F-REV-01…04
- Подготовлены требования/матрица rev4, свойства сырья и операции до пресса
- 'Подготовлена программа TEST-F-01…05: подача, дозирование, формование, выдача и полный цикл'
- Проверена структура и 22 REQ ↔ 22 VAL; фактические испытания NOT_RUN
- C опубликован в origin/work/T-INIT/codex-01
unfinished_step:
  exact_expression_or_node: Собственная схема испытательного узла подачи/дозирования, затем обоснование диапазонов
    и измерений; без фактических проб пока
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS документов; функциональные проверки NOT_RUN
  observed_result: PASS, все численные цели/пороги UNKNOWN
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
- Шнек/рыхление, шибер/предсжатие и дисковая подача — варианты дозирования
- Канал с зажимом и закрытая камера с дверью — варианты уплотнения/выдачи
- IN-REV-A/B/C — альтернативные состояния входа, окончательная кондиция не выбрана
blocker_ids: []
review_refs:
- reviews/input_inventory_codex_01.md — авторский self-check; независимый review NOT_RUN
uncommitted_or_unsaved: []
next_action: 'Создать verification/feed_dosing_rig_scheme.md: функциональная схема узла F-REV-01/02, точки
  контроля состояния сырья и взвешивания доз, датчики/события, безопасные состояния и пустая форма серии TEST-F-01/02'
next_action_success_criterion: Каждое измерение связано с REQ/VAL и возможным механизмом; схема отделяет массу
  дозы/поток/уровень и учитывает своды/неполное заполнение; покупатель не является зависимостью; диапазоны
  и пороги UNKNOWN до обоснования
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: d00f2023d0472277aeddd8835bcb0929b46e6d59
```

C опубликован; этот H обновляет STATE/NEXT_MODEL/капсулу. Все старые условия
выбора покупателя отменены пользователем; не возобновлять их как вход T-INIT.
Реальные пробы/журналы пока отложены, но документальное инженерное развитие
и сравнение механизмов продолжается. G1 открыт, ТЗ и архитектура не утверждены.
