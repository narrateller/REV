# DM03: сохранение исходов всех циклов

DRAFT / NOT_APPROVED / independent OUTPUT-review NOT_RUN. Общий WARNING. Новых инженерных чисел, назначений и разрешений выполнения нет. 42 состояния не рассчитаны; §4/5/6 NOT_RUN; G1 OPEN; W02/physical READY NO-GO. Прочность, устойчивость и реальные реакции не подтверждены. Численный/физический этап, CAD-build/rebuild и испытания не начинались и не разрешены.

Проект правила NOT_APPROVED / execution NOT_RUN; OBS-02 OPEN до независимого recheck.

Обязательные будущие поля: cycle_id, outcome, quality_flag, missing_reason, disposition, raw_event_refs, series_accounting_refs.

- Retain a cycle record for every attempted cycle,including unsuccessful/incomplete and missing-product or missing-measurement cases.
- Absence of product or measurement never permits dropping the cycle,its observed outcome,quality/missing reason or disposition.
- Missing product/measurement IDs and quantities remain null with reasons; no fictitious object,zero mass or inferred successful outcome.
- Signal quality is distinct from process outcome; INVALID/SIGNAL_LOSS does not prove failed motion or no motion.
- Keep raw event references,revision/time/quality and series-accounting links across rejects,stops,incomplete output,residuals and losses.
- Never remove failed/incomplete cycle records from the controlled full-series ledger,including after aggregation/disposition. Derived summaries may select subsets only with links to the unfiltered ledger and declared coverage/exclusions; base records remain available.

Связи полного учёта: DEF-01-E, DEF-04-D, REQ-REV-22, VAL-REV-22, verification/r1_g1_observation_revision_20261117/evidence_schema.json.

Изделие/измерение может отсутствовать; запись попытки цикла, его исход, качество, причина отсутствия и диспозиция сохраняются. Фактических циклов/измерений/результатов здесь нет.
