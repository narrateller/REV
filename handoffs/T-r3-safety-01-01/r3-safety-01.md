# R3 — публикация задачи и claim

- task_id: T-r3-safety-01-01
- role / session_id / model_label: R3 / r3-safety-01 / Codex
- author_sessions: [r3-safety-01]
- assignment_evidence: прямое назначение пользователя 2026-11-11 в текущем чате
- base_commit: 0e65bee44fb72fab9b79849d61061dd55589c239
- branch: work/T-r3-safety-01-01/r3-safety-01
- claim: PROPOSED / PENDING_MAIN; owner_session r3-safety-01
- heartbeat_utc: 2026-11-11T04:14:00Z
- lease_expires_at: 2026-11-12T04:14:00Z
- completed: сверена main; прочитаны протокол, состояние, эстафета, задание; оформлены отдельная задача и предложение claim.
- changed_files: ISSUES_AND_TASKS.md, STATE.md, NEXT_MODEL.md, настоящая капсула. Реестр параметров и инженерные артефакты не менялись.
- unfinished: принятие claim в main; входной аудит; документальный реестр, нормативные вопросы и REQ/VAL-матрица.
- next_action: принять опубликованный claim последовательно в main; проверить точный SHA/owner/lease/изменения входов; только после этого выполнить входной аудит и ограниченную документальную задачу.
- stop_conditions: claim не принят, lease истёк, конкурентный владелец, изменены входы без аудита, нужны неподтверждённые инженерные выводы.
- limitations: B01–B03, R5-OBS-01…04 и G1 OPEN; риск/защиты/нормативная применимость UNKNOWN; пробы/испытания NOT_RUN.
- review: независимый review результата NOT_RUN; самоприёмка запрещена.
