# Фактические результаты условной компоновки A/B

2026-11-11 UTC, R4 / r4-linked-20261111, T-r4-layout-build-01. Самопроверка; независимый OUTPUT review NOT_RUN. Результаты не являются приёмкой конструкции REV. Архитектура/ТЗ не утверждены, G1 открыт, физические испытания NOT_RUN.

Входы: main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 после PR #35; claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят пользователем, owner_session r4-linked-20261111, lease до 2026-11-12T18:06:24Z. Проверены отсутствие конкурирующего принятого владельца и неизменность задания/шаблона относительно пакета 2c6743d39b59e38d85d21684059b4f4afd1ca248. Условный набор до построения: 4865fbfabf861a7c856a2f61300e2a9fc4ab0872, уточнение отверстий 6db54ea4168e83118de70144e2fd08c8750b5d6c. Метаданные purpose/scope/author дополнены без изменения чисел на 0d587fa226fee78abc7c86752adee825febb164d. Входной акт: cad/layout/build_input_audit.md. Полный code/results C записывается следующим commit H в NEXT_MODEL.md и капсулу, без попытки самоссылки.

Команда из корня: `/usr/bin/python3 cad/layout/run_all.py`. Все восемь дочерних команд завершились с exit code 0. В `validation.json` сохранены команды и stdout/stderr: 7 новых тестов адаптера/непрерывности/входов, 33 прежних теста linked_scene и 20 тестов kinematic_press; суммарно 60/60. Новые отрицательные случаи проверяют пропущенное значение, неизвестность криволинейного перекрытия, коллизию в середине прямого и обратного хода при свободных концах, запрещённое граничное касание/малое проникновение, дефекты координаты/времени/lifecycle и неизвестную траекторию.

A: 65 твёрдых тел; B: 61. В каждом документе 446 ASSUMED-записей Spreadsheet. Результат открытия/recompute и изменения координаты через Spreadsheet — PASS. STEP повторно прочитан, твёрдые тела валидны, количество соответствует manifest. Чистая повторная сборка дала одинаковые ID, параметры, границы, состав зон и результаты edit probe для A/B. Контейнеры не обещаны побайтно одинаковыми. Реальный реестр и COTS неизменны, все реальные размеры/ходы/нагрузки/свойства UNKNOWN; условный набор и снимок реестра сохранены отдельно. Файлы models/ неизменны; прежний review не распространяется на новый адаптер и CAD.

## Ограниченная геометрическая выдача

В этой таблице только явно перечисленное в JSON подмножество пути punch/product — камера/канал/stop/lock/препятствие. Полная машина этим результатом не разрешается.

| Вариант | Случай | Геометрия | Коллизия пути | Обязательная связь | Переход подмножества | Возврат подмножества | Непрерывность |
|---|---|---|---|---|---|---|---|
| A | sufficient | GEOMETRY_SUFFICIENT | NO_COLLISION | LINK_CONFIRMED | ALLOWED_FOR_PATH_SUBSET | RESTORED_FOR_PATH_SUBSET | CONTINUOUS |
| A | short | SHORT_STROKE | NO_COLLISION | LINK_CONFIRMED | BLOCKED | NOT_CONFIRMED | CONTINUOUS |
| A | collision | GEOMETRY_SUFFICIENT | COLLISION | LINK_CONFIRMED | BLOCKED | NOT_CONFIRMED | CONTINUOUS |
| A | unknown | INDETERMINATE | INDETERMINATE | LINK_INDETERMINATE | INDETERMINATE | NOT_CONFIRMED | INDETERMINATE |
| B | sufficient | GEOMETRY_SUFFICIENT | NO_COLLISION | LINK_CONFIRMED | ALLOWED_FOR_PATH_SUBSET | RESTORED_FOR_PATH_SUBSET | CONTINUOUS |
| B | short | SHORT_STROKE | NO_COLLISION | LINK_CONFIRMED | BLOCKED | NOT_CONFIRMED | CONTINUOUS |
| B | collision | GEOMETRY_SUFFICIENT | COLLISION | LINK_CONFIRMED | BLOCKED | NOT_CONFIRMED | CONTINUOUS |
| B | unknown | INDETERMINATE | INDETERMINATE | LINK_INDETERMINATE | INDETERMINATE | NOT_CONFIRMED | INDETERMINATE |

Препятствие collision задано до первой стадии; скачка его положения нет. Все границы времени проверены точными рациональными значениями, положение — через конец предыдущей траектории. Событие REMOVE допустимо только в условном подмножестве после прохождения всей оболочкой выходной плоскости при LINK_CONFIRMED; CREATE/SPLIT и действительное отсутствие остатка не подтверждены. Для short/collision/unknown остановка описания до возврата намеренна: возврат и READY не объявляются. В sufficient присутствуют отдельные RETURN, восстановление stop/lock B, inlet_gate и READY-RETURNED; это только восстановление заданных геометрических положений. Геометрическая PRESS/UNLOAD B не моделирует уплотнение/разгрузку. Удержание A, силы и безопасность UNKNOWN.

## Полная матрица и сервис

Все неупорядоченные пары всех присутствующих твёрдых тел проверены по каждой сохранённой фазе; при условном REMOVE реестр продукта меняется явно. Подробные точные интервалы, контакт и LINK находятся в `checks/all_pairs.json.gz` (обычный gzip JSON); сокращённое подмножество пути не подменяет полную матрицу. Для неподдержанной криволинейной геометрии CLEAR означает только доказанную раздельность консервативных AABB, перекрытие даёт INDETERMINATE. CAD/adapter nominal bounds сверены для каждого тела; габариты извлекаются без сетки визуализации через optimalBoundingBox(False, False).

| Вариант | Случай | Фаз | Записей пар | CLEAR | ALLOWED_CONTACT | COLLISION | INDETERMINATE | INVALID_INPUT |
|---|---|---|---|---|---|---|---|---|
| A | sufficient | 7 | 14368 | 13593 | 4 | 729 | 42 | 0 |
| A | short | 4 | 8320 | 7876 | 4 | 416 | 24 | 0 |
| A | collision | 4 | 8580 | 8133 | 4 | 418 | 25 | 0 |
| A | unknown | 4 | 8320 | 7813 | 3 | 416 | 88 | 0 |
| B | sufficient | 13 | 23490 | 22247 | 8 | 1157 | 78 | 0 |
| B | short | 8 | 14640 | 13874 | 8 | 710 | 48 | 0 |
| B | collision | 8 | 15128 | 14359 | 8 | 712 | 49 | 0 |
| B | unknown | 8 | 14640 | 13815 | 7 | 710 | 108 | 0 |

Всего 107486 записей пар по фазам/сценариям, это не число уникальных физических интерфейсов. Доказанные пересечения условных стенок, рамных соединений, габаритных креплений и двигавшихся деталей не скрыты исключением «неинтересных» пар. Часть связана с представлением общих соединений сплошными пересекающимися примитивами; разрешённые реальные контакты и отверстия ещё не заданы. Для всех восьми сцен whole_assembly_transition=BLOCKED_ASSUMED_INTERFERENCES и whole_assembly_ready=INDETERMINATE. Это результат исследования, а не свидетельство отсутствия пересечений всего пресса.

| Вариант | Условное вертикальное извлечение | CLEAR | COLLISION | INDETERMINATE |
|---|---|---|---|---|
| A | conditional vertical extraction cylinder_barrel | 61 | 0 | 3 |
| A | conditional vertical extraction rod | 61 | 0 | 3 |
| A | conditional vertical extraction doser_slide | 56 | 8 | 0 |
| A | conditional vertical extraction clamp_L | 61 | 3 | 0 |
| B | conditional vertical extraction cylinder_barrel | 57 | 0 | 3 |
| B | conditional vertical extraction rod | 57 | 0 | 3 |
| B | conditional vertical extraction doser_slide | 52 | 8 | 0 |
| B | conditional vertical extraction end_stop | 55 | 5 | 0 |
| B | conditional vertical extraction lock | 59 | 1 | 0 |

Сервисные прогоны содержат 556 результатов с полным evidence в `checks/service_pairs.json.gz`; они не подтверждают демонтаж и безопасность. Не проверены (INDETERMINATE, причины в report.json): снятие вставок/правой половины зажима, вращение ограждений и подход оператора, подъём/монтаж, гибкие петли/порты, полная рабочая зона и ёмкость приёмной области. QueryVolumes в CAD — только цилиндр/дозатор; остальные области не выдаются за геометрически заданные или свободные.

## Самоаудит и ограничения

| Пункт | Фактический итог |
|---|---|
| Требования/границы | Созданы оба условных варианта всего пресса; ограниченный путь отдельно от полной установки; реальная инженерная приёмка не заявлена |
| Источники | ASSUMED-набор отдельно; прежние источники/reviews сохранены; актуальная редакция и CAD требуют независимого review |
| Размерности/базы | SI в JSON, мм в FreeCAD, точный перевод; координаты/оси указаны в BUILD_README; численная сверка не назначает допуск |
| Балансы | NOT_APPLICABLE для геометрии; масса/энергия/усилия/прочность не рассчитывались, UNKNOWN |
| Геометрия | CAD/STEP/reopen/recompute/editability/repeat — PASS; полной свободы пересечений нет; цилиндры — ограниченный bounding метод |
| Цикл | Восемь фактических исходов и непрерывность проверены; физические удержание/разгрузка/остаток/выдача UNKNOWN; полный READY не подтверждён |
| Прослеживаемость | Снимки и SHA-256 в manifests/report/validation; входы зафиксированы до применения; C/H и независимый review раздельно |

Первый усиленный контроль обнаружил несогласованный габарит цилиндра: обычный BoundBox после tessellate зависел от визуализационной сетки. Неуспешный прогон сохранён в `history/adapter_triangulation_failure.json`; после перехода на аналитический optimalBoundingBox(False,False) весь запуск выполнен заново. Историческая ошибка не является текущим результатом PASS. Другие ранние локальные отладки launcher/Spreadsheet не являлись приёмочными прогонами; их ограничения и рабочий путь описаны в BUILD_README.

Реальные отверстия/сопряжения/направляющие/опоры, телескопическая форма rod/barrel, зазоры/допуски, реальные материалы/нагрузки, автоматика и безопасное обслуживание UNKNOWN. Схемы load_path.svg — лишь топология предполагаемой передачи усилий; независимые профильные входы R2/R3/R6 необходимы. Сборки не являются выбранной архитектурой, РКД, одобренными COTS или конструкцией REV. Все замечания R5 оставлены на решение независимого reviewer; задача IN_REVIEW, не DONE, G1 открыт.
