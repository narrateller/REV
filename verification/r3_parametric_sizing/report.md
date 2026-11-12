# Сценарии и результаты условного расчёта REV

Все наборы — выбранные what-if ASSUMED; сетка не имеет подтверждённой реалистичности или безопасных пределов. CALCULATED означает выполненную арифметику, а не измеренные свойства. G1 OPEN, оборудование/архитектура/ТЗ не утверждены, физические испытания NOT_RUN.

Входная и математическая постановка: [model.md](model.md). Полные 696 scalar outputs с ID/revision/единицей — [scenarios.csv](scenarios.csv), код — scripts/rev_parametric.py, отдельные манифесты — results/. Числа ниже округлены только для отображения; это не допуски. Встроенные точные пересчёты единиц не являются новыми проектными параметрами.

## Выбранные входы

Базовая нагруженная грань и σ унаследованы как условные интерпретации R2. Масса из рекламного reference не связана источником с выбранной длиной: их сочетание в нашей модели — новая явно условная гипотеза. Не переносить размер/массу/плотность в реальные данные REV.

| Вход | Базовое значение SI и ID |
|---|---|
| width | 0.15 m [R3_IN_WIDTH@1] |
| height | 0.06 m [R3_IN_HEIGHT@1] |
| product_length | 0.11 m [R3_IN_PRODUCT_LENGTH@1] |
| mass | 0.83 kg [R3_IN_MASS@1] |
| rho | 200 kg/m^3 [R3_IN_RHO@1] |
| phi | 0.8 1 [R3_IN_PHI@1] |
| sigma_start | 0 Pa [R3_IN_SIGMA_START@1] |
| sigma_end | 166713050 Pa [R3_IN_SIGMA_END@1] |
| kappa | 0.6 1 [R3_IN_KAPPA@1] |
| supply_work | 30000000 Pa [R3_IN_SUPPLY_WORK@1] |
| supply_eject | 10000000 Pa [R3_IN_SUPPLY_EJECT@1] |
| supply_return | 12000000 Pa [R3_IN_SUPPLY_RETURN@1] |
| back_forward | 1000000 Pa [R3_IN_BACK_FORWARD@1] |
| back_return | 1000000 Pa [R3_IN_BACK_RETURN@1] |
| channel_slide | 30000 N [R3_IN_CHANNEL_SLIDE@1] |
| channel_hold | 40000 N [R3_IN_CHANNEL_HOLD@1] |
| rebound | 10000 N [R3_IN_REBOUND@1] |
| guide | 2000 N [R3_IN_GUIDE@1] |
| seal | 5000 N [R3_IN_SEAL@1] |
| return_load | 10000 N [R3_IN_RETURN_LOAD@1] |
| eject_load_b | 20000 N [R3_IN_EJECT_LOAD_B@1] |
| eject_travel | 0.17 m [R3_IN_EJECT_TRAVEL@1] |
| clearance | 0.03 m [R3_IN_CLEARANCE@1] |
| eta_pump | 0.85 1 [R3_IN_ETA_PUMP@1] |
| eta_motor | 0.9 1 [R3_IN_ETA_MOTOR@1] |
| electric_limit | 30000 W [R3_IN_ELECTRIC_LIMIT@1] |
| leak_hold | 0 m^3/s [R3_IN_LEAK_HOLD@1] |
| t_approach | 1 s [R3_IN_T_APPROACH@1] |
| t_work | 2 s [R3_IN_T_WORK@1] |
| t_eject | 1 s [R3_IN_T_EJECT@1] |
| t_return | 2 s [R3_IN_T_RETURN@1] |
| t_hold | 1 s [R3_IN_T_HOLD@1] |
| t_aux_a | 1 s [R3_IN_T_AUX_A@1] |
| t_unload_b | 1 s [R3_IN_T_UNLOAD_B@1] |
| t_open_b | 1 s [R3_IN_T_OPEN_B@1] |

## Изолированные возмущения

BASE_A/BASE_B имеют одни численные геометрические и гидравлические входы, но разные силовые пути/вспомогательные действия. Неиспользуемое значение варианта не означает физического нуля другого варианта. Остальные наборы изменяют только перечисленные входы относительно базы своего варианта.

| Сценарий | Изменённые ASSUMED-входы |
|---|---|
| BASE_A | база выбранного варианта |
| BASE_B | база выбранного варианта |
| RHO_HALF_A | rho=100 kg/m^3 [R3_RHO_HALF_A_IN_RHO@1] |
| LOAD_HALF_A | sigma_end=83356525 Pa [R3_LOAD_HALF_A_IN_SIGMA_END@1] |
| LOAD_DOUBLE_A | sigma_end=333426100 Pa [R3_LOAD_DOUBLE_A_IN_SIGMA_END@1] |
| EJECT_DOUBLE_B | eject_travel=0.34 m [R3_EJECT_DOUBLE_B_IN_EJECT_TRAVEL@1] |
| TIME_HALF_A | t_approach=0.5 s [R3_TIME_HALF_A_IN_T_APPROACH@1]; t_work=1 s [R3_TIME_HALF_A_IN_T_WORK@1]; t_eject=0.5 s [R3_TIME_HALF_A_IN_T_EJECT@1]; t_return=1 s [R3_TIME_HALF_A_IN_T_RETURN@1] |
| BACK_HIGH_A | back_forward=5000000 Pa [R3_BACK_HIGH_A_IN_BACK_FORWARD@1] |

## Камера и нижние геометрические размеры цилиндра

| Сценарий | V камеры, L | S рабочего хода, mm | F peak, kN | D, mm | d, mm |
|---|---:|---:|---:|---:|---:|
| BASE_A | 5.187 [R3_BASE_A_CHAMBER_VOLUME@1] | 351.1 [R3_BASE_A_WORK_STROKE@1] | 1532.42 [R3_BASE_A_FORCE_WORK_PEAK@1] | 258.21 [R3_BASE_A_BORE@1] | 154.93 [R3_BASE_A_ROD@1] |
| BASE_B | 5.187 [R3_BASE_B_CHAMBER_VOLUME@1] | 351.1 [R3_BASE_B_WORK_STROKE@1] | 1502.42 [R3_BASE_B_FORCE_WORK_PEAK@1] | 255.68 [R3_BASE_B_BORE@1] | 153.41 [R3_BASE_B_ROD@1] |
| RHO_HALF_A | 10.375 [R3_RHO_HALF_A_CHAMBER_VOLUME@1] | 812.2 [R3_RHO_HALF_A_WORK_STROKE@1] | 1532.42 [R3_RHO_HALF_A_FORCE_WORK_PEAK@1] | 258.21 [R3_RHO_HALF_A_BORE@1] | 154.93 [R3_RHO_HALF_A_ROD@1] |
| LOAD_HALF_A | 5.187 [R3_LOAD_HALF_A_CHAMBER_VOLUME@1] | 351.1 [R3_LOAD_HALF_A_WORK_STROKE@1] | 782.21 [R3_LOAD_HALF_A_FORCE_WORK_PEAK@1] | 184.77 [R3_LOAD_HALF_A_BORE@1] | 110.86 [R3_LOAD_HALF_A_ROD@1] |
| LOAD_DOUBLE_A | 5.187 [R3_LOAD_DOUBLE_A_CHAMBER_VOLUME@1] | 351.1 [R3_LOAD_DOUBLE_A_WORK_STROKE@1] | 3032.83 [R3_LOAD_DOUBLE_A_FORCE_WORK_PEAK@1] | 362.96 [R3_LOAD_DOUBLE_A_BORE@1] | 217.78 [R3_LOAD_DOUBLE_A_ROD@1] |
| EJECT_DOUBLE_B | 5.187 [R3_EJECT_DOUBLE_B_CHAMBER_VOLUME@1] | 351.1 [R3_EJECT_DOUBLE_B_WORK_STROKE@1] | 1502.42 [R3_EJECT_DOUBLE_B_FORCE_WORK_PEAK@1] | 255.68 [R3_EJECT_DOUBLE_B_BORE@1] | 153.41 [R3_EJECT_DOUBLE_B_ROD@1] |
| TIME_HALF_A | 5.187 [R3_TIME_HALF_A_CHAMBER_VOLUME@1] | 351.1 [R3_TIME_HALF_A_WORK_STROKE@1] | 1532.42 [R3_TIME_HALF_A_FORCE_WORK_PEAK@1] | 258.21 [R3_TIME_HALF_A_BORE@1] | 154.93 [R3_TIME_HALF_A_ROD@1] |
| BACK_HIGH_A | 5.187 [R3_BACK_HIGH_A_CHAMBER_VOLUME@1] | 351.1 [R3_BACK_HIGH_A_WORK_STROKE@1] | 1532.42 [R3_BACK_HIGH_A_FORCE_WORK_PEAK@1] | 270.26 [R3_BACK_HIGH_A_BORE@1] | 162.16 [R3_BACK_HIGH_A_ROD@1] |

D/d — результат заданного κ и квазистатического неравенства сил. Это не рекомендованный размер, не серийный цилиндр и не проверка штока на устойчивость. Для всех наборов расчёт всей машины остаётся INDETERMINATE.

## Расход, мощность, энергия и бюджет времени

| Сценарий | Q supply peak, L/min | P electric peak, kW | E electric, kJ | T заданный, s | T с ограничением мощности, s |
|---|---:|---:|---:|---:|---:|
| BASE_A | 639.8 [R3_BASE_A_FLOW_PEAK@1] | 360.5 [R3_BASE_A_ELECTRIC_POWER_PEAK@1] | 1408.6 [R3_BASE_A_ELECTRIC_ENERGY@1] | 8.00 [R3_BASE_A_CYCLE_BUDGET@1] | 48.95 [R3_BASE_A_CYCLE_BUDGET_POWER_LIMITED@1] |
| BASE_B | 627.3 [R3_BASE_B_FLOW_PEAK@1] | 353.5 [R3_BASE_B_ELECTRIC_POWER_PEAK@1] | 1381.2 [R3_BASE_B_ELECTRIC_ENERGY@1] | 9.00 [R3_BASE_B_CYCLE_BUDGET@1] | 49.04 [R3_BASE_B_CYCLE_BUDGET_POWER_LIMITED@1] |
| RHO_HALF_A | 1275.9 [R3_RHO_HALF_A_FLOW_PEAK@1] | 834.0 [R3_RHO_HALF_A_ELECTRIC_POWER_PEAK@1] | 2895.3 [R3_RHO_HALF_A_ELECTRIC_ENERGY@1] | 8.00 [R3_RHO_HALF_A_CYCLE_BUDGET@1] | 98.51 [R3_RHO_HALF_A_CYCLE_BUDGET_POWER_LIMITED@1] |
| LOAD_HALF_A | 327.6 [R3_LOAD_HALF_A_FLOW_PEAK@1] | 184.6 [R3_LOAD_HALF_A_ELECTRIC_POWER_PEAK@1] | 721.3 [R3_LOAD_HALF_A_ELECTRIC_ENERGY@1] | 8.00 [R3_LOAD_HALF_A_CYCLE_BUDGET@1] | 26.04 [R3_LOAD_HALF_A_CYCLE_BUDGET_POWER_LIMITED@1] |
| LOAD_DOUBLE_A | 1264.2 [R3_LOAD_DOUBLE_A_FLOW_PEAK@1] | 712.3 [R3_LOAD_DOUBLE_A_ELECTRIC_POWER_PEAK@1] | 2783.4 [R3_LOAD_DOUBLE_A_ELECTRIC_ENERGY@1] | 8.00 [R3_LOAD_DOUBLE_A_CYCLE_BUDGET@1] | 94.78 [R3_LOAD_DOUBLE_A_CYCLE_BUDGET_POWER_LIMITED@1] |
| EJECT_DOUBLE_B | 1047.4 [R3_EJECT_DOUBLE_B_FLOW_PEAK@1] | 353.5 [R3_EJECT_DOUBLE_B_ELECTRIC_POWER_PEAK@1] | 1582.9 [R3_EJECT_DOUBLE_B_ELECTRIC_ENERGY@1] | 9.00 [R3_EJECT_DOUBLE_B_CYCLE_BUDGET@1] | 55.76 [R3_EJECT_DOUBLE_B_CYCLE_BUDGET_POWER_LIMITED@1] |
| TIME_HALF_A | 1279.6 [R3_TIME_HALF_A_FLOW_PEAK@1] | 721.0 [R3_TIME_HALF_A_ELECTRIC_POWER_PEAK@1] | 1408.6 [R3_TIME_HALF_A_ELECTRIC_ENERGY@1] | 5.00 [R3_TIME_HALF_A_CYCLE_BUDGET@1] | 48.95 [R3_TIME_HALF_A_CYCLE_BUDGET_POWER_LIMITED@1] |
| BACK_HIGH_A | 700.9 [R3_BACK_HIGH_A_FLOW_PEAK@1] | 394.9 [R3_BACK_HIGH_A_ELECTRIC_POWER_PEAK@1] | 1543.2 [R3_BACK_HIGH_A_ELECTRIC_ENERGY@1] | 8.00 [R3_BACK_HIGH_A_CYCLE_BUDGET@1] | 53.44 [R3_BACK_HIGH_A_CYCLE_BUDGET_POWER_LIMITED@1] |

Все восемь наборов превышают выбранный электрический бюджет. Исходные времена не выполнимы в этих же сценариях при таком ограничении. Увеличенный бюджет T — лишь арифметическое необходимое увеличение длительности при неизменных supply/η/геометрии; оно не доказывает Q(p), охлаждение, управление, полный цикл или производительность REV. Расходы всех других потребителей пока не учтены.

Понижение ρ увеличивает камеру и путь сжатия, а не непосредственно статическое усилие или bore. Нагрузка меняет bore и энергетические требования. При удлинении выдачи меняется также возврат. Сокращение времён движения повышает Q/P, но не E при фиксированных силах/ходах/supply. Повышение противодавления увеличивает необходимую площадь и сливные потери. См. формулы чувствительности в model.md и точные значения CSV.

## Вычислимо и неизвестно

| Область | Уже вычислимо условно | Что блокирует подтверждённый результат |
|---|---|---|
| Камера/доза | Баланс объёмов/массы и осевые ходы при m,ρ,φ,A,l | Фактические состояние сырья, плотность, влажностная база, дозирование, остатки/потери, мёртвые объёмы |
| Сила | F(σ,A,трение,передача), интеграл работы | Закон материала/трения по ходу/скорости/истории, фактическая грань, силы A/B, инерция, калибровка |
| Цилиндр | Площади, D/d при заданном κ, два давления/потери, оба направления | Устойчивость/прочность/ресурс штока, реальные нагрузки/опоры/крепления, допустимые давления и паспорт компонента |
| Насос/привод | Q,v,t,pQ и энергетические границы одной оси | Схема/одновременность, Q(p), КПД и рабочие зоны, пиковые/пусковые режимы, тепло, другие потребители |
| A | Условное сопротивление и неравенство удержания | Измеренные сопротивление/удержание/пружинение, поведение канала и безопасность |
| B | Условная peak реакция и запас осевого хода | Остаточная реакция/порог открытия UNKNOWN, разгрузка/блокировки/связанная выдача не подтверждены |

Все реальные UNKNOWN отдельно зарегистрированы как R3_REAL_* с null. Неизвестные не назначены нулями. Выбранные нулевые утечка/потери массы/динамика — явно ограниченные идеальные сценарные допущения, а не восстановленные реальные входы.

Независимый R5 должен проверить новые формулы/код/таблицы на точном C; акт R5 исходной базы не проверяет эту реализацию. Нельзя закрывать старые инженерные блокеры данным программным прогоном.
