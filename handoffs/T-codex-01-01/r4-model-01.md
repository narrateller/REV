# Передача R4 на независимый R5 — T-codex-01-01

- status: IN_REVIEW; author_session: r4-model-01; work_commit: 5cb3e8ab274ae4d746ec016ecd11b6c2acd14edb; branch: work/T-codex-01-01/r4-model-01.
- reviewed input commit: 3aebae606011ded0f6d6e0a8d6ccc15094d88feb; input review REV-R5-MODEL-REVIEW-01-001 WARNING; input audit models/kinematic_press/input_audit.md.
- Исправлен ejection: [] → INVALID_INPUT, collision независим; регрессионный тест; 13 фаз, явные пары и гипотетические силовые пути A/B, раздельное отображение проверенных и непроверенных пар.
- Команда python3 models/kinematic_press/model.py: пять synthetic случаев с ожидаемыми статусами, плюс INVALID_INPUT; 04 содержит два подслучая. 6 unit tests OK; check_registry --check-git PASS.
- Ограничения: 2 synthetic пары проверены, 60 нет; REV 0/62. Указанные пары — исследовательские кандидаты, полнота не установлена. Параметры REV и допуски UNKNOWN, силовые контуры не подтверждены. G1 открыт; R5-OBS-01…04 OPEN.
- Запрос независимому R5 в ISSUES_AND_TASKS.md. Reviewer не должен быть автором этой версии; независимый акт NOT_RUN. Проверить точный C, исходные данные/хэши, метод и результаты, соответствие фаз и пути нагрузки.
- running_jobs: []; незакоммиченные результаты: []; любые изменения кода/входов требуют повторного запуска и нового точного SHA для review.
