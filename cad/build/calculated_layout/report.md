# Расчётно связанная исследовательская компоновка REV A/B

**Не утверждённая конструкция. G1 OPEN.** BASE_A/BASE_B fixed-budget из PR #39. Command execution / artifact consistency / test expectation / scene geometry / physical feasibility разделены. Фактические сцены не становятся пригодными при зелёном CLI или совпадении отрицательного теста.

## Выдача и возврат

| Вариант / случай | Граница R3 | Фактический выход CAD | Link WORK/EJECT | Непрерывность | Возврат инструментов | READY | Геометрия всей сцены |
|---|---|---|---|---|---|---|---|
| A/sufficient | GEOMETRY_SUFFICIENT | SHORT_STROKE | [{'phase': 'A-WORK', 'link': 'LINK_CONFIRMED'}, {'phase': 'A-EJECT', 'link': 'LINK_CONFIRMED'}] | CONTINUOUS | RESTORED_TOOLS_ONLY | NOT_CONFIRMED | BLOCKED |
| A/short | SHORT_STROKE | SHORT_STROKE | [{'phase': 'A-WORK', 'link': 'LINK_CONFIRMED'}, {'phase': 'A-EJECT', 'link': 'LINK_CONFIRMED'}] | CONTINUOUS | RESTORED_TOOLS_ONLY | NOT_CONFIRMED | BLOCKED |
| A/collision | GEOMETRY_SUFFICIENT | SHORT_STROKE | [{'phase': 'A-WORK', 'link': 'LINK_CONFIRMED'}, {'phase': 'A-EJECT', 'link': 'LINK_CONFIRMED'}] | CONTINUOUS | RESTORED_TOOLS_ONLY | NOT_CONFIRMED | BLOCKED |
| A/unknown | INDETERMINATE | INDETERMINATE | [{'phase': 'A-WORK', 'link': 'LINK_CONFIRMED'}, {'phase': 'A-EJECT', 'link': 'LINK_INDETERMINATE'}] | INDETERMINATE | RESTORED_TOOLS_ONLY | NOT_CONFIRMED | BLOCKED |
| B/sufficient | GEOMETRY_SUFFICIENT | SHORT_STROKE | [{'phase': 'B-WORK', 'link': 'LINK_CONFIRMED'}, {'phase': 'B-EJECT', 'link': 'LINK_CONFIRMED'}] | CONTINUOUS | RESTORED_TOOLS_ONLY | NOT_CONFIRMED | BLOCKED |
| B/short | SHORT_STROKE | SHORT_STROKE | [{'phase': 'B-WORK', 'link': 'LINK_CONFIRMED'}, {'phase': 'B-EJECT', 'link': 'LINK_CONFIRMED'}] | CONTINUOUS | RESTORED_TOOLS_ONLY | NOT_CONFIRMED | BLOCKED |
| B/collision | GEOMETRY_SUFFICIENT | SHORT_STROKE | [{'phase': 'B-WORK', 'link': 'LINK_CONFIRMED'}, {'phase': 'B-EJECT', 'link': 'LINK_CONFIRMED'}] | CONTINUOUS | RESTORED_TOOLS_ONLY | NOT_CONFIRMED | BLOCKED |
| B/unknown | INDETERMINATE | INDETERMINATE | [{'phase': 'B-WORK', 'link': 'LINK_CONFIRMED'}, {'phase': 'B-EJECT', 'link': 'LINK_INDETERMINATE'}] | INDETERMINATE | RESTORED_TOOLS_ONLY | NOT_CONFIRMED | BLOCKED |

Расчёт R3 проверяет выдачу за chamber_end + clearance. Прежние выходные плоскости CAD перенесены вместе с камерой: канал A сохраняет длину, B сохраняет выходной отступ. При заданном ходе оболочка не проходит фактический выход. Поэтому REMOVE отсутствует, изделие остаётся в сцене, восстановление рабочего READY не подтверждено. Движения возврата/закрытия — диагностические пробы, не разрешение выполнять их на прессе. Возврат инструмента не является полным циклом.

Жёсткий product с самого начала является surrogate готового брикета. Отдельный DoseEnvelope показывает занимаемый дозой объём; уплотнение/деформация/переход сырьё→продукт не реализованы и остаются INDETERMINATE. Нулевые проектные зазоры на нагруженной грани — гипотеза R3, не допуск/подтверждённое сопряжение.

## Сервисы — весь заявленный путь и все пары

| Вариант / путь | Геометрия всей сцены | Service path | Непрерывность | Возврат | Ограниченный успех | Физика |
|---|---|---|---|---|---|---|
| A/service_gate | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_cylinder_barrel | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_rod | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_doser_slide | BLOCKED | BLOCKED | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_clamp_L | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_cylinder_module | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_fp_doser_retract_lift | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_fp_motor | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_fp_powerpack_module | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| A/service_fp_tank_after_motor_park | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_gate | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_cylinder_barrel | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_rod | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_doser_slide | BLOCKED | BLOCKED | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_lock | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_end_stop | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_portal | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_cylinder_module | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_fp_doser_retract_lift | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_fp_motor | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_fp_powerpack_module | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |
| B/service_fp_tank_after_motor_park | INDETERMINATE | INDETERMINATE | CONTINUOUS | RESTORED | False | INDETERMINATE |

Прежние шесть native BLOCKED прямого UP и ограниченный L-путь сохранены в старом пакете без изменения. Новые статусы выше рассчитаны заново, не наследуются из акта прежней геометрии. Физическая выполнимость L-пути INDETERMINATE в обоих пакетах. Полные прежние и новые проблемы перечислены в remaining_issues.json/md и native_interfaces.json.

## Предел готовности

Камера/продукт/осевые ходы/минимальный bore/шток и новая циклограмма связаны с точными расчётными источниками. Рама, опоры, внешний корпус цилиндра, габариты станции и крепления сохраняют исследовательские предположения; преобразованные стыки требуют проверки/данных. Потерянное сопряжение или пересечение остаются видимыми, не выдаются за силовой путь. Истинные COTS/фланцы/порты/массы/риггинг/нагрузки/прочность/безопасность UNKNOWN. Открытие B INDETERMINATE независимо от результатов условного перемещения.

Нет утверждения архитектуры/ТЗ/оборудования или приёмки пресса. Физические испытания NOT_RUN. Whole press READY INDETERMINATE; независимый OUTPUT review NOT_RUN. Все размеры ASSUMED либо CALCULATED из ASSUMED, без новых VERIFIED/LOCKED.

## Файлы и метод

Сохранены все неупорядоченные пары на каждом участке и замкнутый интервал движения: A/scenes.json.gz, B/scenes.json.gz, pair_checks.jsonl.gz и results.json. Exact boxes/linear translations — прежний frozen engine/strict affine inequalities. Для криволинейной формы отсутствие positive-volume на bounds доказывает разделение; перекрытие оболочек остаётся INDETERMINATE, positive native samples лишь свидетельствуют отдельное проникновение. Вращение/гибкие связи/неописанное условие не дают CLEAR. Все QueryVolumes проверяются в сохранённом native CAD до/после recompute.

Таблицы parameter_mapping.md / source_application.json — все 44 привязки; all_parameter_changes.md и */parameter_changes.json — все изменения, formulas/provenance и округление. Генерация отдельно от readonly verifier, команды в cad/calculated_layout/README.md.
