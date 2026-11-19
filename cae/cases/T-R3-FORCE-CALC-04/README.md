# T-R3-FORCE-CALC-04 — W02, итерация 03

**FAILED / CALCULATED_ASSUMED.** Пересчитаны все 42 ID условной огибающей.
Выпуск КД блокируют закрытие зазора при рассогласовании цилиндров и
превышение 315 бар при полном реверсе одним цилиндром.

Физические состояния остаются BLOCKED_INPUTS, физические §§4/5/6 —
NOT_RUN. В расчёте использованы A из базовой сборки и B из поставки R4
ревизии 02. Штатная огибающая содержит 2 518 сочетаний, из которых
2 402 имеют условное решение и 116 не имеют статического равновесия
при отпущенной осевой связи. Отдельно проверены 1 512 сочетаний давлений.

- [Инженерный отказ и пороговые проверки](engineering_failure_note.md)
- [Входной аудит](input_audit.md)
- [Результаты по состояниям и строкам](results/index.json)
- [Контакты приёмника B](results/receiver_fit.json)
- [Гидравлика по фазам](results/phase_hydraulics.json)

```console
python cae/cases/T-R3-FORCE-CALC-04/verify_output.py --check-git
python scripts/check_registry.py --check-git
python -m unittest discover -s tests -v
python verify_output.py --check-git
```
