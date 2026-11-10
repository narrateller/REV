# R4 → независимый R5: непрерывность после REV-R5-RECHECK-04-001

- code/results C debfd085842ccae079cfd6faea1c41bca20f335d; branch work/T-codex-01-01/r4-model-01; author r4-model-01; review NOT_RUN.
- Решение R1 791d0ce8ccb31373b221d0b69063e2f835b442c0; капсула R1 5ff71747b7263220ab25c56f3d329253ee42356d; main при проверке 2f463babdc84382a0ab2502f4acfa7a2047087df; owner r4-model-01, lease 2026-11-11T16:52:25Z.
- Исправлены initial obstacle, применение continuity к transition/READY и охват четырёх исходов; сценарии и хэши в models/kinematic_press/results/linked_report.json, команды в README.
- 8/8 synthetic ожидаемых исходов; B/collision [1/4,7/8] и [3/4,1], разрыва нет; CE-01/02 PASS, 20 unittest OK, 3000/3000 независимых event-partition сравнений повторено, registry PASS; оба JSON воспроизводимы.
- R5-IMPL-01 OPEN до независимого положительного RECHECK; R5-IMPL-02 CLOSED только для проверенного 576a17fc, требуется регрессия на C. G1 открыт, реальные параметры UNKNOWN.
- Следующий шаг: R5 fetch точный C, проверить входы/хэши, выполнить команды и отрицательные мутации по disposition, оформить самостоятельный акт. running_jobs []; uncommitted_or_unsaved [].
