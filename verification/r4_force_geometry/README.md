# Отдельный claim R4 после интеграции PR48

Только подготовка координационных документов. Инженерная геометрия, расчёты,
native CAD/CAE и физические испытания не запускались.

Принятый merge PR48: `381d67d428faacf05f7d076249cf220fb4b94e98`.
Оба родителя сохранены, дерево совпадает с проверенным head
`e51cc669e60444d07a29083c77a93aab9940939b`.
Истории R3/R5/R1 сохранены; исходные merge preflight/receipt находятся рядом.

`claim.json` и `claim.md` — PROPOSED_PENDING_MAIN, owner NONE, lease null.
Фактическая кандидатская сессия 6afb4750-7918-8191-8569-77b5b0c41050 и
переданные модель/инструменты записаны в executor_report_20261116.md/json.
Назначение роли R4 пользователем ещё не подтверждено; точный runtime model ID
неизвестен. Импорт FreeCAD/Part сообщён R4, не является CAD/CAE build. Отдельный предложенный срок — 24 часа от подготовки,
не автоматическое продление прежних claims. Merge этого PR автором как
самопринятие не выполняется. После отдельного принятия claim до срока и
подтверждения назначения исполнитель проверяет ancestry/owner/lease/конкуренцию,
exact inputs, 44 bindings и входной аудит, затем действует только в WARNING scope.

Полная постановка — task.md и неизменённая исходная R4_task_proposal.md;
готовая команда будущему R4 — R4_command.md. Её инженерный этап до принятия
не исполнять. Входной manifest закрепляет 54 файла/12 protected trees на merge PR48.

Проверки из `/workspace/REV` с существующей `.venv`:

```bash
.venv/bin/python verification/r4_force_geometry/verify_claim.py
.venv/bin/python scripts/check_registry.py --check-git
git diff --check
```

Проверка исходного пакета R1 `verification/pr48_integration/verify_preservation.py`
повторена с перенаправлением только HERE в этот каталог, чтобы сохранить старое
доказательство неизменным. Итоги/команды/exit status — validation.json;
claim_validation.json и preservation.json содержат фактические инварианты.
Готовность CI привязывается к точным SHA, а не к старому успешному запуску.

Claim-проверка сознательно проверяет стадию PROPOSED; после отдельной приёмки
понадобится новая запись фактического назначения/acceptance, старое предложение
остаётся в истории. Успешная проверка proposal не является разрешением старта.

42 состояния не рассчитаны. Прочность/устойчивость/реальные реакции не подтверждены;
84 RAW/null и прочие UNKNOWN сохранены. Архитектура/ТЗ NOT_APPROVED,
общий CAD-rebuild не разрешён, W02/physical READY NO-GO, G1 OPEN.

Редакция 1 сохранена в claim_history/20261116T174400Z/. Для редакции 2
использовать identity_update_validation.json; срок предложения не изменён.
