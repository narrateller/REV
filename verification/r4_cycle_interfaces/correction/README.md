# Исправление R5-CI-B01/B02/B03 — кандидат RECHECK

Прямое поручение пользователя: исправить C `ed8272ce6ebc2047bb0d896db5951d02c42d5208`
по акту R5 `13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2`.
Исполнитель R4 / Codex / `r4-cyc-fix-20261113`, корректирующее продолжение
принятого PR45 claim `r4-linked-20261111`, без смены owner, продления или merge.
Main `3a9258c57e4bc15d6de98f1d17e8412ad6e8899a`; срок до
2026-11-14T00:13:12.404899+00:00 (14 ноября 03:13 МСК). Аудит — input_audit.json.
Из-за существующей локальной ветки `work` используется префикс `work-r4/`.

**R5-CI-B01/B02/B03 OPEN до независимого RECHECK.** Исходный REJECT и все
его evidence/probe сохранены. Старый helper C0c4eb5d и прежние два отказа
материального контракта не пересматриваются; consecutive_rejections=2 сохранён.

## B01: одна адресная передача, явная граница commit

Все пять LOAD/REFILL определяют D0→D1→D0. Режимы и исходная/конечная поза
каждого тела каждой стадии записаны в permissions.json, pose_endpoints и полной
CSV; mode_parent_bindings задаёт допустимого родителя отдельно для режима.

1. FEED-OPEN — собственная подготовка G1→G0 при D0 и выбранном P0/PF.
   Полный START родителя ещё не выдан; все необходимые собственные условия
   и текущие инварианты будущего родителя обязательны.
2. DOSE-DELIVER — после полного START LOAD/REFILL движение D0→D1 при G0.
   D1 подтверждает только позу; parent ещё не завершён.
3. FILL-CONFIRM — удержание D1/G0/того же P. Адресное наблюдение завершённой
   передачи и DOSE_DELIVERED для **той же** dose_id, material_id, subject,
   batch, epoch, basis, режима, LOAD и transfer operation. Команда, таймер,
   чужая/старая квитанция не подтверждают передачу. FALSE блокирует; UNKNOWN
   оставляет ожидание/INDETERMINATE и не разрешает возврат или отсечение.
4. DOSER-RETURN — только с валидным FILL_COMPLETE, полным безопасным sweep,
   удержанием материала и ресурсом: D1→D0. Исторический D1 не обязан оставаться
   текущей позой; локальный конец стадии не завершает родителя автоматически.
5. Parent commit — после возврата, при текущем D0, со всеми исходными completion
   guards и тем же историческим FILL_COMPLETE/DOSE_DELIVERED. Учёт/масса не
   фиксируются раньше этой границы. Источник свидетельства не переписывается.
6. FEED-ISOLATE — собственная подготовка G0→G1 перед GATHER/COMPACT. Нужны
   явный completed_load_ref, FILL_COMPLETE и LOAD_COMMITTED_CURRENT,
   FEEDER_SAFE (D0, удержание, полный D/G sweep и P_FEED_CLEAR). Текущий G1
   не заменяет подтверждённую изоляцию под материалом/нагрузкой. PRESS начинает
   только со свежим ISOLATION_CONFIRMED и полным набором собственных условий.

cycle_protocol.json и fill_binding содержат машинно-читаемую адресацию.
LOAD commit исходного helper меняет MATERIAL и FEED. Поэтому successor record
после commit явно связывает receipt ID, исходные ревизии, ту же операцию/дозу
и новые MATERIAL/FEED +1. Остальные ревизии должны совпадать. Любое дополнительное
изменение/неподтверждённый переход требует нового доказательства, а не автоматического
переноса TRUE. Новый REFILL даже того же batch/остатка требует новой дозы и операции.
Историческая квитанция не означает текущего D1 и не разрешает будущий путь сама.

A APPROACH/WORK/HOLD-UNLOAD теперь только A_STEADY согласно их родителям.
Частичный startup PG_A и возврат PG_A→PF не подменены полным рабочим ходом.

## B02: восстановление closure и история — отдельные операции

STOP-CLOSE/RELOCK привязаны к B-RESET / RESTORE_B_CLOSURE и адресному closure
fault ID. У них отсутствует общий DEPENDENCY_VALID; неизменённые необходимые
инварианты, receipt, ledger, текущие ресурсы/feedback, сохранение остатка и
RESET_SWEEP_CLEAR обязательны. Материальный/сервисный отказ, нарушающий любое
из этих условий, блокирует и восстановительное движение. Это не общий обход
неизвестных причин отказа. Позы stop/lock и STOP_CLOSED_CURRENT/LOCK_CLOSED_CURRENT
явные; RELOCK требует завершённого STOP-CLOSE.

Только актуальный адресный результат B_RESET_CONFIRMED разрешает targeted
recovery closure fault. Это не очищает DEPENDENCY или другие fault IDs. Затем
отдельный RECONCILE_HISTORY проверяет каждую причинную цепочку; при неустранённой
материальной/сервисной причине сверка отклоняется. Новый NEXT проверяет все свои
условия, включая DEPENDENCY_VALID. Старые rejected operation IDs не разрешаются
повторно. Никакой автоматической выдачи общего READY нет.

## B03: семантика после законного re-export

check_package.py использует отдельный document_semantics.py: типизированные
позы и endpoints, непрерывность DOSE→CONFIRM→RETURN, точные mode/parent-связи,
непотерянные инварианты, обязательные guards, scope квитанций и commit boundary,
все 22 scenario refs каждого действия и phase t/v refs с ID/revision/source/value/unit,
8 pose source refs, адресность recovery и отсутствие циклического dependency.
Проверяется полное содержимое CSV (все поля), Markdown и SVG, включая видимый
текст и встроенные данные; совпадение manifest hashes — дополнительная проверка.
Проверка только читает пакет и ничего не исправляет.

Исходный R5 probe воспроизведён до правок: **1345 / 1328 PASS / 17 FAIL**,
пять согласованно переэкспортированных семантических мутаций приняты старым checker.
baseline_reproduction.json сохраняет исходы. Сначала пришлось получить недостающий
исторический Git object CAD3591; предварительное отклонение по его отсутствию
не засчитывалось как воспроизведение семантического замечания. CAD не перестраивался.

Новые регрессии: 7 методов unittest, 28 мутационных вариантов после re-export,
27 сочетаний TRUE/FALSE/UNKNOWN, все пять LOAD и их шесть допустимых mode bindings,
неверные dose/material/operation/revision, команда/таймер, неполный commit и
сохранение остатка. Неизменённый checked helper воспроизводит положительный путь
fault→closure recovery→отдельная history reconciliation→новый NEXT и отрицательные
материальные/сервисные случаи. Это условные программные примеры, не сигналы машины.

Из корня репозитория:

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

Намеренный экспорт документов (не CAD) выполняется отдельно:

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/render_schemes.py --output-dir /tmp/rev-ci-export
```

Текущие результаты — checks.json и сопутствующие журналы в этой папке.
Исторические proposal/checks.json, document_checks.json, export_checks.json
относятся только к ed8272c и не объявляются текущими.

**Все 44 bindings и четыре невыбранных силовых варианта сохранены побайтно.**
Расчёты, CAD, registry, source helpers, исходные R5 акты/probe не изменяются.
Новые геометрические пары/нативные свидетели не проверялись. W02 OPEN/NOT_IMPLEMENTED,
исполняемая материальная логика и физический READY NO-GO; G1 OPEN. Архитектура и
ТЗ не утверждены, реальные R2/R3 подтверждения UNKNOWN. RECHECK оценивает только
исправленный документальный интерфейс и его инструменты.
