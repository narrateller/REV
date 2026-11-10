# Независимый R5 RECHECK — T-codex-01-01

- Автор исправления r4-model-01 / R4; проверяемый code/results C debfd085842ccae079cfd6faea1c41bca20f335d; ветка work/T-codex-01-01/r4-model-01. Ревью новой версии NOT_RUN.
- Решение R1 verification/r5_recheck_04/disposition.md на 791d0ce8ccb31373b221d0b69063e2f835b442c0; актуальная капсула R1 5ff71747b7263220ab25c56f3d329253ee42356d; пользовательский акт REV-R5-RECHECK-04-001 сохранён в verification/r5_recheck_04/submitted_review.md.
- R5-IMPL-01 OPEN, общий результат предшествующей версии REJECT_WITH_BLOCKER. R5-IMPL-02 CLOSED только в проверенной области 576a17fc; регрессионный recheck изменённого кода обязателен. G1 открыт.
- Команды из корня: python3 models/kinematic_press/model.py; python3 models/kinematic_press/run_linked.py; python3 -m unittest discover -s models/kinematic_press -p 'test_*.py'; python3 verification/r5_model_02/independent_check.py; python3 scripts/check_registry.py --check-git. Отчёты models/kinematic_press/results/report.json и linked_report.json; хэши входов внутри.
- Авторские проверки: 8/8 исходов с соответствующими проверками всех границ, CE-01/02, 20 тестов OK, benchmark 3000/3000, registry PASS; воспроизводимость обоих JSON проверена. B/collision: product [1/4,7/8], punch [3/4,1], несовпадений нет.
- Первая проверка R5: exact C и SHA входов; восемь исходов; мутации позиции/времени/lifecycle → BLOCKED, UNKNOWN без блокера → INDETERMINATE, COLLISION не скрывается; регрессии интерфейсов/матрицы и READY. Только отдельный положительный RECHECK закрывает R5-IMPL-01.
- Все данные синтетические; реальные характеристики REV UNKNOWN, физическая безопасность/процесс не подтверждены. Капсула handoffs/T-codex-01-01/r4-model-01.md.
