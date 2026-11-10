# Эстафета R4 — частичная реализация T-codex-01-01

- Сессия r4-model-01 / Codex / R4; claim принят в main 2f463babdc84382a0ab2502f4acfa7a2047087df; lease до 2026-11-11T16:52:25Z. Сначала fetch main и повторно проверить owner/lease/входы.
- Код и результаты: C b3ba802fb1bad642338a18ef82493f44ac069067; ветка work/T-codex-01-01/r4-model-01. Входной акт models/kinematic_press/input_audit.md; вход brief/циклы 3aebae606011ded0f6d6e0a8d6ccc15094d88feb; документальный акт REV-R5-MODEL-REVIEW-01-001 WARNING.
- Запуск: python3 models/kinematic_press/model.py; проверки: python3 -m unittest discover -s models/kinematic_press -p 'test_*.py' (4 OK), python3 scripts/check_registry.py --check-git (PASS). JSON/SVG в models/kinematic_press/results/.
- Пять synthetic сценариев: 01 COLLISION; 02 NO_COLLISION с XY overlap; 03 NO_COLLISION с пересечением XY траекторий; 04 обе нехватки INDETERMINATE; 05 INSUFFICIENT_STROKE и NO_COLLISION. Дополнительно INVALID_INPUT. Это результаты автора, не независимое подтверждение.
- Существенный остаток: это проверка отдельных пар в отдельных фазах, не полная модель альтернатив и их силовой топологии; непроверенные фазы/пары указаны в отчёте. Требуются полное моделирование/прослеживаемость по заданию и отдельная независимая проверка точного C, прежде чем считать задачу выполненной. Не выдавать частичный код за законченный пакет.
- Результат для независимого reviewer: проверить аналитические шесть неравенств, границы численной модели и все synthetic случаи, точные хэши, а также перечисленный незавершённый объём. Проверка NOT_RUN; G1 открыт, реальные параметры UNKNOWN, R5-OBS-01…04 OPEN.
- Капсула handoffs/T-codex-01-01/r4-model-01.md; работа в этой ветке, данные доступны после push.
