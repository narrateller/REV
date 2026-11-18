# REV — активная инженерная очередь

Основание: [решение оператора](decisions/ARB-OPERATOR-FORK-BASELINE-01.md).
История: [архив](archive/context/operator-fork-20261118/manifest.json).
Старые claims/tasks/scopes закрыты; исходные файлы сохранены в
`coordination/completions/operator-fork-20261118/`. На момент ротации владельцев нет.
Каждая новая сессия использует собственный ID и новый claim по AGENT_PROTOCOL.md.

| Задача | Роль | Приоритет / состояние |
| --- | --- | --- |
| [T-R3-42-STATES-ENVELOPE-01](coordination/tasks/T-R3-42-STATES-ENVELOPE-01/task.json) | R3 | P0 / READY |
| [T-R2-INPUTS-01](coordination/tasks/T-R2-INPUTS-01/task.json) | R2 | P0 / READY |
| [T-R3-42-STATES-01](coordination/tasks/T-R3-42-STATES-01/task.json) | R3 | P0 / DELIVERED_BLOCKERS_REMAIN |
| [T-R4-FORCE-GEOMETRY-01](coordination/tasks/T-R4-FORCE-GEOMETRY-01/task.json) | R4 | P0 / DELIVERED_BLOCKERS_REMAIN |
| [T-R3-CAE-456-01](coordination/tasks/T-R3-CAE-456-01/task.json) | R3 | P1 / WAITING_CASE_INPUTS |
| [T-R4-W02-CAD-01](coordination/tasks/T-R4-W02-CAD-01/task.json) | R4 | P1 / READY_INPUT_AUDIT |
| [T-R4-DRAWINGS-01](coordination/tasks/T-R4-DRAWINGS-01/task.json) | R4 | P1 / WAITING_ENGINEERING_BASELINE |
| [T-R5-ENGINEERING-VERIFY-01](coordination/tasks/T-R5-ENGINEERING-VERIFY-01/task.json) | R5 | P1 / WAITING_RESULTS |

R1 завершил [T-R1-ENGINEERING-PLAN-01](coordination/tasks/T-R1-ENGINEERING-PLAN-01/dispatch_plan.md). Claims принимаются в порядке R3 → R4, результаты включаются в порядке R4 → R3.

Входы и критерии находятся в каждой задаче. READY_INPUT_AUDIT разрешает аудит
и работу по пригодным входам, но не выдумывание недостающих величин.

- R1: сериализовать принятие новых claims и интеграцию результатов.
- R2: подготовить численные входы с единицами, источниками и областью применимости.
  BP500 — основа; другие прессы — по релевантности. Площадка адаптируется под пресс.
- R3: после свежего claim выполнить условный расчёт 42 состояний и §§4/5/6 по [огибающей R1](cae/cases/design_boundary_phase_load_envelope/README.md). Физический расчёт остаётся заблокирован [по аудиту R3](cae/cases/T-R3-42-STATES-01/README.md).
- R4: определить опоры, эксцентриситеты, свободные длины, сечения, материалы,
  двусторонние соединения; выполнить W02 и подготовить drawings/ по готовой базе.
- R5: воспроизвести результаты, проверить физику, размерности, балансы и CI.

По команде оператора этот цикл выполняют R1 и R3. Самостоятельная проверка R3 относится к своей постановке. R4 и R5 временно на паузе.

Открыты реальные свойства сырья, фазовые нагрузки, геометрия/материалы/BC,
критерии/допуски, метрология, безопасные состояния и нормативная область/юрисдикция.
Power/pressure/moisture и девять групп пробелов прежнего DRAFT сохранены как входы.
Определяющий UNKNOWN означает BLOCKED_INPUTS/NOT_RUN, а не ноль или PASS.
Косметика закрывается узким тестом в текущей задаче, без новых scope_amendments.

Статус базы: WARNING; 42 состояния не рассчитаны, §§4/5/6 NOT_RUN,
G1 OPEN, W02 и physical READY NO-GO. Физические испытания не разрешены этим форком.
