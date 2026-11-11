# Входной акт R3 — измерительная модель и наблюдаемость

T-r3-compaction-measure-01; R3 / Codex / `r3-safety-01`; 2026-11-11 UTC. Ограниченная документальная область WARNING. База `adaf5593edb7c374c112bbcc58c802d35bd4ccd3` (PR #26), claim `5f046982b59376eb26d89541adb81955b27e6ffb`, owner `r3-safety-01`, lease до `2026-11-12T12:29:35Z`. На момент сверки конкурирующего владельца этой задачи в принятом трекере нет. Между базой claim `461a9abcc4bb0011291f6f7a1747524713b371ec` и main изменены только записи задачи, STATE, NEXT_MODEL и новая капсула; содержательные инженерные входы не изменены. Срок claim T-INIT R1 истёк; эта задача не перехватывает его владельца.

## Точные входы

Пути ниже — Git blob на базе `adaf5593edb7c374c112bbcc58c802d35bd4ccd3`; blob — идентификатор Git, не SHA-256:

| Файл | Git blob | Область |
|---|---|---|
| verification/compaction_measurement_program_draft.md | `7d42b3a0dc3d43c2c6facff73d2f5e319a753e95` | Принята только как документальный черновик с WARNING |
| verification/compaction_program_r1_disposition.md | `4288d06cb0747cdd11d4304b73b5ffcd28623e75` | Условия приёмки и OPEN W01–W05 |
| verification/r5_compaction_program_output/review.md | `3c63a87e4e623f0461b653069cf59bf40dc3c0b9` | Акт R5 `d8c7ee2e9797f9abd88f048ece315412f84f3ee0`; W03/W04 OPEN |
| verification/r2_compaction_data/specification.md | `5b994d66feb0e8ee485dd2276314e1c0728e11dd` | Граф событий, границы массы и связанные погрешности |
| verification/r2_compaction_data/disposition.md | `7532b049c2e5dca24d12166545f7144d09dc7241` | PR #25: документальный черновик с WARNING |
| verification/r5_r2_compaction_data_review/review.md | `7207cf5f4d1634c947e01dc137cf71e0f223900c` | Независимый review R2-постановки |
| verification/engineering_input_map.md | `4817c698ed96a7ac1bf87577489d7ebb6c8c47e8` | Условные зависимости и границы цилиндра |
| controls/press_variant_state_tables.md | `7c82985fa6572f427de907992cc8483c71d62643` | DRAFT фаз A/B, не доказательства состояний |
| verification/feed_dosing_rig_scheme.md | `748dd1b20b33f297e797aa201ccb9b1c6ff3794a` | Проектные L/F/M и ограничения OBS-04 |
| requirements/system_requirements.md | `879014cbb84c5634c6f7e928e5ea9eb9a45d3fcd` | REQ DRAFT, rev7 |
| requirements/verification_matrix.md | `ea6ec2596070ceeadb8512ddecd71ca5e75411af` | VAL DRAFT, rev7, NOT_RUN |

## Аудит по разделу 6 AGENT_PROTOCOL

| Пункт | Статус и основание |
|---|---|
| 1. Требования, границы, режимы | WARNING: вход после подготовки предварителен, T/U и поставка UNKNOWN; REQ/VAL DRAFT. Достаточно для постановки вопросов, не для применимой методики. |
| 2. Источники | WARNING: R5 и R2 дают ограниченные документальные выводы; физическая установка, пригодность каналов и исходные партии не подтверждены. |
| 3. Единицы, знаки, допуски | WARNING: определены кандидаты для согласованной модели; реальные единицы каналов, базы, пределы и неопределённости UNKNOWN. |
| 4. Балансы и пересчёт | NOT_RUN: измерения и числовые данные отсутствуют; символическая постановка не является расчётом, балансом реальной установки или выбором метода. |
| 5. Геометрия и связи | WARNING: A/B — неутверждённые альтернативы, геометрия, контакт и силовой путь UNKNOWN. |
| 6. Циклограмма | WARNING: таблицы DRAFT; команды и положения не доказывают физическое состояние, реальные фазы/переходы UNKNOWN. |
| 7. Прослеживаемость | WARNING: есть проект графа R2 и связи с REQ/VAL, фактические ID, наблюдения и результаты NOT_RUN. |

Разрешено составить ограниченную документальную постановку до истечения lease; самостоятельная приёмка исключена. B01–B03, R5-COMP-W01–W05, R5-OBS-01…04 и G1 OPEN; физическая работа, пробы, испытания и калибровка NOT_RUN.
