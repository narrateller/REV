# R5 — независимый recheck DOC01/TRACE02

**Общий вердикт WARNING. DOC01 и TRACE02 CLOSED только в документальной области
на exact C `45d5964786e608cdfcc656819fd6df8c77e495fe`.** Новая ревизия достаточна
для исправления двух замечаний к предварительному предложению. Это не утверждение
ТЗ/G1/программы и не подтверждение сил, безопасного состояния или конструкции.
B01/B02/B03 и source power/pressure/moisture остаются OPEN.

`reviewed_commit = 45d5964786e608cdfcc656819fd6df8c77e495fe`.
Target request H `2b99776187345729f1c3e177d0e5ed83e1239b07`, substantive PR57.
Принятая execution command/scope main `b8485a93b7ced741261e7979f9438bad8590d368`.
Эти три версии различаются: main разрешает область, request H указывает target,
а выводы относятся к exact C. Target25 artifacts не исправлялись reviewer.

## Идентичность и действующие полномочия

Actual session/thread `6afb0a73-b16c-8191-a539-9a6685e89034`; роль R5 в той же
задаче `T-r5-g1-supplement-output-review-01`. Codex на базе GPT-6; exact runtime
model ID UNAVAILABLE. Проверены Bash, Git/Git LFS, gh/API, Python3.12.14/PyYAML.
[Identity](identity.json) сохранена до содержательной оценки.

Reviewer не соавтор новой R1 ревизии, её renderer/схем/карточек. Автор target —
R1 `6afb300b-1540-8191-a5c4-be1a684c20e0`. Эта же reviewer session создала исходные
DOC01/TRACE02 и акт C `1f9206312f3429c2c357b836fce11bb3d70ff74c` /
H `32c40d7ab5cc377ecc170aec0fc045b66bcb40f2`, а также прежние upstream R5 акты и
claim proposal. Это участие раскрыто. Их правильность заново независимо не
удостоверяется; здесь проверены новые авторские исправления и сохранение входов.
Организационная независимость не удостоверяется; смена роли/сессии не заявляется.

Main — обычный merge PR58, parents `e8f1d6bf41c0cfd2dcc4d3a673e642ecfb53588a` и
`09764e9d39a9433e053a601163dca7b71a574414`. Scope amendment
`coordination/scope_amendments/T-r5-g1-supplement-output-review-01/DOC01-TRACE02-REVISION-01.json`
находится в main, ACCEPTED_MAIN, owner actual R5. Его target/request и manifest SHA
совпали; base-claim SHA256
`9b610dbb7bbbaaa1590e72ac8ea407f0075994cdb0056e005ac6a0499bd12ab3`
совпал с неизменным canonical claim. Старый claim по-прежнему указывает predecessor
fe10c0bc…, новый target разрешён именно явным amendment. Ни claim, ни amendment
reviewer не переписывал. Исходный deadline `2026-11-18T01:58:30.990734+00:00`
действует на момент проверки и не продлён. У session одна принятая задача;
конкурирующего владельца/scope для данного target не найдено. Нового claim/lease нет.

Точный target H и accepted main объединены только в изолированной review-ветке.
Четыре Markdown-конфликта разрешены сохранением обеих точных добавленных историй
и общего основания; JSON R1 task — рекурсивным объединением операционного контекста
с обеими версиями в snapshots. Canonical claims/amendment и sealed artifacts не
менялись: [merge_context.json](merge_context.json). PR57/main этой веткой не слиты.

Свежий [input_audit.json](input_audit.json): WARNING,4 bounded PASS/3 NOT_RUN,
22 immutable input seals и25 target artifacts совпали. §1/2/3/7 проверяют только
документальные границы/версии/представление/идентификацию; §4/5/6 NOT_RUN.
Входной аудит не подменяет новый recheck выхода.

## DOC01 — CLOSED_DOCUMENTARY_EXACT_C

Численный uncertainty budget DOCUMENT удалён; вместо него заданы четыре
качественных assurance dimensions: перечисленная полнота, полномочность источника,
контроль ревизий, компетентность/независимость reviewer. Каждая имеет собственные
обязательные evidence fields и правило. Неполная область, unresolved applicable
items, неизвестный метод или отсутствие основания компетентности не превращаются
в PASS по числу проверок.

У чистого аудита instrument/range/resolution/calibration/numeric budget/measurement
series N_A обоснован по полю и ограничен отсутствием измеряемой численной величины.
Controlled method revision остаётся APPLICABLE_UNKNOWN; enumerated scope тоже
UNKNOWN и обязателен. В чистых REQ18–21 нет выдуманного порога/повторной серии,
но есть требование согласованного scope, метода, source authority и компетентности.
Timestamp аудита остаётся метаданными записи, а не измеренным временным интервалом.

Смешанные DOCUMENT строки сохраняют исходный numerical/calibration/time/uncertainty
контекст и все применимые UNKNOWN. Нельзя распространить N_A канала DOCUMENT на
измеренные подутверждения. У остальных12 metrology rows без DOCUMENT сохранены
полные исходные объекты. Десять прежних non-DOCUMENT channel objects неизменны.

Условная evidence schema различает DOCUMENTARY_AUDIT, NUMERIC_MEASUREMENT, MIXED,
MODEL_PREDICTION. Выбор — по фактическому виду evidence/подутверждения, не по названию
REQ. Общие method/criterion/program/quality/authorization fields не сняты.
MIXED требует обе составляющие; pure computational output может иметь обоснованный
instrument N_A, но measured inputs модели сохраняют свои calibration/uncertainty
requirements. Applicable unknown остаётся null с причиной и блокирует зависимый PASS.
Схема — будущий контракт, actual_records пусты. Исполнимый evaluator/программа и
физическое подтверждение здесь не созданы и не проверены.

Эти изменения устраняют исходную неоднозначность DOC01. Закрытие не означает,
что метод/полнота/приборы/бюджеты/компетентность уже утверждены либо проверены.

## TRACE02 — CLOSED_DOCUMENTARY_EXACT_C

H01 сохраняет все исходные source cells и REQ16/17. Добавлены прямая REQ09/VAL09,
MET09/16/17 и единый load-evidence plan. CRIT09 и MET09 согласованно ссылаются на
предлагаемый FORCE_REACTION и требуют load provenance, frame/sign conventions,
route/method, validated output scope и uncertainty/model-error basis. Исходные
evidence fields не удалены. Остальные19 hazard objects и17 criterion cards неизменны.

План требует первоисточник/роль input-output, actual configuration, автора/оператора,
точную версию/хэш, точку/интерфейс, frame/origin/axes/units/signs, временной контекст,
качество/неопределённость и область независимой валидации. Actual mass/CoG/подъёмные
интерфейсы/опоры/поза/направления/материалы/геометрия/такелаж/limits — UNKNOWN/null
с отдельными причинами и без source records. Это требования к будущему evidence,
а не подстановка donor gross mass или новых сил/моментов.

DIRECT_MEASUREMENT и MODEL_PREDICTION — два пока не выбранных маршрута. У первого
неизвестны метод, приборы/каналы/точки, диапазоны, калибровка/неопределённость,
синхронизация и правила данных. У второго неизвестны собственные входы/геометрия/
материал/контакты/границы, model/code/solver, convergence/sensitivity, балансы,
discrepancy/validation domain и independent review. Оба execution_permission=false,
NOT_RUN. Прогноз явно не объявляется подтверждением фактической реакции; измеренные
входы модели не освобождаются от метрологии. Имя отчёта, source pressure, brochure
mass и command signal сами по себе не доказывают силу или удержание.

Все future_result_fields null, actual_load_cases/actual_records пусты, реальный
engineering owner не назначен. Ни route, ни аппарат, ни архитектура не выбраны.
Новые нагрузочные случаи/сценарии42 state matrix, расчёты/CAE/испытания не выполнены.
Это устраняет исходный документальный trace gap; физическая состоятельность силового
контура, реакций и критериев остаётся непроверенной.

## Собственные доказательства и сохранение области

[independent_results.json](independent_results.json) и [recheck.py](recheck.py)
содержат собственные оценки всех22 cards,22 metrology rows,20 hazards,12channels,
четырёх assurance dimensions идвух routes. Восемь самостоятельных semantic policy
cases рассматривают missing method/scope, numeric subclaim под REQ18, mixed
calibration gap, prediction versus actual reaction, measured model inputs,
негодные provenance shortcuts иinvalid/known-violation handling. Это документальные
рассуждения по предложенной спецификации, не запуск реализованного evaluator и не
машинные observations/результаты испытаний. Author332 истарые4117 не использованы
как новая независимая проверка.

Собственные guards: **3804 PASS /0 FAIL**. Вывод о закрытии основан на достаточности
исправлений в указанной области, а не числе guards. Проверены все25 новых target
artifacts и22 exact inputs. Active bundle однозначно разрешает17 logical names в
точные paths/SHA:12 новых outputs и5 unchanged predecessor-scoped outputs;
сам resolver —13-й output. Ни locator, ни предшественник не подменяют новую ревизию.

Исходные26 predecessor artifacts,25 rev8 target artifacts,54 old pins/12 trees,
3300 прежних файлов вне разрешённого операционного контекста и59 hydrated LFS
payload/OID сохранены. Все44 полные bindings/нагрузки/ходы/CAD,52interfaces,
84 RAW/null UNKNOWN,42 полных state-объекта и15 OPEN gaps неизменны. RAW40 не
повышены. Source conflicts/qualifiers сохранены через неизменённые outputs.
История REJECT/STALE/material2/четыре FAIL и старое OBS01 closure только на R4
Cbeb4cf4ebcf6a99d3271a1560bdbd19caee8adfe сохранены; её корректность заново
независимо не удостоверяется. Старые WHAT_IF к новой цели NOT_EVALUATED.

Старый акт остаётся CURRENT/WARNING только для exact predecessor fe10c0bc…;
его applicability к новому target STALE_TARGET_CHANGED. Исходный journal сохранён
точным prefix, новый scoped closure добавлен отдельным актом. Исторические OPEN
в исходных замечаниях/author observation_status не переписываются; этот акт даёт
новое решение CLOSED_DOCUMENTARY_EXACT_C на конкретную исправленную ревизию.

Код renderer прочитан до запуска. Все13 outputs воспроизведены в свежем TEMP,
совпали с C: [renderer_replay.json](renderer_replay.json). Это воспроизводимость,
не самостоятельное доказательство смысла. Author verify_revision.py с R1 identity
guard изучен, но не запускался; session не подменялась.

```sh
python3 verification/r5_doc_trace_recheck_20261117/recheck.py --output /tmp/r5-doc-trace-independent.json
python3 verification/r1_g1_observation_revision_20261117/render_revision.py --output-dir /tmp/r5-doc-trace-fresh
python3 scripts/check_registry.py --check-git
git diff --check
```

Registry/сохранённые команды/хэши собственных evidence — [validation.json](validation.json).
Источник CI — [target_CI.json](target_CI.json); software CI не закрывает замечания
самостоятельно и не подтверждает физику. Собственные C акта затем H для R1,
CI обоих опубликованных SHA иremote SHA проверяются после публикации.

## Что остаётся обязательным

B01/B02/B03/source issues OPEN. До ТЗ/G1 нужны согласованные измеримые или
объективно перечисленные критерии/режимы/допуски, действительные владельцы,
контролируемые методы/область/правила полноты, обоснованная программа/метрология/
неопределённость/серии, риск/safe-state/изоляция/удержание и нормативная применимость.
Выбор иисполнение силового маршрута потребуют своих реальных входов/оснований,
independent program review иотдельного разрешения. Закрытие двух documentary notes
не закрывает эти пробелы. G1 требует определений/плана; оно не подменяется уже
выполненными физическими результатами будущих этапов.

**42 состояния не рассчитаны; §4/5/6 NOT_RUN; прочность/устойчивость/реальные реакции
не подтверждены. ТЗ/архитектура NOT_APPROVED, G1 OPEN, W02/physical READY NO-GO.
PR57 не слит; RAW не повышены. Расчёты, CAD-build/rebuild ииспытания не начинались
и этим актом не разрешаются.**
