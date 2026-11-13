# B03 — prevalidation по ARB-R1-CI-SEMANTICS-03

Решение `39826eb2f5dbd1f83d81882022e6f59313ebe5d5` прочитано, SHA
зафиксирован в капсуле до кода; checkpoint `b08f365` содержит аудит и схему.
[Схема и результаты](snapshot_correction/README.md). Проверяются все используемые
snapshots по fixed guard/action, E B_RESET={B_CLOSURE}; пропуски не дополняются.
Compatibility только в объявленном домене; scoped UNKNOWN не скрывает общий
BLOCKED известного запрета. Положительный адресный recovery сохраняется.
Четыре REJECT сохранены, interface counter=4 / material counter=2. B03 OPEN,
независимый RECHECK нового exact C PENDING; стабильная CAD-передача NO-GO.
Main3a9258c/PR45 owner/lease не менялись. Норматив, frozen helper, B01/B02,
44 bindings/четыре варианта/loads/calculations/CAD сохранены. W02/PLC/CAD вне
итерации; physical READY NO-GO, архитектура/ТЗ не утверждены, G1 OPEN.

---

## Предыдущие записи — история

# B03 — строгие типы по ARB-R1-CI-SEMANTICS-02

Решение `e0fea7bbf3bd32fda601bca2f7567f8e2c3342b3` прочитано и записано
в капсуле до изменения кода. Узкая коррекция checker/recovery predicate;
норматив и frozen helper не меняются. [Проверки типов](type_correction/README.md).
Три интерфейсных REJECT сохранены, B03 OPEN до независимого RECHECK.
Owner/lease/main не изменены; B01/B02 и 44 bindings/четыре force variants сохранены.
W02/PLC/CAD вне scope; physical READY NO-GO, архитектура/ТЗ не утверждены, G1 OPEN.

---

## Предыдущие записи — история

# B03 — корректирующая итерация по ARB-R1-CI-SEMANTICS-01

Решение R1 `5fe510bbc55a052c360ab39a2491a061584b8fb7` прочитано и записано
в капсуле до изменения checker. Owner/lease PR45 сохранены; main не меняется.
B01/B02 CLOSED только документально на C144941c согласно R5 5fb7311; их
регрессии сохраняются. B03 OPEN / RECHECK_PENDING; interface_consecutive_rejections=2,
стабильная CYC-to-CAD передача NO-GO. [Новая редакция и проверки](semantic_iteration/README.md).
W02/PLC/CAD вне итерации, physical READY NO-GO, архитектура/ТЗ не утверждены, G1 OPEN.

---

## Предыдущие записи — история

# R4 — исправление по OUTPUT R5, RECHECK PENDING

Прямое поручение пользователя, исполнитель R4 / Codex / r4-cyc-fix-20261113.
Корректирующее продолжение accepted PR45 claim r4-linked-20261111: owner и
lease 2026-11-14T00:13:12.404899+00:00 не менялись, main 3a9258c не менялась.
Входной C ed8272ce6ebc2047bb0d896db5951d02c42d5208, акт R5
13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2. Исправления/тесты — correction/README.md.
R5-CI-B01/B02/B03 OPEN до нового независимого RECHECK, parent IN_REVIEW, не DONE.
44 bindings и четыре силовых варианта сохранены; расчёты/CAD не менялись.
W02/physical READY NO-GO, G1 OPEN, архитектура/ТЗ не утверждены.

---

# Передача результата на review

Задача IN_REVIEW; owner r4-linked-20261111, heartbeat 2026-11-13T00:54:05.040681+00:00.
Срок исходный, без продления. [Результат](proposal/README.md); независимое review PENDING.

---

# Актуализация после PR №45

**ACCEPTED_MAIN; IN_REVIEW; owner_session: r4-linked-20261111.**
Основание: merge `3a9258c57e4bc15d6de98f1d17e8412ad6e8899a` и прямое подтверждение пользователя.
Lease неизменен: `2026-11-14T00:13:12.404899+00:00` (14 ноября 03:13:12 МСК); продления нет.
Входной акт: proposal/input_audit.md/json. Историческое предварительное состояние ниже
сохранено как история, его запрет до принятия выполнен PR45.

---

# Предложение claim — T-r4-cycle-interfaces-01

**PROPOSED_PENDING_MAIN / TASK READY / owner_session NONE.**
Предлагаемый исполнитель r4-linked-20261111 / Codex / R4 по поручению пользователя.
Ветка work-r4/T-r4-cycle-interfaces-01/r4-linked-20261111; база main 8a82b30d185a10c71dbedbb8b581cf6b5162b1b7.
Предложено 2026-11-13T00:13:12.404899+00:00, proposed lease_expires_at **2026-11-14T00:13:12.404899+00:00**
/ **14.11.2026 03:13:12 МСК**. Истечение не продлевается молча; срок проверить при принятии.

Старый claim T-r4-cycle-contract-01 принят PR43, срок до 2026-11-13T18:16:39Z,
owner тот же. Он действует для прежнего документального контракта/подготовки
интеграции, но не расширяется до новой CYC-02/03 проектной задачи. Другие claims/
lease не меняются. Назначение роли сохраняется, принятый claim новой задачи нет.

Просьба о принятии — последовательно в main после сверки актуальной базы,
входов, отсутствия принятого конкурирующего owner и неистёкшего срока. Принятие
отразить явно: owner_session r4-linked-20261111, claim_acceptance ACCEPTED_MAIN,
статус CLAIMED, heartbeat UTC и конкретный lease_expires_at. Пока эти поля не
приняты в общей ветке, существование этого PR/файла — только предложение.
После принятия R4 повторяет fetch/main/owner/lease/inputs и входной акт.

Результат будущей работы — task.md: интерфейсные/силовые схемы A/B, таблицы
предельных поз/разрешений и альтернативы геометрии с критериями последующей
проверки. Зафиксированные D/d, нагрузки/ходы не уменьшаются; необходимость
изменения — отдельное предложение R3. До принятия реализация NOT_STARTED.

Контракт используется только документально с WARNING. W02 OPEN; исполняемая
материальная логика и физический READY NO-GO. Архитектура/ТЗ/COTS не утверждаются,
CAD/rebuild/физические испытания не выполняются этим подготовительным claim.
G1 OPEN. Автор PR не принимает свой claim и не сливает PR.
