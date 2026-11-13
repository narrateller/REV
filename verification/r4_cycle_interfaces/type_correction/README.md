# B03 — узкая коррекция типов по ARB-R1-CI-SEMANTICS-02

Решение R1 **e0fea7bbf3bd32fda601bca2f7567f8e2c3342b3** прочитано и записано
в капсуле до изменения кода. Preflight/input SHA — input_audit.json; merge/audit
checkpoint 64154d8. Base H 480cc59ac76638802dcb96e231e5598c26594d37, R5 акт
3d317b32596884cc60d9d42675924b88fcb29bf0 на Cbd7ce8a. Исполнитель R4 / Codex /
r4-b03-types-20261113 по прямому поручению пользователя. Main 3a9258c, accepted
PR45 owner r4-linked-20261111, lease до 2026-11-14T00:13:12.404899+00:00
(14 ноября 03:13 МСК) не переназначались/не продлевались.

## Контракт типов

metadata_types.py — единый слой без coercion, читающий тип до equality:

| Поле/класс | Поддержанный тип/диапазон | Отказ |
|---|---|---|
| source/ref/AST/binding/norm `revision` | JSON integer, `type(x) is int`, >=1 | bool/float/string/null/container/отрицательное/0 не проходят |
| `origin_revision`, fault/context/origin/current snapshots | JSON integer >=0; snapshot — object с непустыми string keys и только такими counters | Невалидный snapshot не даёт TRUE |
| Числовые `schema`, `increment`, `acceptance_PR` | integer >=1, затем точное значение действующего контракта | bool и integral float не alias integer |
| Named schema | непустой string ID, точное совпадение с закреплённой нормой | Не переводится в числовой schema |
| Счётчики истории отказов | integer >=0 | Не обнуляются и не преобразуются |
| Metadata dict/list/scalars и flags | точный JSON type/shape/value рекурсивно | `1 != true`, `0.0 != false`, пропущенный ключ не default |
| `basis_revision` в identity scope | прежний непустой textual tag | Не интерпретируется как integer revision |

Верхней границы счётчиков, не объявленной прежней схемой, не добавлено.
Положительные fixtures включают исходные integer counters, 0 для snapshots,
1 и большой допустимый integer. Допустимый тип сам по себе не разрешает
несовпадающую с закреплённым source revision ссылку.

Plural origin_revisions в документальном recovery **binding** является
декларацией источника, а не числовым snapshot. Такой binding сравнивается со
всей неизменённой нормой типизированно. Конкретные runtime snapshot objects
проверяются revision_map до вызова frozen policy. Историческое FILL
описание origin_revisions также не подменяется числовым counter.

Аудит аналогичных сравнений:

- check_package.read, semantic_minimum.load/minimum и document_semantics.read
  проверяют все вложенные метаданные до прежних semantic comparisons;
- standalone AST source_ref валидируется отдельно, затем сравнивается по
  строгим типам, ключам и значениям с независимой нормой;
- authority/schema/manifest, phase_pose_bindings, outputs, pose constraints
  и recovery binding используют metadata_equal. Числа вместо bool flags не
  легализуются даже после согласованного re-export;
- action/phase/pose source refs используют тот же контракт; `value` численной
  source-row сохраняет физическую numeric equality без bool-чисел. Для
  quantities integer/float с тем же значением по-прежнему допустимы. Exact
  rational strings сохраняются строками; parser/алгебра/времена не менялись;
- FILL commit/current revision maps сравниваются строго, а прежние per-domain
  integer checks и MATERIAL/FEED successor сохранены.

## Recovery predicate и frozen policy

recovery_value проверяет типы пяти snapshots: proof origin/current, context
current, fault immutable origin и expected current. Затем использует неизменённый
frozen recover на **том же** proof/context/fault; его предложенный новый state
отбрасывается, в caller не применяется. ALLOWED_ASSUMED/BLOCKED/INDETERMINATE
преобразуются в TRUE/FALSE/UNKNOWN. Origin false/0.0 не преобразуется в 0.
Исходные proof, context, fault IDs/rejected IDs не исправляются ради успеха.
Невалидные origin snapshots дают UNKNOWN/INDETERMINATE, fault остаётся OPEN.
Сохранение readonly само по себе не считается доказательством корректного TRUE.

Норматив и весь semantics_v1 **не изменены**. SHA minimum.json остаётся
`b1c13c18c408120ae66d4995eac706e8dbf5842f35976494efb682c74e64d3df`.
Payload permissions/poses/protocol, 44 bindings, четыре force variants, нагрузки,
frozen helper, расчёты и CAD сохранены. Переэкспорт меняет только source hashes
в manifest; сами JSON/CSV/MD/SVG exports побайтно прежние.

## Проверки и область

До исправления неизменённый R5 probe воспроизведён в изолированной копии без
reuse: 765 checks / 759 MATCH / 6 FAIL. baseline_reproduction.json сохраняет
конкретные исходы. После исправления тот же probe даёт 765/765; полный отчёт
independent_replay.json — авторское воспроизведение, не новый независимый акт R5.
Оригинальные R5 scripts/evidence и все три REJECT сохранены.

type_cases.json: 244 fresh re-export cases, включая A/B action/source refs,
разные фазы/стадии, pose source catalog, каждый класс AST source и phase_pose
bindings, authority/manifest, bool flags, отсутствие и контейнеры. Проверены
true/false, 1.0/0.0, строка/null, отрицательное/0, исходный корректный пакет и
эквивалентная формула. Каждый случай проверяет свежесть hashes и отсутствие
записей checker. 36 differential recovery cases проверяют те же inputs в
predicate и frozen helper, положительные границы, разные домены, stale/wrong
snapshots, target scope и сохранение fault/rejected history. Прежние 411
semantic cases и 7 методов B01/B02 также выполнены без изменения fixtures.

Точные команды/exit codes и хэши evidence — checks.json. Из /workspace/REV:

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

Явный exporter отдельно, только документация:

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/render_schemes.py --output-dir /tmp/rev-ci-types-export
```

B03 OPEN до независимого RECHECK нового C. interface_consecutive_rejections=3,
отдельная material-contract history=2 не сброшены. B01/B02 закрыты только в
документальной области прежнего C144941c, здесь сохранены их регрессии.
Стабильная передача интерфейса и новая CAD-итерация NO-GO. W02/PLC/CAD/rebuild/
physical trials вне scope, physical READY NO-GO. Архитектура/ТЗ не утверждены,
G1 OPEN. Автор не присваивает себе независимую приёмку R5.
