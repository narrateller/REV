# Запрос независимого OUTPUT review геометрии и нового анализатора

Code/results `120a9582f4835e81cdf324605a14f632ce7db2cb`, ветка work-r4/build-layout/r4-linked-20261111. Основание: checked tool de377f0 и R5 WARNING акт 214b055f04d5b061a68dfd744afb6c956ac9a9d1. Все 15 checked-tool файлов побайтно сохранены; B01/B02 не переоткрываются без нового основания. Проверить **новый набор геометрии и отдельно новый код run_revision/assess/verify_output/face-touch policy**, которые прежним актом не проверялись.

Из корня после checkout C и git lfs pull, предварительно сохранить исходные результаты и сверить hashes:

```sh
/usr/bin/python3 cad/layout_correction/run_revision.py
/usr/bin/python3 cad/layout_correction/verify_output.py
```

Все исходные тела сохранены, 70/68 bodies. Целевые native проникновения устранены геометрией: слот/корпус заслонки, portal с выходным окном, расширенный lock, полный guard вне хода/гидроагрегата. 79 tests, 8 limited outcomes, native CAD/STEP/queries/repeat PASS. 130453 рабочих и 121470 сервисных строк; 618 target rows без strict penetration, 6 старых native свидетелей стали zero volume. 12 сервисных последовательностей непрерывны, позиции восстановлены. Отдельно 216 строк двух новых design counterexamples и новые тела не имеют введённых положительных/envelope пересечений.

Проверить полноту всех combinations/intervals, возврат, кап-обслуживание gate, lock/end_stop/portal extraction, геометрические feed/closure/reaction witnesses, отсутствие необоснованных исключений. Raw core COLLISION не удалены; conditional face-touch требует positive area и named policy при нулевом объёме, не доказывает физическую допустимость. Криволинейные bounds и native witnesses не заменяют непрерывную BRep-проверку. Остальные frame/mount/powerpack и service препятствия/UNKNOWN остаются; новый whole-press READY INDETERMINATE.

Навигация cad/layout_correction/README.md; причины/размеры/до-после/полное evidence cad/build/layout_correction/assessment.md/json, raw_checked_tool/, classifications.jsonl.gz, service_scenes.json.gz, before_after_native.json, changes.json, run.json. Исходные reviews/probes/evidence и обе пробные неудачные расстановки сохранены. Frozen raw metadata source_commit_inputs/known_native_penetrations/tool_blockers исторические, текущий input/source provenance в run.json.

Claim/lease проверены в audit, исходная задача покрывает корректировку. Перед интеграцией координатору сверить актуальный main/owner/lease и исторический предварительный учёт main. Реальные размеры/нагрузки/сырьё/безопасность UNKNOWN, все числа отдельно ASSUMED. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Задача IN_REVIEW, не принята, merge не выполняется.
