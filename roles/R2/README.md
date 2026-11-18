# R2 — Данные и референсы

Onboarding: AGENTS.md → STATE.md → этот файл. Архив и старые капсулы не читать по умолчанию.
Текущие правила: AGENT_PROTOCOL.md. Основание: decisions/ARB-OPERATOR-FORK-BASELINE-01.md.

## Context Scope

- sources/
- process/
- baselines/operator-fork-20261118/r2/
- params/registry.yaml


## Очередь

- T-R2-INPUTS-01: coordination/tasks/T-R2-INPUTS-01/task.json

Проверять точные источники, страницы, единицы, применимость и неопределённость. BP500 — основа; остальные прессы — по релевантности. Не смешивать отдельный набор R2 из 55 записей с активным реестром.

Новая сессия использует свой actual session ID и новый claim в main.
Старые UUID и lease не наследуются. READY-задачи предварительно разрешены оператором;
повторное подтверждение роли не требуется. Формат claim: coordination/claims/README.md.
Старые claims внутри исходных пакетов — происхождение данных, а не полномочия.
Результат содержит точные inputs/outputs, хэши, команды и проверки verify_output,
registry --check-git и CI. CI не подтверждает невычисленные величины.
Физические испытания и выпуск в производство требуют отдельного решения человека.
