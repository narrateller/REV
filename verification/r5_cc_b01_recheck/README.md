# Независимый RECHECK B01

Основной акт: [review.md](review.md). Проверенный C
`0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed`; R5 session `r5-cc-b01-20261112`.

Из `/workspace/REV`:

```sh
.venv/bin/python -B verification/r5_cc_b01_recheck/independent_probe.py
.venv/bin/python -B verification/r5_cc_b01_recheck/reproduce.py
```

Первый command readonly; 587 проверок, exit nonzero при несовпадении.
Второй запускает все argv из commands.json и обновляет только собственные
логи/evidence. Registry занимает несколько минут. `--preservation-only`
повторяет только сверку source/tree/file identity, сохраняя прежние command logs.
Последующая добавленная review-метаинформация допустима лишь в четырёх общих
документах при сохранении полного прежнего содержимого H; helper/JSON/CAD/
расчёты/пакеты старых R5/R1 остаются побайтно неизменны. Финальная проверка
индекса нового акта — final_registry.log, отдельно от baseline команды 06.

commands.json фиксирует argv/exit/logs. command_01…08.stdout/stderr — полные
сырые результаты; исторические JSON сравниваются точно, текущие 205 — с
авторским results.json, независимый результат — с independent_results.json.
initial_attempt.json/initial_document_failure.stderr сохраняют неуспешную
попытку до fetch точного CAD-объекта. initial_preservation_failure.log сохраняет
ошибку нового сборщика: внешний Git-only источник ошибочно искался в main;
проверка исправлена с учётом in_current_main_worktree, затем preservation прошёл.
Это ошибки доступности/сборщика review, не дефекты проверяемого контракта.

B01 CLOSED только в документальной области; WARNING для условных интерфейсов
CYC-02/03, NO-GO для executable material/physical READY. W02/G1 OPEN,
physical tests/solver/CAD rebuild NOT_RUN. История двух отказов не обнулена.
