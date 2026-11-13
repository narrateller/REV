# B03 — prevalidation recovery snapshots

Основание ARB-R1-CI-SEMANTICS-03, точный commit
`39826eb2f5dbd1f83d81882022e6f59313ebe5d5`. SHA решения записан в капсуле,
main/owner/lease и 612 protected inputs проверены до кода. Checkpoint `b08f365`
содержит merge решения, аудит и [схему допуска](DOMAIN_SCHEMA.md), записанную
до реализации. Accepted PR45 owner `r4-linked-20261111`, lease до
`2026-11-14T00:13:12.404899+00:00` не переназначен и не продлён.

`proposal/recovery_snapshots.py` получает E и собственные ENTRY domains из
закреплённого contract; проверяет hash helper и typed equality переданного
contract. Поддержана пара RESTORE_B_CLOSURE / B_RESET_CONFIRMED. Неизвестная
пара не создаёт пустое E. E={B_CLOSURE}; current дополнительно требует только
домены собственных ENTRY. FEED/RETENTION не обязательны для этой ветви.
Extra-key policy и предел доверия к истории — DOMAIN_SCHEMA.md.

Проверяются origin/expected целевого fault, causal ancestors и используемых
ENTRY faults, proof origin/result, current и каждый ENTRY snapshot по своему
guard definition. Все counters — exact integer >=0. Expected следует из
immutable origin через адресную +1 revision_history. Пропуски не дописываются,
current не копируется в origin, нули не подставляются.

`semantic_minimum.recovery_assessment` разделяет validation/reasons,
compatibility_domain, policy_result, recovery_value и action_gate.
За пределами схемы recovery UNKNOWN, permissive legacy recover не вызывается
как доказательство. Независимые ENTRY/state/causal FALSE дают общий BLOCKED
даже при неполном proof. `recovery_value` сохраняет интерфейс scoped predicate.
Возвращённая helper копия нигде не применяется к caller.

Совместимость с frozen policy заявлена только IN_DOMAIN: структурно полные
карты с допустимыми типами/доменами/историей. В ней stale/wrong scope/revision
bindings и известные запреты остаются отрицательными. OUT_OF_DOMAIN — намеренное
ограничение: legacy TRUE на четырёх неполных снимках не является эталоном.
Legacy exceptions на malformed expected также записаны отдельно.
[Таблица](policy_comparison.md) классифицирует каждый случай;
[полные результаты](cases.json) содержат пути и причины отказа.

## Регрессии

Все 7 исходных incomplete cases R5 воспроизведены unchanged в изолированной
копии: до исправления 3/7 и четыре ложных TRUE; после исправления 7/7.
[Baseline](baseline_reproduction.json), [author replay](independent_replay.json).
Это авторское воспроизведение, независимый RECHECK нового C ещё требуется.
Оригинальные R5 scripts/results не перезаписаны. Поля C/session внутри unchanged
R5 output — исторические constants скрипта, не identity нового review. Новая
реализация определяется source hashes в checks.json и exact C следующей капсулы.

Новая матрица: 11 методов / 118 случаев. Покрывает независимые origin/expected,
empty/missing/foreign/extra maps, exact types, 0/1/large integers, подтверждённые
advances и повреждённые histories, minimum context, неиспользуемые domains,
каждый обязательный current domain, неприменимость старого EVENT_FRESH другого
operation_id, ENTRY/causal fault maps по их собственным
определениям, отрицательные gates с неполным proof, адресный положительный путь,
сохранение постороннего отказа и запрета штатной работы. Caller/proof/history/
rejected IDs неизменны; returned legacy copy оценивается отдельно.
Предыдущие fixtures не переписаны.

Команды и exit codes — [checks.json](checks.json). Из корня репозитория:

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/render_schemes.py --output-dir verification/r4_cycle_interfaces/proposal/exports
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/snapshot_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

Сохранены весь semantics_v1 (53 actions / 84 mode rules / 18 poses), типовые
исправления, B01/B02, frozen helper/contract, 44 расчётные привязки, четыре
силовых варианта, loads/calculations/CAD и payload/data exports. Меняется только
source manifest после явного переэкспорта. Побайтный аудит — preservation.json.
Все четыре REJECT/акта/findings/hashes сохранены, interface counter=4,
отдельный material counter=2. B03 OPEN до независимого R5 RECHECK exact C.
Stable documentary/CAD handoff NO-GO. W02/PLC/CAD/physical trials вне scope,
physical READY NO-GO, архитектура/ТЗ не утверждены, G1 OPEN.
