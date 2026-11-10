# Капсула T-INIT — codex-01

- capsule_version: 1.0
- status: BLOCKED — ожидание принятия claim в main.
- task_id / role / session_id / model_label: T-INIT / R1 / codex-01 / Codex.
- author_sessions: codex-01.
- assignment_evidence: прямое подтверждение пользователем; текст зафиксирован в T-INIT.
- created_at_utc / heartbeat_utc: 2026-11-10T12:06:09Z.
- lease_expires_at: 2026-11-11T12:06:09Z.
- base_commit: 2e479849cea10dab9376a68cb44d2ff716c215da.
- work_commit / claim_record_commit: a31a6d86cde8799807e6d21454deda8db55b695a.
- branch: work/T-INIT/codex-01.
- availability: LOCAL_ONLY при записи; после push проверить удалённый ref.
- input_refs: файлы и ревизии перечислены в NEXT_MODEL.md и T-INIT.
- completed_steps: сверена main; подтверждено назначение; подготовлено предложение claim.
- changed_files: ISSUES_AND_TASKS.md, STATE.md, NEXT_MODEL.md, handoffs/T-INIT/codex-01.md.
- unfinished_step: публикация ветки и PR, последовательное принятие claim в main.
- environment: Python 3.12.14, PyYAML 6.0.3, Git LFS 3.6.1; .venv/bin/python; CAD/CAE UNAVAILABLE (не запускались).
- running_jobs / open_hypotheses / blocker_ids / review_refs: NONE.
- uncommitted_or_unsaved: эта капсула и сводки сохраняются следующим commit H.
- next_action: проверить актуальную main, принятие claim, владельца, lease и ревизии входов.
- next_action_success_criterion: принятый claim codex-01 и действительный lease без конкурирующего владельца.
- stop_conditions: claim не принят; lease истёк; конфликт владельца или входов.

Анализ источников не начат. Расчёты и инженерные утверждения отсутствуют.
GitHub API при подготовке возвращал CONNECT 403; Git read работает.
