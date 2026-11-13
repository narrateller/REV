# Независимый RECHECK B01 по ARB-R1-CC-01

Объект — неизменяемый C из следующего H (NEXT_MODEL.md и capsule
handoffs/T-r4-cycle-contract-01/r4-linked-20261111.md), репозиторий
https://github.com/narrateller/REV, ветка work-r4/T-r4-cycle-contract-01/r4-linked-20261111.
Автор R4 r4-linked-20261111; новая независимая проверка не выполнена автором.

Основания — оба исходных отказа d99afb4… / c56e494… и точное решение
616135755d1b6cbaa09ae9800bad5af8bbc28aed. consecutive_rejections=2; B01 OPEN,
parent BLOCKED; W02 не включён. Просим проверить весь план R1:

- Все 26 исходных и 45 RECHECK случаев с правильными ожидаемыми исходами,
  особенно чужой subject/epoch → fault остаётся, causal history BLOCKED и
  rejected-A после rejected-B всё ещё BLOCKED.
- Два material faults одного guard, оба порядка создания/адресного восстановления;
  независимые IDs и origin, никакого вытеснения/массового снятия по guard.
- Неполные/чужие база/ревизия/guard/fault_id, stale evidence, соответствие нового
  proof исходному fault и подтверждённым текущим версиям того же субъекта.
- Составные FALSE/UNKNOWN и dependency cause IDs, новый уникальный аудит без
  общего READY, отдельный положительный путь audit → resolution → history →
  свежие условия следующего действия; правильные ENTRY/COMMIT и частичный B.
- A→B→A, A→B→C→A, другой субъект/эпоха, восстановление иного fault, export/restore;
  старые rejected ID никогда не разрешаются, missing trusted history не чистая.
- Адресное подтверждение обработки rejected request не подменяет его EVENT_FRESH;
  отказ памяти остаётся даже после RESOLVED соответствующей записи.
- Наблюдённые факты/неизвестные массы/refs/дубликаты не стираются; это metadata
  contract и queue, не W02 entity-level material engine/доказанный баланс.
- Сохранность обоих R5/R1 источников, 17 inputs/11 trees, численных/CAD tools и
  артефактов; согласованность текста/JSON/helper и diff adapters в replay_r5.py.

Команды — README.md. Старые probe запускаются отдельно на старом C и по-прежнему
показывают старые ошибки: их exit 0 не PASS нового контракта. Новый verify
возвращает nonzero при несовпадении и публикует full actual/expected. Повтор
авторской suite — воспроизводимость, не независимый акт. B01 закрывает R5 на
точном новом SHA; G1 OPEN, физическая работоспособность/безопасность UNKNOWN.
Solver/CAD/rebuild/physical tests NOT_RUN, архитектура/ТЗ не утверждаются.
