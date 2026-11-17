Пользователь задал референтную основу REV: характеристики/сырьё по BP500, адаптация площадки под пресс и релевантное использование других имеющихся руководств. PR52 доставляет предварительный пакет intake R1, предложение claim и независимый акт R5 с решением R1. **Общий WARNING; инженерная пригодность не подтверждена.**

Точные версии:

- Проверенный пакет R1 C `f2cbd96bb78c915dca74cb4eb29daffbb52ee172`, исходный H `411bb36f9559d80caec4e2f870e8120148d9c6a9`.
- Независимый R5 C/H `853a72b63fd8c89a3fa54ac1f309f24e7104f1c4` / `c086c2a497614c193373d58c1b854078cd7accd0`.
- Акт `REV-R5-REFERENCE-INTAKE-REVIEW-01-001`: **1250 PASS / 0 FAIL**, 4 PDF/11 просмотренных страниц, 40 деклараций и квалификаторы проверены. Verdict WARNING_DOCUMENTARY_REFERENCE_ONLY.
- Решение R1: `decisions/R1-REFERENCE-INTAKE-PRELIMINARY-ACCEPTANCE.md`. Полная история сохранена обычным merge; source C и проверенные файлы остаются неизменными.

40 полей остаются scoped RAW; активный registry не меняется. Сохранены 8 supplemental и 8 качественных записей, 21 группа/84 прежних UNKNOWN, 26 intake pins/54 прежних pins, 52 интерфейса/42 исходных состояния, 44 полные bindings/нагрузки/ходы/CAD. Исторические R3/R4/R5 review, OBS-01 exact-C closure, STALE/четыре FAIL и REJECT history сохранены. SOURCE-POWER, SOURCE-PRESSURE-UNIT и влажностная база/метод остаются открытыми; up-to/material-dependent qualifiers сохранены, диапазоны не усреднены.

Уточнение источника: ARS PDF4 §4.6 допускает и неметаллическое сырьё (включая plastic chips/sawdust). Это не доказывает совпадение физических свойств/уставок с BP500/REV. Путь eject на ARS PDF17 также возвращается в retract/reset; не выводить готовую логику PLC/безопасного открытия. R1 сохраняет этот контекст в решении, не переписывая reviewed snapshot.

Claim intake **PROPOSED_PENDING_MAIN**, owner NONE/lease null; предложенный actual R1 owner `6afb300b-1540-8191-a5c4-be1a684c20e0`, исходный proposed deadline **2026-11-17T23:16:47.225017Z**, без продления. Review claim не принимает. Для последующего разрешённого принятия предусмотрена отдельная запись владения, чтобы не менять claim.json из CURRENT artifact manifest; план `verification/r1_reference_intake_acceptance/integration_and_claim_plan.md`. Роль R1 заново не подтверждается, иных сессий/сроков этот PR не назначает. Merge/auto-merge сейчас не выполняются.

**42 состояния не рассчитаны; §4/5/6 NOT_RUN.** Прочность/устойчивость/реальные реакции/цикл не подтверждены. Архитектура/ТЗ NOT_APPROVED, G1 OPEN, W02/physical READY NO-GO. Численный/физический этап, CAD-build/rebuild, физические испытания/изготовление/выпуск не разрешены. Готовые чертежи будущего пресса не требуются от оператора.

Проверки подготовки R1: 1163 PASS, 951 сохранённый baseline-файл; root `registry --check-git` PASS, код 0; `git diff --check` PASS. Оба exact R5 C/H CI прошли registry и по 100 тестов. Финальный CI обновлённого PR head проверяется отдельно.
