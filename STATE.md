# REV — отправная база после ротации 2026-11-18

Режим: Stateless Agents / Stateful Repo. На момент ротации все старые claims сняты,
новых владельцев нет. Административный переход выполнен R1, сессия
`6afb300b-1540-8191-a5c4-be1a684c20e0`, по прямой директиве оператора.

Основание: [решение оператора](decisions/ARB-OPERATOR-FORK-BASELINE-01.md),
[авторизация](coordination/user_authorizations/operator_fork_20261118.json).
Полная история сохранена побайтно: [архив](archive/context/operator-fork-20261118/manifest.json).
Старые полномочия: [закрытые записи](coordination/completions/operator-fork-20261118/retirements.json).

## Принятая отправная база

- PR60 — обычный merge `5da433af81874640d2e82bbbe408633cfa8b7e73`. Exact C
  `5b72e18d83cb0b10cf0a1c2c50fbe0d72fd8ae1a` принят оператором.
  OBS-01/02/03: CLOSED_DOCUMENTARY_BY_OPERATOR_AUTHORIZATION.
  Дополнительный R5 на этом C: NOT_RUN / WAIVED. Прежние акты и FAIL сохранены.
- R2: `4fd6f32b4df3186a805ac7e654be6c4c9e1c6a50` — отдельный набор из 55 записей,
  сохранён в `baselines/operator-fork-20261118/r2/`; активный реестр не заменён.
- R3: `93b4aead4983f88919d8e8b4165e29d7f3246600` / PR48 — условная постановка,
  каталог 42 состояний, `verification/r3_force_path/analysis/`.
- R4: `beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe` — 52 символических интерфейса,
  четыре варианта, `verification/r4_force_geometry/symbolic_20261116/`.

Точные источники, хэши и теги: [baseline manifest](baselines/operator-fork-20261118/manifest.json).
Фиксация базы не повышает RAW/ASSUMED и не означает VERIFIED/LOCKED физики.
Общий WARNING сохранён: документальная база пригодна для дальнейшей инженерной работы.

## Фактический срез

| Область | Сохранено | Что предстоит |
| --- | --- | --- |
| cad/ | Скрипты layout/layout_correction/frame_mount/feed_power; 235 build-артефактов условных моделей | Редактируемая инженерная сборка и W02; cad/source и cad/export пусты |
| params/ | 1144 записи: 1072 CALCULATED, 47 ASSUMED, 25 RAW/null; исходные 44 привязки, нагрузки и ходы | Проверить пригодность входов для инженерных расчётов; арифметические статусы не подтверждают прочность |
| controls/ | press_variant_state_tables.md — функциональный DRAFT | Численные режимы, реализация управления и безопасных состояний |
| cae/ | Каталоги cases/models/results | Расчётные пакеты и фактические результаты |
| drives/ | Шаблоны/схема COTS | Выбор приводов; components и schematics пусты |
| drawings/ | Каталог | Выпуск КД после готовности инженерной базы |

**42 состояния не рассчитаны; §§4/5/6 NOT_RUN.** Прочность, устойчивость и реальные
реакции не подтверждены. ТЗ/архитектура NOT_APPROVED, G1 OPEN; W02 и physical READY NO-GO.
Источник power/pressure/moisture и реальные свойства/геометрия/связи остаются открытыми.

Оператор разрешил следующим свежим R3/R4 расчёты и W02 после принятия нового claim
и входного аудита. Эти работы здесь не выполнены. Физические испытания и выпуск
в производство требуют отдельного решения человека.

## Следующий шаг

[Очередь](ISSUES_AND_TASKS.md), машинный индекс `coordination/task_index.json`.
R1 завершил [план эстафеты](coordination/tasks/T-R1-ENGINEERING-PLAN-01/dispatch_plan.md).
Claims принимаются в порядке R3 → R4, результаты включаются в порядке R4 → R3.
R2 готовит входы; R5 проверяет поставленные инженерные результаты и CI.
UNKNOWN не заменять нулём; данные источников автоматически не повышать.

Проверки: `python verify_output.py --check-git`,
`python scripts/check_registry.py --check-git`,
`python -m unittest discover -s tests -v`. PASS относится только к проверенной области.
