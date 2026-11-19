# Следующая сессия

Прочитай AGENTS.md → STATE.md → roles/<R1..R5>/README.md.
Не загружай архив и старые капсулы для onboarding.
История: [архив](archive/context/operator-fork-20261118/manifest.json).
Основания — [решение о форке](decisions/ARB-OPERATOR-FORK-BASELINE-01.md) и [решение о проектном базисе](decisions/ARB-OPERATOR-DESIGN-BASIS-02.md).

Следующая задача — [T-R4-REDESIGN-1.5MN-01](coordination/tasks/T-R4-REDESIGN-1.5MN-01/task.json).
[Claim](coordination/claims/T-R4-REDESIGN-1.5MN-01.json) принят по поручению оператора. Перед инженерным
стартом R4 проверяет действующего владельца и выполняет входной аудит.
Основание — [отказ Ø80/45](coordination/completions/T-R3-FORCE-CALC-01/engineering_failure_note.md).
Критерии для W02 под 1,5 МН — давление ≤ 315 бар, 0 точек вне хода,
запас прочности ≥ 1,5 и `compression_over_euler` < 0,5.

OBS-01/02/03 закрыты оператором документально; ещё один R5-круг не нужен.
Общий WARNING сохранён. Огибающая 42 состояний `CALCULATED_ASSUMED`. Физические
состояния `BLOCKED_INPUTS`, физические §§4/5/6 `NOT_RUN`. G1 OPEN,
ТЗ/архитектура NOT_APPROVED, W02/physical READY NO-GO.
Прочность, устойчивость и реальные реакции не подтверждены.
Следующая инженерная работа разрешена после нового claim и аудита;
физические испытания и выпуск в производство — отдельное решение человека.
