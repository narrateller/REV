# Прослеживаемость редакции 2

Все исходные 20 строк карты 43f03359fabe2b664935b17f9ac7851504093ece сохранены. Нормативный перечень transition/state/READY/resource/questions — traceability.json. R5-CC-B01/W01/W02 и CYC-01…09 остаются OPEN до независимого решения.

| Строка / стадия | Переходы | READY targets |
|---|---|---|
| A0 / startup | A-AUDIT, A-COLUMN, A-READY-START-LOAD | A-READY-START-LOAD |
| A1 / load | A-LOAD-START, A-REFILL, A-LOAD-STEADY, A-READY-START-REFILL | A-READY-START-REFILL |
| A2 / isolate | A-GATHER, A-COMPACT, A-READY-START-PRESS-A_STARTUP_RAW, A-READY-START-PRESS-A_COLUMN_BUILDING, A-READY-PRESS | A-READY-START-PRESS, A-READY-PRESS |
| A3 / press | A-GATHER, A-COLUMN, A-COMPACT, A-READY-START-PRESS-A_STARTUP_RAW, A-READY-START-PRESS-A_COLUMN_BUILDING, A-READY-PRESS | A-READY-START-PRESS, A-READY-PRESS |
| A4 / hold_unload | A-COMPACT | через зависимое действие |
| A5 / eject | A-SEGMENT, A-EJECT, A-CROSS, A-RECEIVE, A-REMOVE, A-READY-EJECT | A-READY-EJECT |
| A6 / return | A-RETURN, A-STARTUP-RETURN-A_COLUMN_BUILDING, A-STARTUP-RETURN-A_COLUMN_ESTABLISHED, A-READY-START-REFILL | A-READY-START-REFILL |
| A7 / ready | A-REMOVE, A-NEXT, A-READY-START-LOAD, A-READY-STEADY-LOAD | A-READY-START-LOAD, A-READY-STEADY-LOAD |
| A8 / resources | RESOURCE-BASIS | через зависимое действие |
| B0 / startup | B-AUDIT, B-READY-LOAD | B-READY-LOAD |
| B1 / load | B-LOAD, B-REFILL, B-SELECT, B-GATHER-RETURN, B-READY-REFILL | B-READY-REFILL |
| B2 / isolate | B-GATHER, B-COMPACT, B-READY-PRESS, B-READY-GATHER | B-READY-PRESS, B-READY-GATHER |
| B3 / press | B-GATHER, B-SELECT, B-COMPACT, B-READY-PRESS, B-READY-GATHER | B-READY-PRESS, B-READY-GATHER |
| B4 / hold_unload | B-COMPACT, B-OPEN-CONFIRM | через зависимое действие |
| B4U / unlock | B-OPEN-CONFIRM | через зависимое действие |
| B4O / open | B-OPEN-CONFIRM, B-READY-EJECT | B-READY-EJECT |
| B5 / eject | B-EJECT, B-CROSS, B-RECEIVE, B-REMOVE, B-READY-EJECT | B-READY-EJECT |
| B6 / return | B-RETURN, B-RESET, B-GATHER-RETURN | через зависимое действие |
| B7 / ready | B-RESET, B-NEXT, B-READY-LOAD | B-READY-LOAD |
| B8 / resources | RESOURCE-BASIS | через зависимое действие |

A8/B8 — overlays, не дополнительные физические стадии. R5-CYCLE-W01/W02 OPEN: ранние 08/09 — документальная постановка; native CAD не проверялся. Кандидат 3591a5f: declared coordinates / author native witnesses / independent native NOT_RUN. Расчёты/CAD/ходы/нагрузки/прошлые findings не изменены.
