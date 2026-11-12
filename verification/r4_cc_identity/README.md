# B01 — адресные отказы и сохраняемая история operation ID

**Корректирующий кандидат по ARB-R1-CC-01**, точный SHA решения
`616135755d1b6cbaa09ae9800bad5af8bbc28aed` записан в капсулу до правки helper.
Parent T-r4-cycle-contract-01 BLOCKED до независимого RECHECK; корректирующая
итерация IN_REVIEW. Owner r4-linked-20261111, claim PR43, срок до **13 ноября
2026 21:16:39 МСК / 2026-11-13T18:16:39Z**, не продлён. Актуальная main при
входе — `8a82b30d185a10c71dbedbb8b581cf6b5162b1b7`.

[Входной акт](input_audit.md), input_audit.json;
[нормативная семантика](../r4_cycle_contract/fault_identity.md),
[условия каждого действия](../r4_cycle_contract/action_conditions.md).

Изменения B01:

- `faults[fault_id]` хранит отдельные неизменяемые origin (субъект/партия/эпоха,
  база/ревизия по применимости, guard/причина, операция, source evidence).
  RESOLVED сохраняет запись; чужое evidence не меняет оригинал.
- Recover требует явный fault_id и адрес именно этой записи. Причинные
  dependency records ссылаются на исходные fault IDs; сверка не очищает других.
- Все отклонённые operation IDs и записи причин накапливаются. A→B→C→A,
  смена view/эпохи, восстановление другого fault и export/restore их не забывают.
- Новый уникальный ID может начать аудит по его entry без общего READY.
  Подтверждение обработки отвергнутого запроса не делает старый ID допустимым.
- Evaluate привязан к хэшу исходного контекста, decide сохраняет отказ атомарно;
  observed facts/inventory refs не удаляются, W02 не реализован.

Фактические результаты в results.json: **205 проверок**, из них **26 исходных
R5 + 45 случаев RECHECK + 134 проверки плана R1**; несовпадений с корректными
ожиданиями **0**. Все три прежних расхождения исправлены. Дополнительно
check_documents.py сохраняет 59/59 условных примеров и две state traces;
исходные required guards обоих прежних C сохранены/усилены.

```sh
python3 -B verification/r4_cc_identity/verify.py --baseline-second-rejection > /tmp/rev-cc-old-recheck.json
python3 -B verification/r4_cc_identity/verify.py
python3 -B verification/r4_cycle_contract/check_documents.py
python3 -B scripts/check_registry.py --check-git
git diff --check
```

Baseline запускает **неизменённый** probe c56e494 на старых document blobs
`4f31ed6…` в temp-dir: 45 случаев / 3 старых ошибки, JSON точно совпал с R5 и R1.
Его exit 0 — воспроизведение старого отказа, не приёмка. Default verify использует
те же 26/45 корректных ожиданий; fixture ABI адаптирован к явным fault IDs,
original source и оба review не изменены. Ненулевой exit означает несовпадение.
replay_r5.py открыто содержит эту адаптацию; это авторский replay, не новый
независимый review. Командный успех, совпадение теста и permission_outcome различены.

Старый check_fix.py без опций явно направляет на новую suite для ABI v3;
прежние 154 guard-keyed fixtures/их результаты сохранены на C `4f31ed6…`, но
не выданы за новые независимые доказательства. Старый --baseline по исходному
отказу d99afb4 остаётся доступен.

Полные readonly/results/publication записи сохраняются рядом. Проверяющие
команды не обновляют контракт/evidence; публикация отчётов — отдельный явный
redirect. Расчёты, CAD, 17 входов/11 защищённых деревьев, ledger_examples.md,
resources.json и пакеты обоих R5/R1 неизменны. Diff documentary helper/fixture
checker входит в предмет нового RECHECK, существующие численные/CAD tools нет.

[История двух отказов](history.md), [запрос RECHECK](recheck_request.md).
consecutive_rejections=2 не сброшен. **B01 OPEN**, W01 CLOSED только документально
на ранее проверенном `4f31ed6…`, W02 OPEN и вне итерации. CYC-02/03 NO-GO как
стабильный вход до независимого акта; CYC/R5-CYCLE warnings/G1 OPEN. Реальные
параметры/физика UNKNOWN, B opening/L-путь/полный физический цикл INDETERMINATE.
Архитектура/ТЗ не утверждены, solver/CAD/rebuild/physical tests NOT_RUN.
Точный C результата — в следующем H/капсуле.
