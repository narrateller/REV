# T-0.1b · CAD-тесты G-FEED для критериев v5

`check_all_gates` и `FaceGap` используют временную копию критериев, из которой удалён только ключ `C-FEEDPATH-01.min_window_area_mm2`. Оба теста проверяют `WARN` с причиной «порог окна не задан». Все 106 исходных ассертов сохранены, включая сравнение `criteria_version` с версией использованного файла.

В исходной модели `OpenWindow` гейт суммирует контакт по четырём стенкам выреза: 4 × 4 × 6,8 = 108,8 мм². Для проверки 16 мм² добавлена отдельная модель `OpenWindow` с плоским контактом 4 × 4 мм. В новых моделях путь подачи касается вкладыша и бункера торцами, поэтому площадь окна равна произведению сторон торца. Порог 30 000 мм² задан D-OP-25, а расчёт контакта по площади описан в D-GK-22. [Критерии v5](ops/criteria/design_criteria.yaml) · [Решения](DECISIONS.md)

| Модель | Размеры торца, мм | Площадь, мм² | G-FEED |
| --- | --- | ---: | --- |
| `OpenWindow` с плоским контактом | 4 × 4 | 16 | FAIL |
| `FeedWindowAtThreshold` | 200 × 150 | 30 000 | PASS |
| `FeedWindowBelowThreshold` | 199 × 150 | 29 850 | FAIL |

Для всех трёх моделей проверяется порог `30000` из репозиторных критериев. В обоих случаях `FAIL` единственная причина в отчёте гейта — «площадь окна меньше порога».

## Прогоны

`E:/Tools/FreeCAD-1.1/bin/freecadcmd.exe tests/ops/test_geom_gates.py` завершился с кодом **0**. Строки вывода:

```text
PASS FaceGap
PASS all five gates, role precedence, window area, liner and hopper contacts
PASS OpenWindow: G-FEED FAIL, 16 mm2
PASS FeedWindowAtThreshold: G-FEED PASS, 30000 mm2
PASS FeedWindowBelowThreshold: G-FEED FAIL, 29850 mm2
PASS missing and invalid REV_GATE_ARGS diagnostics
```

`E:/Tools/Python313/python.exe -m pytest -p no:cacheprovider tests/ops` завершился с кодом **0**. Строка вывода:

```text
================= 151 passed, 1 skipped in 138.76s (0:02:18) ==================
```

Первый запуск pytest с системным временным каталогом дал `PermissionError` (код 1, `121 passed, 31 errors`). Для успешного прогона `PYTEST_DEBUG_TEMPROOT`, `TEMP`, `TMP` и `TMPDIR` указывали на временный каталог внутри worktree. В обычном Python тест `test_freecad_geometry` пропущен, его проверки выполнены отдельным CAD-прогоном.

## Ограничения

Модели проверяют ветви геометрического гейта на синтетических телах. Приёмочный G-SCOPE выполняет раннер. Открытых вопросов по тестам нет.
