# ARB-R1-CI-SEMANTICS-05 — независимый current FALSE при ошибке journal-reader

R1 / codex-01; Q-R1-CI-SEMANTICS-ARBITRATION-01; T-r4-cycle-interfaces-01.
База main `3a9258c57e4bc15d6de98f1d17e8412ad6e8899a`.
R1 claim PR #44 до 2026-11-13T22:14:32Z, R4 PR #45 до
2026-11-14T00:13:12.404899Z; решение не продлевает сроки/области.
Уточнение решения `60eeddce71c9440a2fa08f7acbe6f1121c974b29`.

## Основание и воспроизведение

R5 `18e5af1dae177cdfcb24951d3b36c2fd43395421`, C
`3060dbf561f95e4384fbfd13a9cc5569690515e5`, H
`98861219f0adda96af0aca0a3a35078aec022eb9`: все восемь возвратов используют
finish, прежние два свидетеля/19 вариаций исправлены, но ошибка сканирования
постороннего journal fault теряет независимый current FALSE до композиции.
Это шестой REJECT, interface counter=6; прежние пять и material counter=2
сохраняются без обнуления. Новых ложных TRUE в проверенной матрице нет.

R1 в изолированной копии H акта
`f209ed23748652b20afc4a9a91931f73b10ab794` выполнил unchanged
`reproduce_journal.py` и `independent_probe.py`. Минимальный witness:
нормально адресованный current RESOURCES_READY=FALSE отдельно подтверждён
fixed `_raw_value` как FALSE/CURRENT_ASSUMED_RECORD; missing guard в чужом
fault вызывает KeyError reader, общий gate INDETERMINATE вместо BLOCKED.
Matrix=231, matches=223, failures=8: два собственных guards × четыре выхода.
Caller/proof не изменены; повреждение журнала само по себе не является FALSE.
Полные inputs/output и meta сохранены в `verification/r1_ci_journal_arbitration/`.

## Решение

Выбрана изоляция независимых источников отказа и сохранение валидного raw
current FALSE при exception journal-dependent reader. Вариант считать любой
fault-scan exception недостоверностью всех current records отклонён. Frozen
helper и журналы не исправляются автоматически, норма/physical data не меняются.
Это narrow follow-up прежней deny-dominance, а не новая функция PLC/W02.

R4 разрешена только корректирующая итерация B03 после фиксации точного SHA
решения и проверки main/owner/lease/входов. Приёмка интерфейса BLOCKED;
стабильный documentary/CAD handoff NO-GO до независимого RECHECK. B03 не закрыт
арбитражем. Документальные B01/B02 и прежние type/domain/gate исправления
сохраняются с областями исходных актов, требуют регрессий нового C.

### Обязательная семантика

1. Раздельно оценивать доступный fixed raw current record и journal-dependent
   reader; один источник не должен уничтожать уже доказанный результат другого.
   Отдельно хранить input validity/reasons, raw truth, journal status,
   own/scoped/causal values и общий gate. Если reader бросает исключение, его
   вывод UNKNOWN, но ранее независимо валидированный current FALSE сохраняется
   как достаточное обязательное основание BLOCKED.
2. Нельзя доверять только буквальному record.value=FALSE. Raw-доказательство
   должно пройти fixed guard/action, scope/phase, строгие relevant revisions,
   provenance/method и покрытие operation interval. Устаревшее, чужое,
   неподдержанное или плохо типизированное record не даёт достоверный FALSE.
   Воспроизведённое независимое основание — политика fixed frozen `_raw_value`,
   не обход её проверок прямым чтением поля. Иные реализации должны сохранять
   ту же поддерживаемую валидацию и быть независимо проверены.
3. Эта fallback-проверка **не расширяет разрешения**: raw TRUE при неизвестном/
   повреждённом journal не устанавливает отсутствие latched fault, успешный
   recovery или READY. Без другого достоверного FALSE общий gate INDETERMINATE.
   Raw UNKNOWN/невалидный record при ошибке reader также не даёт blanket BLOCKED.
4. Любая exception ветвь сохраняет уже доступные достоверные own/state/causal
   запреты и идёт в общий finish. Исключение в raw reader не даёт права
   выдумывать его FALSE; если оба независимых основания недоступны, остаётся
   UNKNOWN. Поддержанный known FALSE другого обязательного условия по-прежнему
   сохраняется. Не превращать отсутствие всех оснований в успешный default.
5. Не удалять/ремонтировать повреждённый fault, не пересчитывать F-ID в caller,
   не подставлять target/домен/ревизию и не применять helper copy. Согласованный
   digest не доказывает семантическую полноту записи. Caller, immutable origin,
   history, rejected IDs и pending observations сохраняются readonly.
6. Успешная compatibility с frozen policy относится лишь к допустимым входам.
   Здесь legacy scan бросает exception на malformed foreign record, поэтому
   unconditional equality не требуется: действует отдельный уже выбранный
   composite criterion по независимо валидированному current evidence.

## План независимого RECHECK

R4 публикует точный C, схему двух источников own assessment, exception table и
положительные/отрицательные fixtures. R5 проверяет:

- тот же minimal witness и все 8 вариаций: RESOURCES_READY/METHOD_SUPPORTED
  current FALSE × proof null, unknown target, unsupported dispatch, snapshot
  rejection — scoped UNKNOWN, общий BLOCKED, reader exception явно отражён;
- посторонние malformed faults в различных позициях и видах повреждения,
  current TRUE/FALSE/UNKNOWN и reader exceptions на каждом доступном пути;
- current stale/wrong scope/action/phase/revision/interval/provenance/method
  FALSE не получает статус independently confirmed; без другого запрета gate
  INDETERMINATE, а при другом достоверном FALSE сохраняется BLOCKED;
- raw TRUE/UNKNOWN с недостоверным journal не создаёт ложных TRUE/recovery;
  raw-reader exception и повреждение context не выдумывают данные;
- два own условия с независимыми сочетаниями, state/causal запреты и прежний
  единый finish на восьми выходах, отсутствие фиктивного target;
- корректный positive recovery, чужой fault и отсутствие искусственного тупика,
  сохранение histories/rejected IDs и ordinary WORK-запретов;
- prior gate295, incomplete7, strict types, normative/source/B01/B02 и readonly;
  helper, norm53/84, 44bindings/4variants, расчёты и CAD unchanged.

Нет требования доказывать физику или реализовывать полноценный journal repair
для такого документального gate. Критерий исправления — сохранение независимо
подтверждённого запрета без новых разрешений и без blanket BLOCKED на unknown.
B03 закрывает новый независимый R5 акт, не R1. R3 условные force studies WARNING
могут продолжаться в своей области/claim; W02/PLC/physical READY NO-GO.
Прочность/геометрия/CAD/rebuild/физические испытания NOT_RUN. Архитектура/ТЗ/
оборудование не утверждены, G1 OPEN.
