# Запрос независимого RECHECK R5 — T-r4-layout-build-01

Code/results: `5449fb9bc4c20fcbc40fdec932876dcecc90ef4d`, ветка `work-r4/build-layout/r4-linked-20261111`, база main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53. Входной акт REV-R5-LAYOUT-BUILD-01-001 на e939b41d0139b0a3a08a5950eeeec6e92324cf9b, исходный C 6bb66a566719593a59935e341b1b5c80a1cbc9a7 сохранены. Проверить R5-CAD-TOOL-B01/B02; автор оставляет их OPEN.

REMOVE валидируется до изменения эффективного реестра, каждое событие учтено, unsupported CREATE/SPLIT не применяются; подтверждённый дефект сохраняется при UNKNOWN других событий. PASS CAD требует actual FCStd/STEP, hashes, нативных состава/форм и соответствия STEP. Ошибка/отсутствие/рассогласование дают FAILED.

Воспроизведение после checkout/materialize LFS и сохранения исходных результатов:

```sh
/usr/bin/python3 cad/layout/run_all.py
```

69 unit tests, 33 lifecycle-контрпримера, 14 CAD-negative и 8 limited outcomes PASS, все 12 дочерних команд exit 0. Полное evidence: cad/build/research_layout/validation.json и checks/*.json; оценка assessment.md. Исходный adapter_probe.py фиксирует старые ошибочные исходы; исправление проверяют новые независимые ожидания, не успех его старых assertions.

Геометрия/входной JSON/build_model/manifest.objects, все PNG и 107486 записей фаз/пар сохранены; нативные static/dynamic пробы R5 повторены и совпали. 556 сервисных результатов сохранены. Проникновения A/B не устранены, full READY INDETERMINATE. Восемь исходов относятся только к path_subset. Не подтверждены реальные нагрузки, физика, посадки, обслуживание и безопасность; параметры REV UNKNOWN, условные ASSUMED отдельно. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Задача не принята, слияние не выполняется.
