# R4 → R5: RECHECK SYN-LINKED-EJECTION

- status IN_REVIEW; author_session r4-model-01; code/results commit 576a17fc0b127cb7d377992c01d645a77bed42d4; branch work/T-codex-01-01/r4-model-01.
- Арбитраж ARB-R1-RECHECK-03: 1283c9e6f3b14dbbe820dd06798399c611d34ce8, решения и критерии decisions/ARB-R1-RECHECK-03.md; R5-IMPL-01/02 OPEN, consecutive_rejections=2. Проверенная main 2f463babdc84382a0ab2502f4acfa7a2047087df; lease до 2026-11-11T16:52:25Z.
- Выполнено: параметры A/B, четыре исхода, геометрический непрерывный интерфейс и выдача, все пары независимо заданного состава, условия READY/жизненный цикл, CE-01/02. Отчёт models/kinematic_press/results/linked_report.json; README содержит команды.
- Проверки автора: 8/8 исходов соответствуют контракту; CE-01/02 PASS; прежние 28 synthetic результатов сохранены; 17 unittest OK, R5 benchmark 3000/3000; registry PASS; JSON воспроизводим. Независимая проверка исправлений NOT_RUN.
- Следующий шаг R5: fetch ветку/C, сверить SHA и результаты, проверить каждый критерий R1 и собственные контрпримеры, оформить отдельный акт и независимо решить судьбу блокеров. Нельзя закрывать G1 или утверждать реальную выдачу по synthetic сцене.
- running_jobs []; uncommitted_or_unsaved []; физика/реальные данные REV UNKNOWN.

- 2026-11-10: вход R1 verification/r5_recheck_04/disposition.md на 791d0ce8ccb31373b221d0b69063e2f835b442c0; капсула 5ff71747b7263220ab25c56f3d329253ee42356d. main 2f463babdc84382a0ab2502f4acfa7a2047087df, owner r4-model-01, lease до 2026-11-11T16:52:25Z. R5-IMPL-01 OPEN; R5-IMPL-02 CLOSED только для проверенной синтетической области 576a17fc; G1 открыт.
