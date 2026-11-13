# REV-R5-CI-SNAPSHOTS-RECHECK-01-001

**B03 OPEN — REJECT_WITH_BLOCKER. Стабильная документальная передача CYC-02/03 — NO-GO.**
Четыре прежних ложных TRUE устранены, domain/type/history prevalidation подтверждена
в проверенных случаях. Остался другой явно заданный критерий R1: некоторые ранние
возвраты по malformed proof скрывают известный BLOCKED общего action gate.
Это несоответствие документальной семантики; новых ложных TRUE не обнаружено.

R5 / Codex / session **r5-ci-snapshots-20261113**, прямое поручение пользователя,
13 ноября 2026, МСК. Reviewer не автор проверяемого checker, helper или норматива.
Авторские сессии: r4-linked-20261111, r4-cyc-fix-20261113,
r4-b03-semantics-20261113, r4-b03-types-20261113, r4-b03-snapshots-20261113.
Организационная независимость не удостоверяется. Parent ownership/lease и main
не присваивались; публикация акта в отдельной ветке, без merge в main.

| Неизменяемый вход | SHA |
|---|---|
| Проверенный C | **e30b4b7caf3040905cc23c79ca696af2871c958a** |
| Эстафета H | **ff050572f88f108c2092827e98cd4d98bd874737** |
| R1 ARB-R1-CI-SEMANTICS-03 | **39826eb2f5dbd1f83d81882022e6f59313ebe5d5** |
| Четвёртый REJECT | 0ff3c8f4502ea29c712bf1f41e223f172c5a21c7 |
| Третий REJECT | 3d317b32596884cc60d9d42675924b88fcb29bf0 |
| Второй REJECT | 5fb731182a2bdf6b11246558eca58962e48568d9 |
| Первый OUTPUT/REJECT | 13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2 |
| Frozen contract/helper | 0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed |

C/R1/четыре акта — предки H. Интерфейсный пакет совпадает в C/H/рабочем дереве.
SHA самого акта фиксируется следующей H-капсулой, без самоссылки.

## Независимый oracle и положительные результаты

Ожидаемые домены взяты `git show` из frozen contract, не из предъявленных maps
или результата candidate assessment. Рабочие contract/helper предварительно
побайтно сверены с фиксированными Git blobs. Для B_RESET_CONFIRMED E={B_CLOSURE};
для current дополнительно нужны объединённые evidence_domains собственных ENTRY
RESTORE_B_CLOSURE. Для каждого ENTRY guard используется свой набор.
Fixtures — собственные функции прежнего независимого R5, без author fixture imports.

Проверена явная схема DOMAIN_SCHEMA.md:

- origin/expected/proof.origin требуют exact E; пустые, отсутствующие, чужие-only
  и дополнительные известные/неизвестные домены не заменяют E;
- proof.revisions содержит E; разрешённые известные extras — typed annotations,
  не подтверждение чужих guards; current содержит только E ∪ ENTRY obligations,
  а не обязательный полный глобальный map;
- bool, float, string, null, array/object и отрицательная revision отклоняются;
  source/snapshot диапазоны и неподтверждённые integer revisions не смешиваются;
- отдельно удалён каждый из семи обязательных current domains, каждый требуемый
  domain каждого ENTRY proof; multi-domain partial maps сохраняли прочие keys;
  E целевого guard одноэлементно, поэтому его partial map является пустым;
- expected проверен независимо от origin: отсутствие/пустота, неверный domain,
  extra keys и неподтверждённый advance не проходят. Допустимые +1 histories
  длиной 1/2/5 сохраняют отличающийся от current immutable origin;
- правильные integer snapshots 0/1/2^63 и минимальные consumed maps допускают
  адресный recovery. Отсутствие или корректное изменение FEED/RETENTION само
  по себе не блокирует B_CLOSURE;
- отдельная последовательность сохраняет FEED fault после допустимого closure
  recovery; последующий обычный B-COMPACT остаётся BLOCKED. Возвращённая helper
  копия используется только как следующий синтетический вход, не применяется
  к caller или машине.

Все семь неизменённых прежних incomplete cases повторены в временной tracked
копии: **7/7**, включая исправление четырёх coherent F-digest/causal-ID подмен.
Пустой expected, согласованные пустые origin/proof, FEED-only origin/proof и
пустые origin+expected теперь дают UNKNOWN с причиной до делегирования.
Исторические C/session literals неизменённого скрипта не объявляются identity
нового запуска; actual C зафиксирован authority_and_prior.json.

Собственная матрица: **295 случаев, 276 совпадений, 19 несовпадений**.
Все 19 относятся к двум ранним ветвям общего gate, не к ложному TRUE.
Полные ожидания/диагностики/digests — independent_results.json.

## Остаток B03: BLOCKED скрывается ранними возвратами

R1 §2 и критерий RECHECK прямо требуют сохранять известные resource/state/causal
FALSE в общем BLOCKED даже при невалидном proof. Нельзя объявить эти случаи
успешными только потому, что UNKNOWN также не является разрешением движения.

| Независимое свидетельство | Ожидалось | Получено |
|---|---|---|
| Полноценный context с текущим RESOURCES_READY=FALSE, либо OPEN resource fault; proof целиком null/array/string/bool/number | recovery UNKNOWN, общий BLOCKED | recovery UNKNOWN, общий **INDETERMINATE** |
| Полноценный context с заведомо недопустимым для recovery состоянием; тот же malformed proof | общий BLOCKED | **INDETERMINATE** |
| Валидно адресованный B_RESET fault с OPEN causal FEED fault; в proof отсутствует/подменён action или guard | recovery UNKNOWN, общий BLOCKED | **INDETERMINATE** |

Первая ветвь: recovery_snapshots.py:56–57 возвращает начальный result до
независимого ENTRY/state assessment. Это 15 вариаций: три вида известного запрета
(resource record, latched resource fault, state) × пять типов целого proof.
Frozen ENTRY на тех же contexts — BLOCKED; proof не нужен для установления
этого собственного запрета.

Вторая ветвь: recovery_snapshots.py:99–100 возвращает finish при отсутствующем
или чужом action/guard до оценки causal statuses на :101–104. Target fault_id,
origin, parent ID и OPEN ancestor известны, но causal_value остаётся UNKNOWN.
Это четыре вариации. Frozen recover на тех же proof/context/fault — BLOCKED
по unresolved causal fault. Адрес не выдумывался из malformed proof.

Минимальные полные inputs и outputs двух ветвей — minimal_witnesses.json;
19 вариантов — independent_results.json. Быстрый повтор двух свидетелей:
`.venv/bin/python -B verification/r5_ci_snapshots_recheck/reproduce_blocked.py`
(minimal_replay.json:0/2 совпадений ожидаемого BLOCKED). Caller/proof/immutable origins,
expected/history/rejected IDs не менялись. Faults не сняты, TRUE/physical
permission не получены. Это два нарушения порядка композиции, не 19 разных
физических неисправностей и не доказанное ложное разрешение движения.

При повреждении только snapshot-полей внутри корректного proof object новый
код сохраняет BLOCKED; именно переходы до общей композиции остаются неполными.
Исправлять helper, норматив или payload reviewer не стал.

## Область frozen compatibility

**46 IN_DOMAIN случаев** совпадают с frozen policy на уровне action gate;
при VALID revision bindings совпадает также scoped value. Stale revisions,
чужой scope/epoch, FALSE/UNKNOWN proof и causal/собственные отказы проверены
на одинаковых proof/context/fault. Безусловное равенство для malformed inputs
не заявляется и не требуется решением R1.

**249 OUT_OF_DOMAIN случаев** имеют явные schema reasons и NOT_EVALUATED
candidate policy: 37 намеренных ужесточений относительно legacy ALLOWED_ASSUMED,
193 прочих объяснённых отказа вне схемы и 19 описанных нарушений общего gate.
Намеренные UNKNOWN вместо legacy TRUE не считаются дефектами: неполные/чужие
maps или неподтверждённая история вне допустимого домена. Legacy exceptions
сохраняются как диагностический результат, не PASS. Постатейные reasons и
классификация каждого случая — policy_comparison.json и policy_comparison.md.
Нарушение сохранения BLOCKED за пределами схемы — отдельный критерий композиции,
не попытка снова потребовать unconditional policy equality.

## Воспроизведение и сохранность

Из `/workspace/REV`, Python 3.12.14 `.venv/bin/python -B`. Точные argv, exit codes,
capture environment и raw stdout/stderr — commands.json. Exit 0 собственного
probe означает завершённый сбор; FAIL остаются в failed.

| Команда после `.venv/bin/python -B` | Результат |
|---|---|
| `verification/r4_cycle_interfaces/proposal/check_package.py` | 3277 MATCH, PASSED_DOCUMENTARY_ONLY |
| `verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py` | 8 MATCH, свежие exports и readonly repeat |
| `-m unittest discover -s verification/r4_cycle_interfaces/snapshot_correction -p 'test_*.py' -v` | 11 методов, 118 случаев PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v` | 6 методов, 244 re-export cases / 36 comparisons PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v` | 6 методов, 411 случаев PASS |
| `-m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v` | 7 методов B01/B02 PASS |
| `verification/r5_ci_snapshots_recheck/repeat_prior.py` | norm reproduced; неизменённые probes654/654,765/765,incomplete7/7 |
| `verification/r5_ci_snapshots_recheck/independent_probe.py` | 295/276/19; собственные compound witnesses |
| `verification/r5_ci_snapshots_recheck/verify_preservation.py` | source/helper/norm/44bindings/4variants/calculations/CAD/история сохранены |
| `scripts/check_registry.py --check-git` | registry.log; согласованность repository evidence, не инженерная приёмка |
| `git diff --check`; `git lfs fsck` | PASS |

Прежние probes выполнялись без reuse в materialized tracked временной копии
с Git object DB только для чтения. Оригинальные evidence не перезаписаны.
Source expectation semantic probes включает собственные family obligations,
полиномиальный phase/source oracle и прежние coherent re-export substitutions.
Типовые/семантические source mutations повторены после свежего JSON/CSV/SVG
экспорта с обновлёнными hashes; это отдельно от runtime recovery fixtures,
которые не имеют CSV/SVG exporter.

Норматив 53 действий / 84 режимных правил / 18 поз точно воспроизведён из fixed
blobs, SHA256 minimum.json:
`b1c13c18c408120ae66d4995eac706e8dbf5842f35976494efb682c74e64d3df`.
612 protected files, 7 frozen packages, 11 protected trees,17 input blobs,
44 bindings, четыре force variants и все четыре прежних акта сохранены.
Диаметры, нагрузки, ходы, расчёты и CAD не менялись. Сохранность доказана
сравнением bytes/trees; это не независимый пересчёт физики или проверка native
проникновений. Геометрических пар проверено 0, прочность/устойчивость/геометрия/
CAD rebuild/физические испытания NOT_RUN.

## Вердикты и передача

- **B01/B02:** прежнее документальное закрытие в границах C144941c сохранено,
  LOAD/FILL/RETURN/COMMIT, recovery/history регрессии PASS.
- **B03:** OPEN, REJECT_WITH_BLOCKER по сохранению общего known BLOCKED;
  прежние четыре false TRUE и snapshot domain/history admission исправлены
  в проверенной области. Новых ложных TRUE не найдено.
- **Стабильная документальная передача CYC-02/03:** NO-GO до устранения ранних
  возвратов и нового независимого exact-C RECHECK. Ранее разрешённые R3 force-path
  studies остаются WARNING с действующим claim и точными inputs; это не приёмка
  силового пути или разрешение новой CAD-итерации/физического действия.

История четырёх отказов/SHA/evidence сохранена; текущий — пятый:
interface_consecutive_rejections=5, отдельный material counter=2. По §6.1
AGENT_PROTOCOL вопрос Q-R1-CI-SEMANTICS-ARBITRATION-01 REOPENED, следующая
коррекция BLOCKED до записанного решения/плана R1; карточка R1_followup.md.
**W02 OPEN/NO-GO, physical READY NO-GO, G1 OPEN.** Архитектура/ТЗ не утверждены.
