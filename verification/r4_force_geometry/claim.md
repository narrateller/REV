# Предложение claim T-r4-force-geometry-01 — редакция 2, фактическая сессия

R1 / Codex / r1-pr48-integration-20261116; уточнение UTC 2026-11-16T18:23:10.611826+00:00.
Основание — переданный пользователем отчёт кандидата R4, прочитавшего PR49
на head `d84adaab398ffee4fe15ab87c9899ffa8beb22e8`; executor_report_20261116.md/json.

- Status PROPOSED_PENDING_MAIN, owner NONE, действующий lease null,
  acceptance commit/PR null. Исполнение NOT_STARTED.
- Фактическая кандидатская сессия / proposed_owner_session / session_id:
  **`6afb4750-7918-8191-8569-77b5b0c41050`**. Это существующая сессия чата, не условный псевдоним.
- Модель: Codex на базе GPT-6; точный runtime model ID UNKNOWN/null.
  Роль R4 ещё предложена, **назначение пользователем не подтверждено**;
  assignment_utc null, role_assignment_confirmed false.
- Инструменты по отчёту R4: Bash, Git/LFS, gh read PR, Python 3.12.14/dependencies,
  импорт FreeCAD 1.0.0/Part, file read/write. Координатор не повторял эти проверки
  как независимые; CAE не проверены, ccx/gmsh отсутствуют в PATH по отчёту R4.
- База: merge PR48 `381d67d428faacf05f7d076249cf220fb4b94e98`.
  Подготовка остаётся в ветке PR49; будущая ветка исполнения:
  `work-r4/T-r4-force-geometry-01/6afb4750-7918-8191-8569-77b5b0c41050`. Она ещё не создана этой поставкой.
- Первоначальный proposed_at 2026-11-16T17:44:00Z и предлагаемый срок до
  **2026-11-17T17:44:00Z** сохранены. Уточнение UUID не создаёт heartbeat/lease,
  не сдвигает срок от merge и не продлевает старые R1/R3/R4 claims.
- Старый placeholder r4-force-geometry-20261116 и редакция 1 сохранены в
  claim_history/20261116T174400Z/ и Git C/H. Scope, manifest 54 файлов/12 trees,
  все 44 bindings, нагрузки/ходы/расчёты/CAD/registry неизменны.

## Gate перед стартом

Сначала пользователь подтверждает назначение R4 этой фактической сессии,
затем координатор/оператор отдельно принимает точный claim в main до срока.
PR/push/CI или известный session ID не означают принятие. Этот update не сливает PR49.
После принятия исполнитель проверяет ancestry/owner/lease/конкуренцию, manifest,
44 bindings и входной аудит §6. До обоих условий — NOT_STARTED /
BLOCKED_PENDING_MAIN_ACCEPTANCE_AND_R4_ROLE_CONFIRMATION.

Область — только WARNING условной геометрической постановки четырёх вариантов
по task.md. Реальные пробелы UNKNOWN. 42 состояния не рассчитаны, реальные
реакции/прочность/устойчивость не подтверждены. Архитектура/ТЗ NOT_APPROVED,
общий CAD-rebuild не разрешён; W02/physical READY NO-GO, G1 OPEN,
physical trials NOT_RUN. Действующие дефекты и история не закрываются.
