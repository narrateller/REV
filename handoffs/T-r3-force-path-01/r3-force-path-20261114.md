# Капсула — публикация постановки T-r3-force-path-01

```yaml
capsule_version: '1.0'
task_id: T-r3-force-path-01
role: R3
session_id: r3-force-path-20261114
model_label: Codex
assignment_basis: Direct user instruction to prepare and publish a separate task and new claim
status: HANDOFF_AWAITING_MAIN_CLAIM_ACCEPTANCE
task_status: READY
claim_status: PROPOSED_PENDING_MAIN
owner_session: NONE
proposed_owner_session: r3-force-path-20261114
proposed_at_utc: '2026-11-14T12:11:55Z'
proposed_lease_expires_at: '2026-11-15T12:11:55Z'
lease_expires_at: null
base_main: e35086f2e87611faa7013095d110092198b912dc
branch: work-r3/T-r3-force-path-01/r3-force-path-20261114
C_commit: d5c1afd74a152f9e04596b296df0e6812a3b2d18
C_availability: REMOTE_VERIFIED
claim_acceptance_commit: null
self_merge: NOT_PERFORMED
old_claims_extended: false
input_manifest: verification/r3_force_path/input_manifest.json
input_blobs_and_sha256: 20
protected_trees: 12
baseline_bindings: 44
baseline_scenarios: [BASE_A, BASE_B]
baseline_mode: fixed-budget
baseline_revisions_and_values: UNCHANGED
engineering_input_audit: NOT_RUN_PENDING_ACCEPTANCE
force_path_calculation: NOT_STARTED
independent_output_review: NOT_RUN
CAD_rebuild: NOT_RUN
physical_trials: NOT_RUN
W02: OPEN
PLC: NO_GO
physical_READY: NO_GO
G1: OPEN
architecture_TZ: NOT_APPROVED
enforcement: PROCEDURAL
next_role: R1/operator for sequential claim acceptance, then R3 under accepted current claim
created_at_utc: '2026-11-14T12:19:16Z'
```

## Что сохранено и проверено

C содержит только новую постановку/claim/manifest/UNKNOWN/документальные checks
в verification/r3_force_path/ и добавленную запись ISSUES_AND_TASKS.md.
Registry --check-git PASS, exact input hashes и protected trees совпали; ссылки
документов/JSON/pending claim и git diff --check PASS. Прежний трекер сохранён
целиком как исторический суффикс. Проверки не являются инженерным расчётом,
физической валидацией или независимым OUTPUT-review.

H добавляет только STATE.md, NEXT_MODEL.md и эту капсулу; пакет C не меняется.
Перед H повторная `.venv/bin/python scripts/check_registry.py --check-git`
завершилась exit 0: PASS (engineering acceptance NOT assessed).
`git diff --check` и ограничение H только тремя файлами эстафеты проверены;
все 20 входных hashes и прежние STATE/NEXT/трекер сохранены. Численные расчёты NOT_STARTED.

## Следующий атомарный шаг и критерий

Оператор/координатор последовательно принимает отдельную постановку и claim
в main. До этого остановиться на документальном результате. После принятия R3
проверяет fetch/ancestry/owner/lease/конкуренцию и manifest/44 bindings, разбирает
изменения базы и оформляет входной аудит §6. Только затем начать свободные тела
и матрицу нагрузочных состояний всех четырёх вариантов из task.md. Неизвестные
плечи/сечения/материалы/закрепления/профили остаются UNKNOWN; новую количественную
гипотезу регистрировать отдельно с условиями, исходный BASE_A/B не менять.

Входы/DoD и CI-R3-CARRIER/OFFSET/MOUNTS: verification/r3_force_path/task.md;
пробелы/владельцы: input_gaps.md. Для future exact C требуется независимый R5
вне author_sessions. Старые вопросы, claims/leases, семь REJECT и ограничения
W02/physical READY/G1/архитектуры/ТЗ сохранены. CAD/CAE/испытания не запускались.
