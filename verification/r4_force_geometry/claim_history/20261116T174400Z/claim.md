# Предложение claim T-r4-force-geometry-01 — R4

R1 / Codex / r1-pr48-integration-20261116; UTC 2026-11-16T17:44:00Z.
Основание: прямое поручение пользователя слить PR48 обычным merge-коммитом,
затем подготовить отдельный claim R4, без инженерного исполнения до принятия.

- База main / merge PR48: `381d67d428faacf05f7d076249cf220fb4b94e98`; head `e51cc669e60444d07a29083c77a93aab9940939b`.
- Status PROPOSED_PENDING_MAIN; owner_session NONE, session_id null,
  lease_expires_at null, acceptance commit/PR null. Это предложение, не захват задачи.
- Предлагаемая новая сессия: `r4-force-geometry-20261116`, роль R4;
  фактический исполнитель/модель/возможности пока UNKNOWN и требуют подтверждения.
- Предлагаемый срок: от 2026-11-16T17:44:00Z до **2026-11-17T17:44:00Z**, 24 часа.
  Это отдельный новый срок предложения; прежние claims R1/R3/R4 не продлены.
  До принятия действующий lease отсутствует; срок истечения не сдвигается от merge.
- Подготовка в `work-r1/claim-r4-force-geometry/r1-pr48-integration-20261116`;
  будущая ветка исполнения — `work-r4/T-r4-force-geometry-01/r4-force-geometry-20261116`.
- Область WARNING: только условная геометрическая постановка четырёх вариантов.
  Полные scope/выходы/DoD/stop — task.md и исходная R4_task_proposal.md.
- Точные входы: input_manifest.json (54 файлов), 12 protected trees,
  исходные 44 bindings. Исходные нагрузки/ходы/расчёты/CAD/registry неизменны.

## Gate перед стартом

Координатор/оператор подтверждает фактического R4 и его новую сессию; если
предложенный ID отличается, proposal сначала уточняется. Затем последовательно
принимает claim в main до предложенного срока. Сам файл, PR, CI и push не
означают принятия. Этот PR автором не сливается как самопринятие.

После принятия исполнитель повторяет fetch/ancestry/owner/lease/конкуренцию,
manifest/44 bindings и входной аудит. До этого инженерная работа NOT_STARTED,
start gate BLOCKED_PENDING_MAIN_ACCEPTANCE_AND_EXECUTOR_CONFIRMATION.
При истечении срока, гонке владельца или изменении входов — остановка, без
автоматического продления, захвата чужой задачи или подмены UNKNOWN.

42 состояния не рассчитаны. Реальные реакции/прочность/устойчивость не
подтверждены. Архитектура/ТЗ NOT_APPROVED, общий CAD-rebuild не разрешён,
W02/PLC/physical READY NO-GO, G1 OPEN; physical trials NOT_RUN.
