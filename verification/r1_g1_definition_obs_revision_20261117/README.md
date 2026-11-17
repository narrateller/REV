# Исправление замечаний R5-DEF-OBS-01/02

Только документальная ревизия в существующем claim R1. Предшественник exact C
`7e2d5ecff42fe1d09b461e05375924cb644c27c9`, независимый акт
`1d4593f93ba0b315379a885ba9fd955b7ded392c`/H
`ad627d310ee9f49d730b71c84ab4af7c9c1ff0da` сохранены полностью.
Исходный срок `2026-11-18T01:58:30.990734+00:00` не продлён.

Изменены только две пары определений и два метода. Добавлены DEF-02-G (плотность
и отдельно насыпная плотность) и DEF-03-F (масса изделия и остатка при применимости).
Итого 146 предложенных scope items; все 144 прежних и остальные 20 полных строк/
методов неизменны. Четыре mappings в quantity_crosswalk.json связывают frozen
VAL02/03, MATERIAL/MASS и REQ22 с этими конкретными пунктами. Плотности и массы
разных объектов не отождествляются; значения, пределы, методы, допуски UNKNOWN.

DM02/03 теперь DRAFT-02. DM03 явно сохраняет запись каждой попытки цикла, включая
неуспешные и неполные: исход, quality flag, missing reason, disposition, исходные
события и учёт серии. Отсутствовать может изделие/измерение, запись не исчезает.
Missing reason сопоставлен с retained schema.unknown_reason; конкретная исполнимая
схема и срок хранения не утверждены. Производные выборки не удаляют полный журнал.
Фактических циклов и новых результатов нет. Это предложение определения, не запуск.

Новый independent recheck NOT_RUN. Оба OBS остаются OPEN_PENDING_INDEPENDENT_RECHECK;
автор R1 их не закрывает. Акт R5 остаётся exact-C evidence предшественника, а не
проверкой нового target. Все 40 source dispositions, девять открытых групп решений,
старые требования/каналы/метрология/акты и свидетельства сохраняются без изменения.
BP500 primary, прочие прессы по релевантности, площадка адаптируется. RAW не повышены.

Команды (author checks не независимая оценка):

```bash
.venv/bin/python verification/r1_g1_definition_obs_revision_20261117/render_register.py --output-dir /tmp/rev-def-obs-render
.venv/bin/python verification/r1_g1_definition_obs_revision_20261117/verify_revision.py
.venv/bin/python scripts/check_registry.py --check-git
```

Шесть renderer outputs: четыре сводки новой ревизии, quantity_crosswalk.md и
record_retention_plan.md. Точный новый C задаётся следующим H. R5 нужен explicit
main scope amendment на новый C/H при прежнем владельце/сроке; предложение/старый
exact-target claim не дают полномочий. Содержательный PR60 пока не сливается.

WARNING; ТЗ/архитектура NOT_APPROVED; G1 OPEN. 42 состояния не рассчитаны;
§4/5/6 NOT_RUN; W02/physical READY NO-GO. Прочность, устойчивость и реальные реакции
не подтверждены. Расчёты, CAD-build/rebuild и испытания не разрешены и не выполнялись.
