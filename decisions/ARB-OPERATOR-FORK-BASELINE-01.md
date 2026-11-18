# ARB-OPERATOR-FORK-BASELINE-01

```yaml
record_type: decision
decision_id: ARB-OPERATOR-FORK-BASELINE-01
gate: null
status: APPROVED_WITH_LIMITATIONS
approved_by: OPERATOR_DIRECT_USER_INSTRUCTION
approver_kind: HUMAN
authorization_evidence: coordination/user_authorizations/operator_fork_20261118.json
approved_at_utc: '2026-11-18T01:05:31.984803Z'
baseline_commit: 5b72e18d83cb0b10cf0a1c2c50fbe0d72fd8ae1a
scope: Operator documentary closure and engineering-start baseline; administrative
  protocol fork and full session rotation,not physical conformity
parameter_refs: []
review_ids: []
artifacts:
- path: coordination/user_authorizations/operator_fork_20261118.json
  sha256: 13e0b93e1b60c53b2c35578e59809957ba4e5f2e9dd68d02a269a67f50aff6dd
- path: baselines/operator-fork-20261118/manifest.json
  sha256: 883fcd9f5de4da4b241467b05f4e8be4d36764b3af0628140333d5f7a5860578
accepted_limitations_and_open_risks:
- 42states and§§4/5/6 not calculated at fork
- Strength/stability/actualreactions unconfirmed;G1OPEN;physicalREADY/W02 not passed
- UNKNOWN/RAW and source conflicts remain;no auto maturity promotion
- OBS03 accepted by operator,not a fabricated independentR5PASS
blocking_issues_remaining:
- Real engineering inputs/criteria/materials/geometry/BC where stillUNKNOWN
next_authorized_stage: NEW_SESSION_ENGINEERING_TASKS_AFTER_FORK_AND_FRESH_CLAIMS
```

Оператор принимает точный5b72e18 и закрывает OBS01/02/03 в документальной области без нового R5.
Прежние независимые акты/FAIL/closures не переписываются; это решение оператора.
PR60: MERGED ordinary merge `5da433af81874640d2e82bbbe408633cfa8b7e73`. Parents/tree/ancestry/CI подтверждены;квитанция coordination/completions/operator-fork-20261118/PR60_integration.json.
R2 4fd6f32b4df3186a805ac7e654be6c4c9e1c6a50,R3 93b4aead4983f88919d8e8b4165e29d7f3246600(PR48),
R4 beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe зафиксированы как отправная база.
Это не LOCKED/VERIFIED инженерных параметров и не расчёт42состояний.
Причина форка:прекратить документарную рекурсию R1↔R5,разгрузить>1.2МБ контекста и перейти
к прямым инженерным задачам/КД. Старыеleases не продлеваются,все старыеUUID освобождены
при включении этой транзакции в main. Новые сессии получают новые claims по новому протоколу.
Эта старая сессия заканчивает только административную миграцию по прямой директиве оператора.
Физические испытания/выпуск в производство не разрешены этой операцией.

R2/R3/R4 source commits также сохраняются annotated Git tags operator-fork-20261118/R2,R3,R4,без force и без замены действующего реестра.

## Constitution fork applied

2026-11-18T01:27:06.472992+00:00;actor 6afb300b-1540-8191-a5c4-be1a684c20e0. Compact contexts,roles/R1..R5,newtaskqueue anddeterministicverify_output replace legacycontext recursion. This oldsession finishes administrative migration only,then retires.
