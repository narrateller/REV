# B03: bounded semantic admission всех OPEN записей

ARB-R1-CI-SEMANTICS-06 `a85e69f3a495176c614202a518be6784be8f3b31` прочитано
и записано в капсуле до кода; checkpoint `f7aa9d1`. Вход: Cb89854ad, седьмой
акт R5 4e52c395/H962a2a9e. Accepted PR45 owner/lease и main3a9258c сверены;
срок и owner не переоформлялись. Точный результат C — в следующей H-капсуле.
B03 OPEN, независимый RECHECK PENDING; автор не закрывает блокер.

`proposal/journal_admission.py` проверяет каждую запись до положительного
journal/recovery результата. Namespace берётся из всех pinned guard definitions,
а не только ENTRY текущего action. Полная [таблица admission](ADMISSION.md)
записана до реализации. Identity/status, guard/type, scope, own revision domains,
history и causal addresses дают APPLICABLE / NOT_APPLICABLE / UNCLASSIFIABLE.
Сканирование продолжается после ошибок; конечный graph walk проверяет реальные
ссылки и циклы. Target не выбирается из журнала. Исторические физические evidence
не переоцениваются в current scope, F-ID/history/maps не чинятся.

Совместимость с frozen policy ограничена confirmed history и семантически
классифицированными записями. RESOLVED вне используемой causal цепи остаётся под
прежней history policy. Для известного EVENT_FRESH другого operation, вне causal
ancestors, сохраняется прежний scope неиспользуемого snapshot: maps должны иметь
правильные типы и собственные domains, но полнота не нужна для доказанной
operation-specific non-applicability. Это не доказательство acknowledgement и не
исключение для неизвестного guard. Остальные OPEN требуют полного E и согласованной
цепи origin→expected; missing revisions не дополняются zero/current values.

При UNCLASSIFIABLE admission UNKNOWN, positive journal observations только
диагностические, scoped UNKNOWN/OUT_OF_DOMAIN, success helper не вызывается как
доказательство. Отдельно валидированные raw/own/state/addressed-causal FALSE
сохраняют BLOCKED через общий finish. UNKNOWN сам не создаёт FALSE. Known
неприменимый FEED не создаёт blanket BLOCKED; result и нижестоящий DEPENDENCY
не добавляются к собственным ENTRY. Caller/proof/origin/expected/history/rejected
IDs/pending observations readonly. Frozen helper copy не применяется к caller.

| Повтор исходных независимых R5 inputs автором | До | После |
|---|---:|---:|
| Matrix | 696/732 | 732/732 |
| Missing/null/known-FEED minimal | 2/3 | 3/3 |
| 36 erroneous TRUE observations | 36 | 0 |

[36 same-input сравнений](thirtysix_variations.json) сохраняют typed и ordered
input digests: 18 ordered inputs / 6 canonical maps / одна семантическая причина.
Это не 36 физических дефектов. Original R5 evidence/scripts/source pins сохранены.
`replay_r5.py` работает в изолированной копии; закреплённый minimal baseline runner
не изменён. Current reader передаёт текущему исходнику тот же immutable JSON.
Исторические C/session literals старых probes не обозначают новый C; фактические
source hashes — corrected_capture.json/checks.json, exact C — в H. Все повторы
здесь авторские, не независимое R5 принятие.

Новые 8 методов /417 controls: все fixed guards, типы tags, три позиции,
несколько unknown/known записей, scope/kind/variant/mode/basis, origin/expected
maps и strict revisions/history, статусы, causal links/direction/cycles; raw
TRUE/FALSE/UNKNOWN, stale/foreign controls и независимые own/state/causal FALSE.
Есть known-FEED positive, historical scope без current physical reproof,
confirmed RESOLVED policy, old operation scope и classifier exception. Проверяются
полный scan, caller readonly и отсутствие положительного recovery делегирования.

Прежние suites проходят с исходными ожиданиями: raw9methods/966cases,
gate11/220 и все8exits, snapshot11/118, type6/244+36, semantic6/411,
B01/B02 7methods. Прежние independent probes:654/654,765/765,7/7,295/295,
231/231;19+8witnesses имеют прежние input digests. Новый export сделан явно;
3277 package и8export checks проверяют содержание поз/guards/parents/modes/
расчётных ссылок и подмены, помимо воспроизводимости/hashes.

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/render_schemes.py --output-dir verification/r4_cycle_interfaces/proposal/exports
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/journal_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/raw_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/gate_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/snapshot_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B verification/r4_cycle_interfaces/journal_correction/replay_r5.py --prior --output-dir /tmp/rev-journal-recheck
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

`preservation.json`:612 protected inputs,15 полных деревьев прежних нормативов,
author regressions и семи независимых review packages, payload/data exports,
44bindings/4force variants/calculations/CAD byte-identical. Изменён manifest с
source hashes после экспорта; latest review index — только validity/stale_reason,
без переписывания REJECT/findings/reviewed C/hashes. Interface counter7/material2
сохранены. B03 OPEN,stable documentary/CAD handoff NO-GO; W02/PLC/physical READY
NO-GO,G1 OPEN. Архитектура/ТЗ не утверждены. CAD/rebuild/strength/geometry/
physical trials NOT_RUN.
