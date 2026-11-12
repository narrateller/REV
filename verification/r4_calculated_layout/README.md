# Результат реализации после принятия PR #40

T-r4-calculated-layout-01: расчётно связанный исследовательский пакет создан,
ожидает независимого OUTPUT review. Точный C — в следующем H/NEXT_MODEL/капсуле.
Owner r4-linked-20261111, принятый main 0353414369e8cffdd7b4289eafd665cc35c0ee36,
lease без продления до 2026-11-13T13:17:33Z. Старое предложение ниже — история.

- Редактируемые модели/STEP/виды/сечения: cad/build/calculated_layout/A и B.
- Фактическая таблица 44 применений: cad/build/calculated_layout/parameter_mapping.md;
  все 478 изменений: all_parameter_changes.md и */parameter_changes.json.
- Запуск/метод: cad/calculated_layout/README.md; полный отчёт: cad/build/calculated_layout/report.md.
- Выводы/предел готовности: findings.md; исходные/отрицательные случаи отдельно в finding_scope.json.
- Не закрытые покрытием условия и сервисы: unverified_conditions.md/json;
  дополнительные функциональные стыки, включая потерянный контакт зажима A: functional_interfaces.json.
- Входной акт/44 сверки: input_audit.md, entry_checks.json, R3_readonly_replay.json.
- Проверки: unit_tests.json, native_regressions.json, path_regressions.json,
  prior_group_regressions.json, read_only_verification.json, repeatability.json.
- История отказов/исправления адаптера: history.md; запрос независимого R5: review_request.md.

833332 записей полного интервала, 8 рабочих диагностических сцен и 22 сервисных
последовательности. Номинальная граница R3 достигнута, фактические выходы CAD нет:
SHORT_STROKE, продукт не удалён, READY не подтверждён. Новые rod/chamber/feed
проникновения и B reset/product BLOCKED не скрыты. Прежние 18/14/10 группы без
новой подтверждённой коллизии, legacy6 BLOCKED сохранены. L physical и B open
INDETERMINATE. Реальные REV UNKNOWN, COTS/архитектура/ТЗ не утверждены, G1 OPEN,
физические испытания NOT_RUN. Это не приёмка конструкции.

Generation и verifier раздельны. Default verifier подтверждает консистентность
артефактов, не пригодность сцены; --require-clear обязан отказать на текущем
результате. Старые файлы/акты/frozen tool не переписаны. Интеграция не выполнялась.

---

## История подготовительного предложения

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

Число 478 относится к изменённым полям отдельных input/native Spreadsheet реестров, включая совместимые config и сохранённые шаблоны другой альтернативы. Какие поля непосредственно управляют телами выбранной A/B, явно показано в parameter_usage.json; поле без выбранного тела не объявляется применённой размерностью. Все 44 расчётные привязки отдельно применены в заявленной геометрической, временной либо интерфейсной роли.
