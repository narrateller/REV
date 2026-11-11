# Фактический пакет B02 QueryVolumes для независимого RECHECK

2026-11-11T19:29:39Z, R4 r4-linked-20261111, T-r4-layout-build-01. Вход: REV-R5-CAD-TOOL-FIX-01-001 на 8f381c4b080d902cb023429c54d518bfd6fab681, проверенный C 5449fb9bc4c20fcbc40fdec932876dcecc90ef4d. B01 CLOSED независимым R5 в его проверенной области; lifecycle-код не изменён и блокер не переоткрывается. B02 OPEN до следующего независимого RECHECK, самоприёмка не выполняется.

Команда `/usr/bin/python3 cad/layout/run_all.py`: exit 0, все 14 дочерних команд exit 0. Пройдены 73 unit tests (20 CAD/layout, 33 linked_scene, 20 kinematic_press), 64 новых отрицательных случая QueryVolumes, прежние 14 отрицательных CAD и 33 lifecycle-случая, 20 независимых lifecycle-проверок R5. Все 8 ограниченных исходов A/B сохранились. Полные команды/exit codes/stdout/stderr/source/artifact hashes — validation.json.

| Область | Фактический результат | Граница |
|---|---|---|
| Все сохранённые зоны | CylinderRemoval/DoserRemoval обоих A/B проверены до/после recompute: канонические ID/Role/тип, нативные размеры, локальный/глобальный Placement, bounds/volume и BRep | Это четыре определённые условные зоны, прочие неопределённые сервисные операции не получают PASS |
| Исходный Q01 | Native Height=99999 мм с удалённым выражением и обновлённым hash даёт FAILED API; CLI exit!=0, FAILED, scenarios=NOT_RUN | Успех старого probe с ошибочным Q01 assertion не является критерием исправления |
| 64 отрицательных случая | Все три размера и координаты каждой зоны, удаление/подмена manifest-списка, другая/пустая форма, BRep override при прежних свойствах, Role, совместные изменения; сдвиг/удаление группы, лишние/осиротевшие зоны | В 60 случаях обновлён FCStd hash и получен именно native semantic failure; 4 старых hash отклонены проверкой целостности |
| Сохранность зон | Все нативные query records идентичны actual-артефактам исходного C 5449fb9; snapshot/hash источника в verification/r4_query_volume_fix/query_geometry_baseline.json | Контейнеры CAD/STEP/PDF могут менять служебные timestamps/hashes, не геометрию |
| Сохранность компоновок | build_model.py/ASSUMED JSON/manifest.objects, 8 PNG, все 107486 записей фаз/пар и 556 сервисных результатов сохранены | Геометрические дефекты A/B не исправлялись |
| Нативные проникновения | Повторены исходные static/dynamic пробы R5; 17 положительных статических common volumes A и 18 B, прежние промежуточные свидетельства совпали | Полная установка BLOCKED_ASSUMED_INTERFERENCES, whole_assembly_ready=INDETERMINATE |

Доказательства: checks/query_regressions.json, checks/report.json (cad_adapter.A/B.query_volumes), checks/geometry_preservation.json, checks/lifecycle_closed_recheck.json; нативные проникновения — checks/native_static_recheck.json и native_dynamic_recheck.json. Все источники прежних независимых review/probes/evidence сохранены без изменений. До правки исходный cad_probe.py R5 повторён и сохранил ошибочный Q01 PASS в verification/r4_query_volume_fix/baseline_cad_probe.json; после правки новые assertions требуют FAILED. Geometry/query baseline зафиксированы отдельно до итоговой пересборки.

Ожидаемый набор определяется формулами от параметров исходных тел и service_lift, не из mutable manifest. Зоны не превращены в материальные детали, не добавлены в STEP/матрицу. Совпадение обновлённого hash не заменяет проверки содержания. Численные пределы сериализации прежние, реальными зазорами/допусками они не являются. Проверка нативной формы зоны не подтверждает возможность обслуживания или безопасность.

Registry/COTS/models и lifecycle-код неизменны. Все реальные параметры REV UNKNOWN, условные входы ASSUMED отдельно. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Новый точный code/results C записывается последующим H в эстафету; независимый RECHECK этого нового C NOT_RUN.

---

## История предыдущих оценок (статусы на соответствующих C, не текущая эстафета)

# Фактический RECHECK-пакет исправления инструмента

2026-11-11T19:04:26Z, R4 r4-linked-20261111, T-r4-layout-build-01. Входной R5 акт e939b41d0139b0a3a08a5950eeeec6e92324cf9b, REV-R5-LAYOUT-BUILD-01-001: REJECT_WITH_BLOCKER на исходный C 6bb66a566719593a59935e341b1b5c80a1cbc9a7. B01/B02 OPEN, независимый RECHECK нового C NOT_RUN. Задача IN_REVIEW, не принята. Полный новый C записывается отдельным H в NEXT_MODEL/капсулу.

Команда `/usr/bin/python3 cad/layout/run_all.py`: exit 0, все 12 дочерних команд exit 0. 69 unit tests (16 адаптер/CAD/lifecycle, 33 прежних linked_scene и 20 kinematic_press), 33 lifecycle-случая и 14 отрицательных CAD-случаев PASS по исправленным ожиданиям; 8/8 исходов ограниченного пути сохранились. Фактические команды/stdout/stderr/hashes — validation.json. Самопроверка не закрывает замечания R5.

| Область | Проверенный результат | Неопределённость/граница |
|---|---|---|
| Lifecycle | Каждое событие учтено; преждевременный REMOVE блокируется, тело удержано в эффективном реестре; тип/время/реестр/геометрия/условия выхода проверены до удаления | CREATE/SPLIT INDETERMINATE и не применяются; нет подтверждения физического отсутствия остатка |
| Сочетания дефектов | BLOCKED/INVALID сохраняются вместе с неизвестностью другого события; отдельное подтверждённое удаление не теряет своё доказательство из-за UNKNOWN CREATE | Неизвестность любого необходимого события не разрешает общий READY |
| Реальные CAD-файлы | Оба FCStd открыты/recompute, 65/61 bodies, нативные формы/границы сверены с входами; STEP перечитан и сопоставлен по форме/составу | Только условные примитивы и численная сериализация; реальные посадки и допуски UNKNOWN |
| Отрицательные CAD | Manifest-only, отсутствующие/пустые/повреждённые файлы, изменённые FCStd/STEP с обновлёнными hashes и несогласованный manifest дают FAILED; native crash проверен отдельным unit test | Недоступный нативный backend не разрешает PASS |
| Восемь исходов | Сохранены geometry/path_collision/link/continuity/return A/B, все соответствуют прежним ожиданиям ограниченного подмножества | Полная машина не разрешена; whole_assembly_ready=INDETERMINATE |
| Геометрия/матрицы | Входной ASSUMED JSON, build_model.py и все manifest.objects неизменны; все 8 PNG побайтно совпали; 107486 записей фаз/пар совпали полностью; 556 сервисных результатов сохранены | FCStd/STEP/PDF контейнеры могут иметь иные служебные timestamps/hashes, форма не изменена |
| Нативные проникновения | Повторены исходные R5 cad_probe.py и dynamic_probe.py; совпадают 17 положительных static common volumes A и 18 B, а также все промежуточные свидетельства | Выборочные нативные пробы не доказывают непрерывную BRep-проверку всех ходов |

Контрпримеры и новое evidence: checks/tool_regressions.json. Геометрическая неизменность: checks/geometry_preservation.json с baseline из verification/r4_layout_tool_fix/geometry_baseline.json. Повторные фактические нативные результаты: checks/native_static_recheck.json и checks/native_dynamic_recheck.json. Исходный независимый review и probes/evidence не редактировались, находятся в verification/r5_layout_output_review/. baseline_probe.json — исходное ошибочное поведение до исправления; оригинальный probe с его старыми assertions не используется как критерий исправления.

Подтверждённые проникновения сохранены: cylinder_barrel/cylinder_mount_front, tank/pump_motor, рамные сопряжения; на промежуточном ISOLATE inlet_gate/pocket_R (560000 мм³); B OPEN-LOCK guard_right/lock и lock/stop_support; B OPEN-STOP end_stop/guard_right и end_stop/stop_support. Эти записи и нативные объёмы присутствуют в сохранённых JSON. Касание коробок и положительное проникновение различены в независимых BRep-свидетельствах; автор не объявляет их разрешёнными контактами.

Исторический неуспешный итоговый прогон (экспорт изменённого STEP для отрицательного теста через makeCompound) сохранён в history/tool_regression_export_failure.json. Отрицательный fixture теперь экспортируется как перечень отдельных solids; исходные A/B и build_model.py не менялись. После исправления тестового генератора весь прогон повторён с exit 0. История исходного дефекта габаритов визуализационной сетки также сохранена, она не является текущим результатом PASS.

Реальный registry/COTS/models неизменны. Числа ASSUMED отдельно от UNKNOWN REV. Удержание, разгрузка, реальная выдача, нагрузки/прочность/безопасность UNKNOWN. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Требуются независимый RECHECK B01/B02 и отдельная последующая работа над самой геометрией; исходный review самих компоновок остаётся отрицательным для утверждения свободы пересечений.

---

## История исходной оценки C 6bb66a5 (не текущий статус review)

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
