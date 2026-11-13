# ARB-R1-CI-SEMANTICS-03 — допустимость recovery snapshots

R1 / codex-01; Q-R1-CI-SEMANTICS-ARBITRATION-01, T-r4-cycle-interfaces-01.
База main `3a9258c57e4bc15d6de98f1d17e8412ad6e8899a`. Claims не продлеваются:
R1 PR #44 до 2026-11-13T22:14:32Z, R4 PR #45 до 2026-11-14T00:13:12.404899Z.
Уточнение `ARB-R1-CI-SEMANTICS-02` на
`e0fea7bbf3bd32fda601bca2f7567f8e2c3342b3`, не изменение ТЗ/архитектуры.

## Основание

Акт R5 `0ff3c8f4502ea29c712bf1f41e223f172c5a21c7`, проверенный C
`fa0626372c03d11655624bb454458f82c30117f7`, H
`ab0fb1900a2bbdfa81e284112b318320f3c5b480`. Шесть type-контрпримеров
исправлены; B03 остаётся OPEN из-за четырёх ложных TRUE неполных snapshots.
interface_consecutive_rejections=4; material_contract_consecutive_rejections=2.
Все предыдущие акты/счётчики/закрытия сохраняются.

R1 выполнил unchanged `incomplete_snapshots.py` R5 в изолированном checkout
эстафеты акта `e4e32de5b6f0103a5f09c4bdd972f1f10bab5c51`:
7 случаев, 3 совпадения, 4 FALSE-acceptances. `empty-expected`,
`empty-origin-matched-proof`, `foreign-domain-origin-matched-proof`,
`empty-origin-and-expected` дали TRUE вместо UNKNOWN. Frozen recover на
тех же данных вернул ALLOWED_ASSUMED и RESOLVED **только в возвращённой копии**;
caller/proof остались неизменны. Воспроизведение не является новой проверкой
исправления, физическим снятием отказа или разрешением движения.

## Решение: строгая prevalidation и условная совместимость policy

Выбран вариант A из R5 follow-up: проверка допустимости входов по закреплённым
определениям guard/action **перед** делегированием frozen policy. Frozen helper
не переписывается. Вариант принять пустые maps ради equality с legacy отклонён.
Отдельное изменение версии frozen material helper возможно только новой задачей,
с отдельным review; это не требуется для данной исправительной итерации.

R4 разрешена узкая корректировка B03 после фиксации SHA решения в капсуле и
проверки актуальной main, owner/lease и входов. B03 остаётся OPEN, interface
BLOCKED и стабильный документальный/CAD handoff NO-GO до независимого RECHECK.
53/84 норматив, типовые исправления, B01/B02, 44 bindings, четыре force variants,
расчёты и CAD не меняются; новые численные данные или физические решения не нужны.

### 1. Независимые доменные обязательства

Источник ожидаемых доменов — фиксированная версия определения **целевого
fault guard** и разрешённого recovery action, а не keys предъявленного map,
хэш F-digest или результат legacy helper. Для B_RESET_CONFIRMED
`evidence_domains=['B_CLOSURE']`, следовательно E={B_CLOSURE}. Неизвестный
тип guard/action или отсутствующее определение не превращается в пустое E.
Для иного поддержанного guard нужен его собственный явно закреплённый scope.

До исправления выписать схему для **каждого** используемого snapshot:

| Map | Обязательный состав и проверки |
|---|---|
| fault.origin.revisions | Точный E исходного guard, без пропусков/подмены чужими доменами; значения integer по принятой схеме; origin и causal identity сохранены |
| fault.expected_revisions | Точный E того же guard; значения integer; новые значения только по подтверждённой адресной revision_history, а не по пустой карте |
| proof.origin_revisions | Точный E и типизированное равенство с валидным immutable origin |
| proof.revisions | Обязательно содержит E и совпадает с expected/current в E; дополнительно допустимы лишь явно разрешённые схемой известные домены, не замена E |
| context.revisions | Содержит E для результата и все отдельно требуемые домены собственных ENTRY-предикатов; не требует всех глобальных доменов только ради B recovery |

Схема полей и extra-key policy должны быть явными, покрытыми тестами и
обоснованными fixed definitions. Отсутствие/корректное изменение постороннего
FEED/RETENTION не считать ошибкой B_CLOSURE recovery само по себе; собственные
условия других действий проверяются отдельно. Не требовать искусственного
полного глобального map для любого узкого guard. Допустимая пустота возможна
только если закреплённый тип **явно** не требует ни одного домена; в показанном
B_CLOSURE случае E непусто и пустые maps недопустимы.

### 2. Полнота и тип предшествуют equality

Пустой map, пропущенный/чужой обязательный домен, неизвестная revision,
невалидный тип или несогласованная история не дают TRUE. Для четырёх
контрпримеров prevalidation возвращает UNKNOWN с причиной; не делегировать
такой вход в permissive legacy ветвь как достаточное доказательство.
Не восстанавливать origin копированием текущих revisions, нулём, setdefault,
выбором произвольного домена или правкой хэша. Coherent F-digest показывает
целостность записи, но не её смысловую полноту.

Разделить validation status/reason, scoped policy result и составное разрешение
действия. Известный независимый запрет ресурса/состояния сохраняет BLOCKED
составного gate при невалидном proof, а не скрывается под UNKNOWN recovery.
Readonly predicate не должен менять origin, expected, fault/history, proof,
rejected IDs и состояние; proposed copy helper также не применять к caller.

### 3. Что означает согласованность с frozen policy

Отменяется слишком широкая интерпретация полного equality результатов для
всех произвольных malformed contexts. Совместимость заявляется **только в явно
допустимой области входов**, которая удовлетворяет новой полноте/domain/type
схеме и собственным требованиям action. В ней положительный адресный путь,
ошибки scope/revision, причинные отказы и результаты должны соответствовать
frozen policy. За её пределами prevalidation может отклонить то, что legacy
ошибочно допускает; это намеренное ограничение с явным диагностическим выводом,
а не основание изменять helper или ослабить норматив.

При консервативном UNKNOWN против legacy TRUE отдельно указать нарушенную
схему и почему вход вне области. При UNKNOWN predicate и известном FALSE
другого обязательного условия общий gate остаётся BLOCKED. Не выдавать эти
различия за доказанную физическую неисправность или число независимых дефектов.

## Критерии независимого RECHECK

R4 публикует точный C, доменную/type/extra-key схему и таблицу различий policy
с классификацией in-domain/out-of-domain. R5 использует независимый domain oracle
из fixed guard/action definitions, не из изменённых maps:

- все 7 исходных incomplete cases, в том числе 4 coherent F-digest/causal-ID
  подмены, получают ожидаемые результаты, correct valid baseline сохраняется;
- origin/expected/proof maps: empty, missing, чужой-only, частичный и extra-key,
  invalid types/unknown revisions; expected и origin проверяются независимо;
- корректные 0/1/large integer, подтверждённое адресное изменение revision и
  положительный recovery остаются допустимыми; старый origin не равен current
  просто по требованию теста, а проверяется с revision_history;
- missing/изменённый неиспользуемый current domain сам по себе не блокирует
  правильную B_CLOSURE ветвь; используемый отсутствующий domain не разрешает её;
- malformed proof + известный resource/state/causal denial сохраняют BLOCKED
  общего gate; valid proof не обходит посторонний неустранённый fault;
- frozen-helper differential tests ограничены объявленным допустимым доменом;
  каждое намеренное ужесточение за его пределами объяснено без ложного TRUE;
- readonly/неизменность input/output histories/rejected IDs и предыдущие
  normative/type/B01/B02/source checks проходят; CAD и расчёты сохранены.

R5 закрывает B03 только новым независимым актом на точном C; R1 этого не делает.
При необходимости иных доменов/новой версии helper — отдельная область и review.
R3 conditional force studies с WARNING допускаются в действующем scope; W02/PLC,
исполняемый material engine и physical READY NO-GO. Геометрия/прочность/CAD/rebuild
и физические испытания NOT_RUN. Архитектура/ТЗ/оборудование не утверждены, G1 OPEN.
