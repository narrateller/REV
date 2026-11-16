# PR #48 — подготовка интеграции R1 без слияния

Сессия `r1-pr48-integration-20261116`, прямое поручение пользователя.
Новый документальный task — не восстановление истёкшего claim T-INIT.
Решение: `decisions/R1-FORCE-PATH-CONDITIONAL-ACCEPTANCE.md`.
Следующая отдельная задача: `R4_task_proposal.md`, owner NONE, lease null.

История R5 H `6ef3afc123004c43e007dc477241edfed8efabbb` включена в head PR48
merge-коммитом с родителем R3 H `aadc08a70fbaee16b7ba4c16463bab97275926bb`.
Конфликтов Git не было; последовательные STATE/NEXT/tracker сохранены целиком,
новая сводка R1 ставится перед историей. Старые PENDING/NOT_RUN не являются
текущим итогом независимого акта, но их исторический текст не переписывается.
Корневой registry, CAD, нагрузки/ходы/fixed-budget и расчётные пакеты не меняются.

Из `/workspace/REV`, Python 3.12.14 / PyYAML 6.0.3:

```bash
.venv/bin/python verification/pr48_integration/verify_preservation.py
.venv/bin/python verification/pr48_integration/replay_oracle.py
.venv/bin/python -m unittest discover -s verification/r3_force_path/analysis -p 'test_*.py' -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python verification/r3_force_path/analysis/compare.py --validate-case
.venv/bin/python scripts/check_registry.py --check-git
git lfs fsck
git diff --check
```

R1 проверяет воспроизводимость существующего R5 oracle, не выдаёт это за новую
независимую экспертизу. Обёртка меняет только HERE для выходного файла oracle,
чтобы не перезаписывать исходное evidence R5; результат должен совпасть побайтно.
Не запускать compare.py --write; scoped case и active registry проверяются отдельно.
Проверки реестров занимают несколько минут; дождаться exit status.

Сохранность: `preservation.json`; итог команд/exit status: `validation.json`;
локальные логи рядом. Метаданные GitHub до изменений и PR47 acceptance сохранены
отдельно. CI окончательного head проверяется через GitHub Actions после push;
прежние успешные runs на R3 H не доказывают CI нового head.

Первый запуск реестра при onboarding начат до материализации LFS и обнаружил
пять обращений к pointers. После git lfs install --local / pull / fsck обязательная
проверка повторена; результаты интеграции относятся к материализованным файлам.
Никакие проверки TLS/подписей/checksum не отключались.

WARNING только для условной постановки R4. 42 строки условий не рассчитаны;
реальные реакции/прочность/устойчивость не подтверждены. W02/physical READY
NO-GO, G1 OPEN, архитектура/ТЗ NOT_APPROVED. Общий CAD-rebuild и физические
испытания не выполнялись и не разрешены этим пакетом. Main не сливается.
