# Следующая сессия

Прочитай AGENTS.md → STATE.md → roles/<R1..R5>/README.md.
Не загружай архив и старые капсулы для onboarding.
История: [архив](archive/context/operator-fork-20261118/manifest.json).
Основания — [решение о форке](decisions/ARB-OPERATOR-FORK-BASELINE-01.md) и [решение о проектном базисе](decisions/ARB-OPERATOR-DESIGN-BASIS-02.md).

Следующая задача — [T-R3-FORCE-CALC-02](coordination/tasks/T-R3-FORCE-CALC-02/task.json).
R3 принимает свежий claim и проверяет входы. Использовать [интерфейсы W02 r1](cad/force_geometry/redesign_1p5mn/interfaces.json)
и [манифест CAD](cad/source/force_geometry/redesign_1p5mn/manifest.json).
Пересчитать 42 состояния и §§4/5/6 с двумя цилиндрами, новыми направляющими и отдельными ветвями седла и замка B.
[Пакет R4](coordination/completions/T-R4-REDESIGN-1.5MN-01/completion.json) содержит точный commit,
результаты статического скрининга и запись CI.

OBS-01/02/03 закрыты оператором документально; ещё один R5-круг не нужен.
Общий WARNING сохранён. Огибающая 42 состояний `CALCULATED_ASSUMED`. Физические
состояния `BLOCKED_INPUTS`, физические §§4/5/6 `NOT_RUN`. G1 OPEN,
ТЗ/архитектура NOT_APPROVED, W02/physical READY NO-GO.
Прочность, устойчивость и реальные реакции не подтверждены.
Следующая инженерная работа разрешена после нового claim и аудита;
физические испытания и выпуск в производство — отдельное решение человека.
