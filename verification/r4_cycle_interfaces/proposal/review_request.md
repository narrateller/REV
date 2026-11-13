# R4 → независимый R5: B03 RECHECK по ARB-R1-CI-SEMANTICS-01

Основание: решение R1 5fe510bbc55a052c360ab39a2491a061584b8fb7, прочитанное
и записанное в капсуле до правок. Проверять точный новый C из последующего H.
Предыдущий RECHECK 5fb731182a2bdf6b11246558eca58962e48568d9 на C144941c:
B01/B02 CLOSED только документально; B03 OPEN. interface_consecutive_rejections=2
и отдельная история material B01 сохранены. Автор R4 не закрывает B03.

1. Проверить нормативный минимум semantics_v1/minimum.json и происхождение
   его правил из immutable C0c4eb5d/C144941c, независимых FAMILY/COMMON и решения
   R1. Проверяемый payload/manifest не определяет собственную норму; новая
   ревизия не должна ослабляться ради MATCH. Матрица coverage.csv/json содержит
   все 53 действия и 84 mode rules с parent invariants, from/to, ENTRY, COMMIT,
   outputs, выбранными позами, phase/pose links, источником и check ID.
2. Для каждой подстадии проверить минимальные текущие условия и точные outputs,
   prerequisite до START versus active parent, допустимые режимы и результаты.
   Проверить другие стадии того же класса, не только шесть подмен R5.
3. Проверить typed coordinate AST/unit/axis/frame/scenario sources, каждый
   операнд P1/P2/P3/P_RETURN_END, привязки фаз действий к from/to и источникам,
   частичные/aux UNKNOWN без подмены полными ходами. Подпись, JSON, CSV, SVG
   и manifest согласованы с нормой. Поддержанная линейная эквивалентность
   нормализуется; unsupported/null/чужая база не получает успешный gate.
4. Повторить 17 старых замечаний и шесть новых R5 подмен на новом экспорте;
   синхронно испортить JSON/CSV/SVG и hashes без изменения нормы. Проверить
   missing own-path/producer-current/COMMIT/output/parent/mode/phase refs,
   лишние outputs и неизвестные поля. Checker ничего не чинит и различает
   SEMANTIC_MISMATCH / INPUT_ERROR / UNSUPPORTED при ненулевом CLI exit.
5. Recovery declarations требуют типизированной ссылки на будущий конкретный
   fault_id и original scope/revisions, permitted result/action/guard по frozen
   helper. Schema не является выполненным recovery. Проверить конкретные
   synthetic fault fixtures с null/wildcard/foreign target, чужой scope/type,
   сохранением остальных faults/rejected IDs. Нельзя вернуть DEPENDENCY_VALID
   в собственный старт closure recovery или удалить его у штатной WORK.
6. Сохранить B01/B02: D0→D1→FILL-CONFIRM→D0→LOAD commit→изоляция, адресную
   квитанцию/ревизии/successor, отдельные closure result/history/new NEXT,
   residual inventory и запрет повторного denied ID. 44 bindings и четыре
   невыбранных force variants, frozen helper, расчёты/CAD — побайтно прежние.

Команды и авторские результаты — semantic_iteration/README.md. Неизменённый
R5 probe воспроизведён в отдельной временной копии; это авторская проверка,
не новый независимый акт. Исходные акты/probes/evidence не переписаны; в индексе
старого RECHECK изменены только validity/stale_reason для новой редакции.

B03 закрывает только независимый R5 на точном новом C. Приёмка интерфейса и
CYC-to-CAD BLOCKED до RECHECK. W02/PLC/CAD/rebuild/physical trials вне scope,
physical READY NO-GO. Архитектура/ТЗ не утверждены, G1 OPEN, geometry pairs 0.
