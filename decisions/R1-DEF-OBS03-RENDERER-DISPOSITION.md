# R1: диспозиция recheck и исправления renderer

Входной акт REV-R5-G1-DEF-OBS-RECHECK-01-001, C234ea8a1917899c69e68ec3ef6e7ebcefbe79fae /
H9140a2dec3679934e0b24ece1ff7190db87d0f39, проверяет exact C97f58fd437947e26963bdbbc2f2d89df7438e8cc.
OBS-01/02 приняты как CLOSED_DOCUMENTARY_EXACT_C только на этом C. Общий WARNING
сохраняется: исходный 1 FAIL OBS-03 и все доказательства остаются неизменными.

Ошибка автора renderer признана: фиксированная DRAFT-01 в представлении не совпала
с JSON DM02/03 DRAFT-02. Исправленная отдельная ревизия выводит revision_label
соответствующей строки по method_id/REQ/VAL и берёт идентичность общего protocol
из JSON. Данные требований, методов, quantities и retention не меняются.

Новый active_bundle выбирает исправленный renderer/summary. Старые views остаются
историческим свидетельством OBS-03, а не актуальной сводкой этой ревизии.
Авторский readback всех 22 меток и replay не закрывают OBS-03: статус
OPEN_PENDING_INDEPENDENT_RECHECK до нового самостоятельного R5 exact-C акта.
Прежние closure OBS-01/02 не переносятся автоматически на изменённый target.

G1/ТЗ/архитектура не утверждены, RAW не повышены. B01/B02/B03/source issues/
country/engineering owners OPEN/UNKNOWN. 42 состояния не рассчитаны; §4/5/6 NOT_RUN;
прочность/устойчивость/реальные реакции не подтверждены; W02/physical READY NO-GO.
Расчёты, CAD-rebuild и испытания не разрешены. Claims/owners/исходный срок
2026-11-18T01:58:30.990734+00:00 не продлеваются.
