# REV-R5-CI-STRICT-TYPES-RECHECK-01-001

**B03 OPEN — REJECT_WITH_BLOCKER. Стабильная документальная передача CYC-02/03 — NO-GO.**
Шесть прежних типовых escapes исправлены. Независимо найдены четыре ложных
TRUE при неполных recovery snapshots; строгий тип значений не доказывает
полноту и принадлежность набора доменов. Это документальный блокер, не вывод
о прочности, геометрии или работе физической машины.

R5 / Codex / session **r5-ci-strict-types-20261113**, прямое поручение пользователя.
Reviewer не автор проверяемого checker, норматива или исправления. Проверены
авторские сессии r4-linked-20261111, r4-cyc-fix-20261113,
r4-b03-semantics-20261113, r4-b03-types-20261113. Организационная независимость
не удостоверяется. Main/owner/lease не присваивались, merge не выполнялся.

| Вход | Точный SHA |
|---|---|
| Проверенный C | **fa0626372c03d11655624bb454458f82c30117f7** |
| Эстафета H | **ab0fb1900a2bbdfa81e284112b318320f3c5b480** |
| R1 ARB-R1-CI-SEMANTICS-02 | **e0fea7bbf3bd32fda601bca2f7567f8e2c3342b3** |
| Третий REJECT | 3d317b32596884cc60d9d42675924b88fcb29bf0 |
| Второй REJECT | 5fb731182a2bdf6b11246558eca58962e48568d9 |
| Первый OUTPUT/REJECT | 13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2 |
| Frozen contract/helper | 0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed |

Все входы — предки H; весь интерфейсный пакет совпадает в C/H/рабочем дереве.
Собственный commit акта указывается последующей H-капсулой, без самоссылки.

## Воспроизведение и независимые ожидания

Рабочая директория `/workspace/REV`, `.venv/bin/python` 3.12.14. Полные argv,
exit codes, environment overrides и raw outputs — [commands.json](commands.json).
Exit 0 исследовательского probe означает завершённый сбор; это не PASS.

| Команда после `.venv/bin/python -B` | Наблюдение |
|---|---|
| `verification/r4_cycle_interfaces/proposal/check_package.py` | 3277 MATCH, PASSED_DOCUMENTARY_ONLY |
| `verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py` | 8 MATCH, повторяемый явный экспорт, readonly checker |
| `-m unittest discover -s verification/r4_cycle_interfaces/type_correction -p 'test_*.py' -v` | 6 методов OK; 244 re-export cases и 36 same-input recovery comparisons |
| `-m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v` | 6 методов OK; 411 cases |
| `-m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v` | 7 методов B01/B02 OK |
| `verification/r5_ci_strict_types_recheck/repeat_prior.py` | Неизменённые независимые probes 654/654 и 765/765; норматив точно воспроизведён |
| `verification/r5_ci_strict_types_recheck/independent_probe.py` | 215 re-export cases; 167 same-input recovery cases; raw 1222 assertions, 1144 совпадений |
| `verification/r5_ci_strict_types_recheck/incomplete_snapshots.py` | 7 конкретных случаев, 3 совпадения и **4 ложных TRUE** |
| `verification/r5_ci_strict_types_recheck/assess_results.py` | Классификация raw mismatches без выдачи их числа за число дефектов |
| `verification/r5_ci_strict_types_recheck/verify_preservation.py` | Inputs/helper/minimum/calculations/CAD/история сохранены |
| `scripts/check_registry.py --check-git` | Отдельный registry.log; согласованность реестра, не приёмка B03 |
| `git diff --check`; `git lfs fsck` | PASS |

Прежние probes исполнены без reuse в временной materialized tracked копии;
Git object DB использована только для чтения. Их исторические hardcoded
reviewed_C в raw JSON не переименованы: actual C установлен authority_and_prior.json.
Оригинальные scripts/evidence обоих актов не изменены.

Норматив 53 действий / 84 пар действие–режим / 18 поз воспроизведён builder
из фиксированных Git blobs, отдельно от mutable payload. SHA256 minimum.json:
`b1c13c18c408120ae66d4995eac706e8dbf5842f35976494efb682c74e64d3df`.
Неизменённый независимый probe повторил собственные family obligations,
parent/output/mode rules, полиномиальный oracle фаз и подложенный минимум;
ожидаемые ограничения не получены из проверяемой копии или renderer.

Собственные **215** согласованных re-export случаев: **198 правильных отказов,
17 правильных MATCH**. По другим стадиям A/B проверены все структурные классы:
action source_bindings; main-axis phase refs; phase_pose_bindings/stroke_source;
AST source_ref (включая neg operand возврата); pose source catalog; 44-row catalog;
permissions/poses normative provenance; export manifest provenance. Типы:
true/false, 1.0/0.0, строка, null, отсутствие, array/object, отрицательное, 0,
integer 1/2/большое значение. Integer 1 сохраняет закреплённую source identity;
integer 2 или большой integer типологически допустим, но не подменяет revision 1.
Три составные подмены нескольких классов отклонены. Эквивалентная P3-формула и
исходная physical quantity проходят. Дополнительный свежий случай
quantity_equivalence.py заменяет float на численно равный integer в
BASE_A/load.return_required: MATCH, metadata revisions не меняются
(quantity_result.json). Рациональные времена,
формулы и прежние семантические ограничения дополнительно покрыты прежними
наборами. В каждом случае exporter фактически запущен, source/export hashes
свежие, JSON/CSV/SVG согласованы, checker не пишет. Raw CLI evidence — mutations/.

## Recovery: подтверждено и обнаружено

Независимая fixture строит history/fault/proof через frozen helper, без авторских
fixture imports. Одинаковые proof/context/fault передаются predicate и frozen
recover; возвращённый state нигде не применяется. Валидные snapshots **0, 1,
2**63** проходят адресный путь, caller не меняется, rejected IDs сохраняются.
Bool/float/string/null/container/отсутствующий proof origin и несовпадающие
значения затронутых доменов не дают TRUE. Прежние false/0.0 исправлены.

Однако revision_map проверяет значения, но допускает пустой map и не устанавливает
обязательный набор доменов. Источник независимого требования: frozen guard
`B_RESET_CONFIRMED.evidence_domains == ['B_CLOSURE']`, R1 пункты 1–3, а не
мутированный snapshot. Исходный fault действительно создан по этому guard.
Для подменённого immutable origin заново вычислены F-digest и causal IDs;
history_valid остаётся TRUE. Это проверка семантики provenance после согласованной
подмены, а не случайный отказ по испорченному хэшу.

| Свидетельство в incomplete_results.json | Ожидалось | Predicate | Frozen recover / возвращённый fault |
|---|---|---|---|
| `empty-expected`: expected_revisions={} | UNKNOWN | **TRUE** | ALLOWED_ASSUMED / RESOLVED |
| `empty-origin-matched-proof`: origin.revisions={} и proof.origin_revisions={} | UNKNOWN | **TRUE** | ALLOWED_ASSUMED / RESOLVED |
| `foreign-domain-origin-matched-proof`: обе origin maps содержат только FEED:0 | UNKNOWN | **TRUE** | ALLOWED_ASSUMED / RESOLVED |
| `empty-origin-and-expected`: согласованно пустые origin/proof/expected | UNKNOWN | **TRUE** | ALLOWED_ASSUMED / RESOLVED |

Валидный контроль — TRUE; пустой origin с несовпадающим proof и полностью
отсутствующий proof.origin_revisions — UNKNOWN. Каждый исходный caller fault
остаётся OPEN, proof/context неизменны, rejected IDs сохранены. RESOLVED относится
только к возвращённой helper копии, не к применению recovery или физическому READY.
Concrete runtime fixtures не имеют CSV/SVG exporter: их согласованность доказана
JSON, domain oracle и валидными F-digest; статические re-export проверки выше
выполнены отдельно. Не выдаём runtime fixture за экспорт схемы.

Исходные места: metadata_types.py:20 (revision_map), semantic_minimum.py:191–211
(recovery_value), frozen permission_examples.py:203–210 (complete/origin/expected
comparisons).

Наследование permissive helper ветви не делает такой TRUE корректным: обязательный
B_CLOSURE origin уже отсутствует. Frozen helper сохранён; его изменение здесь не
разрешалось. Требуется согласовать полноту/набор доменов с R1 и затем проверить
отдельный narrow follow-up, не менять норму ради принятия подмены.

Расширенное сравнение также зафиксировало **23** различия policy classification:
20 консервативных UNKNOWN против frozen ALLOWED_ASSUMED (посторонние context
домены или невалидные expected values), 3 UNKNOWN против BLOCKED при одновременно
повреждённом proof и отдельном resource denial. Итоговый составной gate остаётся
BLOCKED; не обнаружено снятия resource fault. Полная эквивалентность policy
**не подтверждена**. Это отдельно от четырёх доказанных ложных TRUE выше.

Raw matrix имеет 78 несовпавших assertions, **не 78 дефектов**. Первоначальное
исследовательское ожидание «любая перемена любого context domain блокирует
B recovery» шире frozen guard scope: FEED/RETENTION не входят в его evidence
обязательства. Их отсутствие/корректная новая revision не объявлены дефектами.
Консервативность candidate относительно permissive frozen ветвей также не
объявлена ложным разрешением. Полная построчная классификация — assessment.json;
сырые результаты сохранены без ретуши. Блокер опирается на отдельные минимальные
B_CLOSURE свидетели, а не на эту завышенную исследовательскую гипотезу.

## Сохранность и границы

preservation.json подтверждает 612 protected files, 7 frozen packages, 11 protected
trees, 17 fixed input blobs, исходные акты и R1, весь semantics_v1, payload,
44 привязки и четыре силовых варианта. Нагрузки, диаметры и ходы не уменьшены;
расчёты/CAD побайтно сохранены. Сохранность — сравнение bytes/trees, без повторного
инженерного расчёта, rebuild или вывода о native проникновениях. Геометрических
пар проверено 0; прочность/устойчивость/нативная геометрия/физические испытания NOT_RUN.

- **B01/B02:** прежнее документальное закрытие сохранено в границах C144941c,
  положительные LOAD/FILL/RETURN/COMMIT, адресный B recovery и history регрессии PASS.
- **B03:** OPEN, REJECT_WITH_BLOCKER из-за неполных/чужих origin/expected domains.
  Типовые шесть исправлены, source/export строгие типы подтверждены.
- **Стабильная документальная передача CYC-02/03:** NO-GO. R3 может использовать
  точный immutable пакет только для ранее разрешённого force-path study с WARNING
  и действующим claim; это не подтверждение полноты силового пути. Новая CAD-итерация,
  стабильная контрактная интеграция и реальные команды не разрешены этим актом.

Три прежних REJECT сохранены с SHA/evidence; текущий — четвёртый:
interface_consecutive_rejections=4, material_contract_consecutive_rejections=2.
По AGENT_PROTOCOL §6.1 вопрос Q-R1-CI-SEMANTICS-ARBITRATION-01 снова открыт,
корректирующая итерация BLOCKED до записанного решения/плана. Карточка R1_followup.md.
Архитектура/ТЗ не утверждены. **W02 OPEN/NO-GO, physical READY NO-GO, G1 OPEN.**
