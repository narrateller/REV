# Независимый RECHECK интерфейсного C144941c

Акт [review.md](review.md): B01/B02 CLOSED документально, B03 OPEN;
общий REJECT_WITH_BLOCKER. Session r5-ci-recheck-20261113.
Reviewed C 144941cbfc67002cbe81765e38c80e237473deff,
H 7ee1c8f16eca515a3e21f64177152b4e7b93ce92,
prior review 13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2.

Из /workspace/REV:

```sh
.venv/bin/python -B verification/r5_cycle_interfaces_recheck/historical_replay.py
.venv/bin/python -B verification/r5_cycle_interfaces_recheck/independent_probe.py
.venv/bin/python -B verification/r5_cycle_interfaces_recheck/reproduce.py
```

Старый неизменённый probe на старом C даёт полный JSON 1345/1328/17,
точно совпадающий с исходным актом. Временная копия с Git object DB только
для чтения — не Git worktree. Новые критерии проверены отдельно: 17/17 исправлены.

Собственные 654 проверки: 648 совпадений, 6 FAIL новых semantic mutations.
**Exit 0 означает сбор evidence, не успешную приёмку.** Данные —
independent_results.json и raw mutations/*.json. Для всех 14 мутаций обновлены
экспорт и source/export hashes; проверяется их консистентность и отсутствие
записей checker. 8 отклонены semantic: reason, 6 ошибочно MATCH/exit 0.

reproduce.py запускает авторские проверки, семь unittest методов и независимые
пробы, обновляет только собственные журналы. Авторский missing_svg error содержит
случайный /tmp/rev-ci-doc-* prefix: нормализован лишь этот prefix при сравнении,
сырые stdout неизменны. argv/exit/timestamps — commands.json. Финальный registry
новой формальной записи — final_registry.log.

preservation_during_checks.json фиксирует исходные 1249 файлов; preservation.json
разрешает позднее добавление review-meta только в STATE/NEXT/ISSUES/cross_check_log
при сохранении полного текста исходного H. 612 protected files, 7 frozen packages,
11 trees, 17 blobs, 44 bindings и четыре force SVG/JSON/MD сохранены.

arbitration_request.md — Q-R1-CI-SEMANTICS-ARBITRATION-01 по второму возврату B03
и AGENT_PROTOCOL §6.1. R1 не назначен reviewer, решение не принято вместо R1.
W02/physical READY NO-GO, G1 OPEN. Ни прочность, ни native CAD не принимаются.
