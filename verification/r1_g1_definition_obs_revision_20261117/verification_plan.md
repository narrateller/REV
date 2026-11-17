# Проект документальных методов и будущей проверки

DRAFT / NOT_APPROVED / independent OUTPUT-review NOT_RUN. Общий WARNING. Новых инженерных чисел, назначений и разрешений выполнения нет. 42 состояния не рассчитаны; §4/5/6 NOT_RUN; G1 OPEN; W02/physical READY NO-GO. Прочность, устойчивость и реальные реакции не подтверждены. Численный/физический этап, CAD-build/rebuild и испытания не начинались и не разрешены.

## DOC-DEFINITION-AUDIT-01 / DRAFT-01

1. Freeze scope/input revisions and confirm actual claim/lease.
2. For each scope item locate definition, source, criterion, method and responsible owner.
3. Record INCLUDED, JUSTIFIED_EXCLUSION or UNRESOLVED with reason; silence or absence is UNRESOLVED.
4. Check mixed/numeric subclaims retain applicable units/calibration/timebase/uncertainty, pure audit uses categorical assurance.
5. Submit definition completeness and exclusions to independent reviewer; no auto G1 closure.

Предложенные диспозиции: INCLUDED, JUSTIFIED_EXCLUSION, UNRESOLVED. Отсутствие ответа/источника — UNRESOLVED. Исключения требуют обоснования и независимой оценки. Документальная полнота определения и фактическое соответствие машины — отдельные решения.

DOCUMENTARY_AUDIT применим только к чистым качественным подутверждениям. MIXED/NUMERIC/MODEL сохраняют применимые единицы, калибровку, время, неопределённость, покрытие и контроль модели. Физический метод, средства, серия, критерии остановов и разрешение выполнения не выбираются этими документальными DM.

## DM-01 — REQ-REV-01 / VAL-REV-01

Сопоставить функции F-REV-01…04 с интерфейсами, строками программы и будущими evidence records; проверить отсутствие функций без входа, выхода или критерия.

Входная область: DEF-01-A, DEF-01-B, DEF-01-C, DEF-01-D, DEF-01-E. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-02 — REQ-REV-02 / VAL-REV-02

Проследить каждую характеристику к спецификации/методу/пробе; исключить перенос происхождения древесины в доказательство пригодности и объединение окон разных прессов. Явно сверить плотность VAL02 и насыпную плотность MATERIAL с DEF-02-G и quantity_crosswalk.json; определить вид, состояние пробы и границы массы/объёма. Не отождествлять виды плотности и не назначать значения, метод или пределы без основания.

Входная область: DEF-02-A, DEF-02-B, DEF-02-C, DEF-02-D, DEF-02-E, DEF-02-F, DEF-02-G. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-03 — REQ-REV-03 / VAL-REV-03

Составить раздельные проверки геометрии/состояния, массы и выдачи; связать их с DEF-03-F и quantity_crosswalk.json. Сохранять запись каждого цикла, включая неуспешные и неполные: cycle_id, outcome, quality_flag, missing_reason, disposition и ссылки на исходные события/учёт серии. При неполной выдаче отсутствовать может изделие или измерение; запись цикла и его исход не удаляются. Неизвестная масса остаётся UNKNOWN, не нулём. Полнота учёта связана с DEF-01-E, DEF-04-D и REQ22/evidence schema; см. record_retention_plan.json.

Входная область: DEF-03-A, DEF-03-B, DEF-03-C, DEF-03-D, DEF-03-E, DEF-03-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-04 — REQ-REV-04 / VAL-REV-04

Проверить одинаковые границы числителя и окна наблюдения, исключение двойного учёта и сохранение up-to/material-dependent квалификаторов; не считать декларацию гарантированным минимумом.

Входная область: DEF-04-A, DEF-04-B, DEF-04-C, DEF-04-D, DEF-04-E, DEF-04-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-05 — REQ-REV-05 / VAL-REV-05

Для каждого предложенного режима перечислить разрешённые и запрещённые переходы, evidence и реакцию на отсутствие подтверждения; не использовать исходный каталог 42 состояний как рассчитанную циклограмму.

Входная область: DEF-05-A, DEF-05-B, DEF-05-C, DEF-05-D, DEF-05-E, DEF-05-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-06 — REQ-REV-06 / VAL-REV-06

Сверить договорённости каждой стороны интерфейса и направление передачи; отличить геометрию бункера от фактической дозы и будущую линию от имеющегося контекста.

Входная область: DEF-06-A, DEF-06-B, DEF-06-C, DEF-06-D, DEF-06-E. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-07 — REQ-REV-07 / VAL-REV-07

Сопоставить каждый источник питания/потребитель/режим с будущим требованием к площадке; не суммировать неоднозначные строки BP500 и не назначать собственный бюджет мощности.

Входная область: DEF-07-A, DEF-07-B, DEF-07-C, DEF-07-D, DEF-07-E, DEF-07-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-08 — REQ-REV-08 / VAL-REV-08

Проверить определения величин/точек и зависимости по каждой фазе; не исправлять kg/cm² в kgf/cm² догадкой и не получать силу из неоднозначной декларации.

Входная область: DEF-08-A, DEF-08-B, DEF-08-C, DEF-08-D, DEF-08-E, DEF-08-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-09 — REQ-REV-09 / VAL-REV-09

Сохранить H01 → REQ09/VAL09/MET09 → FORCE_REACTION и связи REQ16/17; проверить перечень входов для будущего обоснования и не подменять реакции общей массой референса.

Входная область: DEF-09-A, DEF-09-B, DEF-09-C, DEF-09-D, DEF-09-E, DEF-09-F, DEF-09-G, DEF-09-H. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-10 — REQ-REV-10 / VAL-REV-10

Сопоставить каждую зону/режим с опасностью, защитой и будущим доказательством; отсутствие выбранных PL/SIL не заменять произвольной категорией.

Входная область: DEF-10-A, DEF-10-B, DEF-10-C, DEF-10-D, DEF-10-E, DEF-10-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-11 — REQ-REV-11 / VAL-REV-11

Проследить каждый отказ до безопасного состояния и разрешения восстановления; истечение выдержки не считать подтверждением нулевой реакции или разрешением открытия.

Входная область: DEF-11-A, DEF-11-B, DEF-11-C, DEF-11-D, DEF-11-E, DEF-11-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-12 — REQ-REV-12 / VAL-REV-12

Проверить раздельные переходы при неисправности канала и реальном отсутствии движения; INVALID/SIGNAL_LOSS не преобразовывать в NO_MOTION_CONFIRMED.

Входная область: DEF-12-A, DEF-12-B, DEF-12-C, DEF-12-D, DEF-12-E, DEF-12-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-13 — REQ-REV-13 / VAL-REV-13

Сверить границы и определения условий отдельно для помещения и материала; окна BP500/E55/WEIMA не усреднять и не объявлять взаимозаменяемыми.

Входная область: DEF-13-A, DEF-13-B, DEF-13-C, DEF-13-D, DEF-13-E. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-14 — REQ-REV-14 / VAL-REV-14

Связать материал/операцию/опасность/защиту/будущий evidence; ARS допускает также неметаллическое сырьё, но его режимы не становятся параметрами REV.

Входная область: DEF-14-A, DEF-14-B, DEF-14-C, DEF-14-D, DEF-14-E, DEF-14-F, DEF-14-G. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-15 — REQ-REV-15 / VAL-REV-15

Для каждой операции проверить изоляцию, остаточную энергию, повторное накопление и условия возврата; документ о процедуре не считать выполненной безопасной операцией.

Входная область: DEF-15-A, DEF-15-B, DEF-15-C, DEF-15-D, DEF-15-E, DEF-15-F, DEF-15-G. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-16 — REQ-REV-16 / VAL-REV-16

Сохранить H01 и FORCE_REACTION трассу к REQ09/16/17; не переносить массу/габариты BP500 в реальные реакции и не требовать от пользователя будущий готовый чертёж.

Входная область: DEF-16-A, DEF-16-B, DEF-16-C, DEF-16-D, DEF-16-E, DEF-16-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-17 — REQ-REV-17 / VAL-REV-17

Проследить каждое предложение изготовления к возможности и контролю; названия брендов референса и hardened/cemented не считать выбранной маркой или APPROVED_FOR_LAYOUT.

Входная область: DEF-17-A, DEF-17-B, DEF-17-C, DEF-17-D, DEF-17-E, DEF-17-F, DEF-17-G. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-18 — REQ-REV-18 / VAL-REV-18

По каждому элементу области и N01…N06 сопоставить доказательство, основание и решение; кандидат или место изготовления в РФ не являются выводом о юридической применимости.

Входная область: DEF-18-A, DEF-18-B, DEF-18-C, DEF-18-D, DEF-18-E, DEF-18-F, DEF-18-G. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-19 — REQ-REV-19 / VAL-REV-19

Перечислить каждый обязательный артефакт и сверить версии/хеши/доступность/результат; программные PASS не выдавать за проверку физики, независимости или готовности изделия.

Входная область: DEF-19-A, DEF-19-B, DEF-19-C, DEF-19-D, DEF-19-E, DEF-19-F, DEF-19-G. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-20 — REQ-REV-20 / VAL-REV-20

Сверить покрытие всех REQ/VAL без подмены планируемого результата фактическим; G1 определяет как проверять, а не требует преждевременных физических испытаний.

Входная область: DEF-20-A, DEF-20-B, DEF-20-C, DEF-20-D, DEF-20-E, DEF-20-F, DEF-20-G, DEF-20-H, DEF-20-I. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-21 — REQ-REV-21 / VAL-REV-21

Для каждой REQ и всех 40 полей проверить locator/revision/disposition/qualifier/decision; RAW не повышать, старые акты не распространять на новый target.

Входная область: DEF-21-A, DEF-21-B, DEF-21-C, DEF-21-D, DEF-21-E, DEF-21-F. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.

## DM-22 — REQ-REV-22 / VAL-REV-22

Проверить возможность раздельного описания split/merge/refill/residual/loss/unknown и происхождения каждой связи; не считать дозу изделием и не делить неизвестные доли поровну.

Входная область: DEF-22-A, DEF-22-B, DEF-22-C, DEF-22-D, DEF-22-E, DEF-22-F, DEF-22-G, DEF-22-H, DEF-22-I, DEF-22-J, DEF-22-K, DEF-22-L. Выход: scope_item_id, definition_revision, source_locator, criterion_ref, method_ref, owner_ref, disposition, reason, reviewer, remaining_gap. Статус метода: PROPOSED_NOT_APPROVED; фактических результатов нет.
