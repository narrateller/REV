# R4 → независимый R5: RECHECK R5-CI-B01/B02/B03

Проверить точный новый C, указанный в следующем H/STATE/NEXT_MODEL. Основания:
исходный C ed8272ce6ebc2047bb0d896db5951d02c42d5208 и акт R5
13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2. Авторское исправление не закрывает
B01/B02/B03: все OPEN, задача IN_REVIEW. Авторские сессии r4-linked-20261111
и r4-cyc-fix-20261113 / R4 не выступают независимым reviewer.

Пакет: 53 действия (31 inherited + 22 mechanical), типизированные позы/endpoints,
режимы/parent-связи, cycle_protocol.json, 6 SVG, полная CSV/MD, semantic checker,
44 неизменённые bindings и четыре неизменённых силовых варианта. Доказательства
исправления и команды — ../correction/README.md, checks.json, preservation.json.

Критерии нового независимого акта:

1. Проверить все пять LOAD/REFILL и шесть mode bindings: D0→D1→FILL-CONFIRM→D0,
   parent commit после возврата и отсечение G0→G1 только с адресной квитанцией
   той же дозы/материала/операции и актуальным FEEDER_SAFE. Локальное завершение
   подстадии не требует преждевременного parent completion. Команда, таймер,
   UNKNOWN, чужая/старая квитанция не разрешают продолжение. Отдельно проверить
   MATERIAL/FEED +1 successor после commit исходного helper, invalidation,
   новый REFILL с сохранением того же остатка и запрет молчаливого PF→P0.
2. Проверить положительный путь B: fault → новая адресная recovery operation →
   STOP-CLOSE → RELOCK → текущий closure result → targeted closure fault recovery →
   отдельный RECONCILE_HISTORY → новый NEXT с полными условиями. DEPENDENCY_VALID
   не циклическая предпосылка closure motion, но остаётся у штатных действий.
   Материальные/сервисные причины и rejected operation IDs сохраняются; нарушение
   собственного ledger/resource/retention/sweep блокирует и recovery.
3. Снова экспортировать валидный и семантически повреждённые пакеты. Проверить
   poses/body/path continuity, guards/dependency graph, mode/parent/invariants,
   action/phase/pose refs, все CSV поля и SVG/MD. Свежие hashes не заменяют эти
   проверки. Повторные проверки не пишут и не восстанавливают файлы.
4. Сверить 44 bindings, BASE_A/B fixed-budget, исходные D/d/F/ходы/t/v и четыре
   силовых варианта побайтно. Расчёты/CAD/registry/checked helpers и исходные
   R5 акты/probe не изменены. Ограниченные R3 передачи остаются WARNING;
   четыре варианта не выбраны и не приняты как конструкция.

Исходный независимый probe сохранён неизменным и воспроизведён на исходной
редакции: 1345 checks, 1328 PASS, 17 FAIL. Его старые assertions/schema описывают
ed8272c; новые имена стадий и полная расширенная CSV требуют собственного
независимого RECHECK. Авторские новые регрессии — correction/test_documentary.py;
их успех не выдаётся за независимый вердикт R5.

W02 OPEN/NOT_IMPLEMENTED; executable material и физический READY NO-GO.
Проверенных геометрических пар 0. B opening и физический L INDETERMINATE;
CAD/solver/rebuild/физические испытания NOT_RUN. Архитектура/ТЗ не утверждены,
G1 OPEN. Старый B01 helper C0c4eb5d и его исторические REJECT/R1/RECHECK сохранены.
