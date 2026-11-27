# T-2.2h

Материалы пробной квалификации схемы A. Итог и ограничения моделей приведены в [отчёте](../../report.md).

## Воспроизведение

Запуск из корня worktree в PowerShell с Python 3.13, NumPy, SciPy и PyYAML. Gmsh 4.15.0 и CalculiX 2.22 берутся из каталога `REV_FREECADCMD`. Значение по умолчанию `E:/Tools/FreeCAD-1.1/bin/freecadcmd.exe`.

```powershell
$revPy = 'E:/Tools/Python313/python.exe'
$env:OPENBLAS_NUM_THREADS = '1'
& $revPy -B calc/T-2.2h/fea/ring.py --mesh 18 --out calc/T-2.2h/fea/ring_screen.json
& $revPy -B calc/T-2.2h/fea/ring.py --mesh 15 12 --optimise 2 --append --cases roof_force --out calc/T-2.2h/fea/ring_screen.json
& $revPy -B calc/T-2.2h/fea/end.py --mesh 16 13 11 --out calc/T-2.2h/fea/end_screen.json
& $revPy -B calc/T-2.2h/fea/window.py --reinforced --mesh 20 --out calc/T-2.2h/fea/window_screen.json
& $revPy -B calc/T-2.2h/fea/window.py --reinforced --mesh 16 13 --out calc/T-2.2h/fea/window_fine.json
& $revPy -B calc/T-2.2h/fea/window.py --reinforced --quick --mesh 20 --key-factor 0.5 --out calc/T-2.2h/fea/window_half.json
& $revPy -B calc/T-2.2h/fea/window.py --reinforced --quick --mesh 20 --key-factor 2 --out calc/T-2.2h/fea/window_double.json
& $revPy -B calc/T-2.2h/fea/window.py --reinforced --edge-diagnostic --quick --mesh 20 16 13 --out calc/T-2.2h/fea/window_edge.json
& $revPy -B calc/T-2.2h/verify.py
```

Для независимого повтора выведите результаты под именами `replay_ring.json`, `replay_end.json`, `replay_window_half.json` и `replay_window_double.json` в `fea/`. Для `replay_window.json` передайте все три сетки одним запуском `--mesh 20 16 13`. Локальная оценка обрезки использует те же сетки и сравнивается по сходимости. Затем `verify.py` сравнит числовые результаты с допуском 10⁻⁶. При наличии первичных данных скрипт также дважды собирает результаты и проектный YAML и сравнивает SHA-256. Сетки и файлы решателя создаются во временных подкаталогах.

Две тонкие секции кольца в пробной объёмной модели представлены общим телом. Локальный расчёт торца использует перемещения родительской модели на X = 255 мм. Модель окна содержит твёрдые тела корпуса и башмака, а податливость засовов сведена к изгибу, сдвигу и смятию. Квалификационный контактный расчёт зависит от проектирования стыка секций, упоров, соединения с траверсой и посадки вкладыша.

