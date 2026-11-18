# R5 — Инженерная и CI-верификация

Onboarding: AGENTS.md → STATE.md → этот файл. Архив и старые капсулы не читать по умолчанию.
Текущие правила: AGENT_PROTOCOL.md. Основание: decisions/ARB-OPERATOR-FORK-BASELINE-01.md.

## Context Scope

- coordination/task_index.json
- точныйmanifest выбранного результата
- tests/
- выбранные input/output/evidence задачи


## Очередь

- T-R5-ENGINEERING-VERIFY-01: coordination/tasks/T-R5-ENGINEERING-VERIFY-01/task.json

Проверять точный результат, его входы, физику, размерности, балансы, границы и воспроизводимость. Фиксировать авторство и независимость. Косметика закрывается узким тестом без новой цепи scope_amendments; UNKNOWN не является физическим PASS.

Новая сессия использует свой actual session ID и новый claim в main.
Старые UUID и lease не наследуются. READY-задачи предварительно разрешены оператором;
повторное подтверждение роли не требуется. Формат claim: coordination/claims/README.md.
Старые claims внутри исходных пакетов — происхождение данных, а не полномочия.
Результат содержит точные inputs/outputs, хэши, команды и проверки verify_output,
registry --check-git и CI. CI не подтверждает невычисленные величины.
Физические испытания и выпуск в производство требуют отдельного решения человека.
