# Шаблон решения о воротах

Скопировать в decisions/DEC-Gx-Rn.md. Заменить record_type на decision
только для оформленного решения; не переносить шаблонную подпись или дату.

```yaml
record_type: decision_template
decision_id: null
gate: null
status: DRAFT # APPROVED / APPROVED_WITH_LIMITATIONS / REJECTED
approved_by: null
approver_kind: null # HUMAN для G1/G4/G5; HUMAN либо DELEGATED_R1 для G2/G3
authorization_evidence: null # где подтверждены полномочия и само решение
approved_at_utc: null # ISO 8601, UTC, Z; строка в кавычках
baseline_commit: null # существующий полный SHA; решение сохраняется следующим commit
scope: null
parameter_refs: [] # id, revision, engineering_sha256; включить фиксируемые параметры
review_ids: []
artifacts: [] # path, sha256 для доказательств; без хэша этого файла
accepted_limitations_and_open_risks: []
blocking_issues_remaining: []
next_authorized_stage: null
```

APPROVED_WITH_LIMITATIONS разрешает лишь явно указанное исследование и не
превращается автоматически в PASSED или LOCKED. Для изменённой базы создаётся
новое решение; прежнее не переписывать. Поле approved_by не является электронной
подписью: решение человека и полномочия проверяются отдельно от валидатора.
