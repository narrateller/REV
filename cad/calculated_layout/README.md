# REV — расчётно связанная исследовательская компоновка

T-r4-calculated-layout-01; BASE_A / BASE_B **fixed-budget**. Принятый claim
e8ab3272d0fe4b1425779b7d2faac9832562d85d, PR #40/main
0353414369e8cffdd7b4289eafd665cc35c0ee36. Owner r4-linked-20261111,
lease до 2026-11-13T13:17:33Z. Входной акт/entry_checks в verification/r4_calculated_layout/.

Камера/ходы/D/d — sizing C 8a1ad4199fea09d1157972d7aa28eaad1e8e0337;
новые t/v — power C c115f75fd900525d9ddc89d85e097ac5a0f00bc1.
Все 44 строки источников сохраняются, полная таблица применения и изменений
в cad/build/calculated_layout/{parameter_mapping.md,all_parameter_changes.md}.
inputs.BASE_A/B.json — отдельные зарегистрированные исследовательские входы;
прежний CAD/инструмент/registry/COTS не меняются.

Из корня, /usr/bin/python3 с FreeCAD 1.0.0/Part:

```sh
# Явная генерация CAD/STEP/видов и всех доказательств:
/usr/bin/python3 -B cad/calculated_layout/pipeline.py generate
# Проверка только сохранённых артефактов; ничего не чинит и не перегенерирует:
/usr/bin/python3 -B cad/calculated_layout/pipeline.py verify
/usr/bin/python3 -B cad/calculated_layout/pipeline.py verify
# Требовать пригодности полного пути: на текущем результате обязан дать exit 2:
/usr/bin/python3 -B cad/calculated_layout/pipeline.py verify --require-clear
```

`--reuse-native` у generate — явная повторная генерация доказательств из
существующего native CAD; перед этим проходит полная native-проверка.
`--out /tmp/...` позволяет отдельный повтор. Input generation bridge.py отдельно
и только при зарегистрированном изменении входов; verifier не вызывает его запись.

Консистентность артефактов/exit 0 не означает пригодность сцены. Результат
содержит реальные BLOCKED/INDETERMINATE исследовательской модели; все пары и
полные интервалы сохранены. Прежняя длинная геометрия выхода не сокращается
ради расчётной достаточности. При недостигнутом выходе продукт не удаляется;
возврат/закрытие исследуются диагностически, рабочий READY не подтверждается.

Sources Spreadsheet сохраняет ссылки/численные входы R3, Inputs связан формулами
с Sources и управляет нативными телами. FreeCAD нормализует числовые ячейки к
15 значащим цифрам: полный точный исходный JSON сохраняется в Assembly отдельно;
32 ULP проверка служит только сериализации, не физическим допуском. Векторы
линейного solver используют точные рациональные формулы R3; residual относительно
float JSON сохранён. Источники/размеры не менялись ради мощности.

Минимальный bore — **reference**, не отверстие утверждённого корпуса. Наружный
цилиндр/монтаж/станция остаются прежними ASSUMED оболочками. DoseEnvelope —
reference объёма сырья, рабочий product — жёсткий surrogate готового продукта;
физическое уплотнение не реализовано. References и QueryVolumes не экспортируются
как материал STEP, но все их actual BRep/положение/размеры проверяются отдельно.

Новый адаптер мост/циклограмма/native validation/агрегация требует независимого
review. Прежние frozen 34 модуля и исходная CAD-публикация не изменены. Native
samples подтверждают отдельную коллизию; отсутствие sampled penetration не
доказывает полный ход криволинейной формы. Unsupported/unknown не дают CLEAR.

Открытие B и физическая выполнимость L-пути INDETERMINATE. Реальные данные REV
UNKNOWN. Архитектура/ТЗ/COTS не утверждены, физические испытания NOT_RUN, G1 OPEN.
