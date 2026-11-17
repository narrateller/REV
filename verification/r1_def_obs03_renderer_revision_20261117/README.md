# OBS-03: версия метода из контролируемого JSON

Новая ревизия исправляет только renderer и представление определений. Все JSON
определений, 146 пунктов, 22 метода, четыре quantity mappings, retention plan,
40 source dispositions и девять групп решений остаются в неизменённом
`verification/r1_g1_definition_obs_revision_20261117/`.

Новый renderer читает эти точные данные из SOURCE, сопоставляет method_id с REQ/VAL,
проверяет уникальность/непустую версию и выводит revision_label соответствующей строки.
DM02/03 показывают DRAFT-02, остальные 20 — DRAFT-01. Из шести выходов изменены только
две строки definition_register.md; остальные пять совпадают с предшественником.
Полный manifest фиксирует источники; old renderer/summary/акты/FAIL не переписаны.

Проверка версии отделена от replay: все 22 метки сводки сверяются с JSON. Та же
проверка обнаруживает ровно DM02/03 в старой сводке; воспроизводимость старого
renderer не выдана за правильность версии. Дополнительно проверены источники,
неизменность данных и история. Author checks не являются независимым recheck.

OBS-01/02 CLOSED_DOCUMENTARY_EXACT_C только на предшественнике
97f58fd437947e26963bdbbc2f2d89df7438e8cc по акту R5 C234ea8a1917899c69e68ec3ef6e7ebcefbe79fae.
Эти закрытия не переносятся автоматически на новый C; данные исправлений сохранены.
OBS-03 OPEN_PENDING_INDEPENDENT_RECHECK; новый OUTPUT-review NOT_RUN.
Точный C задаёт следующая H. R5 нужен явный main amendment в прежней задаче/owner/сроке.

```bash
.venv/bin/python verification/r1_def_obs03_renderer_revision_20261117/render_register.py --output-dir /tmp/rev-obs03-render
.venv/bin/python verification/r1_def_obs03_renderer_revision_20261117/verify_revision.py
.venv/bin/python scripts/check_registry.py --check-git
```

WARNING; ТЗ/архитектура NOT_APPROVED; G1 OPEN. 42 состояния не рассчитаны;
§4/5/6 NOT_RUN; W02/physical READY NO-GO. Прочность/устойчивость/реальные реакции
не подтверждены. UNKNOWN/RAW и 44 полные привязки/нагрузки/ходы/CAD сохранены.
Численный/физический этап, CAD-rebuild и испытания не разрешены и не выполнялись.
