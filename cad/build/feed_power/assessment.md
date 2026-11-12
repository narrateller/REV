# Дозатор и гидростанция — фактический сервисный исход

R4 self-check, независимый RECHECK NOT_RUN. Расчёт выполнен заново из текущих service state/time, всех обязательных пар, состава движения и declared plan. Команда/тестовое ожидание/пригодность пути — разные результаты. Физическая выполнимость всегда INDETERMINATE, G1 OPEN.

Выполнение расчёта: COMPLETED; совпадение с обязательными ожиданиями: PASS. Геометрические исходы: {'CONFIRMED_NO_POSITIVE_VOLUME': 20, 'BLOCKED': 2}; общие сервисные исходы: {'INDETERMINATE': 20, 'BLOCKED': 2}.

Подтверждённая коллизия блокирует успех даже вместе с unknown. Неподдержанный/неизвестный обязательный метод, участок, пара или boundary не дают подтверждённого геометрического пути. Ни совпадение отрицательного теста, ни exit 0 не означают физическую пригодность.

## Текущие сервисные сцены

| Вариант | Сцена | Геометрия | Метод | План | Continuity / return | Общий сервис | Физика | Ожидание теста |
|---|---|---|---|---|---|---|---|---|
| A | service_cylinder_module | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_cylinder_module | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| A | service_fp_doser_retract_lift | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| A | service_fp_motor | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| A | service_fp_powerpack_module | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| A | service_fp_tank_after_motor_park | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_fp_doser_retract_lift | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_fp_motor | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_fp_powerpack_module | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_fp_tank_after_motor_park | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| A | service_gate | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| A | service_cylinder_barrel | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| A | service_rod | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| A | service_doser_slide | BLOCKED | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | BLOCKED | INDETERMINATE | True |
| A | service_clamp_L | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_gate | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_cylinder_barrel | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_rod | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_doser_slide | BLOCKED | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | BLOCKED | INDETERMINATE | True |
| B | service_lock | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_end_stop | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |
| B | service_portal | CONFIRMED_NO_POSITIVE_VOLUME | SUPPORTED | CONFIRMED | CONTINUOUS / RESTORED | INDETERMINATE | INDETERMINATE | True |

Все stage/pair digests, ошибки/неизвестности метода/плана/непрерывности/возврата и current collision intervals — service_report.json. Это свежий расчёт, не копия сохранённого assessment.

## Доказанные коллизии текущих сервисных путей

| Вариант | Сцена | Фаза | Пара | Нормированный интервал положительного перекрытия |
|---|---|---|---|---|
| A | service_doser_slide | A-SERVICE-doser_slide-1 | doser_slide / hopper_R | ['6/65', '129/130'] |
| A | service_doser_slide | A-SERVICE-doser_slide-1 | doser_slide / hopper_floor_right | ['7/130', '12/65'] |
| A | service_doser_slide | A-SERVICE-doser_slide-1 | doser_slide / receiving_rim_right | ['9/10', '1'] |
| A | service_doser_slide | A-SERVICE-doser_slide-2 | doser_slide / hopper_R | ['1/130', '59/65'] |
| A | service_doser_slide | A-SERVICE-doser_slide-2 | doser_slide / hopper_floor_right | ['53/65', '123/130'] |
| A | service_doser_slide | A-SERVICE-doser_slide-2 | doser_slide / receiving_rim_right | ['0', '1/10'] |
| B | service_doser_slide | B-SERVICE-doser_slide-1 | doser_slide / hopper_R | ['6/65', '129/130'] |
| B | service_doser_slide | B-SERVICE-doser_slide-1 | doser_slide / hopper_floor_right | ['7/130', '12/65'] |
| B | service_doser_slide | B-SERVICE-doser_slide-1 | doser_slide / receiving_rim_right | ['9/10', '1'] |
| B | service_doser_slide | B-SERVICE-doser_slide-2 | doser_slide / hopper_R | ['1/130', '59/65'] |
| B | service_doser_slide | B-SERVICE-doser_slide-2 | doser_slide / hopper_floor_right | ['53/65', '123/130'] |
| B | service_doser_slide | B-SERVICE-doser_slide-2 | doser_slide / receiving_rim_right | ['0', '1/10'] |

## Сохранённая геометрия и before/after исходного CAD

Эта таблица относится к сохранённым native моделям исходной компоновки, а не автоматически к произвольному изменённому сервисному пути. Подменённая траектория оценивается таблицами выше. Actual FCStd/STEP/QueryVolumes и соответствие всех сохранённых доказательств обязан проверить отдельный readonly verifier. Геометрические изображения показывают исходную компоновку и сами не подтверждают текущую траекторию.

| Вариант | Пара | Native до, мм³ | Native после, мм³ | Область |
|---|---|---:|---:|---|
| A | doser_floor_front / pocket_front | 416000 | 0 | STATIC_PENETRATION_REMOVED |
| A | doser_floor_left / pocket_L | 320000 | 0 | STATIC_PENETRATION_REMOVED |
| A | doser_floor_rear / pocket_rear | 416000 | 0 | STATIC_PENETRATION_REMOVED |
| A | doser_floor_right / pocket_R | 320000 | 0 | STATIC_PENETRATION_REMOVED |
| A | doser_front / hopper_floor_front | 1100000 | 0 | STATIC_PENETRATION_REMOVED |
| A | doser_rear / hopper_floor_rear | 1100000 | 0 | STATIC_PENETRATION_REMOVED |
| A | doser_slide / hopper_R | 480000 | 480000 | LEGACY_VERTICAL_BLOCKED_NOT_RELABELED |
| A | doser_slide / hopper_floor_right | 6200000 | 6200000 | LEGACY_VERTICAL_BLOCKED_NOT_RELABELED |
| A | doser_slide / receiving_rim_right | 240000 | 240000 | LEGACY_VERTICAL_BLOCKED_NOT_RELABELED |
| A | hydraulic_tank / pump_motor | 7248108.07 | 0 | STATIC_PENETRATION_REMOVED |
| B | doser_floor_front / pocket_front | 416000 | 0 | STATIC_PENETRATION_REMOVED |
| B | doser_floor_left / pocket_L | 320000 | 0 | STATIC_PENETRATION_REMOVED |
| B | doser_floor_rear / pocket_rear | 416000 | 0 | STATIC_PENETRATION_REMOVED |
| B | doser_floor_right / pocket_R | 320000 | 0 | STATIC_PENETRATION_REMOVED |
| B | doser_front / hopper_floor_front | 1100000 | 0 | STATIC_PENETRATION_REMOVED |
| B | doser_rear / hopper_floor_rear | 1100000 | 0 | STATIC_PENETRATION_REMOVED |
| B | doser_slide / hopper_R | 480000 | 480000 | LEGACY_VERTICAL_BLOCKED_NOT_RELABELED |
| B | doser_slide / hopper_floor_right | 6200000 | 6200000 | LEGACY_VERTICAL_BLOCKED_NOT_RELABELED |
| B | doser_slide / receiving_rim_right | 240000 | 240000 | LEGACY_VERTICAL_BLOCKED_NOT_RELABELED |
| B | hydraulic_tank / pump_motor | 7248108.07 | 0 | STATIC_PENETRATION_REMOVED |

В проверенном исходном CAD 14 static проникновений устранены; 6 native legacy-UP пар BLOCKED сохранены. Нельзя объявить эти шесть устранёнными по успешному тестовому ожиданию. Полный геометрический diff/ID@revision: changes.json и cad/feed_power/change_plan.json. Нативные модели A/B, STEP, PNG/SVG/PDF и before/after виды сохранены.

62 условных nominal interfaces не подтверждают реальные болты/швы/фланцы, радиальную фиксацию, tank wall или несущую способность. Путь сырья/номинальное окно и рабочие ходы сохраняются в исходном CAD; реальные подача/сырьё/физика UNKNOWN.

Конечный baseline inventory — inventory/inventory.json/md, исходные классы/контексты не удаляются. Достоверность current classifications, interval_rows, assessment и их соответствие текущим сценам проверяются пересчётом, не только внешним manifest hash.

**Весь пресс не принят, READY INDETERMINATE.** Архитектура/ТЗ не утверждены, размеры ASSUMED, реальные параметры UNKNOWN, физические испытания NOT_RUN, G1 OPEN.

## Команды

```bash
/usr/bin/python3 -B cad/feed_power/service_semantics.py
/usr/bin/python3 -B cad/feed_power/generate.py --reanalyze
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
```

Reanalysis — явная генерация новых derived результатов из сохранённых poses, без изменения CAD. Полный build: generate.py без --reanalyze. Verifier ничего не исправляет/не пишет, только JSON stdout/exit. Перед воспроизведением сохранять исходный C.
