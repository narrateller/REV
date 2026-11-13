# Q-R1-CI-SEMANTICS-ARBITRATION-01 — snapshot completeness

- task_id: T-r4-cycle-interfaces-01; blocker R5-CI-B03, P1, @R1, REOPENED.
- Прямой RECHECK C fa0626372c03d11655624bb454458f82c30117f7 по R1 e0fea7bbf3bd32fda601bca2f7567f8e2c3342b3.
- Основание §6.1: четвёртый REJECT; три прежних акта и counter history сохранены.
  Следующая авторская коррекция BLOCKED до записанного R1 решения/плана;
  reviewer не выполняет исправление helper, payload или норматива.
- Шесть старых type escapes исправлены; типы значений сами по себе не доказывают
  полноту snapshots. revision_map({}) == True; согласованно пустые или FEED-only
  origin maps скрывают отсутствие обязательного B_CLOSURE, predicate TRUE,
  frozen recover ALLOWED_ASSUMED/returned RESOLVED. Caller остаётся OPEN.
- Доказательства: review.md; incomplete_snapshots.py; incomplete_results.json,
  четыре минимальных свидетеля; static 215/215, prior765/765.
- Неизменяемые требования: отсутствие обязательной revision не даёт успеха;
  domain obligations определяются фиксированным guard/action, не payload;
  readonly, immutable origin, rejected IDs, 53/84 minimum,44 bindings,4variants,
  frozen helper и история сохраняются. W02/physical READY NO-GO,G1 OPEN.
- Параметры изделия не меняются; затронуты documentary permission semantics,
  B03 и границы передачи CYC-02/03. Расчётные последствия/производство/сроки:
  NOT_RUN/UNKNOWN; прочность, геометрия и оборудование вне scope.

| Вариант | Требования/семантика | Физика/CAD/производство | Риск/неизвестное | Решение |
|---|---|---|---|---|
| A: проверять полноту и допустимый набор snapshot domains до делегирования frozen policy | Набор из фиксированного guard/action; malformed maps UNKNOWN; корректные сохраняются | Без изменения calculations/CAD; физическая достаточность NOT_RUN | Требуется явно различить origin, expected и current maps; current содержит и другие домены | Рекомендуемый узкий R1 follow-up и независимый RECHECK |
| B: расширить frozen helper/import validation отдельной версией контракта | Возможно устранить permissive legacy ветвь, требует отдельного разрешения и сравнений | Не является CAD/strength решением | Выходит за разрешение сохранить frozen helper | Новое решение R1, исходный frozen не переписывать |
| C: принять пустые/чужие maps ради equality с helper | Противоречит no-missing-success и адресной provenance | Не подтверждает физику | Ложный TRUE остаётся | Не рекомендован; норматив не ослаблять ради PASS |

Также R1 должен уточнить область точного policy agreement: строгая prevalidation
может быть консервативнее legacy helper на неиспользуемых context domains,
а при known FALSE + invalid proof даёт UNKNOWN против frozen BLOCKED. Нельзя
заявлять полное совпадение без оговорённого контракта. Это не основание снимать
known faults или разрешать действие; составной gate остался BLOCKED.

Следующий тест: собственные required-domain oracles по frozen definitions,
пустой/пропущенный/чужой/частичный origin и expected после coherent F-digest,
валидные 0/1/large integer, stale/foreign proof, compound fault и readonly;
затем все прежние suites. Запреты W02/G1 и история не меняются.
