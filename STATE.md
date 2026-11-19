# REV — состояние на 2026-11-19

Режим: Stateless Agents / Stateful Repo. На момент ротации все старые claims сняты,
новых владельцев нет. Административный переход выполнен R1, сессия
`6afb300b-1540-8191-a5c4-be1a684c20e0`, по прямой директиве оператора.

Основание: [решение оператора](decisions/ARB-OPERATOR-FORK-BASELINE-01.md),
[авторизация](coordination/user_authorizations/operator_fork_20261118.json).
Полная история сохранена побайтно: [архив](archive/context/operator-fork-20261118/manifest.json).
Старые полномочия: [закрытые записи](coordination/completions/operator-fork-20261118/retirements.json).

Проектный базис `DESIGN_BASIS` задан решением [ARB-OPERATOR-DESIGN-BASIS-02](decisions/ARB-OPERATOR-DESIGN-BASIS-02.md).
Обмеры T/U и пробы конкретного сырья исключены из плана. Площадку и периферию
адаптируют под интерфейсы пресса REV. Проектные требования к подготовке сырья
и цели по готовому брикету R2 выводит из четырёх референсов и применимых стандартов.

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
| cad/ | Четыре редактируемые сборки W02 под 1,5 МН на FreeCAD 1.1.4, исходники и база TechDraw | Реакции и контактный расчёт R3, подтверждение интерфейсов и рейтингов поставщиков |
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
Численные требования к мощности, давлениям, подготовленному сырью и геометрии
уточняются в проектном базисе. Фактические свойства партий и физические связи
сохраняют статус `UNKNOWN` при отсутствии подтверждения.

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
Экспорт TechDraw в DXF/SVG/PDF имеет статус `NOT_RUN`.
Предшествующий [аудит источников W02](coordination/completions/T-R1-ENGINEERING-PLAN-09/completion.json)
сохраняет причины по 42 физическим состояниям. По решению оператора ожидание
обмеров и проб снято для проектной работы. R2 завершил [T-R2-DESIGN-BASIS-02](coordination/tasks/T-R2-DESIGN-BASIS-02/README.md).
Базис `REV_DESIGN_BASIS` r1 задаёт условные входы R3/R4, остаточные `UNKNOWN`
и границы для потока A1. [Акт](coordination/completions/T-R2-DESIGN-BASIS-02/completion.json) ·
[Освобождение claim](coordination/completions/T-R2-DESIGN-BASIS-02/claim_release.json).
R3 завершил [T-R3-FORCE-CALC-01](cae/cases/T-R3-FORCE-CALC-01/README.md) по
номиналам поставки R4. Из 2 462 сочетаний 2 346 имеют статус CALCULATED_ASSUMED,
116 не имеют статического равновесия. Все физические состояния и запасы
соединений остаются BLOCKED_INPUTS. Зафиксированы проблемы масштаба и осей FCStd,
нехватка усилия и хода гидроцилиндра Ø80/45. [Независимая проверка R5](coordination/completions/T-R5-FORCE-CALC-VERIFY-01/completion.json)
дала `PASS` в области `CALCULATED_ASSUMED`. Результат интегрирован в main с зелёным CI.
Цикл DESIGN_BASIS r1 открыт до выпуска проверяемых файлов КД W02.
R4 завершил [T-R4-FINAL-DRAWINGS-01](coordination/completions/T-R4-FINAL-DRAWINGS-01/completion.json) — финальный комплект КД W02 с экспортом DXF/SVG/PDF (160 файлов, FreeCAD 1.1.4).
R5 провёл [независимую верификацию](coordination/completions/T-R5-FINAL-DRAWINGS-VERIFY-01/completion.json) на коммите 994f0e9c: все критерии PASS (4 FCStd модели, 53 DXF, 53 SVG, 50 PDF, масштаб 1:1 мм, PistonRod во всех вариантах, ReceiverLock в B-V1/B-V2, BOM привязан к cots_catalog.yaml, CI зелёный).
[Claim T-R4-FINAL-DRAWINGS-01 освобождён](coordination/completions/T-R4-FINAL-DRAWINGS-01/claim_release.json).

R4 завершил [перепроектирование W02 под 1,5 МН](coordination/completions/T-R4-REDESIGN-1.5MN-01/completion.json) в области `CALCULATED_ASSUMED`.
Два Ø250/140 × 700 мм дают расчётные 2,295 МН выдвижения и 1,540 МН втягивания при 250 бар.
[CAD и TechDraw](cad/source/force_geometry/redesign_1p5mn/manifest.json) пересобраны на FreeCAD 1.1.4 / OCCT 7.8.1.
[Claim освобождён](coordination/completions/T-R4-REDESIGN-1.5MN-01/claim_release.json).
R3 завершил [T-R3-FORCE-CALC-02](cae/cases/T-R3-FORCE-CALC-02/README.md)
с инженерным итогом `FAILED / CALCULATED_ASSUMED`. Штатная огибающая
проходит по давлению, ходу, запасам и устойчивости. В закрытой ветви B
запас контакта ключей при 315 бар составляет 1,111 при требовании 1,5.
[Инженерный отказ](cae/cases/T-R3-FORCE-CALC-02/engineering_failure_note.md) блокирует выпуск КД.
[Акт и точный SHA для R5](coordination/completions/T-R3-FORCE-CALC-02/completion.json).
Физические входы остаются `BLOCKED_INPUTS`.

R3 завершил [перерасчёт W02 по итерации 02](cae/cases/T-R3-FORCE-CALC-03/README.md)
с результатом `FAILED / CALCULATED_ASSUMED`. Ключи и опоры B при 315 бар
имеют запас 1,881. Выпуск КД блокируют закрытие зазора при рассогласовании
и превышение 315 бар при реверсе одной ветвью.
[Акт и точный SHA для R5](coordination/completions/T-R3-FORCE-CALC-03/completion.json).

R3 завершил [итерацию 03 W02](coordination/completions/T-R3-FORCE-CALC-04/completion.json) с итогом
`FAILED / CALCULATED_ASSUMED`. Пересчитаны 42 ID. Предельный остаточный
зазор −2,142 мм, реверс одной ветвью требует до 503,524 бар в полости.
Claim освобождён для следующей итерации R4. Физические статусы сохраняются.

R4 завершил условную итерацию 04 W02 на коммите `83407d0`.
Сборки и расчётные границы переданы на интеграцию через [PR 76](https://github.com/narrateller/REV/pull/76).
CI ветки и PR прошёл. [Акт поставки](coordination/completions/T-R4-REDESIGN-1.5MN-03/completion.json)
и [освобождение claim](coordination/completions/T-R4-REDESIGN-1.5MN-03/claim_release.json) записаны в main.
Следующий шаг по задаче — проверка R3/R5 поставленного коммита и интеграция PR.

Проверки: `python verify_output.py --check-git`,
`python scripts/check_registry.py --check-git`,
`python -m unittest discover -s tests -v`. PASS относится только к проверенной области.


