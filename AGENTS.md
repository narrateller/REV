# REV — Stateless Agents / Stateful Repo

1. Прочитай этот файл, компактный STATE.md и roles/<своя роль>/README.md.
   Архив, старые handoffs и длинные журналы для onboarding не читать.
2. Правила текущего форка — AGENT_PROTOCOL.md. Роль берётся из задачи/поручения;
   если она уже указана, не запрашивай её повторно. Затем читай только точные
   входы выбранной задачи в пределах Context Scope роли.
3. Истина хранится в Git: параметры params/registry.yaml либо явно названный scoped
   registry; задачи ISSUES_AND_TASKS.md; результаты/команды/хэши в пакете задачи.
   UNKNOWN — null с причиной, не ноль. RAW/ASSUMED не повышаются автоматически.
4. Старые UUID, claims и scope amendments сняты оператором. История находится в
   coordination/completions/operator-fork-20261118/ и archive/context/.
   Новая сессия использует свой actual session ID и новый claim; старый lease
   не переносится. Один владелец/одна задача; main принимает claims последовательно.
5. Сначала воспроизводимые результаты и verify_output.py, registry --check-git, CI.
   Косметические исправления не требуют новых scope_amendments или кругов R1↔R5.
   Смена инженерных входов/алгоритма/границ требует обновления задачи и проверки.
6. CI PASS относится к проверенной области. Он не доказывает физику при UNKNOWN,
   не разрешает назвать невыполненные 42 состояния рассчитанными и не выпускает изделие.
   Инженерные задачи R3/R4 теперь разрешены оператором после fresh claim/input audit.
   Физические испытания и выпуск в производство требуют отдельного решения человека.
7. Перед записью проверь main/head/владельца/срок/конкуренцию и сохрани чужие правки.
   Обычные merge согласованных задач заранее разрешены, повторно не спрашивать.
   Нельзя force-push, переписывать старые акты или выдавать operator waiver за R5 PASS.

Основание: decisions/ARB-OPERATOR-FORK-BASELINE-01.md и
coordination/user_authorizations/operator_fork_20261118.json.

## Changelog

- 2026-11-18 — R1 Codex, actual session 6afb300b-1540-8191-a5c4-be1a684c20e0,
  по прямой директиве оператора: stateless onboarding, пять новых Context Scope,
  retirement старых сессий и переход от документарной рекурсии к инженерным результатам.
  Предыдущий файл сохранён побайтно в archive/context/operator-fork-20261118/manifest.json.
