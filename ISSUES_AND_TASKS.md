# REV — активная инженерная очередь

Основание: [решение оператора](decisions/ARB-OPERATOR-FORK-BASELINE-01.md).
История: [архив](archive/context/operator-fork-20261118/manifest.json).
Старые claims/tasks/scopes закрыты; исходные файлы сохранены в
`coordination/completions/operator-fork-20261118/`. На момент ротации владельцев нет.
Каждая новая сессия использует собственный ID и новый claim по AGENT_PROTOCOL.md.

| Задача | Роль | Приоритет / состояние |
| --- | --- | --- |
| [T-R3-42-STATES-ENVELOPE-01](coordination/tasks/T-R3-42-STATES-ENVELOPE-01/task.json) | R3 | P0 / COMPLETED (CALCULATED_ASSUMED) |
| [T-R2-INPUTS-01](coordination/tasks/T-R2-INPUTS-01/task.json) | R2 | P0 / READY |
| [T-R3-42-STATES-01](coordination/tasks/T-R3-42-STATES-01/task.json) | R3 | P0 / COMPLETED (CALCULATED_ASSUMED) |
| [T-R4-FORCE-GEOMETRY-01](coordination/tasks/T-R4-FORCE-GEOMETRY-01/task.json) | R4 | P0 / DELIVERED_BLOCKERS_REMAIN |
| [T-R3-CAE-456-01](coordination/tasks/T-R3-CAE-456-01/task.json) | R3 | P1 / COMPLETED (ASSUMED_STATIC_SCREENING) |
| [T-R4-W02-CAD-01](coordination/tasks/T-R4-W02-CAD-01/task.json) | R4 | P1 / READY_INPUT_AUDIT (проверка готовности к rebuild, предыдущий аудит завершён) |
| [T-R4-DRAWINGS-01](coordination/tasks/T-R4-DRAWINGS-01/task.json) | R4 | P1 / WAITING_ENGINEERING_BASELINE |
| [T-R5-ENGINEERING-VERIFY-01](coordination/tasks/T-R5-ENGINEERING-VERIFY-01/task.json) | R5 | P1 / COMPLETED |
| [T-R5-W02-GEOMETRY-VERIFY-01](coordination/tasks/T-R5-W02-GEOMETRY-VERIFY-01/task.json) | R5 | P1 / COMPLETED (VERIFICATION_PASS в области документального аудита) |

Эстафета текущего цикла задана [T-R1-ENGINEERING-PLAN-03](coordination/tasks/T-R1-ENGINEERING-PLAN-03/dispatch_plan.md).

Входы и критерии находятся в каждой задаче. READY_INPUT_AUDIT разрешает аудит
и работу по пригодным входам, но не выдумывание недостающих величин.

- R1: сериализовать принятие новых claims и интеграцию результатов.
- R2: подготовить численные входы с единицами, источниками и областью применимости.
  BP500 — основа; другие прессы — по релевантности. Площадка адаптируется под пресс.
- R3 поставил [отдельные журналы 42 состояний](cae/cases/T-R3-42-STATES-01/results/index.json) по огибающей. Запасы соединений и физический расчёт имеют статус `BLOCKED_INPUTS` [по аудиту R3](cae/cases/T-R3-42-STATES-01/README.md).
- R4: определить опоры, эксцентриситеты, свободные длины, сечения, материалы,
  двусторонние соединения; выполнить W02 и подготовить drawings/ по готовой базе.
- R5: воспроизвести результаты, проверить физику, размерности, балансы и CI.

Следующий шаг из порученных вариантов R3/R4 — [проверка готовности к пересборке W02 ролью R4](coordination/completions/T-R4-W02-CAD-01/handoff_R4.md) после нового claim. В общей очереди `T-R2-INPUTS-01` остаётся P0 / READY.

Открыты реальные свойства сырья, фазовые нагрузки, геометрия/материалы/BC,
критерии/допуски, метрология, безопасные состояния и нормативная область/юрисдикция.
Power/pressure/moisture и девять групп пробелов прежнего DRAFT сохранены как входы.
Определяющий UNKNOWN означает BLOCKED_INPUTS/NOT_RUN, а не ноль или PASS.
Косметика закрывается узким тестом в текущей задаче, без новых scope_amendments.

Статус базы: WARNING; 42 физических состояния BLOCKED_INPUTS, физические §§4/5/6 NOT_RUN,
G1 OPEN, W02 и physical READY NO-GO. Физические испытания не разрешены этим форком.
