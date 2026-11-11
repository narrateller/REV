# R3: claim для измерительной модели и наблюдаемости

- task_id: T-r3-compaction-measure-01; role R3; proposed_owner_session r3-safety-01 / Codex; author_sessions [r3-safety-01]. Прямое поручение пользователя; отдельная задача, T-INIT не перехватывается.
- base_commit: 461a9abcc4bb0011291f6f7a1747524713b371ec; branch: work/T-r3-compaction-measure-01/r3-safety-01.
- claim PROPOSED / PENDING_MAIN; heartbeat `2026-11-11T12:29:35Z`, lease_expires_at `2026-11-12T12:29:35Z`, acceptance_commit NONE.
- Выполнено: проверены PR #25, акт R5, постановка R2 и срок T-INIT; создана задача и предложен claim. Принятие claim, входной аудит и выполнение постановки NOT_STARTED.
- Следующий шаг: последовательно принять claim в main; проверить owner, lease, конкурирующие изменения и точные входы; оформить входной акт; подготовить W03/W04 и направить точный SHA на независимый review.
- Stop: claim не принят, lease истёк, конкурирующий владелец или входы изменились без проверки.
- Входы и критерии в ISSUES_AND_TASKS.md; W03/W04, B01–B03 и G1 OPEN. Приборы, методы и численные пределы не выбирать; пробы и испытания NOT_RUN.
