# Программа/метрология: условная применимость полей

DRAFT,NOT_APPROVED. Новый independent review NOT_RUN. Все VAL/TEST NOT_RUN;UNKNOWN/null не ноль. 42 состояния не рассчитаны;§4/5/6 NOT_RUN,G1 OPEN,W02/physical READY NO-GO. Расчёты/CAD-rebuild/испытания не разрешены.

Чистый DOCUMENT-аудит отделён от численной метрологии. У смешанных проверок метрологические пробелы сохраняются. FORCE_REACTION — предлагаемый класс будущих данных,не выбранный прибор или выполненный расчёт.

| MET / VAL | Каналы | Метод | Применимость |
| --- | --- | --- | --- |
| MET-VAL-REV-01 / VAL-REV-01 | EVENT, MATERIAL, TIME, MASS | Будущий TEST-F-05 и аудит функциональной схемы | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-02 / VAL-REV-02 | MATERIAL, MASS | Будущая характеризация по согласованным методикам | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-03 / VAL-REV-03 | GEOMETRY, MASS, TIME, EVENT | Будущие TEST-F-03/04: обмер, взвешивание, наблюдение выхода | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-04 / VAL-REV-04 | EVENT, TIME, ELECTRICAL, MASS | Будущий TEST-F-05 и раздельный учёт потерь/остановов | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-05 / VAL-REV-05 | EVENT, MOTION, TIME | Будущие проверки автомата и TEST-F-01…05 | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-06 / VAL-REV-06 | MATERIAL, EVENT, MOTION | Будущий review интерфейсов и TEST-F-01/02/04 | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-07 / VAL-REV-07 | ELECTRICAL, TIME, EVENT | Будущий электрический/энергетический review и измерения | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-08 / VAL-REV-08 | PRESSURE, MOTION, FLOW, TIME, ENVIRONMENT | Будущие синхронные измерения и профильный анализ | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-09 / VAL-REV-09 | DOCUMENT, MOTION, FORCE_REACTION | Будущий аналитический/CAE review и отдельное подтверждение | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-10 / VAL-REV-10 | EVENT, MOTION, TIME | Будущий анализ риска и согласованные проверки функций | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-11 / VAL-REV-11 | EVENT, PRESSURE, MOTION, TIME | Будущая матрица отказов и проверки только по разрешённой программе | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-12 / VAL-REV-12 | EVENT, MOTION, TIME | Будущая проверка измерительной цепи и TEST-F-01…05 | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-13 / VAL-REV-13 | ENVIRONMENT, MATERIAL | Будущий review среды и разрешённые проверки воздействий | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-14 / VAL-REV-14 | MATERIAL, ENVIRONMENT, DOCUMENT | Будущая характеризация и профильная оценка риска | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-15 / VAL-REV-15 | DOCUMENT, EVENT, PRESSURE, MOTION | Будущий сервисный/DFM review и демонстрация по программе | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-16 / VAL-REV-16 | GEOMETRY, MASS, DOCUMENT | Будущий компоновочный/монтажный review и обмер | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-17 / VAL-REV-17 | DOCUMENT, GEOMETRY | Будущий DFM и каталоговый review | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
| MET-VAL-REV-18 / VAL-REV-18 | DOCUMENT | Будущий компетентный review применимости | PURE_DOCUMENT_FIELD_RULES |
| MET-VAL-REV-19 / VAL-REV-19 | DOCUMENT | Аудит описи и воспроизведение применимых проверок | PURE_DOCUMENT_FIELD_RULES |
| MET-VAL-REV-20 / VAL-REV-20 | DOCUMENT | Будущий review программы; после разрешения выполнение/оценка | PURE_DOCUMENT_FIELD_RULES |
| MET-VAL-REV-21 / VAL-REV-21 | DOCUMENT | Аудит полной карты происхождения | PURE_DOCUMENT_FIELD_RULES |
| MET-VAL-REV-22 / VAL-REV-22 | EVENT, MASS, DOCUMENT | Будущий TEST-F-05 и аудит журнала происхождения | APPLICABLE_MEASUREMENT_FIELDS_REMAIN_UNKNOWN |
