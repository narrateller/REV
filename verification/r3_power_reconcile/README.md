# R3 — ответ на R5-SIZING-W01/W02

[Сравнение вариантов и фазовые таблицы](report.md), [формулы и границы](model.md), [ответ R5](response_to_r5.md), [обновлённые входы R4](r4_inputs.md), [входной аудит](input_audit.md).

Из /workspace/REV:

```bash
# Исходные восемь несовместимых сценариев, без записи:
.venv/bin/python -B scripts/rev_parametric.py
# Новые отдельные варианты fixed-budget / fixed-times, без записи:
.venv/bin/python -B scripts/rev_power_reconcile.py
.venv/bin/python -B -m unittest discover -s tests -p 'test_rev_power_reconcile.py' -v
.venv/bin/python -B scripts/check_registry.py --check-git
```

`--write` нового скрипта явно генерирует только новые JSON/CSV/снимки после регистрации входов/выходов; не изменяет legacy, реестр или CAD. Данные нового слоя — allocation.json, results/*.json, scenarios.csv. Изменение входов требует явной новой ревизии/нового расчёта и проверки, не подмены хэшей. Identity.json хранит хэши исходных файлов C и инженерных определений всех прежних параметров; код отвергает изменения frozen источников. Активный registry дополнен новыми ID, поэтому его полный текущий файловый хэш отличается от исторического C; старые snapshot/определения/численные outputs неизменны.

Новые API reconcile/assess_hold — ограниченная арифметика, не доказанный контроллер/планировщик реальной машины. Возвращаемый бюджет finite только при явно оговорённых envelopes, а BLOCKED/UNKNOWN и null имеют обязательное значение. Старое Tlower не заменяет новые проверки выдержки.

G1 OPEN; B open INDETERMINATE, оборудование/архитектура/ТЗ не утверждены, физические испытания NOT_RUN. Замечания R5 остаются OPEN до независимого ограниченного RECHECK нового C.
