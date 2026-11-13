# Q-R1-CI-SEMANTICS-ARBITRATION-01 — current FALSE при journal exception

- @R1; P1; parent T-r4-cycle-interfaces-01; blocker R5-CI-B03, REOPENED.
- C3060dbf561f95e4384fbfd13a9cc5569690515e5,H98861219f0adda96af0aca0a3a35078aec022eb9,
  R1 60eeddce71c9440a2fa08f7acbe6f1121c974b29. Reviewer R5/r5-ci-gate-exits-20261113.
- Все2 minimal и19old variants исправлены,295/295,8/8 returns используют finish.
- Остаток: посторонний fault с missing origin.guard и coherent F-ID вызывает
  KeyError guard-wide fault scan. Текущий own record отдельно валиден по fixed
  scope/action/phase/revisions/interval; frozen _raw_value=FALSE/CURRENT_ASSUMED_RECORD,
  history_valid=True. Except :120–123 заменяет результат на UNKNOWN, finish
  возвращает INDETERMINATE вместо обязательного BLOCKED. Ни одного нового TRUE.
- Независимо8вариаций (2own guards×4exit paths) и16TRUE/UNKNOWNcontrols; один
  minimal witness воспроизводится ordinary data без injection. См. review.md,
  reproduce_journal.py,minimal_journal_witness.json,independent_results.json.
- R1 §1 запрещает уничтожать независимое доказательство запрета из-за другого
  повреждённого input. Это separate composite obligation, не unconditional
  legacy-policy equality вне схемы. Область успешного recovery не расширять.
- Шестой REJECT, история пяти сохранена; material counter2 отдельно. По §6.1
  дальнейшая коррекция BLOCKED до записанного R1 решения/плана. Reviewer не правил
  source/helper/norm. Защищённые inputs/norm53/84/44bindings/4variants/CAD неизменны.

| Вариант | Семантика/требования | Физика/CAD/производство | Риск/неизвестное | Решение |
|---|---|---|---|---|
| A: отдельно сохранять доказанный fixed raw current FALSE при ошибке journal-dependent reader | Соответствует уже выбранному R1 independent-evidence правилу | Без product parameters/CAD решений; NOT_RUN | Не принимать stale/foreign/unknown raw record за FALSE; malformed journal сам не FALSE | Рекомендуемый narrow follow-up и independent RECHECK |
| B: считать любую ошибку fault scan недостоверностью всех current records | Ослабляет уже объявленную независимость источников | Физическая достаточность NOT_RUN | Теряет подтверждённый current FALSE; не может молча приниматься | Требует явного пересмотра R1 критерия, здесь не принят |
| C: менять frozen helper/material engine | Выходит за narrow wrapper scope и не требуется для сохранения raw proof | Вне scope | Потеря frozen identity/новая контрактная версия | Отдельная задача/решение |

Следующий тест: malformed unrelated journal record (missing guard/origin variants)
× own current TRUE/FALSE/UNKNOWN × null/unknown-target/unsupported-dispatch/
snapshot-failure; canonical digest не заменяет semantic validation. Включить
stale/wrong-phase/scope/interval/type controls, no proven FALSE=>INDETERMINATE,
no invented target, scoped UNKNOWN при own FALSE=>BLOCKED, readonly и все retained
регрессии. Не выводить новые параметры изделия: ID@revision не меняются, физические
последствия/производство/сроки UNKNOWN/NOT_RUN. W02/physical READY NO-GO,G1 OPEN.
