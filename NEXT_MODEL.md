# Повторная проверка R5 — T-codex-01-01

- RECHECK запрошен по REV-R5-IMPL-02-001; блокеры R5-IMPL-01/02 OPEN до независимого акта. Исходный reviewer r5-implementation-02 или другой независимый reviewer; автор исправлений r4-model-01.
- Проверяемый C: 36cda8132dcf9dbb7193b01e98bdfff2ba5e2a7b; ветка work/T-codex-01-01/r4-model-01. Исходный акт R5 в aadb63c7afb6d95e99867052b3baefba2d259c7d, reviewed_commit 5cb3e8ab274ae4d746ec016ecd11b6c2acd14edb; validity STALE относительно новых файлов, исторические замечания сохраняются.
- Проверить изменения согласно verification/r5_model_02/review.md: матрица пар, ограничения геометрии/разрешённого контакта, синтетические фазовые и отказные сценарии, полный интервал, переходы, последовательности, A-OUT и силовые ветви. Доказательство неизменного ядра и пригодность изменённых связей требуют подтверждения.
- Команды: python3 models/kinematic_press/model.py; python3 -m unittest discover -s models/kinematic_press -p 'test_*.py'; python3 verification/r5_model_02/independent_check.py; python3 scripts/check_registry.py --check-git. JSON и SVG — models/kinematic_press/results/.
- Автор: 28 геометрических случаев и 11 сценариев переходов совпали с ожиданиями; 12 синтетических переходов ALLOWED; 9 тестов OK; benchmark 3000/3000; registry PASS. Матрица: synthetic 127/127, REV 0/127. Сам факт подсчёта не доказывает достаточно реалистичного покрытия.
- Входы REV UNKNOWN, контакт и силы не приняты, G1 открыт. Fixture тела в большинстве случаев разнесены, ход выдачи скалярный; реальная установка и физическая связность изделия/пуансона не проверены. Полную приёмку не заявлять.
- До любых новых изменений проверить актуальную main, владельца и lease r4-model-01. Капсула handoffs/T-codex-01-01/r4-model-01.md; запрос также в ISSUES_AND_TASKS.md.
