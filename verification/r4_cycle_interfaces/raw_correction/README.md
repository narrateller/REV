# B03 — независимый raw FALSE при journal-reader exception

Основание ARB-R1-CI-SEMANTICS-05 на
`3aa5ee100f57aa75315d429afef38f8a982b1afc`. SHA решения записан в капсуле
до кода; checkpoint `a76e298` содержит input audit и [план](EVALUATION.md).
Main3a9258c, accepted PR45 owner r4-linked-20261111 и lease до 14 ноября
03:13 МСК (`2026-11-14T00:13:12.404899+00:00`) сверены, не изменены/не продлены.
Входной шестой акт R5 `18e5af1dae177cdfcb24951d3b36c2fd43395421`,
H `f209ed23748652b20afc4a9a91931f73b10ab794` сохранены предками.

## Два источника own assessment

Для каждого fixed ENTRY guard `_raw_value` проверяет current record отдельно
и до journal-dependent `evidence_value`. Scope/action/guard/phase, strict relevant
revisions, provenance/method/source и covered operation interval проверяет
неизменённый pinned frozen helper. Буквальный value=FALSE не является основанием.

`raw_evidence[g]` хранит value/reason/status VALIDATED, UNCONFIRMED или EXCEPTION.
`journal_evidence[g]` отдельно хранит value/reason/status EVALUATED либо EXCEPTION
и тип ошибки. Exception journal reader оставляет его значение UNKNOWN и явную
validation reason, но не стирает ранее валидированный raw FALSE.
Own entry_values/reasons/sources, state/causal/scoped values и общий action_gate
сохраняют отдельный смысл; все восемь assessment exits по-прежнему идут в finish.

| Raw current | Journal reader | Own value при exception | Gate без другого FALSE |
|---|---|---|---|
| FALSE, все fixed checks пройдены | EXCEPTION / UNKNOWN | FALSE | BLOCKED |
| TRUE, все fixed checks пройдены | EXCEPTION / UNKNOWN | UNKNOWN | INDETERMINATE |
| UNKNOWN либо stale/foreign/invalid | EXCEPTION / UNKNOWN | UNKNOWN | INDETERMINATE |
| raw exception | оба основания недоступны | UNKNOWN | INDETERMINATE |
| raw exception | подтверждённый own journal FALSE | FALSE сохранён | BLOCKED |

Другой достоверный own/state/addressed-causal FALSE сохраняет BLOCKED независимо
от отказа конкретного raw/journal reader. Raw TRUE не доказывает отсутствие latch,
успешный recovery или READY. Нормальная frozen precedence в IN_DOMAIN сохранена;
исправление не вводит unconditional policy equality для повреждённых журналов.

Caller/proof/contract, immutable origin, expected, history, rejected IDs и pending
observations readonly. Foreign fault не удаляется/не чинится, F-ID не пересчитывается,
target/domains/revisions не подставляются; helper copy не применяется к caller.

## Воспроизведение и регрессии

До кода unchanged R5 matrix дал 231/223/8, minimal journal witness — INDETERMINATE
при independently validated raw FALSE. baseline_capture.json хранит source hashes
и восемь IDs; baseline_minimal.json — полный исходный witness. Полная baseline
matrix остаётся также в исходном акте и `verification/r1_ci_journal_arbitration/`.
После правки unchanged matrix даёт 231/231, тот же minimal input — BLOCKED при
scoped UNKNOWN. [Восемь сравнений](eight_variations.json) проверяют равенство typed
input digests до/после. Исторические C/session literals старых outputs не являются
identity нового C: actual source hashes — corrected_capture.json и checks.json,
exact C — в следующей H-капсуле. Это author replay, не новый независимый R5 акт.

Minimal runner R5 закреплён на старом source C3060dbf и не ослаблялся: после
правки отдельный reader передаёт текущему коду неизменённый JSON input. Replay
работает в изолированной копии, original R5 evidence не перезаписывается.

Новые 9 методов / 966 случаев: все own guards, два source guards из восьми
вариаций, TRUE/FALSE/UNKNOWN, пять видов повреждения и три позиции foreign fault;
stale/foreign/missing scope/action/guard/phase/revisions/provenance/method/interval,
bool/float counters и literal-value aliases; каждый invalid control с другим
валидным FALSE и без него. Есть два own условия, raw exceptions пяти типов,
подтверждённый journal FALSE при raw exception, state/causal/context failures,
полностью допустимый proof с broken journal без делегирования success;
положительный recovery 0/1/large, отсутствие unused domains, чужой FEED fault и
ordinary WORK запрет. Frozen `_raw_value` — независимый oracle validation;
ожидаемый gate задаёт truth table R1. Pending observations непустые, проверяются
deep equality, typed digests и JSON order до/после вызова.

Прежние gate220/8 exits, snapshot118, type244/36, semantic411 и B01/B02 fixtures
сохраняются без изменения; также повторяются independent654/765/incomplete7/
prior295 и воспроизведение норматива. Fresh export/content/source checks и
readonly repeat — в checks.json с командами/exit codes/evidence hashes.

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/render_schemes.py --output-dir verification/r4_cycle_interfaces/proposal/exports
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/raw_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/gate_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/snapshot_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B verification/r4_cycle_interfaces/raw_correction/replay_r5.py --prior --output-dir /tmp/rev-raw-recheck
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

Сохранность — preservation.json:612 protected inputs, frozen helper/contract,
весь norm53/84/18,44bindings/4variants, расчёты/CAD, payload/data exports и все
шесть актов/review packages. Меняется source hash manifest после переэкспорта.
В последнем review изменён только artifact validity/stale_reason; REJECT,
findings, reviewed C и hashes сохранены. Interface counter6/material2 не сброшены.
B03 OPEN до независимого exact-C RECHECK, stable documentary/CAD handoff NO-GO.
W02/PLC/physical READY NO-GO, G1 OPEN; архитектура/ТЗ не утверждены.
CAD/rebuild/strength/geometry/physical trials NOT_RUN.
