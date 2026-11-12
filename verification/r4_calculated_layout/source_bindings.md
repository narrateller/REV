# Каталог точных входов для будущей привязки CAD

**NOT_APPLIED / CAD NOT_STARTED.** Поля CAD здесь — целевые имена контракта, а не уже созданные параметры модели. Числа дословно прочитаны из зарегистрированных исходных JSON и сверены с value/unit/revision активного registry. Никакая новая геометрия не назначена. Прежние CAD значения и фактическую привязку исполнитель добавит после принятия claim. SI без округления для отображения; точный JSON locator — source_bindings.json. Статус арифметики не подтверждает физическую гипотезу.

| Целевое поле CAD | Сценарий/источник/ID | Значение SI и статус | Затронутые узлы |
|---|---|---|---|
| chamber.width | BASE_A / sizing / R3_IN_WIDTH@1 | 0.15 m / ASSUMED, CURRENT, NOT_APPLIED | камера, пуансон, дозатор/стык, продукт |
| chamber.height | BASE_A / sizing / R3_IN_HEIGHT@1 | 0.06 m / ASSUMED, CURRENT, NOT_APPLIED | камера, пуансон, стык, продукт |
| product.length | BASE_A / sizing / R3_IN_PRODUCT_LENGTH@1 | 0.11 m / ASSUMED, CURRENT, NOT_APPLIED | продукт, выход/приём |
| chamber.length | BASE_A / sizing / R3_BASE_A_CHAMBER_LENGTH@1 | 0.5763888888888888 m / CALCULATED, CURRENT, NOT_APPLIED | камера, подача/отсечение, рама/опоры |
| material.occupied_length | BASE_A / sizing / R3_BASE_A_OCCUPIED_LENGTH@1 | 0.4611111111111111 m / CALCULATED, CURRENT, NOT_APPLIED | условная доза, камера |
| stroke.approach | BASE_A / sizing / R3_BASE_A_APPROACH_STROKE@1 | 0.11527777777777776 m / CALCULATED, CURRENT, NOT_APPLIED | пуансон, шток, цилиндр, направляющие |
| stroke.work | BASE_A / sizing / R3_BASE_A_WORK_STROKE@1 | 0.3511111111111111 m / CALCULATED, CURRENT, NOT_APPLIED | пуансон, камера, канал/упор |
| stroke.eject | BASE_A / sizing / R3_BASE_A_EJECT_STROKE@1 | 0.17 m / CALCULATED, CURRENT, NOT_APPLIED | пуансон, продукт, канал/упор, выход |
| stroke.return | BASE_A / sizing / R3_BASE_A_RETURN_STROKE@1 | 0.6363888888888889 m / CALCULATED, CURRENT, NOT_APPLIED | пуансон, шток, цилиндр, направляющие |
| cylinder.bore_min | BASE_A / sizing / R3_BASE_A_BORE@1 | 0.25820992809235593 m / CALCULATED, CURRENT, NOT_APPLIED | внутренняя геометрия цилиндра; не наружный габарит/COTS |
| cylinder.rod_diameter | BASE_A / sizing / R3_BASE_A_ROD@1 | 0.15492595685541355 m / CALCULATED, CURRENT, NOT_APPLIED | шток/пуансон; крепления остаются неподтверждёнными |
| load.work_peak | BASE_A / sizing / R3_BASE_A_FORCE_WORK_PEAK@1 | 1532417.45 N / CALCULATED, CURRENT, NOT_APPLIED | цилиндр, камера, силовой контур/сопряжения |
| load.return_required | BASE_A / sizing / R3_BASE_A_FORCE_RETURN_REQUIRED@1 | 12000.0 N / CALCULATED, CURRENT, NOT_APPLIED | шток, направляющие, крепления |
| phase.approach.time | BASE_A / power fixed-budget / R3P_BASE_A_APPROACH_TIME@1 | 8.767532939592336 s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.approach.speed | BASE_A / power fixed-budget / R3P_BASE_A_APPROACH_SPEED@1 | 0.013148257163335828 m/s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.work.time | BASE_A / power fixed-budget / R3P_BASE_A_WORK_TIME@1 | 26.70400394131257 s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.work.speed | BASE_A / power fixed-budget / R3P_BASE_A_WORK_SPEED@1 | 0.013148257163335824 m/s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.eject.time | BASE_A / power fixed-budget / R3P_BASE_A_EJECT_TIME@1 | 4.3098234209080415 s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.eject.speed | BASE_A / power fixed-budget / R3P_BASE_A_EJECT_SPEED@1 | 0.039444771490007476 m/s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.return.time | BASE_A / power fixed-budget / R3P_BASE_A_RETURN_TIME@1 | 12.39065782876903 s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.return.speed | BASE_A / power fixed-budget / R3P_BASE_A_RETURN_SPEED@1 | 0.051360379544280584 m/s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| time.cycle_budget | BASE_A / power fixed-budget / R3P_BASE_A_FIXED_BUDGET_CYCLE@1 | 54.172018130581975 s / CALCULATED, CURRENT, NOT_APPLIED | условная последовательность интервалов; не подтверждённый полный цикл |
| chamber.width | BASE_B / sizing / R3_IN_WIDTH@1 | 0.15 m / ASSUMED, CURRENT, NOT_APPLIED | камера, пуансон, дозатор/стык, продукт |
| chamber.height | BASE_B / sizing / R3_IN_HEIGHT@1 | 0.06 m / ASSUMED, CURRENT, NOT_APPLIED | камера, пуансон, стык, продукт |
| product.length | BASE_B / sizing / R3_IN_PRODUCT_LENGTH@1 | 0.11 m / ASSUMED, CURRENT, NOT_APPLIED | продукт, выход/приём |
| chamber.length | BASE_B / sizing / R3_BASE_B_CHAMBER_LENGTH@1 | 0.5763888888888888 m / CALCULATED, CURRENT, NOT_APPLIED | камера, подача/отсечение, рама/опоры |
| material.occupied_length | BASE_B / sizing / R3_BASE_B_OCCUPIED_LENGTH@1 | 0.4611111111111111 m / CALCULATED, CURRENT, NOT_APPLIED | условная доза, камера |
| stroke.approach | BASE_B / sizing / R3_BASE_B_APPROACH_STROKE@1 | 0.11527777777777776 m / CALCULATED, CURRENT, NOT_APPLIED | пуансон, шток, цилиндр, направляющие |
| stroke.work | BASE_B / sizing / R3_BASE_B_WORK_STROKE@1 | 0.3511111111111111 m / CALCULATED, CURRENT, NOT_APPLIED | пуансон, камера, канал/упор |
| stroke.eject | BASE_B / sizing / R3_BASE_B_EJECT_STROKE@1 | 0.17 m / CALCULATED, CURRENT, NOT_APPLIED | пуансон, продукт, канал/упор, выход |
| stroke.return | BASE_B / sizing / R3_BASE_B_RETURN_STROKE@1 | 0.6363888888888889 m / CALCULATED, CURRENT, NOT_APPLIED | пуансон, шток, цилиндр, направляющие |
| cylinder.bore_min | BASE_B / sizing / R3_BASE_B_BORE@1 | 0.2556782604764038 m / CALCULATED, CURRENT, NOT_APPLIED | внутренняя геометрия цилиндра; не наружный габарит/COTS |
| cylinder.rod_diameter | BASE_B / sizing / R3_BASE_B_ROD@1 | 0.15340695628584228 m / CALCULATED, CURRENT, NOT_APPLIED | шток/пуансон; крепления остаются неподтверждёнными |
| load.work_peak | BASE_B / sizing / R3_BASE_B_FORCE_WORK_PEAK@1 | 1502417.45 N / CALCULATED, CURRENT, NOT_APPLIED | цилиндр, камера, силовой контур/сопряжения |
| load.return_required | BASE_B / sizing / R3_BASE_B_FORCE_RETURN_REQUIRED@1 | 12000.0 N / CALCULATED, CURRENT, NOT_APPLIED | шток, направляющие, крепления |
| phase.approach.time | BASE_B / power fixed-budget / R3P_BASE_B_APPROACH_TIME@1 | 8.596449940509837 s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.approach.speed | BASE_B / power fixed-budget / R3P_BASE_B_APPROACH_SPEED@1 | 0.01340992835130043 m/s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.work.time | BASE_B / power fixed-budget / R3P_BASE_B_WORK_TIME@1 | 26.18292222844442 s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.work.speed | BASE_B / power fixed-budget / R3P_BASE_B_WORK_SPEED@1 | 0.013409928351300431 m/s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.eject.time | BASE_B / power fixed-budget / R3P_BASE_B_EJECT_TIME@1 | 4.225724790033752 s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.eject.speed | BASE_B / power fixed-budget / R3P_BASE_B_EJECT_SPEED@1 | 0.0402297850539013 m/s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.return.time | BASE_B / power fixed-budget / R3P_BASE_B_RETURN_TIME@1 | 12.14887591399821 s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| phase.return.speed | BASE_B / power fixed-budget / R3P_BASE_B_RETURN_SPEED@1 | 0.05238253262226731 m/s / CALCULATED, CURRENT, NOT_APPLIED | новая циклограмма пуансона/штока; материал/разрешения UNKNOWN |
| time.cycle_budget | BASE_B / power fixed-budget / R3P_BASE_B_FIXED_BUDGET_CYCLE@1 | 54.153972872986216 s / CALCULATED, CURRENT, NOT_APPLIED | условная последовательность интервалов; не подтверждённый полный цикл |

Размеры стенок/зазоров, осевое размещение узлов и наружная оболочка цилиндра не следуют из этих чисел. Входы давлений, выдержки/aux/unload/open и cap читать из cases/allocation/registry с точными ID; не заменять выбранными числами при построении. B open — INDETERMINATE. Крепления/полные габариты цилиндра/станции/COTS и реальные свойства/скорости/нагрузки REV — UNKNOWN. Сохранённые прежние ASSUMED-оболочки не становятся подтверждёнными интерфейсами.
