# Текущая ограниченная коррекция R5-SYM-OBS-01

В interfaces.json/md изменены только четыре row-local CI-ссылки datum_motion
по R1 e380f6d05fe58fe5125c940ac90a151c5bba546b. Source catalog/unknown_inputs.json
не меняются. Остальные 48 строк и все другие производные данные неизменны.
OBS-01 OPEN до независимого recheck нового exact C; локальные PASS его не закрывают.
Новые evidence/команды/актуальные counts — ../obs01_correction/. Старые snapshots
(table_checks*, validation, render_repeatability) ниже относятся к b840dfd и
не выдаются за проверку исправленного target. Заменённые документы/код и их
исторические evidence сохранены в obs01_correction/archive_b840dfd/ и в Git.
Историческая broad authority 80f1028 сохранена; дополнительная команда/акт R1
и исходные четыре FAIL R5 закреплены отдельно, без редактирования reviewer oracle.

---

## Исходная поставка — сохранённая история

# Документальная/символическая постановка T-r4-force-geometry-01

WARNING; author/session R4 `6afb4750-7918-8191-8569-77b5b0c41050`.
Основание: прямое поручение пользователя и точная команда/заключение R1 на
C `80f1028c25d1c4344c0115b7908e02346d895701`. Они прочитаны по Git blobs,
не слиты в ветку исполнителя. `continuation_authority.json` сохраняет версии/хэши.
Предыдущая поставка R4: C `45caac78f00ab1535387bb5ed8d7f17caf9afc1f`,
H `d94096faa3ce9904c9a86b6d38ad1d5863e0f6e9`.
Audited/current fetched main: `f731910273b47f46c6d45114cecd76de6fa8adf9`.
Claim принят PR49 merge `cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9`;
owner/session выше, lease до `2026-11-17T17:44:00Z` без продления.

## Что подготовлено

- [interfaces.md](interfaces.md) / `interfaces.json`: отдельные таблицы
  A-V1/A-V2/B-V1/B-V2, по 13 строк интерфейсов; узлы/оси/связи/DOF/контактные
  стороны, необходимость передачи work/return, существующие source ID/revision/
  commit, известное и UNKNOWN, недостающие аргументы, функциональные адресаты
  и следующая проверка. Фактическая геометрия каждой строки UNKNOWN.
- `source_catalog.json`: точные paths/commits/blobs/SHA256. В JSON каждой строки
  повторены полные source path/commit/selector/ID/revision; в Markdown используются
  aliases однозначного каталога. Отсутствующая в source revision не выдумывается.
- `symbolic_dependencies.json`: только процитированные зависимости из источников
  с условиями и отсутствующими аргументами. Ни одна формула не вычислялась.
- [state_dependencies.md](state_dependencies.md) / `state_dependencies.json`:
  все 42 исходные строки сохранены, добавлены только ссылки на интерфейсы и
  требования получения фазовых нагрузок/контактов. Состояния не решены.
- `unknown_index.json`: указатель всех 84 исходных scoped R3F RAW/null и
  потребляющих их строк. Это не новый registry, не новые ID/ASSUMED-сценарии.
- `preflight_start/`, `preflight_final/`: отдельные новые snapshots текущих
  ancestry/owner/lease/конкуренции, 54 inputs/12 trees/44 full bindings и
  материализованных файлов. Старые evidence и входной аудит не редактировались.
- `table_checks_release.json`: текущая авторская проверка источников/покрытия и сохранения
  UNKNOWN. Это не независимый R5 review и не физическая верификация.
- `heartbeat_start.json` / `heartbeat_end.json`: фактические события исполнителя;
  новые записи не продлевают срок. Статусы/команды registry — в отдельных
  `active_registry.log` / `active_registry_status.json`.
- `review_scope.md` — критерии независимой проверки. Сам запрос `review_request.md`
  и точный target C записываются следующим commit H, чтобы не создавать самоссылку C.

## Что означает известное

Известны только source-определения, унаследованная условная топология и требования
к будущим данным. Унаследованное source ASSUMED не становится новой количественной
гипотезой этой поставки и не получает физического подтверждения.
Ни размеры, ни материалы/E, диапазоны/допуски, силы/сечения/жёсткости/контакты
не назначаются; численные source значения в формулы не подставляются.

Скалярные RAW `E_Y/E_Z`, `CARRIER_I/W`, `*_FREE_LENGTH_MAX` не определяют функции
e_y/e_z(q), L_free_rod(q)/L_free_carrier(q), главные плоскости I_y/I_z/W_y/W_z
или совпадение наихудших поз с пиком силы. Род/носитель/портал — разные звенья;
диаметр штока не задаёт носитель. V1 не получает нулевую несоосность; V2 не
получает равное разделение силы. Нужны обе плоскости и полный ход с внутренними
и частичными позами, без численного задания границ в этой поставке.

Source WORK_PEAK/RETURN_REQUIRED — именованные исходные тесты передачи нагрузки,
а не реальные F(q,t) каждой фазы. Source guide/channel повторно не добавляются.
A startup/retention и B unload/unlock/open/reset требуют собственных контактов,
нагрузок/остатков и подтверждений. Знак возврата не создаёт обратный контакт.

Адресаты R2/R3/R4/R5/R6/R1 в таблицах — функции получения/проверки данных,
не назначения новых owners, claims или сроков.

## Проверки и воспроизведение

Из `/workspace/REV` на ветке
`work-r4/T-r4-force-geometry-01/6afb4750-7918-8191-8569-77b5b0c41050`,
Python 3.12 / PyYAML 6.0.3:

```bash
git fetch --no-tags origin main 80f1028c25d1c4344c0115b7908e02346d895701
.venv/bin/python verification/r4_force_geometry/preflight_20261116/verify_inputs.py --output /tmp/r4-symbolic-new-preflight
.venv/bin/python verification/r4_force_geometry/symbolic_20261116/render_tables.py
.venv/bin/python verification/r4_force_geometry/symbolic_20261116/verify_symbolic.py --output /tmp/r4-symbolic-new-table-checks.json
.venv/bin/python scripts/check_registry.py --check-git
git diff --check
```

Использовать новые output paths: прошлые snapshots не перезаписывать.
Текущий повтор — render_repeatability_release.json; ранние candidate snapshots
сохранены отдельно и не подменяют release evidence. Повтор renderer детерминирован; его изменение не является пересчётом физики.
Старый checker используется как read-only проверка тех же точных input invariants
в свежем запуске. Его поле engineering_geometry NOT_STARTED относится к
отсутствию численной/native геометрии; документальный статус этой поставки
записан отдельно. При иной main он выдаёт FAIL: нужен новый разбор diff и
применимости, а не переименование прежнего PASS.
В текущих fresh preflights список открытых PR пуст; если он изменится, сам
открытый PR не доказывает принятого владельца — отдельно проверить его scope/
accepted main и передать конкретное расхождение координатору. Невидимая
неопубликованная работа не наблюдаема; enforcement PROCEDURAL.

## Сохранённые запреты и незавершённое

Аудит AUD-R4-FORCE-GEOMETRY-INPUT-01 остаётся WARNING: четыре PASS только
документальной согласованности, §4/5/6 NOT_RUN. Здесь не выполнялись независимый
физический пересчёт, реальная геометрия/связи или полный цикл. Реакции,
прочность/устойчивость/capacity/margins, collision CLEAR и physical READY
заблокированы UNKNOWN/NOT_RUN. Новые количественные ASSUMED сценарии не создавались.

54 pinned inputs/12 protected trees/44 full bindings, source нагрузки/ходы/
fixed-budget/active registry/CAD/R3/R5 сохраняются. 42 состояния не рассчитаны,
84 RAW/null не повышены. SHORT_STROKE, A clamp contacts, B reset/product collision,
legacy UP, physical L/B opening, семь REJECT и material history=2 не закрыты.
ТЗ/архитектура NOT_APPROVED, общий CAD-build/rebuild запрещён, W02/PLC/physical
READY NO-GO, G1 OPEN; физические испытания/изготовление/выпуск не разрешены.
Полный инженерный объём не DONE/VERIFIED/LOCKED/PASSED. Независимый OUTPUT-review
этого символического результата NOT_RUN до отдельного акта R5 на exact C.
