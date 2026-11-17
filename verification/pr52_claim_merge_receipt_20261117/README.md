# PR52 — фактическая квитанция merge и принятия claim

PR52 MERGED 2026-11-17T00:54:30Z обычным merge
`a63e27cf1e4579bfe8aa7b78f4dfcabbd6ef6dc3`.
Родители: прежняя main `3353de6c9fc699fbd565f1ce63cebedad3137a12` и exact head
`770b05c9f70be83c8e6a2f9f7f91daeab5f0a1ce`; дерево совпадает с exact head.
C принятия `01a5fe0512769b8863b4fe3948983e5b1c928285`, H — указанный exact head.
20 проверенных исторических C/H — ancestors merge; squash/rebase не применялись.

Прямое разрешение сохранено в verification/pr52_claim_merge_20261117/authorization.json.
Claim T-r1-force-inputs-intake-01 фактически принят в main отдельной записью
coordination/claims/T-r1-force-inputs-intake-01.json; единственный owner
`6afb300b-1540-8191-a5c4-be1a684c20e0` / R1, исходный lease до
`2026-11-17T23:16:47.225017Z`, без продления. Runtime session проверена.
Проверенный proposal `verification/r1_force_inputs_intake/claim.json` остаётся
историческим NONE/null, сохраняя точный manifest CURRENT акта R5. Статус владения
определяется включённым в main live ledger и актуальным временем/конкуренцией.

premerge.json, merge_request/result.json и postmerge.json сохраняют факты GitHub/Git.
Оба CI exact head SUCCESS, registry PASS и по 100 тестов; main CI43991412075
SUCCESS, registry PASS и 100 тестов. CI JSON/выдержки логов сохранены без регенерации
старых доказательств. Первый локальный разбор вывода CI остановился до merge из-за
ожидания TAB непосредственно перед OK; формат содержит timestamp. Проверка
исправлена на фактический конец строки, оба полных лога проверены повторно.
Это ошибка разбора метаданных; CI и инженерные источники не менялись.

verify_receipt.py / postmerge_checks.json: 134 PASS / 0 FAIL. Проверены ancestry,
дерево, effective owner/срок, unchanged reviewed packet/R5 hashes, 27 pins следующей
задачи, 22 исходных REQ/VAL, RAW40, 84/52/42/44 и границы новых файлов. Эти проверки
не являются независимой инженерной верификацией; source WARNING не повышается.
Root registry --check-git отражён отдельно в registry_status.json.

Следующая постановка: coordination/tasks/T-r1-requirements-draft-01/task.md,
task.json, task_input_manifest.json. READY_FOR_CLAIM_REVIEW, owner NONE/lease null,
execution_authorized false. Она описывает будущую документальную DRAFT ревизию
требований/критериев, source disposition и независимый review exact будущего C.
Перед отдельным claim проверить завершение/освобождение текущего intake, исключить
перекрытие владельцем задач и не переносить старый lease. Текущая поставка только
готовит задачу; фактическая ревизия требований не начата.

BP500 первичен; E55/WEIMA/ARS применяются по релевантности. SOURCE-POWER/UNIT OPEN,
влажностная база/метод UNKNOWN, qualifiers сохранены. 44 bindings/нагрузки/ходы/CAD,
активный registry и прежние R3/R4/R5 пакеты неизменны. REJECT/STALE/четыре FAIL и
OBS-01 exact-C closure сохранены. 42 состояния не рассчитаны; §4/5/6 NOT_RUN;
прочность/устойчивость/реальные реакции не подтверждены. Архитектура/ТЗ NOT_APPROVED,
G1 OPEN, W02/physical READY NO-GO. Численный/физический этап, CAD-build/rebuild и
физические испытания не разрешены. Нового разрешения на выпуск не создаётся.

Эта postmerge-поставка опубликована отдельно с C/H; она сохраняет квитанцию
свершившегося PR52 и готовую постановку. Сам merge SHA не пытается ссылаться на
собственную будущую квитанцию. Состояние её интеграции указывается в PR/эстафете.
