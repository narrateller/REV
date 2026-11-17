# Independent R5 recheck of exact97f58 OBS01/02 correction

[Act](review.md): WARNING; OBS01/02 CLOSED_DOCUMENTARY_EXACT_C only on
`97f58fd437947e26963bdbbc2f2d89df7438e8cc`; new OBS03 OPEN (rendered DM02/03
DRAFT-01 conflicts with JSON DRAFT-02). No TZ/G1/engineering approval.

`semantic_expectations.py` contains own22row/4quantity/11case reasoning.
`recheck.py` imports only those own expectations, not author/prior reviewer checkers.
`independent_results.json` records4261PASS/1FAIL(OBS03)/3NOT_RUN,146scope entries,
22row/22method/40source/9decision assessments. `independent_after_record.json`
is a warranted post-append preservation check; counts are not additive.
The expected script exit1 preserves the open semantic FAIL; do not relabel it PASS.

`renderer_replay.json` separately records actual exact-C TEMP HEAD,53physical pins,
six outputs6MATCH/exit0 before own journal append. Replay reproduces OBS03 too;
it does not prove method revision correctness or physical conformity.

`identity.json`, `input_audit.*`, `remote_context.json`, `merge_context.json`,
`task_before_recheck.json` retain actual identity/upstream disclosure/authority/input
and operational merge evidence. `observation_decisions.json` records the two bounded
closures and new open observation. `target_CI.json` separates exact-C run absence
from requestH/main/activation CI. `validation.json` and `registry.log` record own
pre-C registry exit/seals. H adds actual published C CI/remote proof; H's later CI
is checked remotely after H exists, without a self-referential future-SHA claim.

```sh
python3 verification/r5_definition_obs_recheck_20261118/recheck.py --output /tmp/r5-def-obs-results.json
python3 scripts/check_registry.py --check-git
python3 verification/r5_definition_obs_recheck_20261118/check_publication.py --review-C <C> --handoff-H <H> --branch <branch> --output /tmp/r5-def-obs-publication.json
```

To reproduce presentation, create a separate detached temporary worktree at exact
targetC, materialize pinned LFS files and run its `render_register.py --output-dir`
in TEMP. Use recorded command/HEAD/hashes in renderer_replay.json. Do not substitute
current reviewer-journal inputs for the frozen target. No CAD/engineering execution.

PR60 remains DRAFT/unmerged.42states unsolved;§4/5/6NOT_RUN;strength/stability/actual
reactions unconfirmed;TZ/architecture NOT_APPROVED;G1OPEN,W02/physical READY NO-GO.
No RAW promotion,numerical/physical engineering,CAD-build/rebuild or trials.
