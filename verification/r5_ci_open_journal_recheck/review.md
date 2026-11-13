# REV-R5-CI-OPEN-JOURNAL-RECHECK-01-001

**B03 CLOSED — PASS только в bounded документальной области на C `8b72716021b0c3a64972033d09fe5e80945eb98e`.**
**Стабильная документальная передача CYC-02/03 — GO на этом C, общий WARNING.**
W02/PLC, исполняемая материальная логика и физический READY — NO-GO; G1 OPEN.
Новая геометрия, CAD rebuild, прочность, реальные испытания и утверждение ТЗ/архитектуры не выполнялись и этим актом не разрешаются.

R5 / Codex / session **r5-ci-open-journal-20261113**, прямое поручение пользователя.
UTC 2026-11-13T19:09:09.593707+00:00. Reviewer не автор candidate/helper/норматива; отдельная сессия и
самостоятельный fixed-contract oracle. Организационная независимость не удостоверяется.
Ветка `work-r5/T-r5-ci-open-journal-recheck/r5-ci-open-journal-20261113`; main/owner/lease не изменялись.
Claim R4: PR45, owner r4-linked-20261111, lease 2026-11-14T00:13:12.404899+00:00;
проверенный main 3a9258c57e4bc15d6de98f1d17e8412ad6e8899a. Это review, не захват авторской задачи.

| Вход | Точный SHA |
|---|---|
| Проверенный C | 8b72716021b0c3a64972033d09fe5e80945eb98e |
| Эстафета H | fa4c59702e338e6b6d1e322b0698137a233ad011 |
| R1 ARB-R1-CI-SEMANTICS-06 | a85e69f3a495176c614202a518be6784be8f3b31 |
| Frozen contract/helper | 0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed |
| Седьмой REJECT | 4e52c3953c989c1077107d1d4f4da6d39d923d85 |

Все 205 файлов интерфейсного пакета совпадают в C/H/рабочей копии. R1 и все семь
актов — предки H. SHA текущего акта указывается следующим H, без самоссылки.

## Отдельные вердикты

1. **B03: CLOSED / PASS_DOCUMENTARY_EXACT_C.** Все OPEN должны иметь явную
   классификацию до positive admission. Проверенные неклассифицируемые records
   дают journal UNKNOWN, OUT_OF_DOMAIN, policy NOT_EVALUATED и recovery UNKNOWN.
   Raw TRUE не обходит этот барьер; raw UNKNOWN сам не создаёт FALSE.
   Независимо доказанные raw/own/state/addressed-causal FALSE сохраняют BLOCKED.
2. **Стабильная документальная передача CYC-02/03: GO / WARNING.** Можно ссылаться
   на exact C как на проверенный условный документальный интерфейс, его позы,
   guard/parent/mode/source связи и ограниченный recovery admission.
   Это не приёмка полного журнала, W02, PLC, физического цикла, CAD или оборудования;
   все downstream работы требуют собственного действующего claim и точных входов.

## Повтор прежних inputs

`reproduce.py` материализует exact C через git archive во временную копию; никакие
авторские или прежние R5 evidence в рабочем репозитории не перезаписываются.
Фактические source hashes закреплены в preservation.json и replay/corrected_capture.json.
Исторические C/session/role literals неизменённых replay runners описывают их
старый контекст, а не identity настоящего акта; актуальная identity — таблица выше.

- Неизменённая R5 matrix: **732/732**, все восемь finish exits исполнены.
- Все **36/36** прежних false TRUE, с прежними typed и ordered input digests:
  теперь INDETERMINATE / recovery UNKNOWN / admission UNKNOWN.
  Это 18 ordered inputs / 6 canonical maps / одна семантическая причина,
  не 36 физических дефектов (`thirtysix.json`).
- Minimal missing/null/known-FEED: **3/3**. Known-FEED и адресный positive recovery
  сохраняют TRUE/ALLOWED_ASSUMED; FEED не удаляется и не переписывается.
- Реальные reader errors, инъекции raw/journal/both exceptions, invalid/stale/foreign
  FALSE, state/causal и positive controls прежней матрицы прошли.
- Прежние independent probes: **654/654, 765/765, incomplete 7/7, 295/295, 231/231**;
  все 19+8 старых witnesses сохраняют input digests и известный BLOCKED.

## Собственная независимая матрица

**5368/5368**, без false allowance и без blanket BLOCKED; весь caller, proof,
contract, origin, expected, histories, rejected IDs и pending observations readonly.
Набор guard, identity fields, evidence domains, action ENTRY/result берутся из
Git blobs frozen C0c4eb5d. Fixtures — прежнего независимого R5, не автора кандидата.
Candidate classify наблюдается как проверяемый результат, не как oracle.

| Группа | Cases |
|---|---:|
| Все 40 fixed guards, собственные роли и известная неприменимость | 40 |
| Для каждого guard: missing identity fields, неизвестные/неверно типизированные tags, неполные origin/expected domains, bool/float/null/negative counters, status/truth/history/causal defects × raw TRUE/FALSE/UNKNOWN | 4212 |
| Все 120 перестановок пяти records с двумя различными unknown и known FEED × девять сочетаний двух own raw guards | 1080 |
| Known FEED, исторические scope/revisions, три позиции и три truth | 9 |
| Адресный positive recovery при 0/1/large integer | 3 |
| Advance со stale ENTRY остаётся UNKNOWN | 3 |
| Тот же advance со свежими ENTRY проходит | 3 |
| Unconsumed RESOLVED history и OPEN до/после неё | 6 |
| Независимые raw/state/own/addressed-causal FALSE с unknown в трёх позициях | 12 |

Каждый вызов проверяет число просмотренных records. Для unknown проверяются
явные причины UNCLASSIFIABLE, отсутствие TRUE journal/recovery и отсутствие
положительного делегирования policy. Ошибочная гипотеза собственного первоначального
positive-advance fixture исправлена: смена B_CLOSURE делает RESET_SWEEP_CLEAR stale;
это теперь отдельный отрицательный контроль, а positive получает свежее ENTRY
через fixed fixture. Поведение кандидата при stale не объявлялось дефектом.
RESOLVED вне используемой causal цепи остаётся под прежней history policy;
историческое физическое evidence не переоценивается в current scope.
Ограниченная other-operation EVENT_FRESH policy проверена retained suites и
не используется для легализации неизвестных OPEN guards.

## Регрессии и сохранность

Авторские suites воспроизведены с исходными assertions: journal 8 methods/417 controls,
raw 9/966, gate 11/220, snapshot 11/118, type 6/244+36 differential,
semantic 6/411, B01/B02 7 methods. Package **3277 checks**, export reproduction
**8 checks**, normative minimum из fixed blobs **53 actions / 84 mode rules / 18 poses**.
В type-suite первый положительный контроль не смог прочитать исторический
3591a5f92f78b1edea07d3fc5354fd0a99090798 из исходного snapshot среды.
Git object получен через существующий Git proxy; assertions и candidate не менялись.
Первый stderr сохранён; отдельный type_correction_retry фиксирует повтор после fetch.

`preserve.py` независимо сверяет 612 защищённых inputs, 1329 файлов прежних
деревьев и 23 payload/data exports с Git BASE/C/H и рабочими bytes; для LFS
Git pointers неизменны, hydrated content совпадает с oid sha256 и declared digest.
Целые деревья CAD/models/scripts/tests/params/evidence/drives/calculations,
норматив и семь review packages сохранены. 44 bindings, четыре force variants,
нагрузки/расчёты/геометрия не менялись. Caller hash/equality/serialization
проверены отдельно от файловой сохранности.

Все семь REJECT сохранены, их findings/verdicts/reviewed SHA/hashes не переписаны:
13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2,
5fb731182a2bdf6b11246558eca58962e48568d9,
3d317b32596884cc60d9d42675924b88fcb29bf0,
0ff3c8f4502ea29c712bf1f41e223f172c5a21c7,
88a34f8b7d2d6dbf236101f207e206efb0e3c747,
18e5af1dae177cdfcb24951d3b36c2fd43395421,
4e52c3953c989c1077107d1d4f4da6d39d923d85.
interface_consecutive_rejections history=7 и material_contract=2 не обнуляются.
Новое документальное закрытие supersedes B03 только на exact C, не меняет
выводы старых актов на их версиях и не закрывает родителя CYC/G1 от имени R1.

## Воспроизведение

Из /workspace/REV, Python 3.12 и requirements.txt, доступ к frozen Git objects:

```sh
.venv/bin/python -B verification/r5_ci_open_journal_recheck/reproduce.py
.venv/bin/python -B verification/r5_ci_open_journal_recheck/independent_probe.py
.venv/bin/python -B verification/r5_ci_open_journal_recheck/preserve.py
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
```

Если старый snapshot не содержит pinned Git object, получить его read-only fetch,
а не подменять expected/source pins. `reproduce.py --retry-failed` повторяет только
ранее неуспешные команды и сохраняет первый failure log. Повтор старых probes в
изолированной копии меняет только её disposable outputs.
Прочность/устойчивость/native CAD/rebuild/physical trials NOT_RUN, geometric pairs=0.
W02/PLC/physical READY NO-GO; архитектура/ТЗ не утверждены; G1 OPEN.

Итоговый registry preflight сначала отклонил новую запись акта из-за пропущенного
поля scope. Поле добавлено; первый результат сохранён как registry_initial_schema.log.
Это ошибка оформления данного review, не отказ проверяемого кандидата; окончательный
результат сверки находится в registry.log и final_checks.json.
