# Условные переходы и контрпримеры

Все TRUE явно ASSUMED внутри отдельного логического примера. Численные массы/позы не назначаются. Это проверка документа, не выполнение материального движка. Полные before/guards/event/after/inventory — в transition_examples.json. Положительный результат не подтверждает физику/датчики/READY REV.

Две связанные трассы в sequence_examples.json проходят A startup → steady →
следующая загрузка и B с повторным набором → выдача → следующий batch. У каждого
шага отдельный event_id, все guards явно ASSUMED TRUE. Новый DELIVER_DOSE добавляет
новый дозовый ID, а не продукт. Трассы не требуют REMOVE для READY и не доказывают
численный баланс/физическую последовательность: только непротиворечивость состояний.

| ID | Переход | Ожидаемый исход | Основание |
|---|---|---|---|
| ASSUMED-A-AUDIT | A-AUDIT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-LOAD-START | A-LOAD-START | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-GATHER | A-GATHER | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-REFILL | A-REFILL | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-COLUMN | A-COLUMN | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-LOAD-STEADY | A-LOAD-STEADY | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-COMPACT | A-COMPACT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-SEGMENT | A-SEGMENT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-EJECT | A-EJECT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-CROSS | A-CROSS | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-RECEIVE | A-RECEIVE | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-RETURN | A-RETURN | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-NEXT | A-NEXT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-AUDIT | B-AUDIT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-LOAD | B-LOAD | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-GATHER | B-GATHER | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-REFILL | B-REFILL | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-SELECT | B-SELECT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-COMPACT | B-COMPACT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-OPEN-CONFIRM | B-OPEN-CONFIRM | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-EJECT | B-EJECT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-CROSS | B-CROSS | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-RECEIVE | B-RECEIVE | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-RETURN | B-RETURN | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-RESET | B-RESET | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-NEXT | B-NEXT | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-READY-START-LOAD | A-READY-START-LOAD | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-A-READY-STEADY-LOAD | A-READY-STEADY-LOAD | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| ASSUMED-B-READY-LOAD | B-READY-LOAD | ALLOWED_ASSUMED | Только условно допустимый пример при всех явно ASSUMED предпосылках |
| A-NO-PREFORMED-PRODUCT | A-COMPACT | BLOCKED | Empty не имеет delivered/column/history; COMPACT не может создать готовый продукт |
| B-NO-EARLY-PRODUCT | B-EJECT | BLOCKED | Повторный gather не product/ejectable, завершение набора и сжатия отсутствуют |
| A-REACTION-UNKNOWN | A-GATHER | INDETERMINATE | Неизвестный пуск остаётся неизвестным, не объявляется невозможным |
| A-STEADY-NOT-STARTUP | A-READY-STEADY-LOAD | BLOCKED | Для empty нужен другой READY target; retained column не придуман |
| A-RETAINED-LOST | A-SEGMENT | BLOCKED | Доказанная потеря retained блокирует и при неизвестном partition |
| B-REFILL-NEW-DOSE | B-REFILL | ALLOWED_ASSUMED | Вторая доставленная доза дополняет batch, не выдаёт второй product |
| B-REFILL-NO-CAPACITY | B-REFILL | INDETERMINATE | Вместимость/поза повторного набора не установлены |
| PARTITION-DOUBLE-COUNT | A-SEGMENT | BLOCKED | Outgoing и retained включили одно вещество дважды |
| PARTITION-REMAINDER-LOST | B-RECEIVE | BLOCKED | Подтверждённое исчезновение остатка не скрывается неизвестным receiver |
| BASIS-WET-DRY-MISMATCH | B-COMPACT | BLOCKED | Доза wet и product dry сопоставлены без конверсии/водного потока |
| A-PENDING-IS-NOT-RECEIPT | A-RECEIVE | INDETERMINATE | Целиком за выходом ещё PRESS_ACCOUNT, receiver не подтверждён |
| LEADING-EDGE-ONLY | B-CROSS | BLOCKED | Пересекла выход только передняя грань |
| EARLY-REMOVE | A-REMOVE | BLOCKED | REMOVE до приёма не гасит геометрию и массу |
| UNKNOWN-REMOVE | B-REMOVE | INDETERMINATE | Имя RECEIVED не заменяет актуальное основание ACK |
| RECEIVED-BUT-INTERACTING | B-REMOVE | BLOCKED | ACK есть, но product внутри MODEL_DOMAIN/sweep |
| DUPLICATE-TRANSFER | B-RECEIVE | BLOCKED | Повтор transfer_id не списывает массу второй раз |
| EXTRA-WRONG-TYPE-EVENT | A-LOAD-START | BLOCKED | Событие неверного типа/порядка/epoch не разрешает переход |
| BROKEN-CONTINUITY | A-CROSS | BLOCKED | Разрыв положения/идентичности блокирует несмотря на неизвестный метод |
| UNSUPPORTED-SWEEP | B-EJECT | INDETERMINATE | Неподдерживаемый обязательный метод всего интервала не CLEAR |
| B-OPEN-PHYSICS-UNKNOWN | B-OPEN-CONFIRM | INDETERMINATE | Реальное открытие B не подтверждено |
| B-RESET-RETAINED-PRODUCT | B-RESET | BLOCKED | Приём подтверждён, но product/residue пересекает reset sweep |
| READY-TOOLS-ONLY | B-READY-LOAD | INDETERMINATE | TOOLS_HOME TRUE недостаточно без material/receipt ledger |
| READY-BAD-RESIDUE | B-READY-LOAD | BLOCKED | Недопустимый известный остаток блокирует при неизвестных ресурсах |
| READY-STALE-FEEDBACK | A-READY-START-LOAD | BLOCKED | Старый HOME/epoch не является актуальным подтверждением |
| B-OPEN-WRONG-ORDER | B-OPEN-CONFIRM | BLOCKED | Позы open/clear сами по себе не доказывают порядок; известное OPEN до UNLOAD блокирует |
| A-STARTUP-RETURN-PRESERVES | A-STARTUP-RETURN-A_COLUMN_BUILDING | ALLOWED_ASSUMED | Возврат startup не удаляет накопленный запас |
| B-GATHER-RETURN-PRESERVES | B-GATHER-RETURN | ALLOWED_ASSUMED | Возврат перед новой дозой сохраняет partial batch |
| RESOURCE-NO-HIDDEN-ZERO | RESOURCE-BASIS | BLOCKED | Неизвестные hold/aux/P/Q подставлены нулями; такой вывод запрещён |
| RESOURCE-NO-AXIS-AS-CYCLE | RESOURCE-BASIS | BLOCKED | Старый main-axis budget объявлен временем полного цикла |
| RESOURCE-ACTUAL-UNKNOWN | RESOURCE-BASIS | INDETERMINATE | Реальные стадии/мощности не получены; полный цикл не вычислен |
