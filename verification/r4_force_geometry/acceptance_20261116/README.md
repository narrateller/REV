# Документальная фиксация принятого назначения R4

Источник нового решения — прямое текущее поручение пользователя назначить R4
фактической сессии и интегрировать PR49 после проверок, без продления срока.
PR49 фактически слит обычным merge cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9.
Эта запись нормализует прежние proposal-поля в соответствии с уже разрешённым
и выполненным принятием; нового scope/lease/инженерного разрешения нет.

premerge.json и input_preflight.json фиксируют точные main/head/CI/85 input checks
и срок перед слиянием. merge_result.json/receipt.json — результат GitHub и два
родителя merge, совпадение дерева с reviewed head. operator_authorization.json
записывает прямое назначение пользователем, не имитирует heartbeat R4.

Редакция 2 proposal сохранена побайтно в claim_history/20261116T182310Z/.
Канонические claim.json/md и команда R4 отражают фактические owner/lease/merge.
До входного аудита исполнение NOT_STARTED / BLOCKED_PENDING_INPUT_AUDIT.
