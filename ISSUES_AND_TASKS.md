# REV — активная инженерная очередь

Основания — [решение о форке](decisions/ARB-OPERATOR-FORK-BASELINE-01.md) и [решение о проектном базисе](decisions/ARB-OPERATOR-DESIGN-BASIS-02.md).
История: [архив](archive/context/operator-fork-20261118/manifest.json).
Старые claims/tasks/scopes закрыты; исходные файлы сохранены в
`coordination/completions/operator-fork-20261118/`. На момент ротации владельцев нет.
Каждая новая сессия использует собственный ID и новый claim по AGENT_PROTOCOL.md.

| Задача | Роль | Приоритет / состояние |
| --- | --- | --- |
| [T-R3-FORCE-CALC-02](coordination/completions/T-R3-FORCE-CALC-02/completion.json) | R3 | P0 / COMPLETED. Инженерный итог FAILED в области CALCULATED_ASSUMED. Claim освобождён |
| [T-R4-REDESIGN-1.5MN-01](coordination/tasks/T-R4-REDESIGN-1.5MN-01/task.json) | R4 | P0 / COMPLETED (CALCULATED_ASSUMED). Claim освобождён |
| [T-R4-FINAL-DRAWINGS-01](coordination/tasks/T-R4-FINAL-DRAWINGS-01/task.json) | R4 | P0 / COMPLETED. Экспорт КД W02 выполнен, claim освобождён |
| [T-R5-FORCE-CALC-VERIFY-01](coordination/completions/T-R5-FORCE-CALC-VERIFY-01/completion.json) | R5 | P0 / COMPLETED (PASS в области CALCULATED_ASSUMED). Claim освобождён |
| [T-R3-FORCE-CALC-01](coordination/tasks/T-R3-FORCE-CALC-01/task.json) | R3 | P0 / COMPLETED (CALCULATED_ASSUMED). Claim освобождён |
| [T-R2-DESIGN-BASIS-02](coordination/tasks/T-R2-DESIGN-BASIS-02/README.md) | R2 | P0 / COMPLETED (DESIGN_BASIS r1). Claim освобождён |
| [T-R3-42-STATES-ENVELOPE-01](coordination/tasks/T-R3-42-STATES-ENVELOPE-01/task.json) | R3 | P0 / COMPLETED (CALCULATED_ASSUMED) |
| [T-R2-INPUTS-01](coordination/tasks/T-R2-INPUTS-01/task.json) | R2 | P0 / COMPLETED (аудит входов и проект ТЗ) |
| [T-R3-42-STATES-01](coordination/tasks/T-R3-42-STATES-01/task.json) | R3 | P0 / COMPLETED (CALCULATED_ASSUMED) |
| [T-R4-FORCE-GEOMETRY-01](coordination/completions/T-R4-FORCE-GEOMETRY-01/completion.json) | R4 | P0 / COMPLETED (условная силовая геометрия и кандидаты COTS) |
| [T-R3-CAE-456-01](coordination/tasks/T-R3-CAE-456-01/task.json) | R3 | P1 / COMPLETED (ASSUMED_STATIC_SCREENING) |
| [T-R4-W02-CAD-01](coordination/tasks/T-R4-W02-CAD-01/task.json) | R4 | P1 / COMPLETED (CAD-rebuild, FreeCAD 1.1.4) |
| [T-R4-DRAWINGS-01](coordination/tasks/T-R4-DRAWINGS-01/task.json) | R4 | P1 / COMPLETED (каталог условной КД, экспорт NOT_RUN) |
| [T-R5-DRAWINGS-VERIFY-01](coordination/completions/T-R5-DRAWINGS-VERIFY-01/completion.json) | R5 | P1 / COMPLETED (PASS в области условной КД) |
| [T-R1-ENGINEERING-PLAN-09](coordination/completions/T-R1-ENGINEERING-PLAN-09/completion.json) | R1 | P0 / COMPLETED (аудит физических входов W02) |
| [T-R5-ENGINEERING-VERIFY-01](coordination/tasks/T-R5-ENGINEERING-VERIFY-01/task.json) | R5 | P1 / COMPLETED |
| [T-R5-W02-GEOMETRY-VERIFY-01](coordination/tasks/T-R5-W02-GEOMETRY-VERIFY-01/task.json) | R5 | P1 / COMPLETED (VERIFICATION_PASS в области документального аудита) |
| [T-R5-ENGINEERING-VERIFY-02](coordination/tasks/T-R5-ENGINEERING-VERIFY-02/task.json) | R5 | P0 / COMPLETED (условный расчёт и документальный аудит). Claim закрыт |

Входы и критерии находятся в каждой задаче. READY_INPUT_AUDIT разрешает аудит
и работу по пригодным входам, но не выдумывание недостающих величин.

- R1: сериализовать принятие новых claims и интеграцию результатов.
- R2 передал [численные входы и проект ТЗ](coordination/tasks/T-R2-INPUTS-01/README.md).
  BP500 — основа для адаптации площадки под пресс.
- R3 поставил [отдельные журналы 42 состояний](cae/cases/T-R3-42-STATES-01/results/index.json) по огибающей. Запасы соединений и физический расчёт имеют статус `BLOCKED_INPUTS` [по аудиту R3](cae/cases/T-R3-42-STATES-01/README.md).
- R4: определить опоры, эксцентриситеты, свободные длины, сечения, материалы,
  двусторонние соединения по подтверждённым входам.
- R5: воспроизвести результаты, проверить физику, размерности, балансы и CI.

[Проектный базис r1](coordination/tasks/T-R2-DESIGN-BASIS-02/README.md) задаёт
подготовку сырья, цели для брикета, T/U от пресса и сценарии оценок нагрузки и энергии.
R4 сверяет компоновку, интерфейсы и допуски, R3 проверяет входы каждого расчётного
случая. Работа идёт по свежим claims и аудиту входов.

Открыты реальные свойства сырья, фазовые нагрузки, геометрия/материалы/BC,
критерии/допуски, метрология, безопасные состояния и нормативная область/юрисдикция.
Power/pressure/moisture и девять групп пробелов прежнего DRAFT сохранены как входы.
Определяющий UNKNOWN означает BLOCKED_INPUTS/NOT_RUN, а не ноль или PASS.
Косметика закрывается узким тестом в текущей задаче, без новых scope_amendments.

Статус базы — WARNING. Все 42 физических состояния BLOCKED_INPUTS, физические
§§4/5/6 NOT_RUN, G1 OPEN, W02 и physical READY NO-GO. Физические испытания
и выпуск в производство требуют отдельного решения человека.
