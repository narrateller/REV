# T-0.1a — геометрические гейты REV 1.2.0

Исправлены измерение бокового зазора, проверка контактов пути подачи и учёт операндов FreeCAD. База сравнения — `main` (`a595920fb80ac51a1f504e22c90e6470f0dc0a24`), FreeCAD 1.1.4, критерии v4. `CONTACT_TOL_MM = 0,01 мм`, `GEOMETRY_TOL_MM = 10⁻⁷ мм`, предел зазора 0,3 мм на сторону и предел общего объёма 0 мм³ сохранены. [Критерии](ops/criteria/design_criteria.yaml) · [Решения](DECISIONS.md)

## Воспроизведение на main и проверка исправлений

Команда `& $env:REV_FREECADCMD tests/ops/test_geom_gates.py` на неизменённом `geom_gates.py` вернула **1**. Ниже строки ассертов относятся к версии теста на момент этого запуска. На 1.2.0 тот же набор проверок дважды вернул **0**.

| Дефект и проверка | FAIL на main | PASS проверки на 1.2.0 |
| --- | --- | --- |
| D1 `SquareCentred`, `CircleCentred` | Стр. 421, `assert "min_side_mm" in pair and math.isclose(...)`. Зазор 0,1 мм уже совпадал | Максимум и минимум 0,1 мм, проверены точки, сечения и положение максимума |
| D1 `SquareTouch`, `SquareWideOffset` | Стр. 418, `assert gate["status"] == pair["status"] == expected, gate`. PASS, 0 мм | FAIL, максимум 0,4 и 40 мм соответственно, минимум 0 мм |
| D1 `CircleTouch` | Стр. 419, `assert math.isclose(gate["value"], max_mm, abs_tol=tolerance_mm), pair`. PASS, 0 мм | PASS, максимум 0,2 мм, минимум 0 мм в допуске теста 0,002 мм |
| D1 `CircleOffset`, `TiltedPunch` | Стр. 418, сравнение статуса. PASS, около 0,05 мм у обеих пар | FAIL, соответственно 0,35 ± 0,002 мм и около 0,50 мм в глубине перекрытия |
| D1 `SquareMissedRay` | Стр. 414, `assert gate["status"] == "FAIL" and pair["clearance_mm"] is None, pair`. FAIL, числовой зазор 4,5 мм | FAIL пары с координатами промаха и причиной |
| D2 `LinerEdge`, `LinerPoint`, `HopperEdge` | Стр. 452, `assert gate["status"] == "FAIL" and role in connection.get("missing_contact", []), gate`. WARN | FAIL и соответствующая роль в `missing_contact`. Окно 0 мм² при контакте вкладыша по ребру или точке |
| D2 `FaceGap` | Стр. 447, `assert gate["status"] == "WARN" and math.isclose(gate["value"], 12, abs_tol=1e-6), gate`. WARN, 0 мм² | WARN по отсутствующему порогу, окно 12 мм² при зазоре 0,005 мм |
| D3 `UserLink`, `ExpressionLink`, `UnknownDependency` | Стр. 474, `assert math.isclose(mass["value"], 0.0157, abs_tol=1e-12), mass`. Только 0,00785 кг | Масса 0,0157 кг и WARN с перечнем ссылок. Коллизия по ссылке `UserLink` даёт FAIL, 500 мм³ |
| D3 `check_consuming_types` | Стр. 506, `assert gate["status"] == "PASS" and gate["details"].get("unknown_dependencies") == [], gate`. Масса уже совпадала, поле отсутствовало | Cut, MultiFuse, Compound, Body дают 0,0013816 кг, PASS и пустой перечень |

Существующее окно 108,8 мм² прошло на обеих версиях. Проверка версии критериев сверяет точное значение из переданного YAML. Для прежнего ассерта WARN на кубе 4 500 кг тестовый файл задаёт историческую цель 4 000 кг. При штатной цели v4 в 4 900 кг исходная модель куба давала PASS. Остальные прежние ассерты сохранены.

## Метод и ограничения

- **G-CLEAR.** Три сечения по осевому перекрытию, середина и две плоскости внутри торцов с отступом `min(0,01 мм, перекрытие/4)`. На каждом ребре восемь внутренних точек, на круговых и эллиптических дугах добавляются точки для углового шага не больше 5°. Точки в пределах геометрического допуска от концов исключаются. Луч по нормали ограничен смежным интервалом внутри отверстия. Первая встреча с профилем даёт зазор, совпадение в пределах допуска даёт 0 мм. Измерения по стенкам и сечениям записываются в отчёт. Любой промах даёт FAIL пары. Для измерения нужен замкнутый контур отверстия в каждом сечении. Открытое сечение и недостаточная дискретизация дают диагностический FAIL. Метод проверяет номинальную геометрию в выбранных сечениях и может пропустить локальные экстремумы между ними.
- **G-FEED.** Положительную площадь дают общие участки совпадающих граней и проекции параллельных плоских граней в пределах 0,01 мм. Проекции на одну грань объединяются перед подсчётом. Геометрический минимум 10⁻⁶ мм² соответствует одному квадратному микрометру и отсекает численные остатки. Вкладыш и присутствующий бункер требуют контакта по площади. Итоговое окно — минимум по путям. Числовой порог площади окна остаётся открытым вопросом TECH по C-FEEDPATH-01.
- **G-MASS и G-COLL.** Неизвестные ссылки на независимые тела сохраняют эти тела в расчёте и дают `unknown_dependencies`. PASS повышается до WARN. Виды TechDraw используют `Source` как ссылку для проекции. Источник классификации — `getDocumentationOfProperty("Source")` в FreeCAD 1.1.4 у `TechDraw::DrawViewPart` и производного `TechDraw::DrawViewSection`, описание «3D Shape to view».

| Потребляющие типы FreeCAD | Свойства операндов |
| --- | --- |
| `PartDesign::Body` | `Group` |
| `Part::Cut`, `Part::Fuse`, `Part::Common` | `Base`, `Tool` |
| `Part::MultiFuse`, `Part::MultiCommon` | `Shapes` |
| `Part::Extrusion`, `Part::Scale`, `Part::Fillet`, `Part::Chamfer` | `Base` |
| `Part::Revolution`, `Part::Mirroring`, `Part::Offset`, `Part::Offset2D` | `Source` |
| `Part::Thickness` | `Faces[0]` |
| `Part::Compound` | `Links` |
| `Part::Loft`, `Part::Sweep` | `Sections`, у Sweep также `Spine` |
| `App::Link` | `LinkedObject`, если источник скрыт и находится в том же документе |

## Калибровка W02-04

| Гейт | W02-A-V1, main → 1.2.0 | W02-B-V1, main → 1.2.0 |
| --- | --- | --- |
| G-ENV | FAIL → FAIL, 4505 × 3650 × 3650 мм | FAIL → FAIL, 4505 × 3650 × 3650 мм |
| G-MASS | FAIL → FAIL, 139 908,3565195209 кг, 90 тел | FAIL → FAIL, 140 939,42771297978 кг, 98 тел |
| G-COLL | PASS → PASS, 0 мм³ | PASS → PASS, 0 мм³ |
| G-FEED | FAIL → FAIL, нет тела `feed_path`, камера замкнута | FAIL → FAIL, та же причина |
| G-CLEAR | FAIL → FAIL, 5,5 мм | FAIL → FAIL, 5,5 мм |

В обеих моделях все четыре стенки дали 5,5 мм в сечениях X = 2910,01 мм, 2937,50 мм и 2964,99 мм при перекрытии 55 мм. SHA-256 моделей совпали с карточкой. Массы в 46 раз выше ориентира 3 050 кг, что соответствует назначению W02 как отрицательного примера по D-W02. Итог **MATCH**. [Сводка](ops/calibration/w02_04.json) · [Отчёт A](ops/calibration/w02_A_V1.json) · [Отчёт B](ops/calibration/w02_B_V1.json)

## Команды

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& $env:REV_PYTHON -B -m pytest -p no:cacheprovider --basetemp .pytest-t01a tests/ops
& $env:REV_FREECADCMD tests/ops/test_geom_gates.py
foreach ($variant in 'A', 'B') {
    $env:REV_GATE_ARGS = (@{
        model = "E:/Projects/REV/drawings/W02/output/W02-$variant-V1.FCStd"
        roles = 'ops/gates/roles/w02_legacy.yaml'
        criteria = 'ops/criteria/design_criteria.yaml'
        out = Join-Path $env:TEMP "w02_${variant}_V1.json"
    } | ConvertTo-Json -Compress)
    & $env:REV_FREECADCMD ops/gates/geom_gates.py
    $LASTEXITCODE
}
```

Для повторов использовался отдельный временный каталог FreeCAD в `FREECAD_USER_HOME` и `FREECAD_USER_DATA`. Pytest дал 151 PASS и 1 пропуск CAD-теста. Калибровочные JSON побайтово совпали, оба варианта дважды вернули код 1. При независимой генерации фикстуры `GeometryInputs` объёмы Offset/Thickness менялись в последних разрядах до 5,7 × 10⁻¹⁴ мм³. Повторное открытие одного FCStd давало побайтово одинаковые отчёты. Для отпечатков CAD-тестов нормализованы временные пути и числа до 14 значащих цифр. Ассерты используют исходные значения. Времена, коды возврата и SHA-256 приведены в [self_check.json](self_check.json).
