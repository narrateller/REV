# B03 — корректирующая итерация по решению R1

Решение `ARB-R1-CI-SEMANTICS-01` на **5fe510bbc55a052c360ab39a2491a061584b8fb7**
прочитано и записано в капсуле до изменения checker. Начальная сверка —
input_audit.json; merge/audit checkpoint e8cb278 сохраняет R1 и R5 полными
предками. Main 3a9258c, accepted PR45 owner r4-linked-20261111, lease до
2026-11-14T00:13:12.404899+00:00 (14 ноября 03:13 МСК) без продления.
Исполнитель R4 / Codex / r4-b03-semantics-20261113, прямое поручение пользователя.

**B03 OPEN до независимого RECHECK.** interface_consecutive_rejections=2
сохранён отдельно от material_contract_consecutive_rejections=2. По R5
5fb731182a2bdf6b11246558eca58962e48568d9 B01/B02 закрыты только документально
на C144941c; их сохранение проверено, приёмка интерфейса/CYC-to-CAD BLOCKED.

Новая [норма v1](../semantics_v1/README.md) и [матрица покрытия](../semantics_v1/coverage.csv)
задают минимальные условия и точные результаты для всех 53 действий/84 режимных
строк, parent lifecycle, удерживаемую выбранную позу, типизированные формулы и
источники, addressed recovery. Проверяемый payload не определяет собственные
нормы. Checker загружает закреплённую ревизию отдельно и не исправляет входы.

Все этапы LOAD/FILL/RETURN/COMMIT и исключение recovery B по собственным guards
сохранены. Историческая FILL квитанция адресована той же дозе/материалу/операции,
parent commit остаётся после D0; revision successor MATERIAL/FEED не переписан.
Closure recovery не требует уже восстановленного общего DEPENDENCY_VALID;
штатная WORK его по-прежнему требует. Ledger/resource/service faults и rejected
operation IDs не очищаются. Никакие новые реальные сигналы/PLC не реализованы.

Все формулы поз имеют AST, тип, SI unit, frame и scenario source refs. Проверяются
каждый операнд, полные approach/work/eject/return, подпись и исходный JSON.
P_RETURN_END сохраняет source return в выражении, а не только имя P0.
Поддержанная эквивалентная линейная запись проходит; неизвестная формула не
объявляется корректной. Новые exports coordinate_formulas.json/md и embedded
SVG содержат эти данные. CSV экспортирует все поля действий, включая outputs.
Условная точность/совпадение AST не доказывают фактический геометрический путь.

Исходный R5 probe воспроизведён до правок: **654 checks / 648 MATCH / 6 FAIL**.
baseline_reproduction.json содержит ровно шесть известных семантических пропусков.
После исправления тот же неизменённый probe запущен в временной полной копии:
independent_replay.json фиксирует авторское воспроизведение, включая отображение
всех 17 исходных замечаний. Исходные R5 script/evidence не перезаписывались.
Успех воспроизведения чужого probe не является новым независимым актом R5.

test_semantic_minimum.py выполняет план решения: шесть точных подмен, другие
стадии/режимы тех же классов, собственные path guards, producer D1, COMMIT/outputs,
parent/mode, каждый фазовый/символьный операнд, чужие сценарии, формула/подпись,
одновременно изменённые JSON/CSV/SVG со свежими hashes, null/чужие базы,
неподдерживаемые выражения, лишние outputs, wildcard/null/чужой recovery target,
подмены action/guard/result type и конкретные frozen fault fixtures.
regression_cases.json сохраняет исход каждого переэкспортированного случая,
свежесть всех hashes и отсутствие записей checker. Проверяются также все прежние
7 методов correction/test_documentary.py для B01/B02/28 старых мутаций.

Точные результаты текущего C — checks.json, document_checks.json, export_checks.json,
regressions.log, retained_regressions.log, registry.log и preservation.json.

Из /workspace/REV:

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

Генерация отдельно, только по явной команде:

```sh
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/render_schemes.py --output-dir /tmp/rev-ci-semantic-export
```

44 bindings, четыре невыбранных force variants, frozen material helper, расчёты,
CAD и исходные акты сохранены. W02, PLC, CAD/rebuild и физические испытания
NOT_RUN/вне scope. Все реальные условия UNKNOWN; physical READY NO-GO.
Архитектура/ТЗ не утверждены, G1 OPEN. Следующий участник — независимый R5,
проверяющий точный новый C по proposal/review_request.md, без самоприёмки автора.
