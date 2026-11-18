# R3 — Расчёты 42 состояний, §§4/5/6, cae/ и drives/

Onboarding: AGENTS.md → STATE.md → этот файл. Архив и старые капсулы не читать по умолчанию.
Текущие правила: AGENT_PROTOCOL.md. Основание: decisions/ARB-OPERATOR-FORK-BASELINE-01.md.

## Context Scope

- baselines/operator-fork-20261118/state_catalog_index.json
- verification/r3_force_path/analysis/
- verification/r4_force_geometry/symbolic_20261116/
- params/
- cae/
- drives/


## Очередь

- T-R3-42-STATES-01: coordination/tasks/T-R3-42-STATES-01/task.json
- T-R3-CAE-456-01: coordination/tasks/T-R3-CAE-456-01/task.json

Для каждого из 42 случаев сохранить входы, единицы, формулы, BC, фактический результат и статус. Выполнять расчёты по пригодным входам. Если определяющих данных нет — BLOCKED_INPUTS/UNKNOWN, а не ноль или фиктивный PASS.

Новая сессия использует свой actual session ID и новый claim в main.
Старые UUID и lease не наследуются. READY-задачи предварительно разрешены оператором;
повторное подтверждение роли не требуется. Формат claim: coordination/claims/README.md.
Старые claims внутри исходных пакетов — происхождение данных, а не полномочия.
Результат содержит точные inputs/outputs, хэши, команды и проверки verify_output,
registry --check-git и CI. CI не подтверждает невычисленные величины.
Физические испытания и выпуск в производство требуют отдельного решения человека.
