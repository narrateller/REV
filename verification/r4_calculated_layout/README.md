# Подготовка расчётно связанной компоновки REV

**T-r4-calculated-layout-01 READY / claim PROPOSED_PENDING_MAIN.** Новый CAD
NOT_STARTED. Это постановка/предложение claim; новая компоновка не построена.

- [Предмет и принятие claim](claim.md).
- [Исполнимая задача и обязательные проверки](task.md).
- [Предварительная сверка источников](preflight.json), [точные входные хэши](input_manifest.json).
- [Каталог планируемых привязок](source_bindings.md) — числа из источников, NOT_APPLIED.

База c0053ff7f22fbc10e93efff2691ca6aa1ef90a06 содержит PR #39. Старый R4 claim
не расширен; новый owner NONE до принятия в main. Следующий шаг — принятие
предложения координатором, затем fetch/owner/lease/input audit и реализация.

Readonly проверка расчётных источников из корня (без --write):

```sh
python3 -B scripts/rev_parametric.py
python3 -B scripts/rev_power_reconcile.py
python3 -B scripts/check_registry.py --check-git
```

В текущем checkout .venv из прежней передачи отсутствует; системный python3
фактически запустил оба readonly solver. /usr/bin/python3 импортирует FreeCAD
1.0.0/Part. Сборка новых CAD, геометрические проверки, новые изображения и
независимый OUTPUT review NOT_RUN. Старые CAD/проверки/registry/COTS не менялись.

Git fetch/push доступны. API GitHub через gh возвращает Forbidden для GraphQL
и REST; это ограничение публикации PR, не основание обходить принятие claim.
Ветка и точный C/H передаются через Git; можно открыть PR из опубликованной ветки.

Все новые данные только ASSUMED/CALCULATED условного исследования. Реальные
данные UNKNOWN, B opening/L physical feasibility INDETERMINATE, G1 OPEN;
архитектура/ТЗ/COTS не утверждены, физические испытания NOT_RUN.
