# Независимый OUTPUT-review сквозной карты R3

Акт: [review.md](review.md). Проверенный C `43f03359fabe2b664935b17f9ac7851504093ece`, H `94706e091ba8b27b74b321b6f0ca00b3ea7fd176`.

Из корня репозитория с доступными точными Git-входами и четырьмя materialized PDF:

```bash
git fetch origin 3591a5f92f78b1edea07d3fc5354fd0a99090798
.venv/bin/python -B verification/r5_r3_cycle_trace_review/independent_probe.py > /tmp/r5-cycle-independent.json
.venv/bin/python -B verification/r5_r3_cycle_trace_review/reproduce.py
```

independent_probe читает исходные Git JSON/gzip, независимо считает Fraction-позы, стыки, дефициты выдачи/RESET declared boxes и сверяет 100 параметров цепочек с точным расчётным C. Не вызывает авторский collect, CAD generation, BRep или solver. Это **документальная/координатная проверка**, не доказательство дефекта actual FCStd/STEP.

reproduce пишет новые служебные логи только в этот каталог review; проверяемые пакеты не изменяет. Повторный запуск обновит локальные времена/логи и прочитает текущее состояние PR/main; не смешивать их с исходными доказательствами опубликованного акта. В первом запуске CAD commit локально отсутствовал; отказ сохранён в initial_missing_CAD_object.log, после fetch исходный verifier прошёл.

source_checks.json хранит SHA-256 PDF, точные 25 визуально прочитанных страниц, 17 source claims и ограничения. Страницы воспроизводятся `pdftoppm -f PAGE -l PAGE -singlefile -scale-to 1800 -png PDF /tmp/view`; для навигации `pdftotext -f PAGE -l PAGE -layout PDF /tmp/view.txt`. Самостоятельное визуальное чтение не заменяется успешным скриптом/OCR.

independent_results.json, reproduction.json, object_identity.json содержат численные результаты/ссылки/контроль сохранности. independent_command.json фиксирует команду и SHA probe; evidence_hashes.json — файлы акта и доказательств, кроме самого списка.

CAD review **NOT_AVAILABLE** по уточнению пользователя; native/FCStd/STEP replay **NOT_RUN**. Все девять приоритетов остаются OPEN; принята только условная исследовательская постановка с уточнённой последовательностью. Архитектура/ТЗ/оборудование не утверждены, физические испытания NOT_RUN, G1 OPEN.
