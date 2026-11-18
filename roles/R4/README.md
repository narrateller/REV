# R4 — CAD, W02 CAD-rebuild и drawings/

Onboarding: AGENTS.md → STATE.md → этот файл. Архив и старые капсулы не читать по умолчанию.
Текущие правила: AGENT_PROTOCOL.md. Основание: decisions/ARB-OPERATOR-FORK-BASELINE-01.md.

## Context Scope

- cad/
- drawings/
- params/
- verification/r4_force_geometry/symbolic_20261116/
- cae/


## Очередь

- T-R4-FORCE-GEOMETRY-01: coordination/tasks/T-R4-FORCE-GEOMETRY-01/task.json
- T-R4-W02-CAD-01: coordination/tasks/T-R4-W02-CAD-01/task.json
- T-R4-DRAWINGS-01: coordination/tasks/T-R4-DRAWINGS-01/task.json

Определить опоры, эксцентриситеты, свободные длины, сечения, материалы и двусторонние связи. Подготовить редактируемый CAD и воспроизводимый W02. Новые задачи разрешены оператором после claim и аудита; условный layout не является утверждённым прессом.

Новая сессия использует свой actual session ID и новый claim в main.
Старые UUID и lease не наследуются. READY-задачи предварительно разрешены оператором;
повторное подтверждение роли не требуется. Формат claim: coordination/claims/README.md.
Старые claims внутри исходных пакетов — происхождение данных, а не полномочия.
Результат содержит точные inputs/outputs, хэши, команды и проверки verify_output,
registry --check-git и CI. CI не подтверждает невычисленные величины.
Физические испытания и выпуск в производство требуют отдельного решения человека.
