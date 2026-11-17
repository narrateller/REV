# R1 — предварительный референтный пакет принят с WARNING

Дата: 2026-11-17 UTC. R1, фактическая сессия
6afb300b-1540-8191-a5c4-be1a684c20e0; coordinator alias r1-pr48-integration-20261116.
Это ограниченная документальная приёмка, не независимый review R1 и не инженерный PASS.

## Exact входы

- Исходный пакет C f2cbd96bb78c915dca74cb4eb29daffbb52ee172;
  эстафета H 411bb36f9559d80caec4e2f870e8120148d9c6a9.
- Независимый акт R5 C 853a72b63fd8c89a3fa54ac1f309f24e7104f1c4;
  H c086c2a497614c193373d58c1b854078cd7accd0.
- Акт REV-R5-REFERENCE-INTAKE-REVIEW-01-001,
  verification/r5_reference_intake_review/review.md.
- Проверенная main 3353de6c9fc699fbd565f1ce63cebedad3137a12, PR52 OPEN.

R1 принимает WARNING / WARNING_DOCUMENTARY_REFERENCE_ONLY на исходном exact C.
1250 PASS / 0 FAIL независимого R5 подтверждают перепись/единицы/квалификаторы,
применимость заимствований в документальной области и сохранность. Reviewer
самостоятельно просмотрел 11 страниц четырёх PDF, сверил 40 деклараций и
качественные записи; это не полное перечитывание всех руководств.

Фактический R5 6afb0a73-b16c-8191-a539-9a6685e89034 не входит в авторов intake
по раскрытию identity.json. Прежнее upstream-авторство R5 сохранено: его
собственные акты db6b977/4aa2350/3784efa здесь заново независимо не проверялись;
проверялись сохранность и downstream-ограничения. Организационная независимость
не удостоверяется. Новый акт и обе истории включаются в PR52 без squash/rebase.

## Обязательные пределы использования

- BP500 остаётся основным ориентиром целей/сырья по прямой команде пользователя;
  площадка адаптируется под пресс. Другие документы применяются по релевантности.
- SOURCE-POWER OPEN: объявленный total и перечень двигателей не исправлять
  молча, новый электрический бюджет не вычислять.
- SOURCE-PRESSURE-UNIT OPEN: literal kg/cm² не становится kgf/cm² или SI
  давлением через незафиксированное предположение; силу из него не выводить.
- Влажностная база wet/dry и метод UNKNOWN. Разные source-specific диапазоны
  не объединять и не усреднять. Up-to выпуск не гарантированный минимум REV.
- Все 40 полей остаются scoped RAW, без переноса в активный registry/CAD,
  повышения зрелости или признания физической достоверности параметров REV.
- Геометрия/опоры/e(q)/L_free(q), материалы/E, контакты/силы/ресурс остаются
  UNKNOWN либо будущими выходами разработки. Готовые чертежи будущего пресса
  не являются новым требованием к оператору.

## Уточнение ARS и цикла

R5 дополнительно проверил ARS PDF4/printed3 §4.6; R1 просмотрел соответствующий
сохранённый рендер. Документ допускает металлическую стружку, а также plastic
chips, sawdust и grinding swarf. ARS нельзя описывать как исключительно
металлический пресс. Наличие sawdust в перечне не подтверждает равенство
физических свойств, настроек или модели уплотнения с BP500/REV.

На ARS PDF17 путь eject также возвращается к retract/reset-ветви. Reset не
исключительно partial-extend последовательность; два ромба не определяют полную
приоритетную/взаимоисключающую логику. Выдержка чужого цикла не подтверждает
снятие остаточной нагрузки REV. Удержание E55/уровень WEIMA/door-reset ARS —
документированные принципы для дальнейшей разработки, не готовые контакты/PLC/READY.

Эти квалификаторы приняты по новому акту и сопровождают дальнейшее применение.
Исходные файлы exact C не редактируются, акт CURRENT сохраняет точные хэши.
Данный файл уточняет контекст принятия, не вводит новую характеристику машины.

## Claim и следующая операция

Claim intake остаётся PROPOSED_PENDING_MAIN, owner NONE, effective lease null.
Предложенный owner 6afb300b-1540-8191-a5c4-be1a684c20e0; исходный proposed lease
2026-11-17T23:16:47.225017Z не продлён и не является действующим сроком владения.
Принятие review не принимает claim; назначение R1 в беседе не запрашивается заново.
Claim R4/его heartbeat/исходный lease не меняются. Новых владельцев/сроков
поставщиков входов или инженерного старта нет.

PR52 готовится к последующей отдельно разрешённой интеграции. План принятия
claim, сохраняющий проверенный snapshot, —
verification/r1_reference_intake_acceptance/integration_and_claim_plan.md.
Пока main не изменяется. При изменении проверенных полей потребуется применимый
повторный review/STALE; перенос старого WARNING на изменённые данные запрещён.

42 состояния не рассчитаны; §4/5/6 NOT_RUN. Прочность, устойчивость, реальные
реакции/capacity/margins/цикл не подтверждены. Архитектура/ТЗ NOT_APPROVED,
G1 OPEN, W02/physical READY NO-GO. CAD-build/rebuild, новые инженерные расчёты,
физические испытания/изготовление/выпуск не разрешены. OBS-01 CLOSED только на
прежнем R4 exact C; прежний акт STALE/четыре FAIL/семь REJECT/material history=2 сохранены.

## Формальная запись

```yaml
record_type: decision
decision_id: R1-REFERENCE-INTAKE-PRELIMINARY-ACCEPTANCE
gate: null
status: APPROVED_WITH_LIMITATIONS
approved_by: 6afb300b-1540-8191-a5c4-be1a684c20e0
approver_kind: DELEGATED_R1
authorization_evidence: Existing user R1 coordination assignment; direct start/reference-source
  instructions captured in user_direction.json; current user forwards independent
  R5 verdict. This is preliminary documentary acceptance, not a main merge, claim
  grant or engineering gate.
approved_at_utc: '2026-11-17T00:17:45Z'
baseline_commit: 853a72b63fd8c89a3fa54ac1f309f24e7104f1c4
reviewed_source_C: f2cbd96bb78c915dca74cb4eb29daffbb52ee172
scope: WARNING_DOCUMENTARY_REFERENCE_ONLY; exact source candidate remains RAW, active
  registry unchanged, claim pending main
parameter_refs: []
review_ids:
- REV-R5-REFERENCE-INTAKE-REVIEW-01-001
artifacts:
- path: verification/r5_reference_intake_review/review.md
  sha256: e88312dc1eaf844c034096ea65905253071e482a85608ae54975aa5e25e03f57
- path: verification/r1_force_inputs_intake/reference_policy.json
  sha256: d80e34814f035c7b42f4235684fdb760e083701acfe8ef11f14a01502af15ff2
- path: verification/r1_force_inputs_intake/reference_candidate/params/registry.yaml
  sha256: 8e95ad7f7e2ef0f858f3b5ec862c920fb41aae47bbf74e34ade79dcf06d283d7
accepted_limitations_and_open_risks:
- SOURCE-POWER and SOURCE-PRESSURE-UNIT OPEN; moisture basis/method UNKNOWN; no use
  as physical machine values
- ARS includes nonmetallic feedstocks; source-specific constitutive properties/settings
  not transferred
- Up-to output and reference configuration do not approve REV performance or architecture
- R5 upstream self-authorship disclosed; organizational independence and upstream
  physics not re-certified
blocking_issues_remaining:
- Claim PROPOSED_PENDING_MAIN, owner NONE/lease null; no effective ownership granted
  by review
- §4/5/6 NOT_RUN; 42 states not solved; actual strength/stability/reactions not verified
- G1 OPEN; architecture/TZ NOT_APPROVED; W02/physical READY NO-GO
next_authorized_stage: Prepare PR52 with both histories and this documentary disposition,
  without merge. Claim activation requires a separate direct user decision and sequential
  main acceptance; no new numerical/physical work.
author_sessions:
- 6afb300b-1540-8191-a5c4-be1a684c20e0
```
