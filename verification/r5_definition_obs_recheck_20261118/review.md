# R5 — независимый recheck OBS-01/02 на exact C

**Общий WARNING. R5-DEF-OBS-01 и R5-DEF-OBS-02 CLOSED_DOCUMENTARY_EXACT_C только
на `97f58fd437947e26963bdbbc2f2d89df7438e8cc`.** Их исходные смысловые дефекты
исправлены в предложениях определений/метода. Новый **R5-DEF-OBS-03 OPEN**:
в сводке неверно указана версия DM02/03. Предварительный DRAFT пригоден для
дальнейшей документальной доработки; согласованный контролируемый комплект
методов и ТЗ/G1 не утверждены. Все девять общих групп решений остаются OPEN.

`reviewed_commit: 97f58fd437947e26963bdbbc2f2d89df7438e8cc`.
Request H `46cbf199c3d17049ac31aa337378f0b176e70a2e`; PR60 DRAFT/unmerged.
Команда пользователя `64ed653039275d9eeaaa081681794f54bbe54e73`;
принятая main activation `974767804240ca24997d3ca538825ff9a4baebab` (PR62).
Предшественник exact C `7e2d5ecff42fe1d09b461e05375924cb644c27c9` не подменяет
новый reviewed_commit. Старый акт C `1d4593f93ba0b315379a885ba9fd955b7ded392c` /
H `ad627d310ee9f49d730b71c84ab4af7c9c1ff0da` сохранён без изменения.

## Идентичность, полномочия и входной аудит

Actual session/thread `6afb0a73-b16c-8191-a539-9a6685e89034`; продолжающая R5,
та же задача `T-r5-g1-supplement-output-review-01`. Codex на базе GPT-6;
exact runtime model ID UNAVAILABLE. Фактически использованы Bash, Git/Git LFS,
gh/GitHub API и Python3.12.14/PyYAML. [Identity](identity.json) и собственный
actual heartbeat записаны до содержательной оценки.

Reviewer не соавтор новой R1 ревизии, её quantity mappings, retention plan или
renderer. Автор target — R1 `6afb300b-1540-8191-a5c4-be1a684c20e0`. Эта же reviewer
session создала первоначальные два замечания, прежние force/symbolic/OBS01/source/
rev8/G1/DOC01-TRACE02/definition reviews и участвовала в подготовке claim. Это
upstream-участие раскрыто; правильность собственных прежних актов здесь заново
независимо не удостоверяется. Организационная независимость и профессиональная
компетентность не сертифицируются моделью или числом проверок.

В свежем remote main подтверждены ancestry и ACCEPTED_MAIN amendment
`coordination/scope_amendments/T-r5-g1-supplement-output-review-01/G1-DEF-OBS01-02-REVISION-01.json`.
Его target/request/manifest, owner actual R5 и исходный deadline совпали. Canonical
base claim побайтово неизменён и всё ещё указывает predecessor fe10c0bc…; новый
target разрешает именно явный amendment. Base-claim SHA256
`9b610dbb7bbbaaa1590e72ac8ea407f0075994cdb0056e005ac6a0499bd12ab3`;
target-manifest SHA256
`e40ecd8299a02b2aa32e9a1517bedbb47acac5ab8e676d105734b3e82aec476a`.
У actual session одна принятая задача; конкурирующего owner/scope не найдено.
R1 owner/claim также действуют. Исходный срок `2026-11-18T01:58:30.990734+00:00`
не продлён; нового role/task/claim/lease нет.

[Входной аудит](input_audit.json): WARNING_DOCUMENTARY_ONLY, четыре ограниченных
документальных раздела PASS, §4/5/6 NOT_RUN. Все **53 input seals и 28 target artifacts**
совпали по immutable Git/SHA и материализованным файлам. AGENTS, протокол,
STATE/NEXT, актуальные capsules, R1/R5 profiles и опубликованная команда прочитаны.
Remote main/head/CI и исходные версии — [remote_context.json](remote_context.json),
[target_CI.json](target_CI.json). Отдельного CI-run на source target C нет;
успешные runs H/main/activation относятся к их собственным SHA.

Review-ветка начинается с exact request H и объединяет принятый main только
в изолированном контексте. Два JSON-конфликта разрешены сохранением R1 correction
и external-scope metadata, а также полной предыдущей R5 task history; новый
review status/heartbeat относится к текущему target. R1 heartbeat не выдумывался.
Обе исходные версии/хэши сохранены в [merge_context.json](merge_context.json).
Ни canonical claim, ни amendment, ни target artifacts reviewer не исправлял.

## OBS-01 — CLOSED_DOCUMENTARY_EXACT_C

DEF-02-G явно добавляет определение плотности и отдельно насыпной плотности;
DEF-03-F — массы изделия и отдельно массы остатка при применимости. Все прежние
144 scope items сохранены целиком; всего 146. Новые наблюдения/открытые решения
и additional evidence fields дополняют прежние записи, не заменяя их.

Четыре mappings независимо сверены с frozen VAL02/03, MATERIAL/MASS на exact
45d596… и REQ22/DEF22G:

| Mapping | Охват и собственная оценка |
|---|---|
| DENSITY_DEFINITION | VAL02→DEF02G/MATERIAL. Неуказанный вид плотности требует определения; он не объявлен автоматически насыпной плотностью |
| BULK_DENSITY_DEFINITION | MATERIAL→DEF02G. Отдельные состояние/подготовка пробы, масса и граница объёма; нет вычисленной или измеренной плотности |
| PRODUCT_MASS_DEFINITION | VAL03→DEF03F/MASS. ID/состояние конкретного изделия; масса дозы, остатка или пресса её не заменяет |
| RESIDUE_MASS_DEFINITION | VAL03/REQ22→DEF03F/DEF22G/MASS. Масса остатка при применимости отделена от качественного наблюдения остатка и массы изделия |

MATERIAL сохраняет предложенную единицу kg/m³ насыпной плотности, MASS — kg;
это ссылки на будущие определения каналов, а не основание для собственных новых
инженерных значений. В mappings value/unit/tolerance/method_revision остаются null
с причиной, actual_records пусты. Нет формул, измерений, пределов, утверждённых
методов или назначения исполнителя. Это устраняет исходный пробел явного crosswalk.
Закрытие замечания не означает определения самих величин/методов/критериев или
подтверждения свойств фактического сырья и изделия.

## OBS-02 — CLOSED_DOCUMENTARY_EXACT_C

DM03/DRAFT-02 прямо требует сохранять каждую попытку цикла, неуспешный/неполный
исход, quality_flag, missing_reason, disposition, raw_event_refs и series_accounting_refs.
Фраза об «отсутствии результата» заменена явным различением отсутствующего изделия/
измерения и сохраняемой записи цикла. Неизвестная масса остаётся UNKNOWN, не нулём.

Retention plan связан с DEF01-E, DEF04-D, REQ22/VAL22 и exact retained evidence schema.
`missing_reason` семантически сопоставлен обязательному `unknown_reason` этой схемы,
`quality_flag` — её одноимённому полю. Это проект соответствия определений полей,
а не утверждённый JSON pointer/исполняемая схема. Исход физического процесса и
качество наблюдения различены: INVALID/SIGNAL_LOSS не доказывает останов/отказ
движения или NO_MOTION_CONFIRMED.

Failed/incomplete records нельзя удалять из полного controlled ledger после
aggregation/disposition. Производная выборка допускается лишь с объявленным scope/
coverage/exclusions и ссылками на сохраняемый unfiltered ledger; базовые записи
остаются доступны. Сохраняются raw revision/time/quality и связи с остановами,
браком, остатками и потерями. Неизвестные объекты/массы — null с причинами;
вымышленные изделия, нулевая масса и успешный исход не подставляются.

Actual records пусты, execution NOT_RUN, retention_duration null с причиной.
Конкретная исполнимая схема, хранение и срок не утверждены, разрешения удаления нет.
Исходная неоднозначность устранена в документальном контракте; никакой реальной
серии, реализации evaluator/ledger или безопасного состояния этим не проверено.

## OBS-03 — OPEN, несогласованная версия метода в представлении

В [method_catalog.json](../r1_g1_definition_obs_revision_20261117/method_catalog.json)
DM02 и DM03 имеют `revision_label: DRAFT-02` (строки 70/105). Однако
[definition_register.md](../r1_g1_definition_obs_revision_20261117/definition_register.md)
пишет `DM-02 / DRAFT-01` и `DM-03 / DRAFT-01` (строки 49/74).
Причина — hardcoded `/ DRAFT-01` в
[render_register.py](../r1_g1_definition_obs_revision_20261117/render_register.py), строка 37.

Шесть renderer MATCH воспроизводят эту ошибку; они не подтверждают корректную
идентичность версии. Собственный check `rendered-method-revision-consistency`
даёт **FAIL** с обеими точными парами JSON/rendered. Он не подавлен и не переименован
в PASS. Требуется авторское получение отображаемой revision из соответствующей
строки method_catalog, регенерация затронутых сводок и exact-C review исправления.
Старые snapshots/акты не переписывать. Текущую сводку нельзя считать согласованным
контролируемым методом. Замечание не запрещает предварительное обсуждение DRAFT;
оно сохраняется отдельно от двух узких semantic closures.

## Регрессии, ограничения и обязательная доработка

Все 22 REQ/VAL и 146 scope items самостоятельно рассмотрены в текущей области.
В [independent_results.json](independent_results.json) сохранены 22 row assessments,
146 item entries, 22 method assessments, четыре quantity assessments и 11 отдельных
semantic cases. Последние — reasoning по предлагаемому контракту, а не фактические
machine cases или тесты реализованного evidence evaluator.

Остальные **20 полных строк и методов** целиком совпали с предшественником;
у DEF02/03 сохранены все поля вне названных additions, старые observations/gaps —
точные префиксы. Все **40 полных source rows/qualifiers** и девять decision rows
неизменны. Источники сохраняют 10 TARGET_PROPOSAL/23 REFERENCE_CONTEXT/7 OPEN_SOURCE_ISSUE,
RAW и realized=null; численное использование/повышение запрещены. BP500 primary,
E55/WEIMA/ARS только по релевантности. Up-to/material/settings, literal pressure,
раздельные power declarations и moisture basis не исправлены догадкой. Нового
независимого удостоверения PDF/прежних собственных актов здесь нет.

Pure DOCUMENTARY_AUDIT остаётся только для качественных подутверждений REQ18–21;
18 остальных профилей требуют mixed/numeric subclaim selection. Применимая
метрология измерений и входов модели не снимается словом DOCUMENT. Общий protocol
сохраняет UNRESOLVED для молчания и необходимость независимого review исключений,
контролируемого scope/method/competence и отдельных полномочий утверждения.

H01→REQ09/VAL09/MET09→FORCE_REACTION и REQ16/17 сохранены. Масса/CoG/подъёмные
интерфейсы/опоры/поза/нагрузки/материалы/геометрия/такелаж/limits остаются UNKNOWN;
measurement/model routes не выбраны, actual cases/results отсутствуют. Frame/units/
signs/source revision/hash/time/quality/validation обязательны; предсказание модели
не является подтверждением фактической реакции. Старые DOC01/TRACE02 closures
остаются только для собственного exact C, не наследуются автоматически.

Для ТЗ/G1 остаются обязательными все девять OPEN групп: B01 собственные критерии/
допуски/режимы или согласованный completeness scope; B02 controlled methods,
coverage/missing/stop/metrology и независимый review программы; B03 risk/safe states/
retention/isolation/recovery/normative scope; SOURCE-POWER/PRESSURE-UNIT/MOISTURE-BASIS;
operating country (вопрос уже задан); фактические компетентные engineering owners;
G1 whole-package sufficiency и отдельное пользовательское утверждение. R1 documentary
coordination не является инженерным назначением. Дополнительно нужен OBS-03 fix.
Готовые будущие G2–G4 результаты/CAD/испытания не требуются вместо определения G1.

## Сохранность и воспроизведение

Собственный [recheck.py](recheck.py), без author checker и прежнего R5 checker:
**4261 PASS, 1 FAIL (OBS-03), 3 NOT_RUN**, exit1 вследствие открытого дефекта.
Неожиданных failures нет. Это счётчик конкретных документальных инвариантов,
а не доказательство полноты/физики/компетентности. Author172 и old4171 не выданы
за новый независимый recheck. После нового journal append сохранность проверяется
отдельно; результаты до/после не складываются.

Проверены новые53/прежние92/54 pins по их immutable source commits, 12 protected
trees и старые journal prefixes с законными append-only актами. Новое дерево
reviews закреплено ревизией отдельно. Old22 definition/predecessor25 correction/
original26 supplement/rev8target25/new28 artifacts и manifests сохранены. Все
**3464 non-operational baseline files, 59 materialized LFS SHA, 44 полные bindings,
loads/strokes/CAD, 52 interfaces, 84 UNKNOWN/RAW/null, 42 source-state objects и
15 дополнительных OPEN gaps** неизменны. Сохранены material counter2, четыре
исторических FAIL, STALE/REJECT и old symbolic OBS01 exact-C closure. Их правильность
заново не сертифицируется; проверяется сохранность свидетельств.

В отдельном detached TEMP worktree HEAD exact C **до собственного journal append**
воспроизведены шесть outputs: **6 MATCH, exit0**, все 53 physical input pins совпали.
[renderer_replay.json](renderer_replay.json) содержит фактические команды/хэши;
replay отделён от semantic review и OBS-03. CAD/engineering программы не запускались.

```sh
python3 verification/r5_definition_obs_recheck_20261118/recheck.py --output /tmp/r5-def-obs-results.json
# exit1 сохраняет известный FAIL OBS03;не маскировать его как exit0
python3 scripts/check_registry.py --check-git
```

Own registry/preservation exit и seals — [validation.json](validation.json),
[registry.log](registry.log). Сначала публикуется новый C акта; последующий H прямо
ссылается на C и передаёт R1 фактический C CI/remote proof. H CI проверяется после
публикации H; будущие SHA/CI не выдумываются внутри этих commits.

```sh
python3 verification/r5_definition_obs_recheck_20261118/check_publication.py --review-C <C> --handoff-H <H> --branch <branch> --output /tmp/r5-def-obs-publication.json
```

**PR60 не слит. ТЗ/архитектура NOT_APPROVED; G1 OPEN; RAW не повышены. 42 состояния
не рассчитаны; §4/5/6 NOT_RUN; прочность, устойчивость, реальные силы/реакции не
подтверждены. W02 и physical READY NO-GO. Численный/физический этап, CAD-build/rebuild
и испытания не начаты и этим актом не разрешены.**
