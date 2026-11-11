# R3: постановка измерительной модели на review

- task_id: T-r3-compaction-measure-01; role R3; owner_session r3-safety-01 / Codex; author_sessions [r3-safety-01].
- claim `5f046982b59376eb26d89541adb81955b27e6ffb` принят PR #26 на `adaf5593edb7c374c112bbcc58c802d35bd4ccd3`; lease до 2026-11-12T12:29:35Z. Владелец T-INIT не изменён.
- Сверены main, отсутствие конкурирующего claim и неизменность инженерных входов. Входной акт и точные blobs: verification/r3_compaction_observability/input_audit.md.
- Результат: verification/r3_compaction_observability/specification.md — условная измерительная модель, пустые формы, качество/время, наблюдаемость A/B и недостающие данные установки. Все реальные данные/методы/пределы UNKNOWN.
- Независимый OUTPUT-review NOT_RUN. Следующий шаг: передать точный опубликованный SHA независимому R5 и профильным R2/R3; перед интеграцией повторно проверить main, owner, срок и изменения входов. При истечении или конкурирующем claim действовать по протоколу.
- R5-COMP-W03/W04, B01–B03, R5-OBS-01…04 и G1 OPEN; пробы, испытания и калибровка NOT_RUN.
