# STATE — панель проекта

## Паспорт

| Поле | Значение |
|---|---|
| project_id / изделие | REV / Hydraulic briquetting press |
| Подтверждённая цель | Собственный функциональный аналог BP500 с возможностью изготовления в РФ; F-REV-01…04 |
| Сырьё / подготовка | Отсортированная древесная фракция строительного мусора после металлоудаления; до пресса: сортировка, металлосепарация, дробление/просев |
| Функции / критерии | Приём, дозирование, уплотнение, выдача; размеры/производительность/пороги UNKNOWN; выбор покупателя не является условием T-INIT |
| Контекст компании | Выпуск пеллет и расширение ассортимента; не определяет требования к прессу |
| Владелец и утверждающий инженер | narrator; утверждающий инженер назначается отдельно |
| Источники прототипа | Четыре PDF инвентаризированы: sources/index.md; достоверность инженерных заявлений не принята |
| Принятое ТЗ / базовая линия | NONE / NONE |
| Режим | PROJECT; цель подтверждена, проект требований rev6 не утверждён |
| Текущая ветка / база | work/T-INIT/codex-01 / 876c8712c0c2ecce9d46a9ed594e2c00f7ce9f17 |
| Последнее обновление UTC / session_id | 2026-11-10T16:21:13Z / codex-01 |
| enforcement | PROCEDURAL; серверные ограничения не проверены |
| Численная база | params/registry.yaml |
| Задачи / проверки | ISSUES_AND_TASKS.md / reviews/cross_check_log.md |

## Ворота V-модели

| Ворота | Этап / ветвь | Статус | Обязательное доказательство | Ответственный / проверка / утверждение |
|---|---|---|---|---|
| G1 | Анализ и ТЗ / левая | NOT_STARTED | Измеримые требования, границы, источники, неопределённости, план валидации | R1 / R2+R5 / пользователь |
| G2 | Архитектура / левая | NOT_STARTED | Физика, силовой путь, схемы, балансы, цикл, проверенный COTS-каталог, интерфейсы, риски | R2+R3 / R1+R5 / назначенный R1 |
| G3 | CAD / основание V | NOT_STARTED | Сборка, сопряжения, материалы, массы, движения, экспорт, входы CAE | R4 / R3+R5+R6 / назначенный R1 |
| G4 | Верификация и валидация / правая | NOT_STARTED | Матрица требований и тестов, воспроизводимые прогоны, сходимость, границы применимости | R5+R1 / независимые R2+R3+R4 по области / пользователь |
| G5 | DFM/CAM и РКД / выпуск | NOT_STARTED | РКД, спецификации, допуски, маршрут, контроль, закрытые замечания, решение о выпуске | R6 / R4+R5 / инженер, назначенный пользователем |

Здесь указаны функции; конкретные проверяющие не могут быть авторами проверяемых версий.
Для каждого решения о воротах создать запись в `decisions/<decision_id>.md`: baseline commit, scope, evidence, exclusions, blocker_ids, approver, основание полномочий, UTC.
Текущие решения: NONE. Текущие блокеры: NONE; отсутствие блокеров не означает прохождение ворот.
Независимый review эскизов REV-R5-REVIEW-01-001: WARNING, допускает лишь
ограниченную документальную проработку; четыре замечания OPEN. Новые циклы
и задание этим старым актом не проверены; отдельный акт REV-R5-MODEL-REVIEW-01-001
на постановку rev2/циклы даёт WARNING без обязательных исправлений и допускает
исследовательскую передачу R4 на synthetic данных после назначения/claim.
Открытые технические вопросы: собственная входная спецификация, состав партий/покрытий/клеёной
древесины/примесей, остаточный металл, влажность и фракция по стадиям, состояние
входа и границы поставки. Происхождение сырья и имеющиеся операции известны
со слов оператора; реальные пробы и журналы пока отложены;
цель изготовления в РФ подтверждена, фактическая изготовимость и локализация
ещё исследуются. BP500-ANALOG не используется; OBS/HYP не являются архитектурой REV.

## Активные назначения

| task_id | Роль | session_id / model_label | База | Claim / heartbeat / lease | Капсула |
|---|---|---|---|---|---|
| T-INIT | R1 | codex-01 / Codex | 2e479849cea10dab9376a68cb44d2ff716c215da | ACCEPTED_MAIN (PR #1); claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a; heartbeat: 2026-11-10T16:21:13Z; lease_expires_at: 2026-11-11T12:06:09Z | handoffs/T-INIT/codex-01.md |

## Active Handoff Capsule

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

## Очередь следующей модели

| Порядок | task_id | Адресат | Действие | Условие начала |
|---|---|---|---|---|
| 1 | T-INIT | @R1 | Назначение/claim R4 для T-codex-01-01 | Постановка rev2 проверена R5 с WARNING; только synthetic-исследование, архитектура/G1 открыты |

После назначения сначала читать запись T-INIT. Если входов нет, фиксировать UNKNOWN и готовить структуру требований; не выдавать проект ТЗ за утверждённое ТЗ.

## Оператор и автоматические проверки

Версия шаблона: 1.2.1-candidate. Регламент: OPERATOR_GUIDE.md.
Workflow подготовлен; его выполнение и настройки GitHub не подтверждены.
Форма решения: templates/gate_decision.md; форма арбитража: templates/arbitration.md.

## Переход к следующей модели

Действующая инструкция для нового участника: NEXT_MODEL.md. После завершения задачи исполнитель обновляет её вместе с капсулой; см. AGENT_PROTOCOL.md, раздел 10.

Назначение R1 подтверждено; claim принят в main. Паспорт и проект требований/матрицы/нормативной области подготовлены, требуется
независимая проверка и ответы на вопросы. T-INIT не завершена; G1 остаётся NOT_STARTED.
Текущий результат: постановка модели rev2 на 3aebae606011ded0f6d6e0a8d6ccc15094d88feb; акт её независимой проверки в commit 7e99ecf87874b3bc53b1c08f115b2b5ee2ad4c3c.
Операторские OP-данные сохранены; требования и испытания относятся к прессу.
Товарные предложения — только архивный контекст, не условие продолжения.
Исследование: sources/functional_analysis_r2.md; подтверждённая цель отделена от OBS/HYP.
Выбор архитектуры, расчёты и утверждение G1 не выполнялись.

## Предложение назначения R4

T-codex-01-01: пользователь назначил r4-model-01 / Codex / R4; claim ACCEPTED_MAIN, owner_session: r4-model-01. Координация Q-r4-model-01-01, капсула handoffs/T-codex-01-01/r4-model-01.md. Код NOT_STARTED; G1 открыт. Принятый владелец T-INIT не меняется.
