# Капсула — уточнённая постановка и независимый R5

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
created_at_utc: '2026-11-10T16:21:13Z'
base_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
work_commit: 7e99ecf87874b3bc53b1c08f115b2b5ee2ad4c3c
branch: work/T-INIT/codex-01
availability: REMOTE
claim_record:
  path: ISSUES_AND_TASKS.md
  claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a
  acceptance_commit: 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17
  lease_expires_at: '2026-11-11T12:06:09Z'
  heartbeat_utc: '2026-11-10T16:21:13Z'
subtask: Постановка модели rev2 опубликована и передана независимому R5; проверка завершена WARNING
input_refs:
- commit: 1e28c85b8c747c28e15e85060822731844d418ec
  paths:
  - models/first_digital_model_brief.md
  - controls/press_variant_state_tables.md
- reviewed_commit: 3aebae606011ded0f6d6e0a8d6ccc15094d88feb
  review_id: REV-R5-MODEL-REVIEW-01-001
changed_files:
- models/first_digital_model_brief.md
- ISSUES_AND_TASKS.md
- reviews/cross_check_log.md
completed_steps:
- Проверены main, owner/lease и исходная постановка
- Обязательна непрерывная/консервативно полная проверка всего хода; недоказанное отсутствие коллизии даёт INDETERMINATE
- Разделены проекции, траектории/огибающие без времени и одновременная коллизия тел
- Добавлены пять SYN-MODEL-01…05 с ожидаемыми результатами
- Опубликован immutable SHA 3aebae606011ded0f6d6e0a8d6ccc15094d88feb и передан read-only R5 r5-model-review-01
- R5 выдал WARNING, обязательных исправлений не нашёл; допустима synthetic-only передача R4 после назначения/claim
- Акт и хэши двух immutable artifacts сохранены; код/fixtures/стенд не запускались
unfinished_step:
  exact_expression_or_node: Назначение и claim исполнителя T-codex-01-01, затем исследовательская реализация
    и отдельная приёмка кода/результатов
  last_successful_command: .venv/bin/python scripts/check_registry.py --check-git
  expected_result: PASS документов и immutable artifacts review
  observed_result: PASS; результаты будущего кода NOT_RUN
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
- Обе архитектуры сохраняются; геометрическая модель не подтверждает сырьё/силы/безопасность
- Полнота будущего алгоритма и пять synthetic случаев ещё не проверены исполнением
blocker_ids: []
review_refs:
- 'REV-R5-REVIEW-01-001: WARNING на эскизы 6fe0a417…; R5-OBS-01…04 остаются OPEN'
- 'REV-R5-MODEL-REVIEW-01-001: WARNING на постановку/циклы 3aebae606011ded0f6d6e0a8d6ccc15094d88feb; обязательных
  исправлений нет, R4 synthetic-only после назначения/claim'
uncommitted_or_unsaved: []
next_action: Оформить назначение/claim R4 на T-codex-01-01 с входом 3aebae606011ded0f6d6e0a8d6ccc15094d88feb
  и актом REV-R5-MODEL-REVIEW-01-001; после принятия claim реализовать только исследовательский инструмент/изолированные
  synthetic fixtures
next_action_success_criterion: Есть назначенный исполнитель и принятый claim с immutable входами; ограничения
  synthetic-only сохранены, реальная геометрия REV UNKNOWN, архитектура/G1 не утверждены
stop_conditions:
- Истёк lease
- Конкурирующий владелец или изменились входы
- Инженерный вывод без применимого входного review
previous_work_commit: bacc5ff5e18819d8799c931d1091df7bce9bfe7a
```

C с актом опубликован. Проверенный SHA постановки: 3aebae606011ded0f6d6e0a8d6ccc15094d88feb.
Обязательных исправлений reviewer не обнаружил. Передача R4 разрешена только
для изолированного synthetic исследования после назначения/claim; код и
результаты потребуют отдельного review. Старые замечания эскизов не закрыты.
