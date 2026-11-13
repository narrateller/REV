# B03 RECHECK — normative minimum v1

Основной [акт](review.md): REJECT_WITH_BLOCKER, B03 OPEN. Session r5-ci-minimum-20261113.
Target C bd7ce8a623d6a4ecdff1f106868a4c7086a8a27f,
H 0e519720d55b5b7b19d66b5a90c699b5d6697338,
R1 5fe510bbc55a052c360ab39a2491a061584b8fb7.

53 actions/84 mode rows и авторитет нормы проверены независимо от mutable
payload. Минимум воспроизведён побайтно; шесть прежних пропусков отклоняются.
Но остаются 4 full-checker false MATCH при bool/float revision и 2 reference
predicate TRUE для proof, отклоняемого frozen helper. Никакой fault не очищен.

Из /workspace/REV:

```sh
.venv/bin/python -B verification/r5_ci_semantic_minimum_recheck/authority_and_regressions.py
.venv/bin/python -B verification/r5_ci_semantic_minimum_recheck/independent_probe.py
.venv/bin/python -B verification/r5_ci_semantic_minimum_recheck/record_commands.py
```

Полный independent_probe делает новый sweep 122 temp-копий. `--reuse-mutations`
использует captured_mutations.json и сверяет checker/minimum/code hashes и raw
responses; это повторный audit/reaggregation, не новый запуск mutation CLI.
Все фактические 122 cases исполнены; каждая имела fresh source/export hashes
и readonly checker. 117 правильных отказов, 1 equivalent MATCH, 4 false MATCH.
765 проверок aggregate: 759 совпадений/6 FAIL. **Exit 0 — evidence capture,
не успешный gate/приёмка.** failed содержит все несоответствия.

historical prior probe выполнен только в temp materialized copy, его старый
hardcoded reviewed_C не переписан; authority.json указывает фактический новый
input и сохранность оригинального review evidence. Git worktree не создаётся.

Авторские 3277/8 и 6 методов (411 captured cases) +7 retained methods исполнены;
raw журналы сохранены. record_commands.py проверяет receipts/полные case JSON,
не повторяет дорогой уже успешный 411-case suite. Случайный temp-prefix только
при сравнении нормализуется; raw stderr/stdout сохранены. final_registry.log —
финальная проверка нового индекса. Manifest evidence_hashes.json — все evidence.

preservation_during_checks.json: 1328 старых tracked files без изменения;
preservation.json допускает позднее добавление review-meta лишь в четырёх
общих документах с полным сохранением исходного H. 44 bindings, 4 variants,
612 protected/7 packages/11 trees/17 blobs и старые R5/R1 сохранены.
R1_followup.md сохраняет два прежних отказа и текущий третий. До нового
плана/решения R1 следующая B03 итерация BLOCKED. W02/G1 OPEN, physical READY NO-GO.
Ни прочность, ни геометрия/нативные CAD не принимаются.
