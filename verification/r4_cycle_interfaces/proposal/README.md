# B03 — prevalidation по ARB-R1-CI-SEMANTICS-03

Решение `39826eb2f5dbd1f83d81882022e6f59313ebe5d5` прочитано, SHA
зафиксирован в капсуле до кода; checkpoint `b08f365` содержит аудит и схему.
[Схема и результаты](../snapshot_correction/README.md). Проверяются все используемые
snapshots по fixed guard/action, E B_RESET={B_CLOSURE}; пропуски не дополняются.
Compatibility только в объявленном домене; scoped UNKNOWN не скрывает общий
BLOCKED известного запрета. Положительный адресный recovery сохраняется.
Четыре REJECT сохранены, interface counter=4 / material counter=2. B03 OPEN,
независимый RECHECK нового exact C PENDING; стабильная CAD-передача NO-GO.
Main3a9258c/PR45 owner/lease не менялись. Норматив, frozen helper, B01/B02,
44 bindings/четыре варианта/loads/calculations/CAD сохранены. W02/PLC/CAD вне
итерации; physical READY NO-GO, архитектура/ТЗ не утверждены, G1 OPEN.

---

## Предыдущие записи — история

# Текущая коррекция B03 — строгие типы метаданных

Основание R1 `e0fea7bbf3bd32fda601bca2f7567f8e2c3342b3`. Норматив v1/SHA
и payload неизменны; исправлен только контроль типов в checker/recovery predicate.
[Контракт типов, аудит сравнений, регрессии](../type_correction/README.md).
Третий REJECT сохраняется; B03 OPEN до независимого RECHECK нового C.

---

# Текущая B03 редакция — normative minimum v1

Основание: ARB-R1-CI-SEMANTICS-01 `5fe510bbc55a052c360ab39a2491a061584b8fb7`.
[Описание и результаты](../semantic_iteration/README.md),
[нормативный минимум](../semantics_v1/minimum.json),
[матрица действия/режима → нормы/источники/проверки](../semantics_v1/coverage.csv).
Типизированные формулы: [JSON](exports/coordinate_formulas.json), [таблица](exports/coordinate_formulas.md).
Норма загружается из отдельного доверенного каталога, а не из проверяемого --package;
её ревизия закреплена в checker. Экспорт/hashes не легализуют ослабленное условие.
B01/B02 документально закрыты на предыдущем C144941c, их регрессии сохранены.
B03 OPEN до независимого RECHECK нового C; текущая передача в CAD BLOCKED.
W02/PLC/CAD вне итерации. Physical READY NO-GO; G1 OPEN; архитектура/ТЗ не утверждены.

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v
```

Ниже сохранена документация предыдущей итерации; её counts/results относятся
к указанным старым C, не являются текущим RECHECK.

---

# CYC-02/03 — первая документальная постановка интерфейсов A/B

**Исправление по R5 `13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2`; независимый RECHECK нового C PENDING.**

B01/B02/B03 остаются OPEN до независимого акта. [Описание исправлений и регрессий](../correction/README.md), [протокол передачи/возврата/recovery](cycle_protocol.json). Исторический REJECT исходного C сохранён без изменения вердикта. Не приёмка конструкции. Owner R4 /
r4-linked-20261111, claim принят PR45 на
`3a9258c57e4bc15d6de98f1d17e8412ad6e8899a`; прежний срок сохранён.
Входной акт [input_audit.md](input_audit.md), точные версии/хэши
[input_audit.json](input_audit.json). Предварительные NONE/PENDING поля
актуализированы с основанием merge и прямого подтверждения пользователя;
история предложения сохранена. Архитектура и ТЗ не утверждены; G1 OPEN.

## Что передано

- [Интерфейсы, базы и порядок A/B](interfaces.md),
  [символические позы](poses.json), [полные разрешения/условия](permissions.json),
  [guards и правила evidence](mechanical_guards.json).
  31 исходное материальное действие checked contract сохранено с полными
  entry/completion; 22 дополнительных механических участка, всего 53 строки (добавлены A/B FILL-CONFIRM).
- [Таблица поз/разрешений](exports/positions_permissions.md),
  [полная редактируемая CSV](exports/positions_permissions.csv).
  START, текущие инварианты, предварительные движения и completion различаются;
  HOME не требуется сохранять во время собственного хода. У recovery свои условия.
- Схемы CYC-02: [A](exports/interface_A.svg), [B](exports/interface_B.svg).
- CYC-03: [сравнение и до/после](force_variants.md),
  [редактируемые варианты](force_variants.json).
  V1 задний соосный: [A](exports/force_A-V1.svg), [B](exports/force_B-V1.svg).
  V2 один боковой цилиндр с порталом: [A](exports/force_A-V2.svg), [B](exports/force_B-V2.svg).
  Шток сохраняется, новый носитель/траверса/направляющие требуют отдельного расчёта.
- [44 неизменённые привязки](baseline_bindings.md) и
  [точный JSON](baseline_bindings.json), [UNKNOWN inputs](unknown_inputs.json).
  BASE_A/BASE_B **fixed-budget**, исходные D/d, сечение, усилия и все ходы
  сохранены; новые source t/v не выданы за время полного цикла. Числа не округлены.
- [Вопросы R2/R3](R2_R3_requests.md), [точные ссылки прежних ID](R2_R3_requests.json).
  Новые численные значения **не применены**. Нет подбора креплений/COTS по мощности.
- [Критерии будущей геометрической проверки](verification_plan.md),
  [матрицы фаз и явные пары](verification_plan.json): 16 phase matrices,
  2933 записи пар по фазам; это **план**, не результаты проверки пересечений.
  Проверенных геометрических пар этой итерации **0**, geometry NOT_RUN.

SVG редактируется как текст/в векторном редакторе; источник экспорта —
render_schemes.py + JSON. Пиксели — оформление NTS, не размеры изделия.
Условная топология ASSUMED; все новые размеры/посадки/нагрузки/времена и реальные
параметры REV UNKNOWN (null с причиной). Старый CAD-кандидат не изменён.

## Воспроизведение из корня репозитория

Явный экспорт документации (не native CAD/build):

```bash
python3 -B verification/r4_cycle_interfaces/proposal/render_schemes.py --output-dir /tmp/rev-cycle-interfaces-export
```

Сохранённые SVG/CSV/Markdown и exports_manifest.json должны совпасть с экспортом.
Для намеренного обновления публикации отдельно задать
`--output-dir verification/r4_cycle_interfaces/proposal/exports`.
Read-only проверка сохранённого пакета, **без генерации/исправления**:

```bash
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

Текущие результаты исправления — [correction](../correction/README.md). Следующие файлы относятся только к **исходному C ed8272c**, не являются проверками новой редакции: [checks.json](checks.json),
[документальные проверки](document_checks.json), [экспорт/негативные пробы](export_checks.json),
[сохранность](preservation.json). Два повторных readonly запуска совпали без
изменения файлов; два явных экспорта совпали с публикацией. Отсутствующий или
повреждённый SVG, устаревший экспорт, потерянный исходный guard/действие и
изменённый source input отклонены без автоисправления. Это проверки документов,
не материального движка, геометрии, физических условий или безопасности.

## Оставшиеся проблемы и предел готовности

W02 OPEN/NOT_IMPLEMENTED, исполняемая материальная логика и **физический READY NO-GO**.
Новые механические predicates не реализованы в checked helper и не являются PLC.
B opening и физическая выполнимость L-пути INDETERMINATE. Сохранены шесть старых
UP BLOCKED, SHORT_STROKE A/B к CAD выходу, потеря зажимного контакта A,
B reset/product collision и исходные rod/chamber/feed witnesses. Их исправление
в новом CAD этой задачей не проверено; native CAD/STEP/общий rebuild NOT_RUN.
Старые группы 18/14/10 остаются в плане последующей регрессии; прошлые результаты
не расширены на новые схемы или весь пресс.

Носитель, крепления/направляющие/рама, кинематика D/G/P, сохранение столба A,
разгрузка/упор B, приём и остатки требуют ответов R2/R3 и последующего model review.
Ни один вариант не выбран. Реальная работоспособность не подтверждена;
физические испытания NOT_RUN. Точный C с результатами указывается следующим
handoff-коммитом H; независимый R5 review этого нового пакета PENDING.
