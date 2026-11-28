# T-0.1b — приёмка ГК (28.11.2026)

**ACCEPT.** bos high, 1 круг, 6,5 мин. Изменён только tests/ops/test_geom_gates.py.

- Ветка «порог окна не задан» проверяется через временную копию критериев без ключа min_window_area_mm2: check_all_gates и FaceGap ожидают WARN, причина проверяется явно.
- Ветка v5 проверяется на критериях из репозитория: окно 16 мм² — FAIL, ровно 30 000 мм² — PASS, 29 850 мм² — FAIL; причина FAIL — только «площадь окна меньше порога».
- Существующие ассерты не ослаблены (diff просмотрен ГК).
- Прогоны ГК вне песочницы из worktree: freecadcmd tests/ops/test_geom_gates.py — код 0; pytest tests/ops — 151 passed, 1 skipped. G-SCOPE PASS (раннер).
