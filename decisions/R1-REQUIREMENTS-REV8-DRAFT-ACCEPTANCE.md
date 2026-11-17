# R1 — предварительный DRAFT требований rev8 принят к документальной проработке с WARNING

UTC 2026-11-17T06:16:36.843399+00:00; actual R1 6afb300b-1540-8191-a5c4-be1a684c20e0. Это диспозиция результата независимого R5,
а не собственный независимый review автора требований. Gate null; ТЗ не утверждается.

## Точные входы

Target C 8d1b45afa84eca078a8de0a9822d6925dd87745b, request H 87f2f5889f9ba74e8eef3a3a040d936d13e0a011; R5 C 04502cfe2eb2eadae242690cfad8f414bd96bff2, H 64ac3efbffcf77e50f2e867390cf141e580de644.
Акт REV-R5-REQUIREMENTS-REV8-OUTPUT-01-001 / CURRENT / WARNING.
Main bec317a4483e7f69c2af0aa1c52ef091bdef57b4, PR54 OPEN/draft. R1 claim ACCEPTED_MAIN, исходный deadline
2026-11-18T01:58:30.990734+00:00 действует, не продлён; intake released/NONE.

R5 независимо рассмотрел22 REQ/VAL,40 dispositions,16 qualitative refs; собственные
3890 PASS/0 FAIL. Авторские358, предыдущие source1250 и renderer replay не считаются
новым OUTPUT-review. R5 actual session6afb0a73-b16c-8191-a539-9a6685e89034 не входит
в author_sessions target. Upstream авторство раскрыто; собственные ранние акты и
физика ими заново независимо не переаттестованы, организационная независимость не удостоверена.

R1 принимает пригодность только предварительного DRAFT для документальной доработки.
Недостаточность для ТЗ/G1 сохраняется. Обязательны B01 критерии/режимы/допуски/
владельцы, B02 программа/метрология/неопределённость/полнота, B03 безопасность/
нормативная применимость и решение source power/pressure/moisture вопросов либо
доказательное ограничение зависимого численного принятия. Текст не заменяет
реальных данных и независимого review доработанной exact ревизии.

## Сохранённая граница

BP500 primary по пользователю, площадка адаптируется, сырьевое окно BP500;
реальные партии/модель/геометрия/опоры/материалы/контакты/силы UNKNOWN. E55/WEIMA/ARS
по релевантности; ARS также допускает неметаллическое сырьё, его режимы/свойства не REV.
Все40 поля остаются scoped RAW,10 предложений не стали approved параметрами,
23 контекста и7 source issues сохранены. Up-to не гарантирует минимум; не смешивать
дозу/изделие/gross/moving mass, hydraulic/material pressure, opening/total hopper height.

R5 история/акт/доказательства и target25 artifacts сохраняются без исправлений.
Только task metadata получает actual WARNING review state; target не меняется и
нового stale/recheck для него этим не создаётся. Старые REJECT/STALE/счётчики,
material history=2/четыре FAIL/узкое OBS01 closure не сбрасываются.
44 полные bindings/нагрузки/ходы/CAD,52 interfaces,42 source-state объекта,
84 RAW/null и15 OPEN gaps сохранены. WHAT_IF applicability NOT_EVALUATED.

42 состояния не рассчитаны; §4/5/6 NOT_RUN. Прочность/устойчивость/реальные реакции/
цикл не подтверждены. Архитектура/ТЗ NOT_APPROVED, G1 OPEN, W02/physical READY NO-GO.
Численный/физический этап, CAD-build/rebuild, физические испытания не разрешены.
PR54 готовится к рассмотрению; main merge этим решением не выполняется и не разрешается.

## Формальная запись

```yaml
record_type: decision
decision_id: R1-REQUIREMENTS-REV8-DRAFT-ACCEPTANCE
gate: null
status: APPROVED_WITH_LIMITATIONS
approved_by: 6afb300b-1540-8191-a5c4-be1a684c20e0
approver_kind: DELEGATED_R1
authorization_evidence: Existing user R1 coordination assignment and documentary requirements
  task authorized in verification/r1_requirements_claim_20261117/authorization.json;
  current user forwards independent exact-C R5 verdict. Preliminary documentary disposition
  only, not human TZ/G1 approval, residual physical risk acceptance or main merge.
approved_at_utc: '2026-11-17T06:16:36.843399+00:00'
baseline_commit: 04502cfe2eb2eadae242690cfad8f414bd96bff2
reviewed_source_C: 8d1b45afa84eca078a8de0a9822d6925dd87745b
reviewed_handoff_H: 87f2f5889f9ba74e8eef3a3a040d936d13e0a011
scope: WARNING_PRELIMINARY_REQUIREMENTS_DRAFT_ONLY; suitable for further documentary
  work, insufficient for TZ/G1 approval
parameter_refs: []
review_ids:
- REV-R5-REQUIREMENTS-REV8-OUTPUT-01-001
artifacts:
- path: verification/r5_requirements_rev8_review/review.md
  sha256: c844e88a5b7cf1bb5de53d03f6a4559489adbd1a7c8803d3ab6ca84a5aea2856
- path: requirements/system_requirements.md
  sha256: 2c49b2eabe8aa6c22b3d6c1479d0921bf1413e6c76c5eb346d4891d394c86705
- path: requirements/verification_matrix.md
  sha256: 6a34302ab716cefb8a049eab3c3e80405991460984df07f783006432661ddb99
- path: verification/r1_requirements_draft_20261117/source_disposition.json
  sha256: 0478a7a40469a9de103e831e23308aeb5c86791165e3d7711b3a66283a4a1cb5
- path: verification/r1_requirements_draft_20261117/open_gaps.json
  sha256: c4e6ce382f2532d83843ae9977bd9a831038ef0d769d411a0ee57fb6b23a2178
accepted_limitations_and_open_risks:
- All 22 criteria remain DRAFT/not approved and VAL/TEST NOT_RUN; independent3890
  checks assess documentary wording/applicability/preservation only
- 40 candidate fields remain scoped RAW:10 target proposals/23 context/7 open issues;
  active registry and CAD unchanged
- SOURCE-POWER/PRESSURE-UNIT/moisture basis/method unresolved; no source ambiguity
  repair, numeric pressure/force/performance adoption or mass-rate derivation
- R5 upstream authorship disclosed; earlier own acts not independently recertified,
  organizational independence not certified
- New exact reviewed artifact changes require STALE assessment/exact-C recheck; operational
  summaries do not expand review scope
blocking_issues_remaining:
- 'R5-TZ-B01 OPEN: measurable criteria, modes, tolerances and assigned owners missing'
- 'R5-TZ-B02 OPEN: program coverage/metrology/uncertainty/completeness and independent
  program review missing'
- 'R5-TZ-B03 OPEN: risk/safety functions/safe states/normative applicability missing'
- SOURCE-POWER, SOURCE-PRESSURE-UNIT, SOURCE-MOISTURE-BASIS OPEN; actual REV inputs
  remain UNKNOWN
- All84 original RAW/null and15 additional gaps retained; §4/5/6 NOT_RUN
- 42 states not solved; strength/stability/real reactions/cycle not verified; G1 OPEN,
  architecture/TZ NOT_APPROVED, W02/physical READY NO-GO
next_authorized_stage: Prepare PR54 with preserved R5 C/H and this narrow documentary
  disposition. Further documentary criteria/gap planning only within the live R1 claim.
  Main merge, TZ/G1 approval and numerical/physical/CAD stages are separate and not
  granted here.
author_sessions:
- 6afb300b-1540-8191-a5c4-be1a684c20e0
requirements_approved: false
architecture_selected: false
source_states_solved: false
G1: OPEN
physical_READY: NO_GO
```
