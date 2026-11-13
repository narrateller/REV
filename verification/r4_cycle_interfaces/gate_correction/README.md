# B03 — единая композиция recovery gate

Основание ARB-R1-CI-SEMANTICS-04 на
`60eeddce71c9440a2fa08f7acbe6f1121c974b29`. SHA записан в капсуле,
main/owner/lease и входы сверены до кода. Checkpoint `827bb37` содержит merge
решения, input_audit.json и [план оценки](EVALUATION.md).
Main `3a9258c57e4bc15d6de98f1d17e8412ad6e8899a`, accepted PR45 owner
`r4-linked-20261111`, lease до 14 ноября 03:13 МСК
(`2026-11-14T00:13:12.404899+00:00`) не изменены/не продлены.
Входной пятый акт R5 `88a34f8b7d2d6dbf236101f207e206efb0e3c747`,
H `f0c9fa423cf50c776db7f6355af8a0f06f7e9306` сохранены предками.

## Оценка и доверие к источникам

В `proposal/recovery_snapshots.py` все восемь путей выхода проходят через
один finish, доступный до schema/definition dispatch. Он сводит собственный
ENTRY/state, адресный causal и scoped recovery: обязательный FALSE даёт BLOCKED,
при отсутствии FALSE необходимый UNKNOWN даёт INDETERMINATE; полный положительный
путь даёт только документальный ALLOWED_ASSUMED. Physical permission всегда false.

Форма proof и его action/guard не выбирают другое действие: оценивается fixed
RESTORE_B_CLOSURE. Достоверные собственные основания оцениваются до proof schema:

- current record проходит неизменённые per-guard scope/phase/interval/revision
  проверки frozen evidence policy; повреждение другого источника его не стирает;
- latched own запрет требует подтверждённой истории и адресной записи нужного
  собственного guard. EVENT_FRESH относится к текущему operation_id;
- state/mode оцениваются по fixed enum и подтверждённому контексту. UNKNOWN,
  missing и unsupported state/mode не объявляются доказанным неправильным состоянием;
- permanent rejected-operation запрет требует подтверждённой истории;
- причины, entry_sources, history_confirmed, state_value и causal_sources
  возвращаются отдельно от validation, policy_result и action_gate.

Causal constraints вычисляются до проверки proof action/guard. Нужен явно
предъявленный существующий F-ID, совпадающий с immutable origin digest,
поддержанный B_RESET guard, complete typed identity scope, подтверждённая history
и адресные causal IDs. По fixed policy OPEN parent — обязательный запрет,
RESOLVED подтверждает это условие; отсутствующий/неподтверждённый parent — UNKNOWN.
Без адреса либо для чужого guard causal UNKNOWN; другие faults не сканируются
для подстановки target. Не-object proof не создаёт target из context.

Snapshot admission успеха и адресность записанного запрета разделены. Неполные
origin/expected/proof maps не допускают TRUE и не снимают отказ, но сами по себе
не стирают известный OPEN/latched запрет из подтверждённой адресной истории.
Это сохраняет прежние 118 fixtures без изменения ожиданий. Missing snapshots
не дописываются, current/zero не подставляются, origin/F-ID не чинятся.

Unsupported definitions/context и исключения дают диагностированный UNKNOWN,
а уже доступные независимые достоверные запреты сохраняются общим finish.
Исключение frozen recover также проходит finish; его proposed copy не применяется
к caller. Input/proof/fault/origin/expected/history/rejected IDs readonly.

Область frozen compatibility прежняя: IN_DOMAIN из snapshot DOMAIN_SCHEMA.md.
В ней одинаковые уровни результата сравниваются с frozen policy; equality для
malformed inputs не заявляется. OUT_OF_DOMAIN критерий known FALSE dominance
действует независимо от того, был ли scoped policy вызван.

## Покрытие и воспроизведение

До исправления unchanged R5 probe воспроизвёл 295/276/19 и minimal runner 0/2.
baseline_capture.json содержит точные 19 IDs и source hashes; полный прежний
matrix сохранён в исходном акте и `verification/r1_ci_gate_arbitration/`.
После исправления unchanged matrix даёт 295/295; immutable JSON двух minimal
witnesses дают 2/2. R5 minimal runner закреплён на старом C и намеренно не
ослаблялся: новые входы оценивает отдельный minimal reader в replay_r5.py.
Исторические C/session literals старых outputs не являются identity нового C.
Результаты — corrected_capture.json, corrected_matrix.json, corrected_minimal.json.
Это авторский replay; новый независимый R5 RECHECK остаётся PENDING.

Новые 11 unittest methods / 220 cases проверяют whole-proof types × own
TRUE/FALSE/UNKNOWN, latched/resource/state и два своих условия, OPEN/RESOLVED/
UNKNOWN/missing parents × missing/foreign action/guard, отсутствие и чужой target,
snapshot/field order, source confidence, положительные 0/1/large integer и unused
domains, чужой FEED fault и запрет обычной WORK. Injected definition/ENTRY/history/
policy exceptions проверяют отказ источников; файлы frozen helper не меняются.
cases.json сохраняет typed input digests, оценки и return line каждого случая;
ветви сведены в [exit_coverage.md](exit_coverage.md). Все восемь exits реально
выполнены, ни один не возвращает исходный result в обход finish.

Прежние fixtures сохранены: snapshot118, type244/36 comparisons, semantic411
(шесть подмен R5 и другие стадии), семь методов B01/B02. В изолированной копии
повторяются также independent probes654/765/incomplete7 и builder норматива;
original evidence не перезаписывается. Проверки exports включают явный re-export,
content semantics и readonly/repeat. Команды, exit codes и hashes — checks.json.

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/render_schemes.py --output-dir verification/r4_cycle_interfaces/proposal/exports
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/gate_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/snapshot_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B verification/r4_cycle_interfaces/gate_correction/replay_r5.py --prior --output-dir /tmp/rev-gate-recheck
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

preservation.json проверяет все 612 protected inputs, frozen helper/contract,
весь minimum53/84/18, 44 bindings, четыре силовых варианта, loads/calculations/CAD,
payload/data exports и пять исходных актов/evidence. После переэкспорта меняется
только source hash manifest. Последний review отмечен STALE только для новой
версии artifacts; его REJECT/findings/reviewed SHA/hashes остаются историческими.
interface counter5/material counter2 не обнулены. B03 OPEN до независимого
exact-C RECHECK, stable documentary/CAD handoff NO-GO. W02/PLC/physical READY
NO-GO, G1 OPEN. Архитектура/ТЗ не утверждены, CAD/rebuild/physical trials NOT_RUN.
