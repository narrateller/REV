# Operator fork 2026-11-18

Legacy ledgers retired; exact originals and all source variants are in
coordination/completions/operator-fork-20261118/.
Old UUIDs/scope amendments do not grant authority. New sessions use the new protocol.

## Fresh claim

File: `<task_id>.json`. Use these exact field names:

```json
{
  "task_id": "TASK_FROM_COORDINATION_TASK_INDEX",
  "role": "R3",
  "owner_session": "ACTUAL_NEW_SESSION_ID",
  "model_label": "ACTUAL_MODEL_OR_UNAVAILABLE",
  "source_main_sha": "EXACT_CHECKED_MAIN_SHA",
  "input_manifest": "EXACT_TASK_INPUT_MANIFEST_PATH",
  "proposed_at_utc": "ACTUAL_PREPARATION_UTC",
  "lease_expires_at": "PREPARATION_UTC_PLUS_24_HOURS_UNLESS_OPERATOR_SPECIFIES_OTHERWISE",
  "status": "PROPOSED"
}
```

Do not commit placeholder values as an accepted claim. Before publication check live UTC,
main, task/owner conflicts, the input manifest and tools. A claim can be recorded as
`ACCEPTED_MAIN` in its accepting commit, but authority becomes effective only when that
commit enters main. A normal fast-forward main push or ordinary merge serializes ownership;
never force-push over a competing owner. One accepted task per session; no automatic renewal.
On completion move the claim into completions rather than leaving a stale active lock.
