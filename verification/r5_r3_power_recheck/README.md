# Ограниченный R5 RECHECK W01/W02

Основной акт: [review.md](review.md). Проверенный C `c115f75fd900525d9ddc89d85e097ac5a0f00bc1`, H `1344c1a62b83503a73ab85e5c5fff78907eb820d`.

Из корня репозитория:

```bash
.venv/bin/python -B verification/r5_r3_power_recheck/probe.py > /tmp/r5-r3-power-independent.json
.venv/bin/python -B verification/r5_r3_power_recheck/reproduce.py
```

probe пишет только stdout: 376 независимых Decimal-ожиданий, CSV/таблицы, новые синтетические случаи; ожидаемые значения не получены вызовом авторского solve/reconcile. Авторский API импортируется только как объект проверки. Синтетические overrides — данные проверок, не параметры реального REV.

reproduce сохраняет логи в **этом каталоге review**, читает Git/PR, выполняет авторские readonly команды/тесты/валидатор; проверяемые пакеты автора не изменяет. При повторном запуске дата, длительности тестов и состояние удалённых веток могут измениться. Не смешивать новые служебные логи с исходными доказательствами опубликованного акта.

Полные результаты — independent_results.json; команды/источники/окружение/контроль SHA-size-mtime — reproduction.json и command_01…11.log. object_identity.json связывает проверенные файлы с Git C/H, independent_command.json фиксирует команду и SHA независимого probe. evidence_hashes.json содержит хэши файлов акта и доказательств, кроме самого списка.

Закрытие замечаний ограничено расчётной областью. Реальный полный цикл и открытие B INDETERMINATE, физические испытания NOT_RUN, G1 OPEN; оборудование, архитектура и ТЗ не утверждены.
