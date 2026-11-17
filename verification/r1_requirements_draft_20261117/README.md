# R1 — DRAFT требований и матрицы rev8, только документальная область

Пользователь разрешил завершить документальный intake, принять отдельный 24h claim
в PR53 и после main acceptance/input audit подготовить DRAFT. PR53 MERGED обычным
merge bec317a4483e7f69c2af0aa1c52ef091bdef57b4; parent1 a63e27cf1e4579bfe8aa7b78f4dfcabbd6ef6dc3,
parent2/head bb78bef9661a95c557db765ed2df1e8df4ffddbc. Tree=head. Оба head CI и
main CI44000928125 SUCCESS, registry PASS и по 100 тестов; JSON/выдержки сохранены.

Intake завершён только в DOCUMENTARY_SCOPE с WARNING и освобождён в том же merge.
Его исходный lease 2026-11-17T23:16:47.225017Z не продлён. Новый claim
T-r1-requirements-draft-01 принадлежит actual R1 6afb300b-1540-8191-a5c4-be1a684c20e0,
preparation 2026-11-17T01:58:30.990734+00:00, deadline 2026-11-18T01:58:30.990734+00:00,
ровно 24 часа; перекрытия/переноса нет. Исторический intake proposal NONE/null и R5
source evidence не изменены. Документальный входной аудит: 4 PASS / 3 NOT_RUN,
WARNING_DOCUMENTARY_ONLY. §4/5/6 блокируют численные/физические выводы.

## Результат и воспроизведение

- requirements/system_requirements.md и verification_matrix.md — DRAFT rev8,
  NOT_APPROVED; все 22 REQ/VAL сохранены, будущие критерии/методы/evidence/gaps указаны,
  все VAL/TEST NOT_RUN. Rev7 архивирована побайтно с commit/SHA256.
- draft_requirements.json — структурированные строки и lineage; source_disposition.json/md
  покрывает все 40 полей:10 TARGET_PROPOSAL,23 REFERENCE_CONTEXT,7 OPEN_SOURCE_ISSUE.
  Предложенные targets ссылаются на frozen scoped RAW; новые численные значения REV
  не создаются, активный registry не меняется и RAW не повышается.
- qualitative_applicability.json —16 qualitative/supplemental refs с REQ mappings;
  traceability.md, traceability_schema.json — обратная трассировка и many-to-many
  схема без фактических записей; open_gaps.json/md —15 открытых дополнительных
  source/criteria gaps плюс все 84 исходных UNKNOWN в прежнем index.
- build_draft.py --output-dir TEMP воспроизводит 10 output files. verify_draft.py —
  авторская проверка:358 PASS /0 FAIL; воспроизведение10 MATCH. Это проверки
  целостности/трассировки, не независимая приёмка требований и не физический расчёт.
- input_manifest/audit закрепляют main до редактирования. postmerge/premerge,
  CI/merge_request/result подтверждают приём claim. registry.log/status — отдельный
  фактический root check; CI опубликованного H проверяется после push.

OUTPUT-review rev8 NOT_RUN. R5_review_command.md будет добавлен следующим H с
точным C результата; сам C не ссылается на себя. В artifact manifest не включаются
изменяемые STATE/NEXT/капсулы и будущая команда, чтобы metadata H не меняли target.
Независимый R5 должен раскрыть actual session/model/соавторство и upstream участие,
проверить exact C самостоятельно; повтор авторского renderer/checker — лишь replay.
R5 source act853a по exact f2c остаётся CURRENT/WARNING и не заменяет новый review.

## Граница утверждений

BP500 primary по пользователю, площадка адаптируется под пресс; реальные партии,
геометрия/опоры/материалы/контакты/фазовые силы UNKNOWN. E55/WEIMA/ARS применяются
по релевантности; ARS также неметаллический, его настройки/свойства/проводка не REV.
SOURCE-POWER/PRESSURE-UNIT OPEN, влажностная база/метод UNKNOWN; up-to не минимум,
референтная масса изделия не константа всех настроек, hydraulic max не material
pressure/спектр нагрузок, opening height не общая высота бункера, gross mass не
moving mass/реакции. Материалы/марки/ресурс из гарантии/закалки не получаются.

Старые REJECT/STALE/четыре FAIL/material history=2, R5-TZ-B01/B02/B03 и OBS-01
exact-C closure сохранены. 44 bindings/нагрузки/ходы/CAD, активный registry,
84 RAW/null,52 interfaces и42 source-state объекта неизменны. 42 состояния не
рассчитаны; §4/5/6 NOT_RUN; прочность/устойчивость/реальные реакции не подтверждены.
Архитектура/ТЗ NOT_APPROVED, G1 OPEN, W02/physical READY NO-GO. Численный/физический
этап, CAD-build/rebuild, физические испытания не выполняются и не разрешаются.

Дополнительная проверка change_impact.json: все54 старых pins совпали;12 protected
деревьев без diff/новых файлов. Новые rev8 документы не меняют эти старые входы.
