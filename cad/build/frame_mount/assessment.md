# Исследовательская рамная/монтажная группа A/B — результат R4

Самопроверка, REQUIRES_INDEPENDENT_R5. Задача T-r4-layout-build-01; owner_session r4-linked-20261111. Результат продолжает C 66924aed1cb2d193b9883d2140d85560b1e4b0cb с учётом акта 04efe5703e339112b7d007665b9f3672f0572d37. Интеграции в main и принятия сборки нет.

## Область и причина

Конечный реестр до изменения: verification/r4_frame_mount/before/inventory.json/md, 409 пар. Выбрана связная группа поперечин, боковых рельсов и опор цилиндра, включая стык задней опоры и выходной опоры с поперечинами. Остальные узлы не исправлялись. Все прежние ID сохранены, добавлены две щеки U-опоры, её поперечная опора и шесть стоек от основания к верхним рельсам.

Поперечины размещены между внутренними гранями рельсов с совпадающими верхними плоскостями. Нижняя плоскость исключает внедрение в выходную опору. Задняя опора поднята до опорной плоскости поперечины с сохранением покрытия заднего торца цилиндра. Передняя сплошная плита перенесена к торцу цилиндра и разделена на нижний исходный элемент и две новые щеки; открытый верх сохраняет вертикальный коридор штока. Все тела моделируются и проверяются, исключений пар и удаления старых тел нет.

## Геометрия до/после

В changes.json — фактические границы SI и ссылки ID@revision. Все численные входы ASSUMED, отдельный inputs.assumed.json rev7 заранее зафиксирован на 17501de. Реальные registry/COTS неизменны. Следующие объёмы — результаты native Part.common, не допуски и не данные REV.

| Вариант | Пара | До, мм³ | После, мм³ |
|---|---|---:|---:|
| A | crossbar0 / side_rail_L | 2016000 | 0 |
| A | crossbar0 / side_rail_R | 2016000 | 0 |
| A | crossbar1 / side_rail_L | 2016000 | 0 |
| A | crossbar1 / side_rail_R | 2016000 | 0 |
| A | crossbar2 / side_rail_L | 2016000 | 0 |
| A | crossbar2 / side_rail_R | 2016000 | 0 |
| A | crossbar0 / cylinder_mount_rear | 1360000 | 0 |
| A | crossbar2 / output_support | 13824000 | 0 |
| A | cylinder_barrel / cylinder_mount_front | 15205308.4 | 0 |
| B | crossbar0 / side_rail_L | 2016000 | 0 |
| B | crossbar0 / side_rail_R | 2016000 | 0 |
| B | crossbar1 / side_rail_L | 2016000 | 0 |
| B | crossbar1 / side_rail_R | 2016000 | 0 |
| B | crossbar2 / side_rail_L | 2016000 | 0 |
| B | crossbar2 / side_rail_R | 2016000 | 0 |
| B | crossbar0 / cylinder_mount_rear | 1360000 | 0 |
| B | crossbar2 / output_support | 13824000 | 0 |
| B | cylinder_barrel / cylinder_mount_front | 15205308.4 | 0 |

Виды: frame_before_after.svg/png; crossbar_before_after.svg/png; seat_before_after.svg/png; service_before_after.svg/png. Это проекции нативных тел разных осевых плоскостей, не самостоятельное доказательство коллизии по наложению проекций. Общие виды, реальные сечения, FCStd и STEP в A/ и B/. Скрытые для обзора ограждения в общих изображениях сохранены в моделях и матрицах.

## Сопряжения и условный силовой путь

interfaces.json: 58 записей (A/B), нулевой нативный общий объём и положительная площадь пересечения именно контактных граней. Минимальная фактическая площадь 12000 мм². Эта проверка относится к исходной сборочной позиции; при сервисном движении контакт может исчезать. Отсутствие объёмного проникновения на всём ходе доказывается отдельно. Нулевой common volume сам по себе не принят как доказательство связи.

Условные цепи: задний торец цилиндра → задняя опора → crossbar0 → оба side_rail → upper_post → base; передний торец → нижний элемент/щеки U → cylinder_seat_bridge → рельсы → стойки → основания. Сохранена условная реакционная цепь B end_stop → lock → две стойки → мост → рельсы; неизменны геометрия подачи/отсечения/выхода, оси, цилиндр/шток и рабочие ходы. Проверены открытие/перекрытие подающего окна.

Передача сдвига и момента на торцевых стыках требует будущих закреплений. Болты/швы, фланцы цилиндра, удержание от радиального смещения, предварительный натяг и жёсткость UNKNOWN. Положительная площадь геометрического контакта не подтверждает силовую способность. Концептуальный силовой контур не объявляется рассчитанным или конструктивно завершённым.

## Полный ход, возврат и сервис

Матрицы включают ВСЕ пары каждого этапа: 346709 строк, coverage errors 0. Нет новых исключений. Из 114184 строк, затрагивающих изменённые тела, точные линейные неравенства дают: {"NO_POSITIVE_VOLUME_ON_INTERVAL": 114156, "INDETERMINATE": 28}. Все намеренно неизвестные движения изделия остаются INDETERMINATE. Для известных поддерживаемых движений отсутствие положительного объёма охватывает весь интервал, включая границы, а не только кадры. Консервативное отсутствие перекрытия bounding boxes также исключает объёмное пересечение содержащихся в них цилиндров; отсутствие коллизии по одним нативным выборкам не утверждается.

Регрессия ранее устранённых gate/pocket/lock/end_stop/guard/portal проникновений: 658 строк, {"NO_POSITIVE_VOLUME_ON_INTERVAL": 658}. Исторические нативные контрпримеры R5 воспроизведены в geometry_evidence.json. Отдельно проверенные guard/pump_motor и portal_bridge/output_support сохраняются в полном потоке classifications.jsonl.gz.

Сервис цилиндра отдельно, штока отдельно и цилиндр+шток вместе: 3672 строк, {"NO_POSITIVE_VOLUME_ON_INTERVAL": 3672}. Взяты прежний вход service_lift и точный UP/DOWN, без изменения траектории для скрытия конфликтов. В 14 последовательностях сохранены все тела, непрерывность и восстановление исходных координат. Это геометрические исследовательские последовательности: снятие крепежа, отключение гидравлики, инструменты, стропы, устойчивость и безопасное выполнение UNKNOWN.

| Вариант | Сервис | Непрерывность/возврат | Строки конфликтов движущихся тел |
|---|---|---|---:|
| A | service_cylinder_module | CONTINUOUS / True | 0 |
| B | service_cylinder_module | CONTINUOUS / True | 0 |
| A | service_gate | CONTINUOUS / True | 0 |
| A | service_cylinder_barrel | CONTINUOUS / True | 0 |
| A | service_rod | CONTINUOUS / True | 0 |
| A | service_doser_slide | CONTINUOUS / True | 6 |
| A | service_clamp_L | CONTINUOUS / True | 0 |
| B | service_gate | CONTINUOUS / True | 0 |
| B | service_cylinder_barrel | CONTINUOUS / True | 0 |
| B | service_rod | CONTINUOUS / True | 0 |
| B | service_doser_slide | CONTINUOUS / True | 6 |
| B | service_lock | CONTINUOUS / True | 0 |
| B | service_end_stop | CONTINUOUS / True | 0 |
| B | service_portal | CONTINUOUS / True | 0 |

Восемь исходных limited-cycle сценариев проверены strict oracle и отдельными assertions; их статусы отделены от exit code команды и готовности всего пресса.

| Вариант | Сценарий | Ожидание теста | Геометрический исход ограниченной сцены |
|---|---|---|---|
| A | sufficient | True | LIMITED_READY_CONFIRMED |
| A | short | True | BLOCKED |
| A | collision | True | BLOCKED |
| A | unknown | True | INDETERMINATE |
| B | sufficient | True | LIMITED_READY_CONFIRMED |
| B | short | True | BLOCKED |
| B | collision | True | BLOCKED |
| B | unknown | True | INDETERMINATE |

Limited sufficient требует фактически подтверждённой связи, разрешённой выдачи, непрерывности, валидного REMOVE и возврата READY. Его успех относится к прежнему подмножеству пути; не к всей сборке.

## Остаток и предел готовности

Конечный перечень после изменения — inventory/inventory.md/json: 463 непустых пар, {"INDETERMINATE": 368, "CONDITIONAL_MATING": 73, "NATIVE_PENETRATION": 20, "CONDITIONAL_ENVELOPE_INTERSECTION": 2}. Для каждой пары сохранены исходные классы, все контексты, нативные свидетельства и отдельно отрицательные controls. CONDITIONAL_MATING — предполагаемое геометрическое сопряжение с описанным основанием, не утверждённая посадка/крепление. Сервисные нативные выборки не заменяют непрерывное доказательство. Известные положительные проникновения ниже не объявлены допустимыми сопряжениями.

| ID | Вариант | Оставшееся нативное проникновение | Свидетельство, мм³ |
|---|---|---|---:|
| FM-0093 | A | doser_floor_front / pocket_front | 416000 |
| FM-0096 | A | doser_floor_left / pocket_L | 320000 |
| FM-0104 | A | doser_floor_rear / pocket_rear | 416000 |
| FM-0107 | A | doser_floor_right / pocket_R | 320000 |
| FM-0110 | A | doser_front / hopper_floor_front | 1100000 |
| FM-0112 | A | doser_rear / hopper_floor_rear | 1100000 |
| FM-0114 | A | doser_slide / hopper_R | 480000 |
| FM-0117 | A | doser_slide / hopper_floor_right | 6200000 |
| FM-0119 | A | doser_slide / receiving_rim_right | 240000 |
| FM-0187 | A | hydraulic_tank / pump_motor | 7248108.07 |
| FM-0305 | B | doser_floor_front / pocket_front | 416000 |
| FM-0308 | B | doser_floor_left / pocket_L | 320000 |
| FM-0316 | B | doser_floor_rear / pocket_rear | 416000 |
| FM-0319 | B | doser_floor_right / pocket_R | 320000 |
| FM-0322 | B | doser_front / hopper_floor_front | 1100000 |
| FM-0324 | B | doser_rear / hopper_floor_rear | 1100000 |
| FM-0326 | B | doser_slide / hopper_R | 480000 |
| FM-0329 | B | doser_slide / hopper_floor_right | 6200000 |
| FM-0331 | B | doser_slide / receiving_rim_right | 240000 |
| FM-0401 | B | hydraulic_tank / pump_motor | 7248108.07 |

Следующие связные группы ещё OPEN: монтажные стыки дозатора/кармана и бункера; извлечение дозатора через hopper_R/hopper_floor_right/receiving_rim_right; hydraulic_tank/pump_motor. Остальные непредписанные касания и численно неразличимые контакты — INDETERMINATE, коммуникационные/маршрутные оболочки — отдельный класс, реальное внутреннее устройство/прочность/зазоры/допуски/крепёж/нормы доступа UNKNOWN. Полный конечный список не сокращён до этих примеров.

FCStd/STEP фактически проверены frozen native adapter, включая все QueryVolumes. Повтор построения воспроизвёл семантические manifests и восемь PNG. Все 23 прежних Python-модуля неизменны относительно 66924ae; прежние 83 теста и пять новых тестов supplementary interval audit прошли. Новые run/inventory/evidence/report/figures/verify файлы — отдельная область независимой проверки. Hardcoded metadata frozen check_layout о прежней базе не являются provenance новой редакции; текущие хэши в run.json и publication_manifest.json.

**Весь пресс: BLOCKED оставшимися ASSUMED-проникновениями; READY INDETERMINATE.** Готов только пакет ограниченной геометрической коррекции для независимого R5. Задача IN_REVIEW, не DONE. Реальные размеры/ходы/нагрузки/сырьё/физика/безопасность UNKNOWN, архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 OPEN.

## Воспроизведение

Из корня репозитория, материализовав Git LFS:

```bash
git lfs pull
/usr/bin/python3 cad/frame_mount/run.py
/usr/bin/python3 cad/frame_mount/geometry_evidence.py
/usr/bin/python3 cad/frame_mount/figures.py
/usr/bin/python3 cad/frame_mount/report.py
/usr/bin/python3 cad/frame_mount/verify_output.py
```

FreeCAD 1.0.0/Part и Python 3.13.5; launcher /usr/bin/python3, не падающий freecadcmd. Только входной путь внутри текущего ROOT подтверждён: предупреждение R5 о внешних путях сохраняется. Самостоятельно выбирать новые реальные параметры нельзя. Исходные сохранённые FCStd/STEP не обязаны совпасть побайтно после повторного сохранения (служебные данные); semantic/native соответствие проверяется заново.
