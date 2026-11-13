# Q-R1-CI-SEMANTICS-ARBITRATION-01 — preserve known BLOCKED on every proof rejection path

- @R1; P1; parent T-r4-cycle-interfaces-01; blocker R5-CI-B03, REOPENED.
- Точный проверенный C e30b4b7caf3040905cc23c79ca696af2871c958a,
  H ff050572f88f108c2092827e98cd4d98bd874737, R1 39826eb2f5dbd1f83d81882022e6f59313ebe5d5.
- Основание AGENT_PROTOCOL §6.1: пятый последовательный REJECT, история четырёх
  прежних актов не обнулена; material counter=2 отдельно. Следующая коррекция
  BLOCKED до записанного решения/плана. Reviewer код контракта/helper не менял.
- Snapshot admission устраняет четыре прежних false TRUE. Fixed domain oracle,
  valid advances, минимальный context, unused domains и IN_DOMAIN comparison PASS.
- Два ранних возврата нарушают уже принятое требование §2 R1: known FALSE должен
  сохранять общий BLOCKED при неполном proof. Whole nonobject proof возвращает
  начальный INDETERMINATE до ENTRY/state assessment; missing/foreign proof
  action/guard возвращает finish до известного OPEN causal ancestor.
- 19 вариаций двух ветвей, без новых TRUE; минимальные два witnesses и все входы
  в minimal_witnesses.json/independent_results.json. Caller/fault/history не меняются.

Неизменяемые требования: отдельные admission/scoped/composite results, known
BLOCKED не маскируется, readonly, fixed definitions/domain obligations, norm53/84,
frozen helper,44 bindings/4variants, расчёты/CAD и история. Ни новых параметров
изделия, ни ослабления типовой схемы, ни W02 не требуется. Инженерные параметры
не меняются; численные расчётные последствия/производство/сроки UNKNOWN/NOT_RUN.

| Вариант | Соответствие | Физика/CAD/производство | Риск/неизвестное | Решение |
|---|---|---|---|---|
| A: независимая оценка достоверных own ENTRY/state и адресных causal prohibitions перед всеми отказами proof | Сохраняет уже записанное требование R1, scoped value остаётся UNKNOWN | Никаких физических/CAD выводов | Проверить ранние exits; не придумывать target для отсутствующего fault ID | Рекомендуемый узкий follow-up с новым independent RECHECK |
| B: считать вне схемы весь composite result неопределённым даже при известном запрете | Противоречит текущему §2 R1 и request reviewer | Физика не проверяется | Теряет known BLOCKED, хотя TRUE не возникает | Нужна явная смена требования R1, не молчаливая приёмка |
| C: менять frozen helper или W02 | Не требуется для локального порядка композиции | Вне разрешённой области | Расширение scope без оснований | Отдельная задача/решение, здесь не выполнять |

Следующий тест: malformed whole proof null/array/string/bool/number + known
resource record/latched fault/invalid state; valid target + missing/foreign
proof action/guard + OPEN causal ancestor; snapshot fields malformed + два
собственных запрета; отсутствие адреса не заполнять. Все известные prohibitions
сохраняют BLOCKED, recovery не TRUE, правильный адресный путь остаётся допустим.
Повторить 7 old cases,295 own cases, author118/type244/semantic411/B01/B02,
IN_DOMAIN comparison и preservation. W02/physical READY NO-GO,G1 OPEN.
