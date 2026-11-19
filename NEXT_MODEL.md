# Следующая сессия

Прочитай AGENTS.md → STATE.md → roles/<R1..R5>/README.md.
Не загружай архив и старые капсулы для onboarding.
История: [архив](archive/context/operator-fork-20261118/manifest.json).
Основания — [решение о форке](decisions/ARB-OPERATOR-FORK-BASELINE-01.md) и [решение о проектном базисе](decisions/ARB-OPERATOR-DESIGN-BASIS-02.md).

Следующая задача — [T-R4-FINAL-DRAWINGS-01](coordination/tasks/T-R4-FINAL-DRAWINGS-01/task.json).
После свежего claim R4 сверяет масштаб и оси CAD, состав вариантов и ограничения
привода по [аудиту R3](cae/cases/T-R3-FORCE-CALC-01/input_audit.md). Критерий
завершения — проверяемые DXF/SVG/PDF из FreeCAD 1.1.4 в `drawings/W02/` с
привязкой к ревизии CAD и DESIGN_BASIS r1. Обмеры площадки и лабораторные пробы
исключены из плана. [Проверка четырёх пунктов цели](coordination/completions/T-R1-ENGINEERING-PLAN-13/completion.json).

OBS-01/02/03 закрыты оператором документально; ещё один R5-круг не нужен.
Общий WARNING сохранён. Огибающая 42 состояний `CALCULATED_ASSUMED`. Физические
состояния `BLOCKED_INPUTS`, физические §§4/5/6 `NOT_RUN`. G1 OPEN,
ТЗ/архитектура NOT_APPROVED, W02/physical READY NO-GO.
Прочность, устойчивость и реальные реакции не подтверждены.
Следующая инженерная работа разрешена после нового claim и аудита;
физические испытания и выпуск в производство — отдельное решение человека.
