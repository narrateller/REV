# R4 → независимый R5: B03 snapshot admission RECHECK

Основание ARB-R1-CI-SEMANTICS-03 на
`39826eb2f5dbd1f83d81882022e6f59313ebe5d5`. SHA зафиксирован в капсуле
до кода; checkpoint `b08f365` включает аудит и схему допуска.
Входной четвёртый акт R5 `0ff3c8f4502ea29c712bf1f41e223f172c5a21c7`
на C `fa0626372c03d11655624bb454458f82c30117f7` сохранён вместе с тремя
предыдущими отказами. B03 OPEN, interface counter=4, material counter=2.
Проверять exact новый C из следующего H; автор не закрывает B03.

1. Взять независимый domain oracle из frozen contract/helper C0c4eb5d.
   Для B_RESET_CONFIRMED E={B_CLOSURE}, для каждого ENTRY/causal guard свой E.
   Проверить каждый используемый snapshot по DOMAIN_SCHEMA.md, включая types,
   completeness, extras и адресную revision_history. Payload keys и F-digest
   сами по себе не источник обязательных доменов.
2. Повторить unchanged 7 incomplete cases и четыре coherent false-acceptance
   witnesses. Не дополнять origin/expected нулём, current или сменой F-ID.
   Проверить independent empty/missing/foreign/partial/extra origin и expected,
   proof/current/ENTRY maps, invalid types и неизвестные revisions.
3. Сохранить положительные 0/1/large integer, minimal context, адресный recovery
   после подтверждённого advance с отличным от current immutable origin.
   Missing/changed unused FEED/RETENTION не запрещает closure само по себе.
4. При неполном proof известный resource/state/causal FALSE сохраняет общий
   BLOCKED. Другие нерешённые faults сохраняются, штатные действия продолжают
   проверять свои условия.
5. Сравнивать одинаковые уровни frozen policy только IN_DOMAIN.
   Каждый OUT_OF_DOMAIN с legacy TRUE/exception объяснить нарушенной схемой.
   Отдельно проверить validation/reasons, scoped value и action gate.
   Readonly caller/proof/origin/expected/history/rejected IDs обязателен.
6. Повторить прежние type244/36, semantic411 (включая шесть подмен R5 и другие
   стадии), B01/B02, checker и воспроизведение свежего экспорта. Норматив,
   frozen helper, 44 bindings/четыре варианта, расчёты/CAD неизменны.

[Схема/команды/результаты](../snapshot_correction/README.md),
[policy comparison](../snapshot_correction/policy_comparison.md).
W02/PLC/CAD вне scope, physical READY NO-GO, G1 OPEN. Архитектура/ТЗ
не утверждены; стабильная documentary/CAD передача NO-GO до независимого акта.
