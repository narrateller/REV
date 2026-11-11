# Независимый RECHECK R5-LAYOUT-NEW-B01/B02

Code/results `66924aed1cb2d193b9883d2140d85560b1e4b0cb`, ветка work-r4/build-layout/r4-linked-20261111; входной акт REV-R5-LAYOUT-CORRECTION-01-001 на 04b9f2950a34492b15e1d7c893f680b82f9183b9, исходный C 120a958. Оба блокера OPEN до независимого решения. Исправлена только новая аналитика/оркестрация/verification, геометрия и 15 frozen checked-tool файлов не менялись.

Проверить B01: motion/точные входы/полное SUPPORTED interval evidence обязательны до CLEAR. Unsupported/unknown/пробелы покрытия дают INDETERMINATE с причиной; определённая коллизия другой поддержанной пары сохраняет BLOCKED при UNKNOWN. Raw evidence сохраняется.

Проверить B02: sufficient требует actual/reported link/transition/continuity/lifecycle/восстановленный limited READY и обязательные фазы; UNKNOWN, LINK_ABSENT, BLOCKED и неполный возврат исключают success. Verify_cycles/verify_output не вызывают новый oracle outcomes.py. Execution/exit, test matches и scene geometric outcome раздельны: отрицательная сцена не становится READY из-за test PASS.

```sh
/usr/bin/python3 cad/layout_correction/run_revision.py
/usr/bin/python3 cad/layout_correction/verify_output.py
```

Обе штатные команды exit 0, 83 unit tests, 15 classifier и 40 cycle counterexamples PASS. Для полного исходного R5 counterexample обе команды ниже должны **отклонить** sufficient с exit!=0:

```sh
/usr/bin/python3 cad/layout_correction/run_revision.py --inputs verification/r5_layout_correction_review/evidence/unlinked_inputs.json --out /tmp/rev-unlinked-recheck
/usr/bin/python3 cad/layout_correction/verify_output.py --out /tmp/rev-unlinked-recheck
```

Фактически native builds/checker exit 0, orchestration и verifier exit 1, sufficient A/B LINK_ABSENT/BLOCKED/false. Evidence и команды verification/r4_analysis_fix/negative_full_*. Геометрия/evidence C 120a958 сохранены; повтор geometry_probe R5: 251923 строк без coverage errors, 618 target/58 native zero-positive, 12 сервисов restored. Remaining frame/mount/powerpack/service intersections/UNKNOWN не исчезли, full READY INDETERMINATE. Воспроизведение reviewer script автором не является независимым RECHECK.

Материалы: cad/build/layout_correction/run.json, assessment.md/json, regressions/*.json, classifications.jsonl.gz и raw_checked_tool/. Source/artifact hashes, geometry baseline и final checks сохранены. Критерий sufficient не ослаблен. Реальные параметры/работоспособность/безопасность UNKNOWN, архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Main/claim/owner/lease до интеграции сверяет координатор, merge не выполнялся.
