# Следующая сессия

Прочитай AGENTS.md → STATE.md → roles/<R1..R5>/README.md.
Не загружай архив и старые капсулы для onboarding.
История: [архив](archive/context/operator-fork-20261118/manifest.json).
Основание: [решение оператора](decisions/ARB-OPERATOR-FORK-BASELINE-01.md).

1. R1 завершил [T-R1-ENGINEERING-PLAN-01](coordination/tasks/T-R1-ENGINEERING-PLAN-01/dispatch_plan.md).
   Включи claims последовательно, сначала R3, затем R4 от свежей main с claim R3.
   Используй свой actual session ID и новый lease. Результаты включай в порядке R4 → R3.
2. R3 получает [манифест геометрии R4](cad/source/force_geometry/manifest.json) из коммита включения в `main`.
   В манифесте четыре условные модели, 42 привязки случаев и определяющие UNKNOWN.
3. R2 берёт T-R2-INPUTS-01. R3 — T-R3-42-STATES-01, затем T-R3-CAE-456-01.
   Следующие задачи R4 — T-R4-W02-CAD-01, затем T-R4-DRAWINGS-01.
   R5 проверяет фактическую поставку в T-R5-ENGINEERING-VERIFY-01.
4. После принятия claim проведи аудит точных входов и выполняй инженерную задачу.
   R3 сохраняет для всех 42 case ID inputs/units/frame/BC, формулы, фактические outputs
   и статус. R4 сохраняет редактируемые CAD, воспроизводимый rebuild и хэши.
   Недостающие входы — конкретный BLOCKED_INPUTS/UNKNOWN, а не фиктивный расчёт.
5. Публикуй результат с verify_output, registry --check-git и CI. R5 проверяет
   инженерное содержание; косметика не требует новых scope_amendments.

OBS-01/02/03 закрыты оператором документально; ещё один R5-круг не нужен.
Общий WARNING сохранён. На момент форка 42 состояния не рассчитаны;
§§4/5/6 NOT_RUN, G1 OPEN, ТЗ/архитектура NOT_APPROVED, W02/physical READY NO-GO.
Прочность, устойчивость и реальные реакции не подтверждены.
Следующая инженерная работа разрешена после нового claim и аудита;
физические испытания и выпуск в производство — отдельное решение человека.
