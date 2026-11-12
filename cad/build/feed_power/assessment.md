# Дозатор и гидростанция A/B — ограниченная исследовательская коррекция

R4 self-check, новый независимый OUTPUT review NOT_RUN. База a5d5bad6dd8928045512bca16836fd1d2544b7ca, RECHECK c2e96a58d7efd64ea3364b2bcbfb3f0642bbc430. Все размеры ASSUMED, реальные параметры UNKNOWN, G1 OPEN.

## Изменения и причины

Pocket collar поднятия не требует: его верхняя грань опущена до существующей нижней плоскости дозирующего кольца. Стенки дозатора укорочены до нижней плоскости hopper floor, расширены вдоль Y для поддержки извлечённого ползуна. Кольцо нормализовано до точных общих номинальных рёбер. Рабочий doser_slide, его ось и ход не менялись. Изменения до/после и ID@revision — changes.json/change_plan.json.

Outboard tray и guide разбиты вокруг прежнего вертикального коридора gate_service_cap; непрерывные боковины обходят этот коридор и поддерживают обе секции. Это условные геометрические связи: реальные крепёж, опора длинной консоли, жёсткость/зазоры и привод UNKNOWN. Наличие опорной поверхности не подтверждает её силовую способность.

Motor поднят над tank, сохраняет ось X/радиус/длину, опирается условными торцевыми гранями на две плиты. Плиты стоят на верхней грани tank. Tank смещён от ограждения, его низ связан через две опорные балки/кронштейна с base_R. Реальная конструкция стенки tank, фланцы, крепёж, масса и несущая способность UNKNOWN.

## Каждая из 20 прежних пар

| Вариант | Пара | Native до, мм³ | Native после в том же состоянии, мм³ | Решение |
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

**14 статических native проникновений устранены. Шесть проникновений на старом straight-UP сервисе остаются доказанными и BLOCKED.** Они не переименованы в INDETERMINATE и не исключены из матриц. Для дозатора предложена другая исследовательская последовательность на существующей оси Y: retract → lift → lower → return. Старый подъём через неподвижный hopper остаётся обязательным отрицательным контрпримером. Реальный дополнительный ход привода, условия отсоединения и безопасный подъём UNKNOWN, поэтому фактическая реализуемость нового сервиса INDETERMINATE.

## Сервис и регрессия

Motor извлекается/возвращается отдельно; powerpack поднимается вместе с tank/двумя motor plates; отдельный tank извлекается после подъёма и парковки motor/plates по Y, затем все тела возвращаются. Ни одно тело не удаляется lifecycle-событием. Никакого вывода о безопасном подъёме или реальной расстыковке нет.

Все пары каждого этапа сохранены: 638919 строк. Точный affine interval solver проверил 507043 критических строк; 878 прежних gate/portal target строк без положительного объёма. Все положительные критические строки относятся только к трём прежним doser/hopper парам A/B на явно BLOCKED прямом подъёме. Неизвестные control движения остаются INDETERMINATE.

| Вариант | Сервис | Continuity / return | Конфликтные строки движущихся тел |
|---|---|---|---:|
| A | service_cylinder_module | CONTINUOUS / True | 0 |
| B | service_cylinder_module | CONTINUOUS / True | 0 |
| A | service_fp_doser_retract_lift | CONTINUOUS / True | 0 |
| A | service_fp_motor | CONTINUOUS / True | 0 |
| A | service_fp_powerpack_module | CONTINUOUS / True | 0 |
| A | service_fp_tank_after_motor_park | CONTINUOUS / True | 0 |
| B | service_fp_doser_retract_lift | CONTINUOUS / True | 0 |
| B | service_fp_motor | CONTINUOUS / True | 0 |
| B | service_fp_powerpack_module | CONTINUOUS / True | 0 |
| B | service_fp_tank_after_motor_park | CONTINUOUS / True | 0 |
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

В новых 8 сервисах нет положительного перекрытия движущихся тел на полном ходе/возврате. Возврат координат сам по себе не исправляет старый blocked UP. Общие виды/STEP/FCStd A/B и три native profile before/after представлены рядом. Проекции разных плоскостей не самостоятельное доказательство коллизии.

## Сопряжения, сырьё и предел

62 условных номинальных интерфейсов: positive-area native face intersection и нулевой solid common; interfaces.json содержит причины. Это не утверждение физической посадки, крепежа или силовой способности. Frozen classifier не получил новых разрешающих исключений; непредписанные касания сохраняют INDETERMINATE в его полном потоке.

Вход после имеющихся дробления/просева, throat hopper → дозатор → pocket → прежнее окно gate/chamber и выход пресса сохраняются. Целевое номинальное central aperture сохранено; точные legacy дробные границы колец нормализованы и показаны в changes.json. Фактическое общее положительное окно и его точные границы пересчитываются в verifier JSON. Рабочие doser/punch/gate/lock/stop ходы не менялись. Реальные подача/включения/влажность/трение/зависание/герметичность/производительность UNKNOWN; присутствие ползуна в окне и транспорт сырья физически не моделируются.

Конечный реестр — inventory/inventory.md/json, все non-CLEAR пары с контекстами. Оставшиеся native пары:

| Вариант | Пара | Статус |
|---|---|---|
| A | doser_slide / hopper_R | BLOCKED legacy UP; реальная альтернативная service feasibility INDETERMINATE |
| A | doser_slide / hopper_floor_right | BLOCKED legacy UP; реальная альтернативная service feasibility INDETERMINATE |
| A | doser_slide / receiving_rim_right | BLOCKED legacy UP; реальная альтернативная service feasibility INDETERMINATE |
| B | doser_slide / hopper_R | BLOCKED legacy UP; реальная альтернативная service feasibility INDETERMINATE |
| B | doser_slide / hopper_floor_right | BLOCKED legacy UP; реальная альтернативная service feasibility INDETERMINATE |
| B | doser_slide / receiving_rim_right | BLOCKED legacy UP; реальная альтернативная service feasibility INDETERMINATE |

Остальные контакты отдельно: условные сопряжения (interfaces.json), conservative envelope intersections и INDETERMINATE — inventory/classes. Нативные положительные объёмы не объявляются допустимыми сопряжениями. Восемь cycle ожиданий проверены прежним strict oracle и verify_cycles; это прежнее ограниченное path-подмножество, не весь пресс.

Все 34 прежних Python-модуля неизменны. Новые адаптация/оркестрация/проверки cad/feed_power требуют отдельного R5 review. Исторические hardcoded metadata frozen checker не являются provenance новой редакции; актуальны inputs SHA/generation/publication manifest.

**Весь пресс не принят, READY INDETERMINATE.** Реальные размеры/нагрузки/крепления/сырьё/безопасность UNKNOWN, архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 OPEN.

## Воспроизведение

```bash
git lfs pull
/usr/bin/python3 -B cad/feed_power/generate.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
```

Генерация — явная запись; verifier только читает сохранённый пакет и печатает JSON/exit. Перед повторением сохранить исходный C. Stdout сохранять вне проверяемого каталога. FreeCAD 1.0.0/Part, Python 3.13.5, PIL/reportlab/PySide2.QtSvg.
