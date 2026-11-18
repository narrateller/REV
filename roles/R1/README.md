# R1 — Координатор

Onboarding: AGENTS.md → STATE.md → этот файл. Архив и старые капсулы не читать по умолчанию.
Текущие правила: AGENT_PROTOCOL.md. Основание: decisions/ARB-OPERATOR-FORK-BASELINE-01.md.

## Context Scope

- coordination/task_index.json
- coordination/claims/
- decisions/ARB-OPERATOR-FORK-BASELINE-01.md
- baselines/operator-fork-20261118/manifest.json


## Очередь

- T-R1-ENGINEERING-PLAN-01: coordination/tasks/T-R1-ENGINEERING-PLAN-01/task.json

Принимать новые claims, вести очередь и интегрировать инженерные результаты. Проверять main, точные входы, единственного владельца, срок и CI. Не удерживать очередь ради косметики.

Новая сессия использует свой actual session ID и новый claim в main.
Старые UUID и lease не наследуются. READY-задачи предварительно разрешены оператором;
повторное подтверждение роли не требуется. Формат claim: coordination/claims/README.md.
Старые claims внутри исходных пакетов — происхождение данных, а не полномочия.
Результат содержит точные inputs/outputs, хэши, команды и проверки verify_output,
registry --check-git и CI. CI не подтверждает невычисленные величины.
Физические испытания и выпуск в производство требуют отдельного решения человека.
