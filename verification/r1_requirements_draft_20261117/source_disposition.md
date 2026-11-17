# Применимость всех 40 RAW полей

Численные значения остаются в frozen scoped RAW-кандидате; здесь только ID/revision/units/решение.
TARGET_PROPOSAL — предложенный ориентир, не approved engineering input.

| Source field @revision | Источник/PDF | Unit | Disposition | REQ | Квалификатор / ограничение |
|---|---|---|---|---|---|
| BPR_MOISTURE_MIN @1 | BP500/3 | 1 | OPEN_SOURCE_ISSUE | REQ-REV-02, REQ-REV-13 | BP500 задаёт намерение целевого окна; wet/dry база/метод UNKNOWN, численное инженерное использование заблокировано. |
| BPR_MOISTURE_MAX @1 | BP500/3 | 1 | OPEN_SOURCE_ISSUE | REQ-REV-02, REQ-REV-13 | BP500 задаёт намерение целевого окна; wet/dry база/метод UNKNOWN, численное инженерное использование заблокировано. |
| BPR_AMBIENT_MIN @1 | BP500/3 | K | TARGET_PROPOSAL | REQ-REV-13 | Кандидат области помещения по BP500; фактическая реализация REV, допуски/методы UNKNOWN. |
| BPR_AMBIENT_MAX @1 | BP500/3 | K | TARGET_PROPOSAL | REQ-REV-13 | Кандидат области помещения по BP500; фактическая реализация REV, допуски/методы UNKNOWN. |
| BPR_SUPPLY_VOLTAGE @1 | BP500/3 | V | TARGET_PROPOSAL | REQ-REV-07 | Кандидат будущего подключения адаптируемой площадки; не подтверждение потребления/защиты/готовности. |
| BPR_SUPPLY_FREQUENCY @1 | BP500/3 | Hz | TARGET_PROPOSAL | REQ-REV-07 | Кандидат будущего подключения адаптируемой площадки; не подтверждение потребления/защиты/готовности. |
| BPR_SUPPLY_CURRENT @1 | BP500/3 | A | TARGET_PROPOSAL | REQ-REV-07 | Кандидат будущего подключения адаптируемой площадки; не подтверждение потребления/защиты/готовности. |
| BPR_MOTOR_COUNT @1 | BP500/3 | 1 | REFERENCE_CONTEXT | REQ-REV-07, REQ-REV-08, REQ-REV-17 | Референтное исполнение привода; число/фазы/скорость не выбирают собственный двигатель, архитектуру или BOM. |
| BPR_INSTALLED_POWER @1 | BP500/3 | W | OPEN_SOURCE_ISSUE | REQ-REV-07, REQ-REV-08 | Сохранить опубликованные total и состав мощностей раздельно; SOURCE-POWER не разрешён, собственный бюджет не вычислять. |
| BPR_MAIN_MOTOR_POWER @1 | BP500/3 | W | OPEN_SOURCE_ISSUE | REQ-REV-07, REQ-REV-08 | Сохранить опубликованные total и состав мощностей раздельно; SOURCE-POWER не разрешён, собственный бюджет не вычислять. |
| BPR_INFEED_MOTORS_POWER @1 | BP500/3 | W | OPEN_SOURCE_ISSUE | REQ-REV-07, REQ-REV-08 | Сохранить опубликованные total и состав мощностей раздельно; SOURCE-POWER не разрешён, собственный бюджет не вычислять. |
| BPR_COOLING_POWER @1 | BP500/3 | W | OPEN_SOURCE_ISSUE | REQ-REV-07, REQ-REV-08 | Сохранить опубликованные total и состав мощностей раздельно; SOURCE-POWER не разрешён, собственный бюджет не вычислять. |
| BPR_MAIN_MOTOR_PHASES @1 | BP500/3 | 1 | REFERENCE_CONTEXT | REQ-REV-07, REQ-REV-08, REQ-REV-17 | Референтное исполнение привода; число/фазы/скорость не выбирают собственный двигатель, архитектуру или BOM. |
| BPR_MAIN_MOTOR_SPEED @1 | BP500/3 | Hz | REFERENCE_CONTEXT | REQ-REV-07, REQ-REV-08, REQ-REV-17 | Референтное исполнение привода; число/фазы/скорость не выбирают собственный двигатель, архитектуру или BOM. |
| BPR_CYLINDER_COUNT @1 | BP500/3 | 1 | REFERENCE_CONTEXT | REQ-REV-08, REQ-REV-15, REQ-REV-17 | Конфигурация референса; число/ёмкость/фильтрация не выбирают архитектуру и исполнение COTS REV. |
| BPR_PUMP_COUNT @1 | BP500/3 | 1 | REFERENCE_CONTEXT | REQ-REV-08, REQ-REV-15, REQ-REV-17 | Конфигурация референса; число/ёмкость/фильтрация не выбирают архитектуру и исполнение COTS REV. |
| BPR_HYDRAULIC_PRESSURE_MAX @1 | BP500/3 | Pa | REFERENCE_CONTEXT | REQ-REV-08, REQ-REV-09 | Максимум гидравлического источника; не давление материала и не спектр нагрузок 42 состояний. |
| BPR_OIL_TANK_VOLUME @1 | BP500/3 | m^3 | REFERENCE_CONTEXT | REQ-REV-08, REQ-REV-15, REQ-REV-17 | Конфигурация референса; число/ёмкость/фильтрация не выбирают архитектуру и исполнение COTS REV. |
| BPR_FILTER_COUNT @1 | BP500/3 | 1 | REFERENCE_CONTEXT | REQ-REV-08, REQ-REV-15, REQ-REV-17 | Конфигурация референса; число/ёмкость/фильтрация не выбирают архитектуру и исполнение COTS REV. |
| BPR_FILTER_FROM @1 | BP500/3 | m | REFERENCE_CONTEXT | REQ-REV-08, REQ-REV-15, REQ-REV-17 | Конфигурация референса; число/ёмкость/фильтрация не выбирают архитектуру и исполнение COTS REV. |
| BPR_BUNKER_OPENING_1 @1 | BP500/4 | m | REFERENCE_CONTEXT | REQ-REV-01, REQ-REV-06, REQ-REV-16 | Компоновочный/ёмкостный ориентир; не готовая доза, поток, назначенные оси/геометрия REV. |
| BPR_BUNKER_OPENING_2 @1 | BP500/4 | m | REFERENCE_CONTEXT | REQ-REV-01, REQ-REV-06, REQ-REV-16 | Компоновочный/ёмкостный ориентир; не готовая доза, поток, назначенные оси/геометрия REV. |
| BPR_BUNKER_HEIGHT @1 | BP500/4 | m | REFERENCE_CONTEXT | REQ-REV-06, REQ-REV-15, REQ-REV-16 | Высота отверстия загрузки; не общая высота бункера. Собственная эргономика/доступы не определены. |
| BPR_BUNKER_VOLUME @1 | BP500/4 | m^3 | REFERENCE_CONTEXT | REQ-REV-01, REQ-REV-06, REQ-REV-16 | Компоновочный/ёмкостный ориентир; не готовая доза, поток, назначенные оси/геометрия REV. |
| BPR_BRIQUETTE_SIDE_1 @1 | BP500/4 | m | TARGET_PROPOSAL | REQ-REV-03 | Референтная геометрия изделия, не ход пуансона/полость CAD; допуски, пружинение и годность UNKNOWN. |
| BPR_BRIQUETTE_SIDE_2 @1 | BP500/4 | m | TARGET_PROPOSAL | REQ-REV-03 | Референтная геометрия изделия, не ход пуансона/полость CAD; допуски, пружинение и годность UNKNOWN. |
| BPR_BRIQUETTE_LENGTH_MIN @1 | BP500/4 | m | TARGET_PROPOSAL | REQ-REV-03 | Референтная геометрия изделия, не ход пуансона/полость CAD; допуски, пружинение и годность UNKNOWN. |
| BPR_BRIQUETTE_LENGTH_MAX @1 | BP500/4 | m | TARGET_PROPOSAL | REQ-REV-03 | Референтная геометрия изделия, не ход пуансона/полость CAD; допуски, пружинение и годность UNKNOWN. |
| BPR_THROUGHPUT_UPPER @1 | BP500/4 | 1/s | TARGET_PROPOSAL | REQ-REV-04 | Только up-to/material/settings-dependent ориентир; не гарантированный минимум, не вычислять массовый выпуск. |
| BPR_REFERENCE_BRIQUETTE_MASS @1 | BP500/4 | kg | REFERENCE_CONTEXT | REQ-REV-04 | Масса из условия декларации выпуска; не фиксированная масса каждого изделия и не масса дозы. |
| BPR_MACHINE_DIM_1 @1 | BP500/4 | m | REFERENCE_CONTEXT | REQ-REV-16 | Сравнение установленного габарита/комплектности; порядок источника не назначает оси REV и жёсткий предел площадки. |
| BPR_MACHINE_DIM_2 @1 | BP500/4 | m | REFERENCE_CONTEXT | REQ-REV-16 | Сравнение установленного габарита/комплектности; порядок источника не назначает оси REV и жёсткий предел площадки. |
| BPR_MACHINE_DIM_3 @1 | BP500/4 | m | REFERENCE_CONTEXT | REQ-REV-16 | Сравнение установленного габарита/комплектности; порядок источника не назначает оси REV и жёсткий предел площадки. |
| BPR_WITH_TABLE_DIM_1 @1 | BP500/4 | m | REFERENCE_CONTEXT | REQ-REV-16 | Сравнение установленного габарита/комплектности; порядок источника не назначает оси REV и жёсткий предел площадки. |
| BPR_MACHINE_MASS @1 | BP500/4 | kg | REFERENCE_CONTEXT | REQ-REV-09, REQ-REV-16 | Общая масса источника; не движущаяся масса, центр тяжести, опорные реакции или нагрузочные случаи. |
| BPR_COMPACTION_PRESSURE_LITERAL @1 | BP500/4 | Pa | OPEN_SOURCE_ISSUE | REQ-REV-03, REQ-REV-08 | Literal unit неоднозначна, SI value null сохранено; не предполагать kgf и не получать силу. |
| SUPR_E55_MOISTURE_MIN @1 | E55/14 | 1 | REFERENCE_CONTEXT | REQ-REV-02, REQ-REV-13 | Сравнение источника E55/WEIMA; не заменять/усреднять BP500 окно, база и метод UNKNOWN. |
| SUPR_E55_MOISTURE_MAX @1 | E55/14 | 1 | REFERENCE_CONTEXT | REQ-REV-02, REQ-REV-13 | Сравнение источника E55/WEIMA; не заменять/усреднять BP500 окно, база и метод UNKNOWN. |
| SUPR_WEIMA_MOISTURE_MIN @1 | WEIMA/7 | 1 | REFERENCE_CONTEXT | REQ-REV-02, REQ-REV-13 | Сравнение источника E55/WEIMA; не заменять/усреднять BP500 окно, база и метод UNKNOWN. |
| SUPR_WEIMA_MOISTURE_MAX @1 | WEIMA/7 | 1 | REFERENCE_CONTEXT | REQ-REV-02, REQ-REV-13 | Сравнение источника E55/WEIMA; не заменять/усреднять BP500 окно, база и метод UNKNOWN. |
