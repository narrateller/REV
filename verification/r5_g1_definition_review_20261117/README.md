# R5 exact-C G1 definition-register OUTPUT-review

Reviewed C `7e2d5ecff42fe1d09b461e05375924cb644c27c9`, request H
`7e4ce7aad8396493da6e2284d29441b46b4abb80`, accepted scope main
`04a6486527c9ba4fd4d22fcf50e0427213443507`. [Act](review.md): WARNING,
preliminary DRAFT usable, insufficient for TZ/G1. [Two OPEN observations](observations.json).

Own evidence is separate from the author's checker and four-output replay:

- `semantic_expectations.py`: R5's manual reading/rationale for144scope items and22methods.
- `inspect_definitions.py`, `independent_results.json`: own documentary oracle and full assessments.
- `independent_after_record.json`: warranted post-append preservation check; not additive to counts.
- `renderer_replay.json`: separate exact-C TEMP replay,4MATCH/exit0,before own journal append.
- `identity.json`, `input_audit.*`, `remote_context.json`, `merge_context.json`: actual session/authority/input/merge proof.
- `target_CI.json`: exact source-C/run absence and H/main CI,not independent semantic review.
- `registry.log`, `validation.json`: own pre-C registry exit/seals.
- `check_publication.py`: post-H remote SHA/parent/claim/lease/PR60/ownC-H CI verification.

```sh
python3 verification/r5_g1_definition_review_20261117/inspect_definitions.py --output /tmp/r5-definition-results.json
python3 scripts/check_registry.py --check-git
python3 verification/r5_g1_definition_review_20261117/check_publication.py --review-C <C> --handoff-H <H> --branch <branch> --output /tmp/r5-definition-publication.json
```

For the renderer, create a separate temporary detached worktree at exact target C,
materialize its pinned LFS objects, then run that worktree's `render_register.py`
with `--output-dir` in TEMP. Do not run replay on the reviewer journal's changed
working-tree inputs. The saved replay records actual command/HEAD/SHA for all four
outputs and all92 physical input pins. No CAD or engineering program is executed.

First publish own act C; its handoff H is a direct child with full C reference and
actual C CI proof. H's own subsequent CI is remote evidence, checked after H exists;
no self-referential future SHA or CI result is fabricated in C/H.

42 states unsolved;§4/5/6 NOT_RUN;strength/stability/actual reactions unconfirmed.
TZ/architecture NOT_APPROVED,G1OPEN,W02/physical READY NO-GO. No RAW promotion,
physical/numerical stage,CAD-build/rebuild or trials. PR60 must remain unmerged.
