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
| cad/ | Четыре редактируемые модели W02 пересобраны на FreeCAD 1.1.4. Исходники в `cad/source/force_geometry`, артефакты компоновки сохранены | Фактическая силовая геометрия и инженерная сборка |
| params/ | 1144 записи: 1072 CALCULATED, 47 ASSUMED, 25 RAW/null; исходные 44 привязки, нагрузки и ходы | Проверить пригодность входов для инженерных расчётов; арифметические статусы не подтверждают прочность |
| controls/ | press_variant_state_tables.md — функциональный DRAFT | Численные режимы, реализация управления и безопасных состояний |
| cae/ | Аудит 42 случаев и сверка 52 интерфейсов R4 | Фактические нагрузки, реакции, прочность и устойчивость |
| drives/ | Восемь условных осевых расчётов и шаблоны COTS | Фазовые нагрузки и выбор приводов |
| drawings/ | Каталог | Выпуск КД после готовности инженерной базы |

**42 физических состояния имеют статус BLOCKED_INPUTS; физические §§4/5/6 NOT_RUN.**
По расчётной огибающей все 42 состояния и условные §§4/5/6 имеют статус
CALCULATED_ASSUMED. [Результаты](cae/cases/T-R3-42-STATES-ENVELOPE-01/README.md)
включают 174 освобождённых сочетания без статического равновесия.
[Отдельные журналы 42 состояний](cae/cases/T-R3-42-STATES-01/results/index.json)
фиксируют реакции, условные запасы прочности и устойчивости и нагрузки на
соединения. Запасы соединений имеют статус BLOCKED_INPUTS из-за отсутствия
данных о несущей способности.
[Аудит R3](cae/cases/T-R3-42-STATES-01/README.md) содержит блокер каждого случая.
Прочность, устойчивость и реальные
реакции не подтверждены. ТЗ/архитектура NOT_APPROVED, G1 OPEN; W02 и physical READY NO-GO.
Источник power/pressure/moisture и реальные свойства/геометрия/связи остаются открытыми.

Оператор разрешил R3 расчёты по огибающей и R4 входной аудит W02 после нового
claim. Физические испытания и выпуск в производство требуют отдельного
решения человека.

## Следующий шаг

[Очередь](ISSUES_AND_TASKS.md), машинный индекс `coordination/task_index.json`.
R1 завершил [план эстафеты](coordination/tasks/T-R1-ENGINEERING-PLAN-01/dispatch_plan.md).
По эстафете поставлены условная геометрия R4 и аудит R3.
R1 поставил [расчётную огибающую](cae/cases/design_boundary_phase_load_envelope/README.md).
R3 завершил `T-R3-42-STATES-ENVELOPE-01` для реакций, прочности и устойчивости
выбранных суррогатов.
R3 завершил [T-R3-CAE-456-01](cae/cases/T-R3-CAE-456-01/README.md) в области
`ASSUMED_STATIC_SCREENING`. Физические §§4/5/6 ожидают реальных входов.
R4 завершил [CAD-пересборку W02](coordination/completions/T-R4-W02-CAD-01/completion.json) на FreeCAD 1.1.4.
[Claim освобождён](coordination/completions/T-R4-W02-CAD-01/claim_release.json). [Верификация R5](coordination/completions/T-R5-W02-CAD-REBUILD-VERIFY-01/completion.json)
дала `PASS` для артефактов, метаданных и CI.
R5 завершил [T-R5-ENGINEERING-VERIFY-02](coordination/completions/T-R5-ENGINEERING-VERIFY-02/completion.json)
в области условного расчёта и документального аудита W02. Расхождение идентификаторов
зафиксировано при [закрытии claim](coordination/completions/T-R5-ENGINEERING-VERIFY-02/claim_release.json).
R2 завершил [аудит входов и проект ТЗ](coordination/tasks/T-R2-INPUTS-01/README.md) в
`093a78ad27e46f6b2066ee78d4170704d4307623`. BP500 задаёт ориентиры для адаптации площадки.
Входы REV без подтверждённых значений сохранены как UNKNOWN с `null` и причиной.
[Акт R2](coordination/completions/T-R2-INPUTS-01/completion.json) · [Освобождение claim](coordination/completions/T-R2-INPUTS-01/claim_release.json)
R4 завершил [условную КД W02](coordination/completions/T-R4-DRAWINGS-01/completion.json).
R5 записал [PASS](coordination/completions/T-R5-DRAWINGS-VERIFY-01/completion.json)
на `dcb8ff5`. В каталоге четыре позиции с `BLOCKED_INPUTS`.
R1 завершил [аудит источников W02](coordination/completions/T-R1-ENGINEERING-PLAN-09/completion.json).
Все 42 физических состояния остаются BLOCKED_INPUTS. Очередь ожидает новый
применимый к REV источник для аудита R2.

Проверки: `python verify_output.py --check-git`,
`python scripts/check_registry.py --check-git`,
`python -m unittest discover -s tests -v`. PASS относится только к проверенной области.

