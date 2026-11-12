# Непроверенные обязательные условия

833332 парные строки относятся только к объявленным примитивам/фазам. Следующие условия не закрыты этим покрытием. Неподдерживаемое движение или отсутствующие входы не получают PASS.

| Условие | Статус | Причина |
|---|---|---|
| clamp_R / separate wear inserts | INDETERMINATE | removal path/part interfaces and sequence not defined; existing clamp_L protocol cannot establish these paths |
| guard opening | INDETERMINATE | hinges, rotation and open positions UNKNOWN; supported method is linear translation, not rotation |
| operator approach and service workspace | INDETERMINATE | site extents, human/access/tool envelopes and criteria UNKNOWN; no safety claim |
| hoses / ports / disconnection | INDETERMINATE | routing bodies are placeholders; flexibility, bend radii, couplings, depressurization and disconnection sequence UNKNOWN |
| lifting / installation / physical L path | INDETERMINATE | mass/centre of gravity, supports, rigging, attachment and actual removal stroke UNKNOWN |
| cylinder and powerpack COTS | INDETERMINATE | bore/rod minimum arithmetic does not establish exterior, closed/open length, ports, fastening or station dimensions |
| material compaction / dose transformation | INDETERMINATE | rigid preformed-product surrogate only; changing material geometry, friction, residuals and physics not established |
| complete real power / cycle | INDETERMINATE | main-axis fixed-budget phases and unverified caps only; other axes, concurrency, hold power, actual auxiliaries UNKNOWN |
| B unloading / opening | INDETERMINATE | residual reaction, open threshold, sensors/interlocks UNKNOWN; conditional geometric motion does not permit physical opening |
| receiver / product removal / READY | INDETERMINATE | preserved CAD exit not reached; external reception/transport UNKNOWN; no product REMOVE and no working READY |
