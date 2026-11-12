# Прослеживаемость к принятой карте

Источник 43f03359fabe2b664935b17f9ac7851504093ece; все исходные 20 строк сохранены в traceability.json. Все CYC остаются OPEN. Колонка переходов — детализация documentary proposal, а не подтверждённая последовательность REV. A8/B8 — ресурсные overlays; длительность поверх стадий не суммируется. Ранние 08/09 подготовлены вместе с 01 по R5-CYCLE-W01; закрывать W01 автор не вправе.

| Строка / стадия | Переходы документа | READY target | Ресурсы |
|---|---|---|---|
| A0 / startup | A-AUDIT, A-COLUMN, A-READY-START-LOAD | A-READY-START-LOAD | resources.json: A0 |
| A1 / load | A-LOAD-START, A-REFILL, A-LOAD-STEADY | через следующий target | resources.json: A1 |
| A2 / isolate | A-GATHER, A-COMPACT, A-READY-START-PRESS-A_STARTUP_RAW, A-READY-START-PRESS-A_COLUMN_BUILDING, A-READY-PRESS | A-READY-START-PRESS, A-READY-PRESS | resources.json: A2 |
| A3 / press | A-GATHER, A-COLUMN, A-COMPACT, A-READY-START-PRESS-A_STARTUP_RAW, A-READY-START-PRESS-A_COLUMN_BUILDING, A-READY-PRESS | A-READY-START-PRESS, A-READY-PRESS | resources.json: A3 |
| A4 / hold_unload | A-COMPACT | через следующий target | resources.json: A4 |
| A5 / eject | A-SEGMENT, A-EJECT, A-CROSS, A-RECEIVE, A-REMOVE, A-READY-EJECT | A-READY-EJECT | resources.json: A5 |
| A6 / return | A-RETURN, A-STARTUP-RETURN-A_COLUMN_BUILDING, A-STARTUP-RETURN-A_COLUMN_ESTABLISHED | через следующий target | resources.json: A6 |
| A7 / ready | A-REMOVE, A-NEXT, A-READY-START-LOAD, A-READY-STEADY-LOAD | A-READY-START-LOAD, A-READY-STEADY-LOAD | resources.json: A7 |
| A8 / resources | RESOURCE-BASIS | через следующий target | resources.json: A8 |
| B0 / startup | B-AUDIT, B-READY-LOAD | B-READY-LOAD | resources.json: B0 |
| B1 / load | B-LOAD, B-REFILL, B-SELECT, B-GATHER-RETURN, B-READY-REFILL | B-READY-REFILL | resources.json: B1 |
| B2 / isolate | B-GATHER, B-COMPACT, B-READY-PRESS | B-READY-PRESS | resources.json: B2 |
| B3 / press | B-GATHER, B-SELECT, B-COMPACT, B-READY-PRESS | B-READY-PRESS | resources.json: B3 |
| B4 / hold_unload | B-COMPACT, B-OPEN-CONFIRM | через следующий target | resources.json: B4 |
| B4U / unlock | B-OPEN-CONFIRM | через следующий target | resources.json: B4U |
| B4O / open | B-OPEN-CONFIRM, B-READY-EJECT | B-READY-EJECT | resources.json: B4O |
| B5 / eject | B-EJECT, B-CROSS, B-RECEIVE, B-REMOVE, B-READY-EJECT | B-READY-EJECT | resources.json: B5 |
| B6 / return | B-RETURN, B-RESET, B-GATHER-RETURN | через следующий target | resources.json: B6 |
| B7 / ready | B-RESET, B-NEXT, B-READY-LOAD | B-READY-LOAD | resources.json: B7 |
| B8 / resources | RESOURCE-BASIS | через следующий target | resources.json: B8 |

R5-CYCLE-W02: CAD 3591a5f — declared coordinates / author-reported native witnesses; independent native NOT_RUN. Новый документ не закрывает penetration/output/retention/reset findings, не меняет ход или геометрию. Точные входы и evidence grades — input_acceptance.json, input_audit.md и preflight.json. Источники-аналогии не становятся требованиями REV.
