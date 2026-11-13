# REV-R5-CI-RAW-SOURCES-RECHECK-01-001

**B03 OPEN — REJECT_WITH_BLOCKER. Стабильная документальная передача CYC-02/03 — NO-GO.**
Journal-witness и восемь прежних вариаций исправлены: validated current FALSE
сохраняет BLOCKED при reader exception. Но ранее не проверенная предпосылка
положительного journal admission остаётся неверной: OPEN запись с null/неверным
типом/неизвестным guard молча пропускается, и при raw TRUE получается scoped TRUE
и ALLOWED_ASSUMED. Это не регрессия исправленного raw fallback и не физическое разрешение.

R5 / Codex / session **r5-ci-raw-sources-20261113**, прямое поручение пользователя,
13 ноября 2026, МСК. Reviewer не автор candidate/helper/норматива. Авторские
сессии: r4-linked-20261111,r4-cyc-fix-20261113,r4-b03-semantics-20261113,
r4-b03-types-20261113,r4-b03-snapshots-20261113,r4-b03-gates-20261113,
r4-b03-raw-20261113. Организационная независимость не удостоверяется.
Main/owner/lease не присваивались, merge в main не выполнялся.

| Вход | Точный SHA |
|---|---|
| Проверенный C | **b89854ad709bcb5c2991376bed41bf2f73acef82** |
| Эстафета H | **ce1ad73aae7a5700203103c14290375cc519662b** |
| R1 ARB-R1-CI-SEMANTICS-05 | **3aa5ee100f57aa75315d429afef38f8a982b1afc** |
| Шестой REJECT | 18e5af1dae177cdfcb24951d3b36c2fd43395421 |
| Пятый REJECT | 88a34f8b7d2d6dbf236101f207e206efb0e3c747 |
| Четвёртый REJECT | 0ff3c8f4502ea29c712bf1f41e223f172c5a21c7 |
| Третий REJECT | 3d317b32596884cc60d9d42675924b88fcb29bf0 |
| Второй REJECT | 5fb731182a2bdf6b11246558eca58962e48568d9 |
| Первый OUTPUT/REJECT | 13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2 |
| Frozen contract/helper | 0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed |

Входы/R1/шесть актов — предки H. Все166файлов интерфейсного пакета совпадают
в C/H/рабочем дереве. SHA акта указывается следующей H-капсулой без самоссылки.

## Воспроизведённое исправление

Старый minimal journal input повторён без изменения typed digest: общий BLOCKED,
scoped UNKNOWN, independently validated raw FALSE. Старый runner закреплён на
source3060dbf; его pin не ослаблялся. Собственный reader передаёт immutable JSON
inputs текущему C. Неизменённая матрица **231/231**, все **8** прежних failed inputs
имеют прежние digests и теперь BLOCKED/UNKNOWN (eight_variations.json).

Прежние independent probes в временной materialized tracked копии, без reuse:
**654/654,765/765,incomplete7/7,gate295/295**. Все19 ранних gate-вариаций сохраняют
прежние typed input digests и BLOCKED. Норматив53действия/84режима/18поз воспроизведён
из fixed Git blobs; minimum.json SHA256
`b1c13c18c408120ae66d4995eac706e8dbf5842f35976494efb682c74e64d3df`.
Исторические C/session literals unchanged scripts не объявляются identity нового
review; actual C и source hashes зафиксированы authority_and_prior.json.
Оригинальные пакеты evidence не перезаписаны.

## Независимая проверка двух источников

Oracle — R1 truth table, fixed frozen `_raw_value`, guard/action definitions C0c4eb5d,
а не record.value или результат mutable journal scan. Рабочие helper/contract
сверены с fixed Git blobs. Собственная fixture взята из прежнего независимого R5,
авторские fixture functions для ожиданий не импортируются.

**732 case records:696 совпадений,36 FAIL одного класса.** Все8assessment exits
исполнены через common finish. Покрытие строк используется только как coverage,
не как поведенческий oracle.

| Группа | Cases | Результат |
|---|---:|---|
| прежний minimal input | 1 | PASS |
| реальные reader errors:5damage types×3positions×2guards×3truths×5proof forms | 450 | PASS |
| семантически неизвестные OPEN guard tags | 108 | 72PASS/36false TRUE |
| stale/foreign/missing/неполные raw records с другим FALSE и без него | 56 | PASS |
| сочетания двух own условий | 27 | PASS |
| исключения raw/journal/both,5exception types,other/latch/state/causal controls | 75 | PASS |
| independent state/causal при реальной journal error | 2 | PASS |
| недоступный context/definitions и policy exception | 7 | PASS |
| positive recovery/minimal/advances/unrelated fault | 6 | PASS |

Подтверждено: validated current raw FALSE сохраняется при journal exception;
stale/foreign/wrong-action/guard/phase/revision/interval/source/method/id/неполный
record не превращается в доказанный FALSE. Без другого trusted FALSE gate
INDETERMINATE, при наличии другого — BLOCKED. Raw exception не создаёт FALSE;
достоверный journal latch при доступном reader сохраняется, как и отдельные
state/адресные causal prohibitions. Ошибки источников изолируются; raw TRUE/UNKNOWN
при **обнаруженной** reader error не разрешает recovery. Ни source-reader injection,
ни обычные повреждения не меняют caller/proof/contract/pending observations/
origin/expected/history/rejected IDs. Инъекции исключений только in-memory,
файлы helper/candidate не меняются; новые false TRUE ниже воспроизводятся без injection.

## Остаток B03: unsupported OPEN journal tag объявляется допустимым

Команда: `.venv/bin/python -B verification/r5_ci_raw_sources_recheck/reproduce_guard_tag.py`.
Полные три контрольных inputs/output — minimal_guard_tag_witness.json.

| Та же OPEN запись, свежие raw records и допустимый адресный proof | Ожидалось | Получено |
|---|---|---|
| `origin.guard` отсутствует | UNKNOWN/INDETERMINATE | UNKNOWN/INDETERMINATE |
| `origin.guard=null` | UNKNOWN/INDETERMINATE | **TRUE/ALLOWED_ASSUMED**, IN_DOMAIN |
| `origin.guard=FEED_CLEAR`, корректная известная посторонняя запись | TRUE/ALLOWED_ASSUMED | TRUE/ALLOWED_ASSUMED |

Во всех случаях F-ID согласован с изменённым origin, frozen history_valid=True,
raw own records независимо валидны и TRUE. Сам history_valid проверяет часть
структуры/целостность, но **не** распознаваемость guard. Поддерживаемый набор guard
ID взят из неизменяемого contract; null/bool/integer/array/object/неизвестная строка
не являются его определениями. По такой OPEN записи невозможно установить,
какое обязательное условие она удерживает. Нельзя доказать её неприменимость
одним неравенством неизвестного tag именам own guards.

Негативная fixture создана из FEED record, но checker не получает знания об этом
происхождении после подмены tag. Subject kind INTERFACE_OR_ASSEMBLY_STATE также
общий с несколькими own guards; он не делает запись доказанно посторонней.
Это **UNKNOWN**, не придуманное FALSE и не требование блокировать любой чужой fault.
Положительный known-FEED control доказывает требуемую границу scope.

Одинаковая ошибка подтверждена для guard=null/False/0/[]/{}/unsupported-string,
в first/middle/last позиции. Frozen `open_faults` сравнивает guard с текущим g и
молча пропускает эти значения. Journal readers возвращают EVALUATED/TRUE,
semantic validation отбирает только уже распознанные target/ENTRY/causal faults,
и unsupported запись не попадает в check_fault. Candidate заявляет IN_DOMAIN,
делегирует permissive helper и возвращает TRUE. Проверки raw сами по себе
корректны; **не доказано отсутствие применимого latched fault**.

36 FAIL records —6tags×3positions×2наблюдаемых own guards, один semantic escape,
а не36разных дефектов. При всех raw TRUE выбор наблюдаемого guard не меняет input:
есть18разных serialized inputs и6canonical typed maps (порядок journal entries
различается). Ordered/canonical digests сохранены отдельно. Случаи current FALSE
и UNKNOWN при этих tags не объявляются новыми дефектами: mandatory FALSE блокирует,
UNKNOWN остаётся неопределённым. Новое нарушение — положительный результат на
неразрешимом OPEN tag. Все исходные caller faults остаются OPEN; wrapper не
применяет helper copy. TRUE здесь документальный, не выполненное движение.

Основание ожидания: R1 §3 запрещает raw TRUE доказывать отсутствие latch/успешный
recovery при недостоверном journal; §5 прямо отделяет согласованный digest от
семантической полноты. Совпадение с legacy helper на malformed tag не является
compatibility-доказательством: заявленная допустимая область требует поддержанных
fixed definitions. Мы не требуем полного journal repair/материального engine и
не расширяем нормальную frozen precedence; нужно безопасное positive admission
для OPEN записи, которую нельзя классифицировать. Область этого admission и
исправление переданы R1 (R1_followup.md), без правки helper reviewer-ом.

## Воспроизведённые авторские проверки

Из `/workspace/REV`, Python3.12.14 `.venv/bin/python -B`; exact argv/env, exit codes,
raw stdout/stderr — commands.json. Exit0 probe означает завершённый capture,
не PASS36несовпадений. Все retained mutations повторены с fresh JSON/CSV/SVG exports
и source/export hashes; runtime journal fixtures проверяются JSON/digest отдельно.

| После `.venv/bin/python -B` | Факт |
|---|---|
| `verification/r4_cycle_interfaces/proposal/check_package.py` | 3277MATCH |
| `verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py` | 8MATCH, fresh export/readonly repeat |
| `-m unittest discover -s verification/r4_cycle_interfaces/raw_correction -p 'test_*.py' -v` | 9methods/966cases PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/gate_correction -p 'test_*.py' -v` | 11methods/220cases PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/snapshot_correction -p 'test_*.py' -v` | 11methods/118cases PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v` | 6methods/244fresh-export cases/36comparisons PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v` | 6methods/411cases PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v` | 7B01/B02methods PASS |
| `verification/r5_ci_raw_sources_recheck/repeat_prior.py` | 654/765/7/295/231 allpass,19+8sameinputs |
| `verification/r5_ci_raw_sources_recheck/independent_probe.py` | 732/696/36,all8exits |
| `verification/r5_ci_raw_sources_recheck/reproduce_guard_tag.py` | controls2/3;null guard false TRUE |
| `verification/r5_ci_raw_sources_recheck/verify_preservation.py` | protected inputs/reviews/source PASS |
| `scripts/check_registry.py --check-git` | registry.log;consistency,not engineering acceptance |
| `git diff --check`;`git lfs fsck` | PASS |

## Сохранность и вердикты

SHA256/tree/blob checks:612protected files,7frozen packages,11protected trees,
17input blobs,44bindings,4force variants,norm/helper/calculations/CAD и все6старых
review packages неизменны. Нагрузки/диаметры/ходы не уменьшены. Protected bytes
не являются strength/native geometry/interference проверкой или пересчётом
физики. Геометрических пар0;strength/stability/native geometry/CAD rebuild/
physical trials NOT_RUN. Caller/proof/contract проверены deep/ordered equality и
typed digests во всех732вызовах;physical_permission=False, pending observations
непустые в reader-error matrix и сохранены.

- **B03:** OPEN/REJECT_WITH_BLOCKER. Узкое исправление current raw FALSE при
  исключении подтверждено; unsupported OPEN tag даёт необоснованный TRUE.
- **Стабильная документальная передача CYC-02/03:** NO-GO до уточнения/устранения
  positive journal-admission gap и нового independent exact-C RECHECK. Ранее
  разрешённые R3 force-path studies — только WARNING/current claim/exact inputs;
  ни новая CAD-итерация, ни полнота силового пути/прочность/геометрия этим не приняты.
- **B01/B02:** прежнее документальное закрытие C144941c сохранено с регрессиями,
  область не расширяется до W02 или physical READY.

История6REJECT/SHA/evidence сохранена; текущий седьмой,interface counter7,
отдельный material counter2. Q-R1-CI-SEMANTICS-ARBITRATION-01 REOPENED/P1 по
AGENT_PROTOCOL§6.1;next correction BLOCKED до записанного R1 решения/плана.
**W02 OPEN/NO-GO,physical READY NO-GO,G1 OPEN**. Архитектура/ТЗ не утверждены.
