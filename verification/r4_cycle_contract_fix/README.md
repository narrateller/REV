# Коррекция R5-CC-B01 / W01 — кандидат RECHECK

Вход: `3cf32daef67a91f393b808adb0dc07ba4c73cac2`, независимый акт
`d99afb4c3231d641d4a4921f39987264ce5ffc23`. Claim T-r4-cycle-contract-01 принят
PR #43, owner r4-linked-20261111, lease до 13 ноября 2026 21:16:39 МСК
(2026-11-13T18:16:39Z), не продлён. [Входной акт](input_audit.md), input_audit.json.

[Причины десяти старых расхождений](causes.md),
[полный контракт разрешений](../r4_cycle_contract/permissions.md),
[условия каждого действия](../r4_cycle_contract/action_conditions.md).
Новый полный SHA фиксируется следующим H в NEXT_MODEL.md/капсуле.

Изменения:

- READY bindings обязательны в entry зависимых действий; receiver/resource/
  B closure UNKNOWN не обходятся. Условия всех движений, включая возврат/refill,
  требуют текущего ресурса; возврат первого столба A требует удержания/реакции.
- Start и completion разделены. Reset B не требует своей достигнутой цели на
  старте, но дальнейший press требует подтверждённого восстановленного состояния.
- Evidence имеет scope/epoch/action/phase/версию субъекта; старое TRUE не
  переносится через изменение. Известные дефекты сохраняются до адресного
  восстановления. Аудит/восстановление имеют собственные условия без общего READY.
- Фактическое неразрешённое поступление сохраняется для сверки с entity/dose/
  mass_record, не создаёт обычное разрешение и не стирает старый inventory.

Фактические результаты в results.json: **26/26** исходных случаев R5 соответствуют
ожиданиям, **10 → 0 расхождений**. Всего **154** логических проверок: 26 R5,
45 сочетаний FALSE/UNKNOWN/TRUE, 83 scope/freshness/propagation/recovery/fact checks.
Старые 59 примеров и две state traces по-прежнему соответствуют явно ASSUMED
условиям. Это не entity-level материальный журнал (W02 OPEN), не доказательство
истинности guards и не физическая валидация. Командный успех и совпадение
ожиданий отделены от permission_outcome отдельных действий.

```sh
python3 -B verification/r4_cycle_contract_fix/check_fix.py --baseline > /tmp/rev-cycle-baseline.json
python3 -B verification/r4_cycle_contract_fix/check_fix.py
python3 -B verification/r4_cycle_contract/check_documents.py
python3 -B scripts/check_registry.py --check-git
git diff --check
```

`--baseline` копирует только старые document blobs в temp-dir и запускает **точный
неизменённый** R5 probe; baseline_probe.json совпал с independent_results.json R5.
Его успех фиксирует **старые ошибки**, не приёмку. Без опций runner проверяет
исправленную редакцию и возвращает nonzero при несовпадении actual/expected.
Default проверки read-only; результаты сохраняются отдельным явным redirect,
не перегенерируют проверяемый контракт. integrity_checks.json фиксирует повтор.

Исходный акт/probe/результаты R5 неизменны и включены полным Git-предком.
Индекс validity старого review помечен STALE из-за новой редакции, его REJECT/
findings/проверенный C/хэши не изменены; требуется новый независимый акт.
[История](history.md); [запрос независимого RECHECK](recheck_request.md).
Старые результаты/хэши редакции 1 доступны на её C; текущие результаты не
переименовывают старый REJECT в PASS. Existing CAD/calculation/tool modules,
все 11 protected trees/17 sources и CAD-кандидат 3591a5f неизменны.

R5-CC-B01/W01/W02, CYC-01…09, R5-CYCLE-W01/W02 и G1 **OPEN**. Архитектура/ТЗ/
оборудование не утверждены. Реальная физика/параметры UNKNOWN, открытие B,
L-сервис и полный физический цикл INDETERMINATE. Solver/CAD/rebuild/physical
tests NOT_RUN. Независимый RECHECK NOT_RUN.
