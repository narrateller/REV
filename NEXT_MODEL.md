# Следующая сессия

Прочитай AGENTS.md → STATE.md → roles/<R1..R5>/README.md.
Не загружай архив и старые капсулы для onboarding.
История: [архив](archive/context/operator-fork-20261118/manifest.json).
Основания — [решение о форке](decisions/ARB-OPERATOR-FORK-BASELINE-01.md) и [решение о проектном базисе](decisions/ARB-OPERATOR-DESIGN-BASIS-02.md).

Следующая задача — [T-R4-REDESIGN-1.5MN-02](coordination/tasks/T-R4-REDESIGN-1.5MN-02/README.md),
R4, P0. Принять свежий claim и провести аудит входов. Цель — запас по пику
контактного давления ключей затвора B ≥ 1,5 при 315 бар в поршневых полостях
двух цилиндров при статическом заклинивании.
[Инженерный отказ R3](cae/cases/T-R3-FORCE-CALC-02/engineering_failure_note.md)

Независимая проверка исходного расчёта остаётся открытой. Точный
`target_commit_sha` сохранён в [акте R3](coordination/completions/T-R3-FORCE-CALC-02/completion.json).

OBS-01/02/03 закрыты оператором документально; ещё один R5-круг не нужен.
Общий WARNING сохранён. Огибающая 42 состояний `CALCULATED_ASSUMED`. Физические
состояния `BLOCKED_INPUTS`, физические §§4/5/6 `NOT_RUN`. G1 OPEN,
ТЗ/архитектура NOT_APPROVED, W02/physical READY NO-GO.
Прочность, устойчивость и реальные реакции не подтверждены.
Следующая инженерная работа разрешена после нового claim и аудита;
физические испытания и выпуск в производство — отдельное решение человека.
