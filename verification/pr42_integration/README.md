# PR #42 — подготовка к интеграции после R5

[Решение/область/уточнённая последовательность CYC](../../decisions/PR42-CYCLE-TRACE-INTEGRATION.md). По акту R5 e69a8afbe4df3d53c4cc8b5883319e00eb8130af — **ACCEPT_WITH_WARNING только для документальной карты и условных интерфейсных предложений**. Целевой результат C 43f03359fabe2b664935b17f9ac7851504093ece сохранён; его старые записи NOT_RUN описывают момент выпуска, а не отсутствие последующего акта.

Акт R5 включён полным предком ветки, 23 файла/исходный index WARNING/CURRENT сохранены побайтно. Все 27 файлов каталога C (26 записей artifacts.sha256 и сам манифест), reviewed artifacts, 88 расчётных и 45 прежних R5-файлов проверяются preservation.json/verify_preservation.py. Проверенные документы, расчёты, registry, CAD и генераторы не исправлялись. reproduce.py из каталога R5 **не запускается**, поскольку он обновляет исходные логи акта; подготовка не переписывает доказательства reviewer.

Из корня репозитория:

```bash
.venv/bin/python -B verification/pr42_integration/verify_preservation.py
sha256sum -c verification/r3_cycle_trace/artifacts.sha256
.venv/bin/python -B verification/r3_cycle_trace/verify_trace.py
.venv/bin/python -B verification/r3_cycle_trace/render_documents.py
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

--record нашего verifier пишет только новый preservation.json этой подготовки; default readonly. Свежий fetch/проверка main/owner/срока нужны перед публикацией/интеграцией; повтор неизменности в будущем не продлевает claim. Журналы подготовки — checks.json и *.log. Новых физических/нативных/численных расчётов и самостоятельного OUTPUT-review этой сессией нет.

Сверка входа §6 ограничена подготовкой: границы/полномочия PASS; точная идентичность источников и актов PASS, внешняя подлинность NOT_RUN; единицы/определения сохраняются PASS; арифметика/геометрия не меняются PASS для неизменности, новая физическая/native проверка NOT_RUN; цикл — только принятый R5 порядок с UNKNOWN, готовность полного цикла не подтверждается; прослеживаемость C→R5→решение/claim/хэши PASS. Весь пакет передаётся с WARNING, инженерная готовность не выводится из CI.

CAD-review NOT_AVAILABLE, общий rebuild NOT_READY, полный цикл и B opening INDETERMINATE. CYC-01…09 и R5-CYCLE-W01/W02 OPEN. Оборудование/архитектура/ТЗ не утверждены, G1 OPEN, физических испытаний нет. Без слияния; следующий шаг оператора — отдельное рассмотрение опубликованного SHA/CI. Роль R3/owner/срок из сохранённого принятого claim, без присвоения полномочий R1.
