# REV-R5-CI-GATE-EXITS-RECHECK-01-001

**B03 OPEN — REJECT_WITH_BLOCKER. Стабильная документальная передача CYC-02/03 — NO-GO.**
Два прежних свидетеля и 19 вариаций исправлены; все восемь выходов используют
единый finish. Независимо обнаружен оставшийся путь потери достоверного own
FALSE: исключение при чтении посторонней повреждённой записи fault подавляет
валидный текущий record до общей композиции. Новых ложных TRUE в матрице нет.

R5 / Codex / session **r5-ci-gate-exits-20261113**, прямое поручение пользователя,
13 ноября 2026, МСК. Reviewer не автор проверяемого checker/helper/норматива.
Авторские сессии: r4-linked-20261111, r4-cyc-fix-20261113,
r4-b03-semantics-20261113, r4-b03-types-20261113,
r4-b03-snapshots-20261113, r4-b03-gates-20261113.
Организационная независимость не удостоверяется. Main/owner/lease не присваивались.

| Проверенный вход | Точный SHA |
|---|---|
| C | **3060dbf561f95e4384fbfd13a9cc5569690515e5** |
| H | **98861219f0adda96af0aca0a3a35078aec022eb9** |
| R1 ARB-R1-CI-SEMANTICS-04 | **60eeddce71c9440a2fa08f7acbe6f1121c974b29** |
| Пятый REJECT | 88a34f8b7d2d6dbf236101f207e206efb0e3c747 |
| Четвёртый REJECT | 0ff3c8f4502ea29c712bf1f41e223f172c5a21c7 |
| Третий REJECT | 3d317b32596884cc60d9d42675924b88fcb29bf0 |
| Второй REJECT | 5fb731182a2bdf6b11246558eca58962e48568d9 |
| Первый OUTPUT/REJECT | 13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2 |
| Frozen contract/helper | 0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed |

Все входы/акты/R1 — предки H. Интерфейсный пакет совпадает в C/H/рабочем дереве.
Commit акта фиксируется следующей H-капсулой без самоссылки.

## Исправленные свидетели и регрессии

Оба исходных immutable JSON inputs повторены: **2/2**, scoped UNKNOWN и общий
BLOCKED, исходные typed digests проверены. Исторический minimal runner содержит
pin старого source e30b4b7; его pin не ослаблялся. Новый независимый reader
передаёт те же JSON inputs текущему C (minimal_pair_replay.json).

Неизменённая прежняя матрица исполнена в отдельной materialized tracked копии:
**295/295** вместо 276/295. Для **всех 19** исправленных вариаций отдельно
сопоставлены прежние/новые input digests: они совпадают, scoped UNKNOWN сохранён,
gate BLOCKED. nineteen.json и prior_295_new_inputs.json сохраняют результаты.
Raw C/session literals прежних scripts исторические; actual C фиксируется
authority_and_prior.json, а не выдаётся за новую подпись старого акта.

Выполнены неизменённые independent probes **654/654**, **765/765** и incomplete
**7/7**. Сохранились четыре исправления неполных snapshots, прежние типовые и
семантические ограничения, LOAD/FILL/RETURN/COMMIT, B01/B02 history/recovery.
Норматив 53 действий / 84 режимных правила / 18 поз воспроизведён из fixed blobs:
SHA256 minimum.json `b1c13c18c408120ae66d4995eac706e8dbf5842f35976494efb682c74e64d3df`.
Ожидания прежних probes включают собственные family obligations и полиномиальный
phase/source oracle, а не выводятся из mutable payload/export.

## Восемь выходов и независимая матрица

Собственные **231 случай: 223 совпадения / 8 FAIL**. Поведенческие ожидания
получены из R1 truth table и fixed guard/action definitions C0c4eb5d. Source
locations используются только для измерения покрытия. AST подтверждает общий
finish; sys.settrace фиксирует фактически исполненный assessment return.
Это покрытие выходов, не всех boolean expressions и не физического поведения.

| Выход assess / строка recovery_snapshots.py | Own cases | Наблюдение |
|---|---:|---|
| недоступные/неподдержанные definitions :59 | 1 | INDETERMINATE; без trusted action FALSE не выдуман |
| context не object :67 | 5 | INDETERMINATE; независимого источника запрета нет |
| proof не object :161 | 106 | standard own FALSE сохранён; 2 новых journal-FAIL |
| неизвестный/невалидный target :163 | 27 | target не подставляется; 2 journal-FAIL теряют own FALSE |
| неподдержанный proof action/guard :166 | 26 | addressed causal FALSE сохранён; 2 journal-FAIL |
| snapshot/schema/history rejection :229 | 52 | standard own/causal FALSE сохранён; 2 journal-FAIL |
| исключение frozen policy :240 | 3 | UNKNOWN с сохранением independently known BLOCKED |
| обычный policy outcome :243 | 11 | success и scoped UNKNOWN + независимый FALSE корректны |

Восемь journal-FAIL — две own guards × четыре выхода, **одна причина**, не восемь
физических неисправностей. exit_coverage.json содержит exact lines/counts/outcomes;
independent_results.json — ожидания, assertions, input digests и полные failed inputs.
Исключения policy проверены явной in-memory fault injection без изменения файлов;
они не объявляются реальной недоступностью сервиса или проверкой физики.
Сам новый journal witness воспроизводится обычными данными, **без injection**.

Дополнительно проверены:

- whole proof null/array/string/bool/number/empty object × TRUE/FALSE/UNKNOWN двух
  собственных условий; latched own FALSE/UNKNOWN, state/mode known wrong и unknown;
- неподтверждённая history не создаёт FALSE из одной старой latch/state; текущий
  independently valid FALSE сохраняется даже при недостоверности журнала;
- stale/wrong-phase/wrong-scope/no-interval/no-provenance/bool-revision record
  не принимается за доказанный current FALSE;
- explicit target + OPEN/RESOLVED/UNKNOWN/missing ancestor; proof action/guard
  omission, snapshot defects и неизвестный/missing/noncanonical/foreign-guard
  target. Без достоверного адреса causal UNKNOWN, чужой fault не подставляется;
- malformed fields с known FALSE и без него, перестановки keys, два обязательных
  условия, policy exception, normal return со scoped UNKNOWN;
- адресный positive recovery при revisions 0/1/large integer, minimal consumed
  domains без FEED/RETENTION, подтверждённые advances и чужой FEED fault. Чужой
  fault сохраняется; последующий ordinary B-COMPACT BLOCKED. Helper copy служит
  только синтетическим следующим входом, не применяется к caller или машине.

## Новый минимальный witness — current FALSE теряется в journal exception

Команда: `.venv/bin/python -B verification/r5_ci_gate_exits_recheck/reproduce_journal.py`.
Полные inputs/output — minimal_journal_witness.json. Последовательность:

1. Собственная fixture создаёт корректный frozen history и адресный B_RESET fault.
2. В посторонней FEED_CLEAR записи удаляется origin.guard; её F-ID согласованно
   пересчитан. Это негативная data mutation, не правка helper или repair candidate.
   Frozen history_valid остаётся TRUE, новый F-ID совпадает с digest(origin).
3. Свежий RESOURCES_READY record для fixed RESTORE_B_CLOSURE имеет FALSE, правильные
   scope/action/phase, integer revisions и covered interval. Прямой fixed frozen
   `_raw_value` подтверждает **FALSE / CURRENT_ASSUMED_RECORD** независимо от
   постороннего fault scan. Нельзя вывести FALSE из повреждения журнала; FALSE
   уже доказан отдельным текущим record.
4. Proof=null, scoped UNKNOWN ожидаем. Guard-wide scan frozen evidence_value
   встречает malformed foreign origin и выбрасывает KeyError. На :120–123
   wrapper присваивает UNKNOWN/MALFORMED_ENTRY_INPUT без сохранения отдельно
   доступного raw FALSE. Все ENTRY readers затронуты этим journal scan.
5. Общий finish получает уже потерянный факт: **INDETERMINATE вместо BLOCKED**.

| Независимое основание | Ожидалось | Получено |
|---|---|---|
| Валидный current resource FALSE + повреждённая чужая запись + malformed proof | scoped UNKNOWN; gate BLOCKED | scoped UNKNOWN; gate INDETERMINATE |
| То же для METHOD_SUPPORTED | BLOCKED | INDETERMINATE |
| Контрольные current TRUE/UNKNOWN при той же записи, без другого FALSE | INDETERMINATE | INDETERMINATE |

Повторено для proof=null, unknown target, missing guard и empty origin snapshot:
**8/8 отрицательных witnesses не сохраняют BLOCKED**, а 16 TRUE/UNKNOWN controls
не дают blanket BLOCKED. Ни один input/record/fault/history/rejected ID не меняется;
новых TRUE/physical permission нет. Это нарушение уже принятого R1 §1:
«Повреждение одного входа не уничтожает уже доступное независимое доказательство
запрета». R4 EVALUATION.md также объявляет current raw scope/phase/revision источником
доверия отдельно от журнала. Общий finish структурно исправен; потеря факта
происходит до него, внутри exception обработки оценки guard.

Ранее добавленный raw fallback :115–119 работает только в другой, не exception
ветви. Reviewer не меняет wrapper/helper и не подставляет сведения в caller.
Исправление/повторная приёмка остаются отдельным follow-up по R1.

## Frozen compatibility, readonly и сохранность

Compatibility не заявляется вне принятой snapshot/domain/type/history схемы.
В повторённом наборе 295 **46 IN_DOMAIN** сравнений сохраняют равные уровни
результатов с frozen policy. Строгий UNKNOWN вместо legacy TRUE на malformed
snapshot вне схемы остаётся намеренным ограничением, не дефектом.
Новый journal witness вне области legacy recovery; его основание — independently
valid current guard record и отдельный composite criterion R1. Не требуем
unconditional equality с бросающим исключение legacy fault scan.

Все 231 own calls проверяют deep equality и digest caller/proof/contract до/после;
physical_permission=False. Защищённые входы проверены SHA256/tree/blob comparison:
612 protected files, 7 frozen packages, 11 protected trees,17 input blobs,
44 bindings, четыре force variants, norm/helper, расчёты/CAD и **пять** старых
review packages неизменны. Только review files и четыре append/prepend metadata
файла меняются в рабочей ветке; прежнее содержимое сохранено целиком.
Нагрузки, диаметры, ходы не уменьшены. Bytes preservation не является пересчётом
физики, native interference/geometry или прочностью. Геометрических пар0;
strength/stability/native geometry/CAD rebuild/physical trials NOT_RUN.

## Выполненные команды

Из `/workspace/REV`, Python 3.12.14 `.venv/bin/python -B`; exact argv/env/exit codes
и raw stdout/stderr — commands.json. Probe exit0 означает завершённый capture,
а не PASS восьми несовпадений. Registry log оценивает consistency, не инженерную приёмку.

| После `.venv/bin/python -B` | Результат |
|---|---|
| `verification/r4_cycle_interfaces/proposal/check_package.py` | 3277 MATCH |
| `verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py` | 8 MATCH, readonly/fresh export repeat |
| `-m unittest discover -s verification/r4_cycle_interfaces/gate_correction -p 'test_*.py' -v` | 11 methods / 220 cases PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/snapshot_correction -p 'test_*.py' -v` | 11 methods / 118 cases PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v` | 6 methods / 244 re-export cases,36 comparisons PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v` | 6 methods / 411 cases PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v` | 7 B01/B02 methods PASS |
| `verification/r5_ci_gate_exits_recheck/repeat_prior.py` | 654/654,765/765,7/7,295/295; all19 identical input digests |
| `verification/r5_ci_gate_exits_recheck/independent_probe.py` | 231/223/8, all8exits; original minimal2/2 |
| `verification/r5_ci_gate_exits_recheck/reproduce_journal.py` | current FALSE confirmed, expected BLOCKED not met |
| `verification/r5_ci_gate_exits_recheck/verify_preservation.py` | protected inputs/old acts/source identity PASS |
| `scripts/check_registry.py --check-git` | registry.log |
| `git diff --check`; `git lfs fsck` | PASS |

Прежние probes выполнены без reuse в temporary materialized tracked copy;
оригинальные evidence не перезаписаны. Type/semantic/source mutations повторены
после fresh JSON/CSV/SVG export с новыми hashes. Runtime journal/proof fixtures
не имеют CSV/SVG exporter; их целостность проверена JSON digests и fixed definitions.

## Отдельные вердикты

- **B03:** OPEN / REJECT_WITH_BLOCKER. Прежние 19 вариаций и единая композиция
  исправлены, но independent current FALSE теряется при journal exception.
- **Стабильная документальная передача CYC-02/03:** NO-GO до устранения этой
  ветви и нового independent exact-C RECHECK. Ранее разрешённые R3 force-path
  studies — только WARNING с действующим claim/exact inputs; ни новая CAD-итерация,
  ни полнота силового пути, ни реальные команды этим актом не разрешаются.
- **B01/B02:** исходное документальное закрытие в границах C144941c сохранено;
  положительные и отрицательные регрессии PASS, область не расширена.

Пять предыдущих REJECT/SHA/evidence сохранены; текущий шестой, interface counter6,
отдельный material counter2. Q-R1-CI-SEMANTICS-ARBITRATION-01 REOPENED/P1 по
AGENT_PROTOCOL §6.1; следующий corrective ход BLOCKED до записанного R1 решения/плана.
Карточка R1_followup.md. **W02 OPEN/NO-GO, physical READY NO-GO, G1 OPEN**.
Архитектура/ТЗ/оборудование не утверждены.
