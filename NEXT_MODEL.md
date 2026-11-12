# Арбитраж R1 по контракту цикла — ARB-R1-CC-01

PR #44 принят, claim R1 codex-01 до 2026-11-13T22:14:32Z. R1 воспроизвёл все три новых расхождения из R5 `c56e494a2e89ffa65b5876bfce6a4d6b4ae62f1b`, результат совпал с сохранённым независимым JSON. Решение `decisions/ARB-R1-CC-01.md`, evidence `verification/r1_cc_arbitration/`.

Следующее действие: R4 прочитать решение на точном SHA, зафиксировать в капсуле, проверить main/owner/lease/входы и выполнить только корректирующую итерацию B01 с адресными fault records и накопительными rejected operation IDs. Независимый R5 затем проверяет старые и новые последовательные контрпримеры по плану решения. Contract BLOCKED до RECHECK, CYC-02/03 NO-GO; W02 OPEN, G1 OPEN. Расчёты/CAD/rebuild и физические испытания не выполнялись.

## Предыдущая эстафета (история)

# Предложение восстановления R1 и арбитража контракта цикла

Два последовательных REJECT_WITH_BLOCKER по R5-CC-B01: акты `d99afb4c3231d641d4a4921f39987264ce5ffc23` и `c56e494a2e89ffa65b5876bfce6a4d6b4ae62f1b`. По §6.1 новая итерация исправлений остановлена до решения R1; стабильный вход CYC-02/03 NO-GO. В трекере предложен Q-R1-CC-ARBITRATION-01.

Lease R1 истёк, предложено восстановление `codex-01` до 2026-11-13T22:14:32Z; до принятия в main PROPOSED/PENDING_MAIN. После принятия: проверить базу/owner/lease, воспроизвести три расхождения R5 и опубликовать арбитраж с критериями независимого RECHECK. Расчёты/CAD не менять, G1 OPEN; физических испытаний нет.

## Предыдущая эстафета (история)

# R4 — отдельная документальная задача CYC-01 + ранние CYC-08/09

**C предложения `9fdbcd05c863b93c0ddb84f4fe40ac80a2bfe1ff`**, REMOTE, ветка `work-r4/T-r4-cycle-contract-01/r4-linked-20261111`. T-r4-cycle-contract-01 **READY / owner_session NONE / PROPOSED_PENDING_MAIN**. Предлагаемый исполнитель r4-linked-20261111 / Codex / R4, отдельный proposed lease до **2026-11-13T18:16:39Z (13 ноября 2026, 21:16:39 МСК)**. H только учёт/эстафета, claim не принимает.

Main `b1a4e398741b84d482c96f00a605e98b720ff929` содержит принятые PR #42/карту C 43f03359fabe2b664935b17f9ac7851504093ece и акт R5 e69a8afbe4df3d53c4cc8b5883319e00eb8130af. R4 роль подтверждена пользователем, прежний CAD-claim PR #40 до 2026-11-13T13:17:33Z действует, но новый материальный/resource/READY контракт за его пределами; срок/область старого claim не изменены. Решение PR42 требует отдельного принятого назначения R4.

Подготовлены только конкретная постановка/claim и preflight: verification/r4_cycle_contract/task.md, claim.md, preflight.json, checks.json. Закреплены 17 input blobs и 11 защищённых деревьев main плюс точные CAD candidate trees на 3591a5f92f78b1edea07d3fc5354fd0a99090798. Этот CAD не интегрирован/не принят новой документальной работой; declared coordinates/author native/independent native NOT_RUN сохраняются раздельно.

**Сам контракт/черновики/примеры NOT_STARTED**, numerical solvers/CAD/rebuild/physical tests NOT_RUN. Установлена область будущего результата: материальный журнал пуска/столба/остатка A и batch/repeated gather B на одной массовой базе; нет заранее готового продукта/REMOVE без приёма; ранний граф стадий/перекрытий/ресурсов без скрытых нулей и подмены полного цикла временем оси; READY по узлам и материалу; конкретные условные/запрещённые/UNKNOWN переходы и вопросы R2/R3. Ответы/межролевую приёмку не выдумывать, отсутствие физических данных не блокирует саму условную постановку после claim.

Проверки подготовки: registry --check-git PASS, diff --check PASS, защищённые dirs unchanged. Первый check остановился на нематериализованном local LFS источнике Target_object_BP500.pdf из принятого R5; четыре sources/raw PDF материализованы без изменения committed contents, затем check PASS. Это доступ к источникам, не расчёт/CAD или повторный содержательный review PDF.

Следующий шаг координатора/оператора — последовательное принятие **C предложения** в main с owner_session r4-linked-20261111 и ещё действующим явным lease, проверкой конкурирующего owner/входов. Затем R4 fetch/ancestry/main/owner/lease/source hashes, входной акт и выполнение task.md. До принятия содержательная работа не начинается по AGENT_PROTOCOL §4. Не исполнять старую эстафету CAD rebuild и не считать назначение роли принятой блокировкой новой задачи.

CYC-01…09, R5-CYCLE-W01/W02 **OPEN**. Пакет внутренне согласованных draft interfaces не означает принятия физического цикла/контроллера/архитектуры/ТЗ. **G1 OPEN**, B opening/полный физический цикл INDETERMINATE, physical tests NOT_RUN. Main автором не менялась. Капсула handoffs/T-r4-cycle-contract-01/r4-linked-20261111.md; обновлено 2026-11-12T18:26:32Z.

---

## История прежних состояний

# PR #42 подготовлен к отдельной интеграции — ACCEPT_WITH_WARNING

**Code/results подготовки C `8194e3a81de48480391e18d61a9c10073e733536`**, REMOTE. Проверенный инженерно-документальный результат **43f03359fabe2b664935b17f9ac7851504093ece** неизменён. История независимого R5 **e69a8afbe4df3d53c4cc8b5883319e00eb8130af** включена полным предком ветки; файлы/индекс WARNING/CURRENT сохранены. Вердикт акта **ACCEPT_WITH_WARNING** только для документальной карты и условных интерфейсных/исследовательских предложений R4. Отдельный H меняет только эстафету/статус. PR #42 OPEN, слияние автором не выполняется.

[Решение и последовательность CYC](decisions/PR42-CYCLE-TRACE-INTEGRATION.md), [контроль сохранности/проверки](verification/pr42_integration/README.md), [акт R5](verification/r5_r3_cycle_trace_review/review.md). T-r3-cycle-trace-01 IN_REVIEW до отдельного решения оператора об интеграции; owner_session r3-sizing-20261112 / R3 / Codex. Принятый claim PR #41, 7ec621cb8aa306192536df8598e390daf8726b1d — предок актуальной main 65dca013833b64b446157c6faf4042643d909451. Lease до 13 ноября 2026 19:08:52 МСК / 2026-11-13T16:08:52Z без продления; heartbeat 2026-11-12T17:48:14.280536+00:00. Исторические NONE/PROPOSED main нормализованы по факту merge и подтверждению пользователя, нового owner/входов нет. Роль R1 не присвоена.

Разрешённая последовательность будущей условной работы: CYC-01 **вместе с ранними черновиками CYC-08/09** → совместные CYC-02/03 → A:CYC-04 (можно параллельно 03) либо B:CYC-05 → соответствующий CYC-06 после материального/выходного контракта → B:CYC-07 совместно с 05/06 → **окончательная сверка CYC-08/09**. Между ветвями A/B нет обязательного ожидания. Изменённые ходы/нагрузки/передача требуют новой ревизии R3 и review; сейчас расчёт/CAD не меняются.

CYC-01…09, R5-CYCLE-W01/W02 **OPEN**. W01: ранние контракты должны быть согласованы до общего rebuild; ответ/план записан, работа R4 ещё не выполнена. W02: CYC-03/04/07 различают declared coordinates, author native witnesses и independent native NOT_RUN; закрытие CAD-замечания требует отдельной проверки actual FCStd/STEP/solids/ходов/границ. Условная постановка не девять доказанных нативных дефектов.

**CAD-review NOT_AVAILABLE; общий rebuild NOT_READY; полный цикл и открытие B INDETERMINATE.** Fixed-budget — условная база с caps/увеличенными временами, fixed-times — отдельный неутверждённый ресурс. Неизвестные насос/утечки/удержание/aux/одновременность не ноль. Оборудование/архитектура/ТЗ не утверждены, физических испытаний нет, G1 OPEN.

Проверки подготовки: preservation PASS (27 файлов результата, 23 файла нового R5, исходный индекс и все reviewed artifacts, 88 расчётных/45 прежних R5), checksum 26 записей C PASS, trace/render PASS, registry --check-git PASS, diff --check PASS. Программные/геометрические исходники и источники не изменены. CI смотреть для точного опубликованного HEAD; локальный PASS не независимая инженерная приёмка. Старые NOT_RUN/CYC-порядок ниже описывают историю до нового R5; актуальные ограничения/план выше и в решении.

Следующий атомарный шаг: оператор сверяет опубликованный HEAD PR #42/CI и сохранность C/акта, затем отдельно решает о слиянии. После интеграции завершается только документальная область; R4 продолжает в отдельном принятом назначении по последовательности R5. Полная капсула handoffs/T-r3-cycle-trace-01/r3-sizing-20261112.md. Не исполнять прежний запрос повторного OUTPUT-review неизменного C как новое поручение; не повторять расчёты/CAD-исправления из истории.

---

## История до подготовки PR #42

# Сквозная проверка цикла A/B — результат на независимый review

**Code/results C `43f03359fabe2b664935b17f9ac7851504093ece`**, опубликован в ветке `work-r3/T-r3-cycle-trace-01/r3-sizing-20261112`. T-r3-cycle-trace-01 IN_REVIEW; owner_session r3-sizing-20261112 / Codex / R3, claim ACCEPTED_MAIN: C 7ec621cb8aa306192536df8598e390daf8726b1d принят PR #41 в main 65dca013833b64b446157c6faf4042643d909451. Lease до 2026-11-13T16:08:52Z (13 ноября 19:08:52 МСК) не продлён; heartbeat 2026-11-12T16:49:05.882240+00:00. Main повторно получена явно с удалённого refs/heads/main; входы не изменились. H — только статус/эстафета, без изменения результата C.

Готовы [единая таблица 20 цепочек A/B](verification/r3_cycle_trace/cycle_table.md), [девять приоритетных OPEN исправлений R4](verification/r3_cycle_trace/r4_priorities.md), [17 source claims/страницы/схемы/условия](verification/r3_cycle_trace/source_ledger.md). Расчёт c115f75fd900525d9ddc89d85e097ac5a0f00bc1 и CAD 3591a5f92f78b1edea07d3fc5354fd0a99090798 сопоставлены по exact Git blobs; CAD-кандидат остаётся отдельным входом, не принят/не интегрирован этим результатом. Материальные ограничения аналогов сохранены; гипотезы ASSUMED, неизвестное UNKNOWN/null.

До перестройки: материальный контракт/пуск A и повторный набор B → интерфейсы дозатора/затвора/пуансона и силовой путь → удержание A либо разгрузка/отпирание/открытие B → фактическая выдача/приём/ход → RESET B → общий ресурсный граф/READY. Для A SHORT_STROKE текущего surrogate не обосновывает автоматическое удлинение хода на весь канал: сначала определить retained column/выходящий сегмент. Сохранённые penetration/interface/reset отрицательные данные не скрыты; независимый native/BRep replay NOT_RUN.

Проверки C: trace links/14 обязательных ячеек/параметры/координаты/DAG PASS, rendered tables PASS, оба R3 readonly replay PASS, registry --check-git PASS, diff --check PASS. 88 расчётных и 45 review-файлов R5 неизменны; четыре PDF hashes match, CAD/генераторы/registry не изменены. Логи/границы — result_checks.json/result_preservation.json и artifacts.sha256 в verification/r3_cycle_trace/. Новый независимый OUTPUT review **NOT_RUN**; [запрос](verification/r3_cycle_trace/review_request.md). Это авторская документальная проверка, не приёмка физического цикла.

Fixed-budget — условная база с caps и увеличенными временами; fixed-times — отдельный неутверждённый ресурс. Полный цикл и B opening INDETERMINATE, схема/утечки/насос/aux UNKNOWN, не ноль. Архитектура/ТЗ/оборудование не утверждены, физические испытания NOT_RUN, G1 OPEN. Новых исправлений расчёта/геометрии нет; их реализация требует следующего согласования/задачи.

Следующий атомарный шаг: независимый R5 проверяет точный C по review_request.md, самостоятельно сверяет первичные страницы и координатные/материальные/ресурсные выводы; затем координатор согласует входы/интерфейсные предложения R4. Не исполнять старое ожидание claim ниже — это история до принятия. Полная капсула: handoffs/T-r3-cycle-trace-01/r3-sizing-20261112.md. Merge автором не выполняется.

---

## История предыдущих состояний и предложений

# Сквозная проверка цикла — новая задача/claim ожидает принятия

Предложение **C `7ec621cb8aa306192536df8598e390daf8726b1d`**, T-r3-cycle-trace-01; role R3 / Codex, proposed owner r3-sizing-20261112, owner_session NONE, READY / PROPOSED_PENDING_MAIN. Полная конкретная постановка — verification/r3_cycle_trace/task.md, состояние/хэши входов — preflight.json. Предложенный отдельный lease указан в задаче; старые claims R3/R4 не расширены и не продлены.

Main 0353414369e8cffdd7b4289eafd665cc35c0ee36 содержит PR #39 и принятие claim R4 PR #40. Прежнее PENDING в R4 сводках — история до merge, не фактическое состояние принятия. CAD 3591a5f92f78b1edea07d3fc5354fd0a99090798 доступен в отдельной ветке и не включён в main. Сопоставление должно использовать именно этот C, а расчёт — c115f75fd900525d9ddc89d85e097ac5a0f00bc1 и акты R5 PR #39.

Следующий шаг — последовательное принятие нового claim в main оператором/координатором; затем fetch/owner/lease/input audit и выполнение задачи. До этого содержательное чтение первичных инструкций/схем и единая инженерная таблица стадий A/B NOT_STARTED. PDF materialized/hash checked не означает прочтение.

Будущий результат: source page/scheme → решение/условия → REV A/B → параметр → CAD position/stroke → transition proof → gap для всех стадий, плюс приоритеты/конкретные изменения R4 до перестройки и точный C/H для независимого review. Нельзя изменять проверенные расчёты/CAD/registry или объявлять неподтверждённое решение принятым. Контроль: четыре PDF hashes matched, 88 protected files unchanged, registry --check-git/diff --check PASS. Архитектура/ТЗ/оборудование не утверждены, physical tests NOT_RUN, G1 OPEN.

---

## История прежних задач

# R4 после PR #39 — новая задача/claim ожидает принятия

**C предложения `e8ab3272d0fe4b1425779b7d2faac9832562d85d`**, REMOTE, ветка `work-r4/T-r4-calculated-layout-01/r4-linked-20261111`. T-r4-calculated-layout-01 READY / owner_session NONE / PROPOSED_PENDING_MAIN; предлагаемый исполнитель r4-linked-20261111 / Codex / R4, proposed lease до 2026-11-13T13:17:33Z (13 ноября 2026, 16:17:33 МСК). H только учёт/эстафета, не принимает claim и не меняет пакет C.

main `c0053ff7f22fbc10e93efff2691ca6aa1ef90a06` содержит merge PR #39 и прежний исследовательский CAD. Старый claim T-r4-layout-build-01 принят/действовал до 2026-11-12T18:06:24Z; область/срок не расширены. Новые размерные/power входы и новый результат вынесены в отдельную задачу по прямому поручению пользователя. Исторические сводки ниже сохраняются, их слова «PR #39 не merged» не описывают текущую main.

44 строки источников BASE_A/BASE_B fixed-budget в verification/r4_calculated_layout/source_bindings.md/json — **NOT_APPLIED**, не готовый CAD. Точные 30 input blobs/snapshots/code/review refs в input_manifest.json. Оба R3 readonly solver повторены, исходные 80 публикационных файлов CAD/инструмента/доказательств unchanged, registry --check-git и diff --check PASS. Проверенные акты распространяются только на свои входы; новые CAD/геометрические проверки/OUTPUT review NOT_STARTED/NOT_RUN.

Следующий шаг координатора: последовательно принять предложение claim C в main, записать owner_session r4-linked-20261111 и ещё неистёкший срок, проверить отсутствие конкурирующего owner/новых входов; отдельно нормализовать статус принятия. Затем R4 fetch, ancestry/owner/lease/input hashes, входной акт §6 и реализация строго по verification/r4_calculated_layout/task.md. До этого инженерные изменения не начинаются по AGENT_PROTOCOL §4. Капсула handoffs/T-r4-calculated-layout-01/r4-linked-20261111.md.

Будущий результат: отдельные редактируемые A/B, STEP/виды/сечения, фактическая параметрическая таблица до/после с ID@revision/source/status/узлами, полный ход/выдача/возврат/сервисы, новые raw outcomes и независимый R5. Камера/цилиндр/ходы из sizing C 8a1ad4199fea09d1157972d7aa28eaad1e8e0337; t/v только fixed-budget power C c115f75fd900525d9ddc89d85e097ac5a0f00bc1. Не подбирать COTS/крепления/станцию по мощности, не менять размеры ради энергетики; прежние блокировки/UNKNOWN видимы. B opening/L physical INDETERMINATE, реальные REV UNKNOWN, архитектура/ТЗ/COTS не утверждены, испытания NOT_RUN, G1 OPEN.

Git push проверен. gh GraphQL/REST дают Forbidden: PR через API не создан; опубликованная ветка доступна для последовательного принятия предложения. Main не изменялась. Обновлено 2026-11-12T13:22:39Z.

---

## История предыдущих эстафет

# Итог подготовки PR #39

Commit подготовки с обеими историями R5: **bcb2ab470bca87534a5b96c795649e89a083ddc7**. Проверенный расчётный C **c115f75fd900525d9ddc89d85e097ac5a0f00bc1** и исходные сценарии неизменны; оба акта d92cebd5a539d6845fe114515154e79c639bcb7e и 54c918bc82612a38f74056ff8ff5b62632d3a210 входят в историю ветки. Локальные проверки: 100 tests OK, оба readonly replay OK, итоговый registry --check-git PASS, diff --check PASS. Контроль: 88 расчётных и 45 review-файлов идентичны. Подробности verification/pr39_integration/checks.json.

Fixed-budget — условная база с caps/увеличенными временами; fixed-times — отдельный неутверждённый ресурс. Полный цикл/B open INDETERMINATE; оборудование/архитектура/ТЗ не утверждены, G1 OPEN. Задача IN_REVIEW; слияние PR в main не выполнено. Следующее действие — отдельное рассмотрение подготовленного PR оператором/координатором после проверок опубликованного HEAD. Эта H-запись только сообщает commit подготовки; проверенный расчёт не меняет.

---

# PR #39 подготовлен к интеграции — только ограниченная расчётная область

Расчётный C **c115f75fd900525d9ddc89d85e097ac5a0f00bc1** сохранён без изменения проверенных файлов; исходные восемь несовместимых сценариев сохранены. Ветка включает оба независимых акта и историю: OUTPUT d92cebd5a539d6845fe114515154e79c639bcb7e и RECHECK 54c918bc82612a38f74056ff8ff5b62632d3a210. Вердикт RECHECK ACCEPT_WITH_WARNING; W01 CLOSED_IN_LIMITED_NEW_API_SCOPE, W02 CLOSED_FOR_CONDITIONAL_CALCULATION_HANDOFF_ONLY, без подтверждения реальных условий до полного цикла/подбора. Исторические OPEN/исходные verdict не переписаны.

**Fixed-budget** — условная база с явно выбранными непроверенными caps и увеличенными временами. **Fixed-times** — альтернативный расчёт с отдельным **неутверждённым ресурсом питания**, не совместимый со старым бюджетом при этих временах. **Полный цикл и открытие упора B — INDETERMINATE**. Оборудование, архитектура и ТЗ не утверждены, G1 OPEN, физические испытания NOT_RUN.

T-r3-parametric-sizing-01 IN_REVIEW до отдельного решения об интеграции; owner r3-sizing-20261112 / Codex / R3, heartbeat 2026-11-12T12:11:39.421389+00:00. Main 8867521a83bd4608886d81678683ea89cce7e4a3; claim PR #38, lease до 2026-11-13T08:50:42Z без продления. Подготовка по прямому поручению пользователя, полномочия R1/приёмка изделия не заявлены. Контроль сохранности/актов и границы — verification/pr39_integration/README.md, preservation.json; окончательные результаты проверок — checks.json после завершения. Слияние PR #39 в main не выполнялось.

---

## История предыдущих состояний

# Окончательная передача R3: RECHECK W01/W02

**Финальный code/results C `c115f75fd900525d9ddc89d85e097ac5a0f00bc1`**, исходный расчёт 8a1ad4199fea09d1157972d7aa28eaad1e8e0337, акт R5 d92cebd5a539d6845fe114515154e79c639bcb7e. Промежуточный C cca7333618ba587505f7e5b8ffbb64eab3ddee32 дополнен защитой прямого API-вызова с ненулевой утечкой без модели выдержки; численные значения восьми пар согласования не менялись. Для нового RECHECK использовать только финальный C выше.

T-r3-parametric-sizing-01 IN_REVIEW, owner r3-sizing-20261112 / Codex / R3; heartbeat 2026-11-12T09:55:39.184956+00:00. Принятый claim PR #38/main 8867521a83bd4608886d81678683ea89cce7e4a3 и lease до 2026-11-13T08:50:42Z действуют без продления. Исходные восемь несовместимых сценариев сохранены. Новый слой отдельно показывает fixed-budget Q/v/t/T/rate и fixed-times resource/peak/average/energy bounds, с явными непроверенными caps и actual UNKNOWN. Известный дефицит выдержки или неустановленная модель ненулевой утечки блокируют допустимый цикл (null), а не скрываются длительностью движения/cap.

Окончательно: 100 tests OK (14 новых), registry --check-git PASS, четыре readonly пересчёта, 74 файла SHA/size/mtime unchanged. Данные/ответ reviewer/R4 — verification/r3_power_reconcile/, запрос recheck_request.md. W01/W02 OPEN до независимого ограниченного RECHECK; автором не закрыты. B open INDETERMINATE, G1 OPEN; оборудование/архитектура/ТЗ не утверждены, физические испытания NOT_RUN. H — только эстафета/точный запрос, численный C не изменяет.

---

## История промежуточной передачи

# R3: согласование мощности/времени — ограниченный RECHECK W01/W02

T-r3-parametric-sizing-01 IN_REVIEW; owner r3-sizing-20261112 / Codex / R3, heartbeat 2026-11-12T09:49:41.426354+00:00. **Новый code/results C `cca7333618ba587505f7e5b8ffbb64eab3ddee32`**. Исходный C 8a1ad4199fea09d1157972d7aa28eaad1e8e0337 и восемь несовместимых режимов сохранены. Входной R5 d92cebd5a539d6845fe114515154e79c639bcb7e принял исходную арифметику с WARNING; новый слой не принят автоматически. Claim PR #38/main 8867521a83bd4608886d81678683ea89cce7e4a3, lease до 2026-11-13T08:50:42Z действует без продления.

Новый пакет verification/r3_power_reconcile/: два явных варианта fixed-budget/fixed-times, отдельные фазовые Q/v/t и power–duration, T/условная производительность, энергия/средняя/пиковая мощность и UNKNOWN. Три power envelopes — явно выбранные ASSUMED границы, не реальные мощности. Actual hold/full energy/average остаются null без схемы/компонентов; при дефиците выдержки новый API даёт BLOCKED и null допустимый цикл. Старое Tlower заморожено для воспроизведения, не для планирования.

99 tests OK (13 новых), реестр --check-git PASS, git diff --check PASS. По два readonly пересчёта старого/нового слоя идентичны; 68 файлов без изменения SHA/mtime/size. 376 новых CALCULATED scalar outputs, прежние определения/численные результаты сохранены. Новые VERIFIED/LOCKED отсутствуют.

Следующий шаг — независимый ограниченный R5 RECHECK **C** по verification/r3_power_reconcile/recheck_request.md: W01 budget deficit/UNKNOWN/насос на выдержке, W02 оба согласования/ресурс/условные caps, таблицы/R4. Автор W01/W02 не закрывает. После независимого акта — отдельное решение координатора об интеграции. B open INDETERMINATE, реальная whole-machine feasibility UNKNOWN; оборудование/архитектура/ТЗ не утверждены, physical tests NOT_RUN, G1 OPEN. Капсула handoffs/T-r3-parametric-sizing-01/r3-sizing-20261112.md.

---

# Условный расчёт REV — R3, результат на независимой проверке

T-r3-parametric-sizing-01 IN_REVIEW, owner r3-sizing-20261112 / Codex / R3; 2026-11-12T09:08:47.900489+00:00. **Code/results C `8a1ad4199fea09d1157972d7aa28eaad1e8e0337`**; этот последующий H содержит только эстафету/статус/запрос review. Claim `5fdc50bbc8e83241ad2f8754860a503f5de9f418` принят PR #38 на main `8867521a83bd4608886d81678683ea89cce7e4a3`, lease до 2026-11-13T08:50:42Z, не продлён. Исторические NONE/PENDING/NOT_STARTED ниже относятся к состоянию до принятия.

Вход R2 `4fd6f32b4df3186a805ac7e654be6c4c9e1c6a50`, R5 `81e5dba4bb47cf8a552b3eb55733454ac4f9742d` ACCEPT_WITH_WARNING только для исходной базы. Отдельные копии/хэши входов сохранены. Восемь выбранных ASSUMED-сценариев, 696 CALCULATED scalar outputs; реальные UNKNOWN null, новых VERIFIED/LOCKED нет. Камера/доза/ходы, нагрузка, обе полости/направления цилиндра, Q/v/t/P/E, A удержание и B разгрузка/выдача разобраны в verification/r3_parametric_sizing/.

При исходных временах все наборы превышают выбранный электрический бюджет; более длительный бюджет вычислен условно. D/d — нижняя геометрия из заданного отношения штока, не подбор/прочность. B opening и whole-cycle feasibility INDETERMINATE. Полная проверка ПО 86 tests OK, реестр --check-git PASS, два readonly пересчёта идентичны, 34 проверенных файла без изменения SHA/mtime/size. Это не независимый инженерный review.

Следующий шаг: независимый R5 проверяет **C**, не переносит старый акт на новый код; запрос verification/r3_parametric_sizing/review_request.md, результаты/таблицы report.md, formulas model.md, R4 входы r4_inputs.md; капсула handoffs/T-r3-parametric-sizing-01/r3-sizing-20261112.md. После R5 — отдельное решение координатора об интеграции, без самоприёмки. G1 и прежние блокеры OPEN, конкретные цилиндр/насос и архитектура/ТЗ не утверждены, physical tests NOT_RUN.

---

# Ожидает принятия: отдельный claim условного расчёта R3

T-r3-parametric-sizing-01 READY / PROPOSED_PENDING_MAIN; owner_session NONE, proposed owner r3-sizing-20261112 / R3 / Codex. Постановка и claim C `5fdc50bbc8e83241ad2f8754860a503f5de9f418`; main при сверке `680946b8abba9d921c5723b523be573554c15eca`. Входы R2 `4fd6f32b4df3186a805ac7e654be6c4c9e1c6a50`, R5 `81e5dba4bb47cf8a552b3eb55733454ac4f9742d` (ACCEPT_WITH_WARNING) доступны в Git, в main ещё не интегрированы.

Следующий шаг — последовательное принятие claim оператором/координатором в main; затем fetch, проверка вхождения C/owner/lease/конкуренции/входов, входной аудит и расчёт по полной постановке в ISSUES_AND_TASKS.md. Модель/сценарии NOT_STARTED; это не результат для инженерной приёмки. Чужие назначения и сроки не изменены. Подробности: verification/r3_parametric_sizing/claim.md, хэши preflight.json; капсула handoffs/T-r3-parametric-sizing-01/r3-sizing-20261112.md.

G1 OPEN; архитектура/ТЗ и конкретное оборудование не утверждены; физические испытания NOT_RUN. Предыдущие инженерные сводки и handoffs сохранены ниже, текущая запись не отменяет их ограничений.

---

# Сводная интеграция исследовательских компоновок — R1

Финальный C `7d1bd1c92c7cedc4282e3a903463e88205b86fa3`, H `4bde1194a07244445364a1358678d1d07bd99a0c`, RECHECK `05f149332bc173eaa008250e1a5ab21e4d7611cf`. R1 оформил `decisions/R1-RESEARCH-LAYOUT-ACCEPTANCE.md`: предложение принять исследовательский пакет с WARNING после интеграции, не весь пресс. Истории всех исправлений/отказов/проверок сохранены, CAD и отчёты не перегенерированы.

Следующее действие: последовательно интегрировать ветку после проверки актуальной main/owner/lease/входов; затем поставить конкретную задачу реализуемого сервиса дозатора с креплениями, коммуникациями, поддержкой и подъёмом. 6 прямых UP-пар BLOCKED, физический L-путь INDETERMINATE; не скрывать их успешным verifier. G1 OPEN, архитектура/ТЗ не утверждены, физические испытания NOT_RUN.

## Предыдущая эстафета (история)

# Актуальная эстафета — R5-FP-NEW-B01 semantic RECHECK

- HANDOFF / IN_REVIEW; 2026-11-12T03:05:59Z; R4 r4-linked-20261111. **Code/results C `7d1bd1c92c7cedc4282e3a903463e88205b86fa3`**, REMOTE в work-r4/build-layout/r4-linked-20261111. H только учёт/эстафета, проверять неизменяемый C.
- Вход 2592b470940cea886e033a999c889c15a92889f6 по исходному 8fbbef00023e146e32cb6ff290a0c19408ca13b5. Геометрические 14 fixes/L-path остаются ACCEPT_WITH_WARNING в конечной области, новый semantic adapter был REJECT_WITH_BLOCKER. Исправление на независимый RECHECK NOT_RUN, R5-FP-NEW-B01 OPEN, автор не закрывает.
- main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 повторно проверена; accepted claim 79e9c3aa9aaca33778814957fafecd93a4adc392/PR #35/пользователь, owner r4-linked-20261111, lease до 2026-11-12T18:06:24Z (21:06 МСК) без расширения. Исторический NONE/PENDING main координатор сверяет/нормализует перед интеграцией.
- Пять false PASS воспроизведены до изменений; причины каждого в verification/r4_fp_fix/causes.md. Теперь fresh current state/time/participants/plan/whole interval/all-pairs/method/continuity/return связаны с сохранёнными matrices/interval results/classifications/assessment/report. Registered metadata не даёт скрыть solid collision; mandatory sets выводятся из inputs/current scene, все пары сервисов включены.
- Результаты раздельны: execution, test expectation, interval geometry, whole geometric path, overall/physical service. Known collision/confirmed discontinuity/plan-return defect блокируют whole path; unknown method/mandatory condition не дают успех. Исходный L остаётся limited geometry success, физическая пригодность INDETERMINATE. Expected legacy negative PASS не делает путь успешным.
- 110 tests PASS. Тот же independent R5 probe после правки: все 5 verifier exits1, первые 4 BLOCKED/rotation INDETERMINATE, без записи. 25 цепочечных command records и 4 compound/unknown случая; calculation/report/reanalysis CLI тоже отвергают неверные пути. Восстановленные baseline verifier exit0/0, идентичный stdout/stderr, SHA/size/mtime unchanged.
- Все 638919 pair matrices и classifications пересчитаны, 593931 mandatory interval rows сверены по значениям. Исходный набор: 20 CONFIRMED_NO_POSITIVE_VOLUME/2 legacy BLOCKED, общий физический сервис 20 INDETERMINATE/2 BLOCKED. 34 frozen модуля и 46 native/input/scene/classification files byte-identical, 14 static fixes/6 legacy native conflicts сохранены; CAD/STEP не пересохранялись.
- Файлы/команды verification/r4_fp_fix/README.md/final_checks.json, before_counterexamples.json, after/, запрос recheck_request.md. Новые service_semantics/service_evidence/fixtures/tests плюс common/generate/present/verify diff — отдельная область review. Metadata/cached stages не заменяют fresh calculation. Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md.
- Следующий независимый R5: checkout C, materialize LFS, сохранить оригинал, verifier дважды до generation; затем в отдельной копии пять native/unsupported случаев, compounds/time gaps/missing phase/scene/pair/group/return и вся calculation→aggregation→report→verifier→CLI цепочка. Критерий — независимый RECHECK B01 по C; интеграция координатором отдельно, merge не выполнен.
- R4-FP-SERVICE-01 и реальные UNKNOWN сохраняются; архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 OPEN, весь пресс READY INDETERMINATE. C REMOTE.

---

История прежних эстафет ниже:

# Актуальная эстафета — дозатор и гидростанция A/B

- HANDOFF / IN_REVIEW; 2026-11-12T01:34:06Z; R4 r4-linked-20261111. **Code/results C `8fbbef00023e146e32cb6ff290a0c19408ca13b5`**, REMOTE в work-r4/build-layout/r4-linked-20261111. H только учёт/эстафета, проверять неизменяемый C.
- Входы a5d5bad6dd8928045512bca16836fd1d2544b7ca и независимый RECHECK c2e96a58d7efd64ea3364b2bcbfb3f0642bbc430. Старый R5-FRAME-NEW-B01 CLOSED в его области; новый FP результат не принят автоматически, OUTPUT review NOT_RUN.
- main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53, owner_session r4-linked-20261111; claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят PR #35/пользователем, lease до 2026-11-12T18:06:24Z (21:06 МСК) без продления. Scope прежней all-press задачи достаточен; исторический учёт NONE/PENDING main координатор сверяет до интеграции.
- ASSUMED rev8 заморожен до построения на 450e869. 14 статических native penetration пар устранены (collar/doser/hopper mounts и tank/motor A/B); 6 legacy straight-UP doser/hopper пар остаются доказанными BLOCKED и видимыми. Новый side→UP→DOWN→return проверен геометрически, реальный actuator extra stroke/отсоединение/подъём UNKNOWN, actual feasibility INDETERMINATE. Не заявлять устранение всех 20 или принятие legacy UP.
- Дозаторные боковины/лотки/направляющие сохраняют cap UP corridor; motor end-face mounts и tank brackets связаны номинальными faces с frame. Все old ID сохранены, A91/B89. Рабочие doser/punch/rod/cylinder/gate/lock/stop и прежние config/strokes не менялись. 62 новых +58 прежних conditional native interfaces не подтверждают прочность/реальный крепёж/радиальную фиксацию.
- Все 34 прежних checked Python-модуля/old CAD/reviews/probes неизменны. Новые cad/feed_power adapters — отдельный объект review. Actual CAD/STEP/all canonical queries/repeat/edit/reopen/PNG/eight strict cycle expectations PASS; canonical DoserRemoval намеренно остаётся старым BLOCKED UP, новый L-route проверен posed bodies/full intervals, не новым native query.
- 638919 all-pair строк; 507043 critical rows: 506934 no-positive, 97 INDETERMINATE controls, 12 positive legacy UP/DOWN. 878 старых target rows без регрессии; 22 continuous/restored сервиса, 8 новых без positive moving overlap. 102 tests и 18 package-regression случаев/20 команд PASS, 16 faults rejected without auto repair, включая updated-hash сокрытие остатка/evidence. Два readonly verifier идентичны и не изменяют пакет.
- Конечный inventory: 557 non-CLEAR пар, 6 native BLOCKED legacy UP, 2 envelope controls, 15 old-policy synthetic contacts, 534 INDETERMINATE. Условные новые nominal contacts объяснены в interfaces.json без новой разрешающей policy. Весь пресс READY INDETERMINATE, задача не DONE. R4-FP-SERVICE-01 OPEN до реальных service/actuator данных; положительные collision не переименованы в uncertainty.
- Файлы/команды: cad/feed_power/README.md, cad/build/feed_power/assessment.md и A/B, verification/r4_feed_power/README.md/final_checks.json; запрос review_request.md. Полные причины, bounds/ID@revision, native before/after всех 20 пар, виды/FCStd/STEP, classifications/matrices/intervals сохранены. Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md.
- Следующий независимый R5: checkout C, materialize LFS, сохранить оригинал, verifier дважды до генерации; затем separate clone/gen/verify и независимая проверка новых services, стыков, всех шести remaining и regressed groups. Критерий — новый OUTPUT акт в ограниченной области и оценка новых wrappers; интеграция координатором отдельно. Merge не выполнен.
- Реальные параметры/сырьё/физика/безопасность UNKNOWN, условные размеры ASSUMED; архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 OPEN. C REMOTE, 12 новых LFS объектов загружены.

---

История прежних эстафет ниже:

# Актуальная эстафета — RECHECK readonly verifier

- HANDOFF / IN_REVIEW; 2026-11-12T00:36:54Z; R4 r4-linked-20261111. **Code/results C `a5d5bad6dd8928045512bca16836fd1d2544b7ca`**, REMOTE, ветка work-r4/build-layout/r4-linked-20261111. H только эстафета/учёт, проверять неизменяемый C.
- Входной R5 акт `0b4788dd36f811e4acb202b96d6a76a6a06b63ad` принял геометрическую группу C 5198e01 с WARNING, но отклонил новый процесс выпуска: R5-FRAME-NEW-B01 OPEN. Новый независимый RECHECK NOT_RUN, автор не закрывает B01.
- main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 повторно проверена 12 ноября; claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят PR #35/пользователем, owner_session r4-linked-20261111, lease до 2026-11-12T18:06:24Z (21:06 МСК), без продления. Исторический предварительный NONE/PENDING main координатор сверяет до интеграции; scope прежней задачи достаточен для исправления.
- Verifier теперь только читает сохранённые manifest/input/CAD/evidence и выдаёт JSON stdout/exit, без обновления файлов на успехе/отказе. Явный generate.py выполняет полный выпуск/manifest; run.artifacts не захватывает предыдущий manifest или поздние стадии. 23 frozen модуля и геометрический код неизменны, необходимый diff release-кода выделен для RECHECK.
- 95 tests PASS; 18 regression случаев/23 команды: две explicit generation поверх существующего пакета, по два одинаковых readonly verifier и ещё два после восстановления fixtures; 15 missing/corrupt/stale отказов без auto repair. На текущем пакете также два одинаковых verifier PASS с неизменностью всех 92 файлов по байтам/mtime.
- 35 исходных geometry/evidence хэшей и native manifest.objects A79/B77 сохранены. Все 18 устранённых и 20 оставшихся native пар без изменения области; все прочие контакты/неизвестности видимы. Metadata FCStd/STEP/PDF при явном rebuild могут меняться, геометрия и semantic/native repeat неизменны. Whole press READY INDETERMINATE, сборка/задача не приняты.
- Полные команды/результаты verification/r4_frame_fix/README.md, final_checks.json, read_only_repeat.json, unit_tests.json, regressions/. Запрос verification/r4_frame_fix/recheck_request.md; SHA-256 evidence_sha256.json. Артефакты cad/build/frame_mount/, publication_manifest.json версии 2. Исторический final_checks.json в r4_frame_mount сохранён, verifier его не переписывает.
- Следующий независимый R5: checkout C, materialize LFS, сохранить оригинал, проверить опубликованный пакет дважды ДО генерации. Затем в отдельной копии explicit generate/двойной verifier/fault cases, сверить DAG, CAD/все QueryVolumes, сохранность исходного evidence. Критерий — независимый RECHECK B01, затем отдельное решение координатора об интеграции. Merge не выполнялся.
- Размеры ASSUMED, реальные параметры/физика/безопасность UNKNOWN; архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 OPEN. Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md.

---

История прежних эстафет ниже:

# Актуальная эстафета — рамная/монтажная геометрия A/B

- HANDOFF / IN_REVIEW; 2026-11-11T22:56:14Z; R4 r4-linked-20261111. **Code/results C: 5198e0184b35978701ed1ce762d9e4fcd44997b3**, ветка work-r4/build-layout/r4-linked-20261111, REMOTE. H — только эстафета, проверять неизменяемый C.
- Входы: базовый C 66924aed1cb2d193b9883d2140d85560b1e4b0cb, независимый акт 04efe5703e339112b7d007665b9f3672f0572d37 (R5-LAYOUT-NEW-B01/B02 CLOSED в прежней проверенной области). Новый геометрический результат/дополнительный код НЕ принят, независимый OUTPUT review NOT_RUN.
- main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 проверена fetch до работы и публикации; claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят PR #35 и подтверждён пользователем, owner_session r4-linked-20261111, lease до 2026-11-12T18:06:24Z без продления. Новая коррекция внутри исходного scope. Историческое предварительное NONE/PENDING main координатор сверяет/устраняет перед интеграцией, история сохранена.
- ASSUMED input rev7 зафиксирован на 17501de до построения. Исправлена связная группа поперечин/рельсов/опор цилиндра/выходной опоры, открытый U-коридор, добавлены верхние стойки. Все прежние ID сохранены, A79/B77. 18 прежде положительных native пар стали zero volume; 58 условных сопряжений с положительной площадью native граней. Крепёж/силовая способность/радиальная фиксация UNKNOWN, не принимать геометрический граф за расчёт силы.
- Все 23 прежних reviewed Python-модуля неизменны; новые cad/frame_mount scripts/reporting требуют отдельного review. Сохранены прежние CAD/input/results/акты/probes. Actual FCStd/STEP/все QueryVolumes, повтор/edit/reopen/recompute, 83 прежних+5 новых тестов и 8 strict limited outcomes PASS. Восемь сцен не доказывают готовность пресса.
- 346709 all-pair строк с полным покрытием. Новая группа 114156 строк без положительного объёма и 28 INDETERMINATE unknown-control. 658 прежних target строк без регрессии; старые R5 native witnesses и 187 secondary control строк повторены. Цилиндровый сервис 3672 строки без положительного перекрытия; 14 сервисных последовательностей continuous/restored. Дозаторный сервис остаётся BLOCKED.
- Конечный реестр после: 463 непустых пары, включая 20 native penetration пар OPEN, 73 условных сопряжения, 2 оболочечных пересечения и 368 INDETERMINATE. Остались монтаж дозатора/кармана/бункера, извлечение дозатора, бак/мотор и неизвестные сопряжения/крепления/доступы. Весь пресс BLOCKED остаточными проникновениями, READY INDETERMINATE.
- Файлы/команды: cad/frame_mount/README.md; cad/build/frame_mount/assessment.md и inventory/, FCStd/STEP/PNG/SVG/PDF A/B, четыре before/after вида; verification/r4_frame_mount/final_checks.json. Хэши publication_manifest.json, обзор входа input_audit.md. Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md.
- Следующая роль — независимый R5, не автор. Checkout C/materialize LFS/сохранить исходную копию/сверить hashes, затем cad/frame_mount/review_request.md: самостоятельная проверка полного хода/возврата/сервиса, native face interfaces, остатка и новых supplementary scripts. Критерий — новый независимый OUTPUT акт; задача не DONE. Интеграция координатором отдельно, merge не выполнялся.
- Размеры ASSUMED, реальные параметры REV/физическая работоспособность/безопасность UNKNOWN. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. C REMOTE, 12 новых LFS объектов загружены.

---

История прежних эстафет ниже, не текущий статус:

# Актуальная эстафета — RECHECK новой аналитики

- HANDOFF / IN_REVIEW; 2026-11-11T21:37:52Z, R4 r4-linked-20261111. REV, https://github.com/narrateller/REV, ветка work-r4/build-layout/r4-linked-20261111.
- **Code/results C: 66924aed1cb2d193b9883d2140d85560b1e4b0cb**. Входной акт REV-R5-LAYOUT-CORRECTION-01-001 на 04b9f2950a34492b15e1d7c893f680b82f9183b9; исходный C 120a9582f4835e81cdf324605a14f632ce7db2cb. H содержит только эстафету/учёт/запрос review, не заменяет C.
- Исправления R5-LAYOUT-NEW-B01/B02 представлены, **оба OPEN** до независимого RECHECK. Новый classifier проверяет motion/точные входы/полное SUPPORTED evidence до CLEAR; unsupported/unknown дают INDETERMINATE с причиной/NOT_ESTABLISHED coverage. Доказанный дефект другой пары сохраняется при UNKNOWN.
- Sufficient требует actual/reported LINK_CONFIRMED, разрешённый переход, непрерывность/lifecycle/обязательные RETURN/RESET/READY-RETURNED и восстановленный limited READY; criterion не ослаблен. verify_output имеет отдельные raw-scene assertions без вызова oracle outcomes.py. Командное execution, test_evaluation и geometric_scene_outcome раздельны; отрицательный test PASS не означает READY.
- Штатные команды `/usr/bin/python3 cad/layout_correction/run_revision.py` и затем `/usr/bin/python3 cad/layout_correction/verify_output.py`: exit 0, 10 subprocess commands exit 0, 83 unit tests, 15 classifier и 40 cycle regressions PASS. Sufficient success только для A/B, short/collision/unknown остаются BLOCKED/INDETERMINATE.
- Полный unlinked CAD контрпример исходного R5 повторён с его evidence/unlinked_inputs.json через --inputs и отдельный --out: CAD builds/checker exit 0, обе новые CLI exit 1, sufficient A/B LINK_ABSENT/BLOCKED/limited_cycle_success=false. Это PASS ожидания отказа, не sufficient. Полные отрицательные команды/run/verify/outcomes/logs — verification/r4_analysis_fix/negative_full_*.
- Геометрия, ASSUMED inputs rev6 и 15 checked-tool файлов de377f0 неизменны. Все native manifest.objects и 8 PNG совпали с C 120a958; raw operating/service geometry evidence и before_after_native совпали по hash. Повтор R5 geometry_probe: 251923 строк без пропусков/дубликатов, 618 target rows/58 native checks без положительных проникновений, 12 сервисов непрерывны/восстановлены. Остальные frame/mount/powerpack/service проникновения и UNKNOWN сохранены, весь пресс READY INDETERMINATE.
- Результаты cad/build/layout_correction/run.json, assessment.json/md, regressions/*.json, classifications.jsonl.gz и raw_checked_tool/. Read-only final checks verification/r4_layout_correction/final_checks.json; geometry/negative preservation evidence verification/r4_analysis_fix/. Навигация cad/layout_correction/README.md, запрос review_request.md. Старые R5 probes с ошибочными assertions сохранены; не использовать их исходный PASS как критерий исправления.
- main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53/claim/owner/lease проверены перед C. owner r4-linked-20261111, claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят PR #35/подтверждён пользователем; lease до 2026-11-12T18:06:24Z не продлён. Исторические NONE/PENDING main и рабочая нормализация требуют последовательной сверки координатором перед интеграцией, не меняют поручение текущей коррекции.
- Следующая подходящая роль — независимый R5 (не автор). Первый шаг: checkout C, materialize LFS, сохранить исходную копию/сверить hashes; прочитать входной акт verification/r4_analysis_fix/input_audit.md, R5 review и README/assessment. Воспроизвести штатные команды, полный unlinked контрпример с ожидаемыми nonzero и собственные составные случаи unsupported/unknown + definite defect, link/return/lifecycle.
- Критерий — независимый RECHECK B01/B02 на новом C; новый акт NOT_RUN. Положительная целевая геометрическая проверка C 120a958 сохраняется, весь пресс не принят. Роль/профильная квалификация/физическая применимость не подтверждаются самопроверкой. Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md.
- Реальные параметры/работоспособность/безопасность UNKNOWN, условные числа ASSUMED отдельно. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. C/H публикуются в рабочей ветке без слияния, C REMOTE, запрос независимого RECHECK опубликован в рабочей ветке, merge не выполнялся.

---

История предыдущих эстафет (не текущий статус review):

# Актуальная эстафета — исправление геометрии A/B

- HANDOFF / IN_REVIEW; 2026-11-11T20:34:47Z; R4 r4-linked-20261111. REV, https://github.com/narrateller/REV, ветка work-r4/build-layout/r4-linked-20261111.
- **Code/results C: 120a9582f4835e81cdf324605a14f632ce7db2cb**. Входной акт REV-R5-QUERY-VOLUMES-01-001 на 214b055f04d5b061a68dfd744afb6c956ac9a9d1, checked tool de377f012da08f34796b2e59aee663ba0b2b3d2b. Следующий H — только эстафета/учёт; проверять C.
- Принятый claim T-r4-layout-build-01 охватывает корректировку ещё не принятой компоновки, новая задача не требуется: исходный scope — все узлы, геометрия, движения/сервисы A/B. Main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 сверена до C; owner r4-linked-20261111, claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят PR #35/пользователем, lease до 2026-11-12T18:06:24Z не расширен. Перед интеграцией координатору устранить известный исторический NONE/PENDING main по принятому основанию.
- Устранены целевые positive-volume inlet_gate/pocket_R A/B и lock/end_stop/guard/support B: явный слот и закрытый retract-карман, две опорные стойки с выходным окном/перемычкой, расширенный lock, перенос полной панели guard за ход/гидроагрегат. Исходные ID не удалялись, тела 65→70 A и 61→68 B. Новый отдельный ASSUMED input rev6; реальные параметры UNKNOWN.
- **Все 15 checked-tool файлов неизменны**; старые входы/CAD/results/reviews сохранены. Новые run_revision/assess/verify_output и политика face-touch — отдельный объект независимого review, не наследуют акт инструмента. Raw COLLISION не удалены/не ослаблены; source_commit_inputs/known_native_penetrations/tool_blockers строки frozen checker исторические, новая provenance в run.json.
- Запуск: `/usr/bin/python3 cad/layout_correction/run_revision.py`, затем `/usr/bin/python3 cad/layout_correction/verify_output.py`. 73 прежних + 6 новых tests, 8 limited outcomes, native CAD/STEP/query/repeat PASS. Все 10 subprocess commands exit 0. 130453 рабочих и 121470 сервисных строк; 618 целевых строк без strict penetration и все 6 прежних native witnesses стали zero volume. 12 сервисных последовательностей непрерывны и возвращают позиции; новые gate/lock/end_stop/portal не пересекают движущимися телами препятствия.
- Дополнительная самопроверка: 216 строк двух введённых design-контрпримеров (guard/pump_motor и bridge/output_support) дают CLEAR/обоснованное exact zero-volume face touch; положительных/envelope пересечений с добавленными телами нет. Два пробных размещения и ранняя ошибка нового анализатора сохранены в history. Подающее окно открыто/перекрыто по нужной фазе, условная реакционная цепь B до рамы имеет positive-area face-contact; силы/прочность/реальная подача/выдача/безопасность UNKNOWN.
- Остальные контакты классифицированы явно: conditional synthetic touch, penetration, native penetration witness, envelope intersection или INDETERMINATE; ничто не исключается из raw матрицы. Рамные/mount/powerpack и старые сервисные дефекты сохранены. **Весь пресс не принят, READY INDETERMINATE**. Геометрические результаты limited path не заменяют всю сборку.
- Результаты: cad/build/layout_correction/A,B (FCStd/STEP/PNG/SVG/PDF), gate_before_after.svg, stop_before_after.svg, assessment.md/json, classifications.jsonl.gz, service_scenes.json.gz, raw_checked_tool/. Команды/hashes run.json, последующие проверки verification/r4_layout_correction/final_checks.json. Навигация cad/layout_correction/README.md, причины/параметры change_inputs.json и changes.json.
- Следующая подходящая роль — независимый R5, не автор; профильные входы R2/R3/R6 по реальным силам/подаче/обслуживанию UNKNOWN, не приписывать их проверку. Первое действие: checkout C, materialize LFS, сохранить исходную копию/сверить hashes, прочитать input_audit/frozen_tool, новый README/assessment и R5 акт; воспроизвести обе команды, независимо проверить весь ход/return/services, отсутствие новых вторичных проникновений, обоснование face-touch и новый анализатор.
- Критерий — независимый OUTPUT review геометрии и отдельная оценка нового кода/политики. Review NOT_RUN, задача не DONE. Инструментальные B01/B02 CLOSED лишь в прежних областях; не переоткрываются без основания. Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md, запрос cad/layout_correction/review_request.md.
- Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. C/H публикуются в рабочей ветке без слияния; C REMOTE, запрос независимого review cad/layout_correction/review_request.md опубликован в рабочей ветке; merge не выполнялся.

---

История предыдущих передач ниже, не текущее поручение.

# Актуальная эстафета — B02 QueryVolumes

- HANDOFF / IN_REVIEW; 2026-11-11T19:31:43Z; R4 r4-linked-20261111. REV, https://github.com/narrateller/REV, ветка work-r4/build-layout/r4-linked-20261111.
- **Code/results C: de377f012da08f34796b2e59aee663ba0b2b3d2b**. Предыдущий C 5449fb9bc4c20fcbc40fdec932876dcecc90ef4d; входной независимый акт REV-R5-CAD-TOOL-FIX-01-001 на 8f381c4b080d902cb023429c54d518bfd6fab681. Последующий H — эстафета/учёт, не замена C.
- B01 CLOSED независимым R5 в проверенной области на 5449fb9; его код не изменён, оснований переоткрытия нет. **B02 OPEN** до независимого RECHECK нового C. Исправление не означает приёмку инструмента или компоновок.
- Исправлены canonical registry и нативная проверка всех QueryVolumes A/B: CylinderRemoval/DoserRemoval, размеры/форма, локальное и глобальное положение, Role. Manifest не определяет ожидания. Подменённые/удалённые/пустые/неописанные зоны запрещают CAD PASS даже после обновления hash; CLI даёт FAILED/NOT_RUN и ненулевой код. Результат каждой зоны с source IDs — cad/build/research_layout/checks/report.json.
- Команда `/usr/bin/python3 cad/layout/run_all.py`: все 14 дочерних команд exit 0. 73 unit tests, 64 QueryVolumes-negative (60 обновлённых hashes), прежние 14 CAD-negative и 33 lifecycle, 20 независимых lifecycle-regressions R5, 8 limited outcomes PASS. Полные результаты/source/artifact hashes — validation.json и checks/*.json, оценка assessment.md; описание/отдельные команды cad/layout/BUILD_README.md.
- Геометрия всех четырёх зон сверена с actual-файлами C 5449fb9 и не изменена. build_model/ASSUMED input/manifest.objects, PNG, все 107486 записей фаз/пар и 556 сервисных результатов сохранены. Нативные проникновения R5 повторились: статически 17 положительных A и 18 B, прежние промежуточные случаи совпали. Полная сборка BLOCKED_ASSUMED_INTERFERENCES, READY INDETERMINATE; ограниченный путь не разрешает весь пресс.
- Перед работой и C свежая main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53, claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят PR #35/подтверждён пользователем, owner r4-linked-20261111, lease до 2026-11-12T18:06:24Z. Известное расхождение предварительных NONE/PENDING main и нормализации рабочей ветки сохранено с основанием; координатор сверяет его перед интеграцией, срок не расширяется.
- Следующая подходящая роль — независимый R5, не автор. Первый атомарный шаг: checkout точного C, git lfs pull, сверить hashes/сохранить исходную копию; прочитать входной акт verification/r4_query_volume_fix/input_audit.md, R5 акт, README и assessment; воспроизвести run_all, независимо повторить Q01 и остальные подмены зон. Старый cad_probe.py на 8f381c4 содержит Q01 assertion ошибочного PASS; его успешный запуск до правки сохранён как baseline_cad_probe.json, это не критерий исправления.
- Критерий — независимый RECHECK B02 на C; B01 не переоткрывать без нового основания. Новый акт NOT_RUN, замечания компоновок/безопасности не закрыты. Все независимые review/probes/evidence сохранены. Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md; запрос cad/layout/output_review_request.md.
- Реальные параметры REV UNKNOWN, условные ASSUMED отдельно. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Рабочая ветка C/H публикуется без слияния; C REMOTE, запрос независимого RECHECK B02 сохранён в cad/layout/output_review_request.md, слияние не выполнялось.

---

История предыдущих эстафет, не текущее поручение:

# Актуальная эстафета — RECHECK инструмента компоновки

- HANDOFF / IN_REVIEW; 2026-11-11T19:07:56Z; автор R4 r4-linked-20261111. REV, https://github.com/narrateller/REV, ветка work-r4/build-layout/r4-linked-20261111.
- **Новый code/results C: 5449fb9bc4c20fcbc40fdec932876dcecc90ef4d**. Исходный C 6bb66a566719593a59935e341b1b5c80a1cbc9a7, входной R5 акт REV-R5-LAYOUT-BUILD-01-001 e939b41d0139b0a3a08a5950eeeec6e92324cf9b сохранены. Последующий H — только эстафета, не заменяет C.
- main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 повторно сверена перед C. Владелец r4-linked-20261111, claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят PR #35 и пользователем, lease до 2026-11-12T18:06:24Z, не продлён. Предварительные NONE/PENDING в main остаются расхождением учёта, нормализованным в рабочей ветке по принятому основанию; координатор должен сверить/устранить его перед интеграцией.
- Исправлено: каждое событие lifecycle проверяется, преждевременный REMOVE удерживает изделие и блокирует переход; CREATE/SPLIT не применяются и не дают успеха. CAD PASS теперь требует actual FCStd/STEP, совпадающих hashes и нативной сверки состава/форм; manifest-only, повреждённый/изменённый CAD или native failure дают явный FAILED. R5-CAD-TOOL-B01/B02 остаются OPEN до независимого RECHECK, автор не объявляет закрытие.
- Команда: `/usr/bin/python3 cad/layout/run_all.py`. Все 12 дочерних команд exit 0; 69 unit tests, 33 lifecycle-контрпримера и 14 CAD-negative случаев, 8 ограниченных исходов A/B PASS. Команды/exit codes/hashes в cad/build/research_layout/validation.json, фактическая оценка assessment.md, новые regressions/geometry/native evidence в checks/. Навигация: cad/layout/BUILD_README.md.
- Геометрия не исправлялась: build_model.py/ASSUMED JSON/manifest.objects и 8 PNG неизменны; все 107486 записей фаз/пар идентичны исходному C. 556 сервисных результатов сохранены. Нативные пробы R5 повторены и подтвердили прежние проникновения: статически 17 положительных common volumes A, 18 B, все прежние промежуточные свидетельства. Полная сборка имеет BLOCKED_ASSUMED_INTERFERENCES, READY=INDETERMINATE. 8 ограниченных исходов не означают готовность пресса.
- Следующая подходящая роль — независимый R5 (не автор R4), при необходимости профильные входы R2/R3/R6. Первое действие: checkout C, материализовать LFS, сверить исходные hashes и сохранить копию результатов до перезапуска. Прочитать входной акт verification/r4_layout_tool_fix/input_audit.md, R5 review, README/assessment; воспроизвести run_all и независимо повторить B01/B02 и отрицательные случаи. Оригинальный adapter_probe.py фиксирует ошибочное поведение: его прежние assertions не являются критерием исправления. Исходные review/probes/evidence сохранены без редактирования.
- Критерий следующего шага — собственный независимый RECHECK на точный C. Новый review NOT_RUN, задача не принята; геометрические пересечения требуют отдельной последующей задачи/решения, не разрешаются исправлением инструмента.
- Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md. Реальные параметры REV UNKNOWN, условные значения ASSUMED отдельно. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN, G1 открыт. Публикация C/H в рабочей ветке без слияния; C REMOTE, 12 новых LFS-объектов загружены; запрос RECHECK в cad/layout/output_review_request.md, merge не выполнялся.

---

История предыдущей передачи ниже, не текущее поручение.

# Актуальная эстафета — исследовательские компоновки A/B

- Состояние HANDOFF / IN_REVIEW; UTC 2026-11-11T18:33:56Z; автор R4 / r4-linked-20261111.
- Проект REV, https://github.com/narrateller/REV; ветка `work-r4/build-layout/r4-linked-20261111`. **Code/results C: 6bb66a566719593a59935e341b1b5c80a1cbc9a7**. H содержит только эстафету/учёт, не заменяет этот C для проверки.
- T-r4-layout-build-01: claim 79e9c3aa9aaca33778814957fafecd93a4adc392 принят PR #35 на main 06d68b0ce9c7d0c0ec3b6a66b917098ec9730b53 и подтверждён пользователем. owner_session r4-linked-20261111, lease до 2026-11-12T18:06:24Z; срок не продлён. Предварительные NONE/PENDING в принятом тексте main исправлены в рабочем трекере по основанию принятия; история предложений сохранена.
- Построены отдельные редактируемые FreeCAD A/B, STEP, общие виды PNG/SVG/PDF, сечение, фазовые схемы и схема силового пути. Команда: `/usr/bin/python3 cad/layout/run_all.py`. Навигация/инструменты: cad/layout/BUILD_README.md; фактическая оценка: cad/build/research_layout/assessment.md; воспроизводимость/команды: validation.json; полный JSON всех пар с gzip в checks/.
- Самопроверка: 60 тестов, 8 ограниченных исходов A/B, reopen/recompute/edit probe, STEP и чистый семантический повтор PASS. 107486 полных записей пар и 556 сервисных. **Полная установка имеет условные пересечения и whole_assembly_ready=INDETERMINATE**; ограниченный путь не доказывает работоспособность всего пресса. Реальная физика/безопасность UNKNOWN.
- Входы: неизменённый model_build_task.md/шаблон из пакета 2c6743d39b59e38d85d21684059b4f4afd1ca248; review предыдущей постановки REV-R5-LAYOUT-01-001 на a621f466aac7c31e7812b91ab84c327157411fbc (WARNING). ASSUMED-числа зафиксированы до применения на 4865fbfabf861a7c856a2f61300e2a9fc4ab0872 и 6db54ea4168e83118de70144e2fd08c8750b5d6c; метаданные без изменения чисел на 0d587fa (полный SHA в отчёте). Реальный registry/COTS и проверенные models/ неизменны.
- Следующая подходящая роль — независимый R5 с входами R2/R3/R6; это предложение review, не назначение и не самоприёмка. Прежний акт не проверял новые CAD/адаптер. W01–W03 автором не закрыты, новый OUTPUT review NOT_RUN.
- Первый атомарный шаг reviewer: checkout точного C, `git lfs pull`, прочитать аудит/задание/README/assessment, сверить hashes, выполнить команду воспроизведения и проверить полноту матриц, границы метода и отображение непроверенных условий. Критерий — собственный независимый акт на C; при отсутствии данных сохранять INDETERMINATE. Архитектура/ТЗ не утверждены, физические пробы/испытания NOT_RUN, G1 открыт.
- Капсула: handoffs/T-r4-layout-build-01/r4-linked-20261111.md. Публикация C/H — рабочая ветка для review, без слияния; доступность C REMOTE, все 12 новых LFS-объектов загружены. Draft PR не создан: GitHub GraphQL API Forbidden; текст cad/layout/output_review_request.md, ссылка создания https://github.com/narrateller/REV/pull/new/work-r4/build-layout/r4-linked-20261111 .

---

Исторические эстафеты ниже сохранены; не выполнять их как текущее поручение.

# Подготовительный PR W01/W02/W03 и claim построения

- C подготовительного пакета/предложения claim: 79e9c3aa9aaca33778814957fafecd93a4adc392; ветка work-r4/prepare-layout-build/r4-linked-20261111; база main c00c75dda08889c3e19169476051b3e6980be721.
- История WARNING review REV-R5-LAYOUT-01-001 a621f466aac7c31e7812b91ab84c327157411fbc включена fast-forward. Новая редакция постановки помечает старый review STALE для изменённого текста, исходный проверенный SHA/вердикт сохранены. Ответы — cad/layout/preparation_review_response.md; manifest рядом.
- W01: передача предварительно после дробления/просева, проверка включений и возможная допподготовка — существующая линия, выход — выход пресса. Неподтверждённые характеристики, транспорт/буфер UNKNOWN. W02: учёт принятого claim постановки PR #34 исправляется этим PR, история и основание сохранены. W03: cad/layout/model_build_task.md задаёт FreeCAD, .FCStd/STEP/виды, состав/базы, отдельный template conditional inputs и будущие команды/проверки.
- Новая задача T-r4-layout-build-01 READY; claim PROPOSED/PENDING_MAIN, proposed_owner r4-linked-20261111. Срок в трекере и капсуле. До принятия отдельного claim в main построение и код build/check NOT_STARTED. Условные значения назначать после принятия, до применения фиксировать отдельный ASSUMED-реестр; реальные параметры REV UNKNOWN.
- Ветка опубликована БЕЗ слияния; gh pr create получил GitHub API Forbidden, PR НЕ СОЗДАН. Текст для одного подготовительного PR сохранён в cad/layout/preparatory_pr.md. После review/принятия PR повторно проверить main/owner/lease/входы и оформить входной акт. Прежний принятый claim постановки сам по себе не разрешает построение.
- Проверки: check_registry.py --check-git и git diff --check PASS; импорт FreeCAD 1.0.0/Part через системный Python 3.13.5 проверен без документов/геометрии; native freecadcmd падает, выбран путь через Python. Сам build/reopen/export ещё не проверен и выполняется только после принятия claim.
- Капсула handoffs/T-r4-layout-build-01/r4-linked-20261111.md. Архитектура/ТЗ не утверждены, физические испытания NOT_RUN; G1 открыт.

## Предыдущая эстафета (история)

# OUTPUT-review постановки компоновки всего пресса

R5 / Codex / session `01a1c552-4e0c-75cf-86ba-2922ccdb30f3` проверил `cad/layout/whole_press_layout_brief.md` на `32481da99f436d260e9af6f0bcc9b0979b952cff`; акт `verification/r5_whole_press_layout_review/review.md`, вердикт WARNING. Текущая сессия не автор документа, но ранее как R1 участвовала в разработке части его входов; организационная независимость и квалификация не удостоверены.

Условную исследовательскую компоновку A/B можно передать R4 после фиксации её отдельной задачи, условий и claim; реальные параметры, безопасность и архитектура не подтверждены. W01 — уточнить предварительные ориентиры оператора; W02 — сверить и последовательно исправить учёт принятого claim; W03 — определить воспроизводимый условный набор до новой модели. Сверить актуальную main, входы, владельца и срок; G1 OPEN, CAD и физические испытания этим review NOT_RUN.

## Предыдущая эстафета (история)

# Независимая проверка постановки всего пресса — T-r4-layout-01

- Документальный результат C: 32481da99f436d260e9af6f0bcc9b0979b952cff; ветка work-r4/whole-press-layout/r4-linked-20261111; автор R4 / r4-linked-20261111. Файл cad/layout/whole_press_layout_brief.md, SHA-256 30175b4865bfe977436f2dbe888b466bfc090d14af1d632c39b3aede87d8a0c4; входной manifest, аудит и self-check в той же папке.
- Claim 1683e24d3be2dfcf8ac91eda102e4d376c834d80 принят PR #34 на main c00c75dda08889c3e19169476051b3e6980be721; пользователь подтвердил принятие, owner r4-linked-20261111, lease до 2026-11-12T17:43:20Z. В принятом предложении остались предварительные PENDING/NONE; в рабочей записи они исправлены с явным основанием, без расширения срока/области.
- Область результата: постановка будущей параметрической компоновки всего пресса A (канал/зажим) и B (закрытая камера/выталкивание). Узлы/интерфейсы, необходимые размеры/ходы/положения/нагрузки, силовые цепи и проверки всего диапазона; источники существующих сведений отделены от данных оператора/будущих опытов.
- Независимый OUTPUT-review NOT_RUN. Передать R5 и профильным R1/R2/R3/R6 по протоколу; reviewer не автор документа. Проверить каждую таблицу и ограничения, достаточность входов и происхождение, отсутствие переноса synthetic значений, открытые интерфейсы затвора/зажима/упора/замка/цилиндра/рамы и сервисные зоны.
- Повторяемые документальные проверки: python3 scripts/check_registry.py --check-git; git diff --check; input_manifest.json сверять с Git blobs указанной базы. Эти команды PASS, но не являются независимым инженерным review. Код/registry/COTS и прежние synthetic результаты не изменены.
- Никакой CAD/физический расчёт/пробы/испытания не выполнялись. Все реальные размеры, ходы, нагрузки и свойства сырья UNKNOWN. Архитектура/ТЗ не утверждены; G1 открыт. Капсула handoffs/T-r4-layout-01/r4-linked-20261111.md; задача IN_REVIEW, не DONE.

## Предыдущая эстафета (история)

# Предложение отдельного claim R4 — постановка всего пресса A/B

- T-r4-layout-01 READY; claim PROPOSED / PENDING_MAIN; proposed_owner r4-linked-20261111 / R4. Принятый owner новой задачи NONE, проектная работа NOT_STARTED.
- C предложения 1683e24d3be2dfcf8ac91eda102e4d376c834d80; база main b2d13541225ceb092559747443ec351ecfd0ef84 после PR #33; ветка work-r4/claim-whole-press-layout/r4-linked-20261111. Срок предложения и точные входы — в ISSUES_AND_TASKS.md, T-r4-layout-01.
- Прежний claim T-r4-linked-01 касается только synthetic AABB и не покрывает компоновку всего пресса. Новая задача не переоткрывает и не продлевает прежнюю.
- Следующий шаг: последовательное принятие отдельного claim в main, проверка owner/lease/конкуренции/входов, входной акт R4; только затем документальная постановка обоих вариантов с узлами, интерфейсами, необходимыми размерами/ходами/положениями/нагрузками и источниками данных для будущей компоновки.
- Численные значения и реальные свойства сырья UNKNOWN; synthetic-геометрия не является конструкцией REV. Архитектура не выбрана, ТЗ не утверждено, пробы/испытания NOT_RUN, G1 открыт. Капсула handoffs/T-r4-layout-01/r4-linked-20261111.md.

## Предыдущая эстафета (история)

# T-r4-linked-01 — предложение ограниченной приёмки

R1 оформил `verification/r4_linked_scene_r1_disposition.md` по коду/результатам `8896d70983648ccd33c0f861c9bc9d28327ff9eb`, RECHECK `82d60717ed9621af7f9fee4e57135d12f22cfc32` и документальной правке README `4ebf47a5f6f96708a65653acaf0cebeee1b84c26`. Предлагается принять после интеграции только в проверенной synthetic-области с WARNING; до слияния IN_REVIEW. R5-LINKED-FIX-W01 OPEN до независимой сверки README.

Следующее действие: последовательно интегрировать результат и обе истории проверок после сверки main, владельца, срока и входов. После слияния зафиксировать статус задачи в ограниченной области и выбрать следующий инженерный шаг, не принимая архитектуру. G1 OPEN, физические испытания NOT_RUN.

## Предыдущая эстафета (история)

# Передача R1 — документальное исправление R5-LINKED-FIX-W01

- Документальный C: 4ebf47a5f6f96708a65653acaf0cebeee1b84c26; ветка work-r4/linked-scene/r4-linked-20261111. Изменена одна строка README: 27 отрицательных примеров и ссылка на проверенный code/results 8896d70983648ccd33c0f861c9bc9d28327ff9eb. Остальные файлы models/ побайтно неизменны; отчёты не перегенерировались.
- Исходный OUTPUT-review 2f3c318813474d9c0ff850e83e15b659fc0e3f14 и независимый RECHECK 82d60717ed9621af7f9fee4e57135d12f22cfc32 сохранены с probe/результатами и включены в ancestry через merge a48aee1be35d8217cc96e1764feac76ba24ca21d. Оба probe имеют разное назначение: первый фиксирует старые ошибки, второй — исправленные исходы.
- RECHECK WARNING закрыл имплементационные B01…B03/W01 только для указанной synthetic-области проверенного C; задача не объявлена принятой. Следующий шаг R1: самостоятельно оформить решение об ограниченной приёмке и интеграции, повторно проверить актуальную main/owner/lease перед merge.
- Main при проверке 116b280ffbe579e7545de51282ccfa96aa6cdefd; owner r4-linked-20261111, lease до 2026-11-12T16:05:29Z. В main принят учёт claim PR #32. Изменения этой рабочей ветки в main не интегрированы.
- Проверки git ancestry/байтов, git diff --check и check_registry.py --check-git PASS. JSON SHA-256 c65665332583dfc65b37958321927544a20bd73ee32939eb7876e53c2da52c7f. Физика/безопасность UNKNOWN, G1 открыт.

## Предыдущая эстафета (история)

# Независимый R5 RECHECK — T-r4-linked-01

- Проверить точный code/results commit 8896d70983648ccd33c0f861c9bc9d28327ff9eb, ветка work-r4/linked-scene/r4-linked-20261111; автор r4-linked-20261111, независимый reviewer не автор. Входной акт 2f3c318813474d9c0ff850e83e15b659fc0e3f14, копия verification/r5_linked_scene_output_review/review.md.
- R5-LINKED-IMPL-B01…B03 и R5-LINKED-IMPL-W01 OPEN до независимого акта. Проверить отдельно доказанное исчезновение вместе с UNKNOWN CREATE/SPLIT, ошибки времени/ID/типа и лишние/дублированные события, точные рациональные времена, рёберный/точечный и малый положительный контакт; проверить приоритеты и раздельные доказательства.
- Команды из корня: python3 models/rev_linked_scene/run.py; python3 -m unittest discover -s models/rev_linked_scene -p 'test_*.py'; python3 -m unittest discover -s models/kinematic_press -p 'test_*.py'; python3 scripts/check_registry.py --check-git. Отчёт models/rev_linked_scene/results/report.json, хэши файлов внутри; реестр снимка рядом.
- Результат автора: 8/8 сцен, 27/27 негативных примеров, 33 новых и 20 прежних тестов, registry PASS, JSON воспроизводим и хэши сверены. Проверить свежий вывод и фактические доказательства, а не только счётчики.
- verification/r5_linked_scene_output_review/probe.py — исторический probe, assertions намеренно требуют СТАРОГО ошибочного результата; exit 0 на старом SHA не означает исправления и на исправленном SHA не является passing регрессией.
- Claim: PR #31 в main 76666e8eb1d11d51be144c59980587e4ffa6a1f1 содержит предложение a90927a; старые поля PENDING/NONE в main ещё противоречивы. Сверка R1 ea4fe28af7e4771977928d2262bcf32357744abb опубликована отдельно, её принятие не подтверждено; R5-LINKED-CLAIM-W01 OPEN до интеграции. Lease до 2026-11-12T16:05:29Z.
- Только synthetic линейные AABB; реальная физика, удержание, разгрузка, безопасность UNKNOWN, испытания NOT_RUN, G1 открыт. Капсула handoffs/T-r4-linked-01/r4-linked-20261111.md.

## Предыдущая эстафета (история)

# Эстафета независимому R5 — T-r4-linked-01

- Автор реализации r4-linked-20261111 / R4; точный code/results C: d11c3e0505d455cfdcf15847aea5b06180659e1b, ветка work-r4/linked-scene/r4-linked-20261111. Claim принят PR #31 на 76666e8eb1d11d51be144c59980587e4ffa6a1f1; срок до 2026-11-12T16:05:29Z. Новый независимый OUTPUT review NOT_RUN.
- Вход: контракт 7b5192382b06d4f148a6c98ffecc8e4d50ec4e66. R5 d2ab72f24028f1cc5d8e9cb3a11d14744e46273f проверял предыдущую редакцию bb31d82b4aacebd6ccff8b6b343837d4443f8150 с WARNING. Уточнение схемы ALLOWED_CONTACT/LINK_* и R5-LINKED-W01 остаются OPEN до независимого review нового текста и реализации.
- Код и полные результаты: models/rev_linked_scene/; JSON results/report.json и снимок реестра. Команды: python3 models/rev_linked_scene/run.py; python3 -m unittest discover -s models/rev_linked_scene -p 'test_*.py'; python3 -m unittest discover -s models/kinematic_press -p 'test_*.py'; python3 scripts/check_registry.py --check-git.
- Авторские результаты: 8/8 сценариев A/B, 19/19 негативных примеров, 23 новых и 20 прежних tests OK. 48 фаз, 3 784 парные строки и 11 458 временных записей. JSON повторно воспроизведён и хэши всех входов совпали. Эти счётчики не подтверждают полноту метода и не заменяют review.
- R5: независимо проверить полноту разбиения времени по корням и границам контакта, контактную политику/покрытие обязательной связи и W01, непрерывность и REMOVE/неподдерживаемые CREATE/SPLIT, полные множества пар, негативные примеры и приоритет COLLISION+UNKNOWN, READY и точный C. Оформить независимый акт отдельным commit; не автором проверяемой версии.
- Реальные параметры, удержание, разгрузка, выдача и безопасность REV UNKNOWN; условная геометрия не является изделием; испытания NOT_RUN, G1 открыт. Капсула handoffs/T-r4-linked-01/r4-linked-20261111.md.

## Предыдущая эстафета (история)

# Эстафета R4 — отдельный claim T-r4-linked-01

- Пользователь поручил R4 ограниченную реализацию связанных synthetic-сцен A/B. Claim PROPOSED / PENDING_MAIN; engineering NOT_STARTED. Прежняя T-codex-01-01 завершена в ранее проверенной области; её claim не переиспользуется.
- C предложения claim: a90927a09d12e988e4bcfb6583cfd6c9a1d8866c; база 0b54471e9e5a7f148558804c93d3302f19907ce4; ветка work-r4/claim-linked-scene/r4-linked-20261111; owner_session в принятой main NONE.
- Источник: models/rev_linked_scene_contract.md на 7b5192382b06d4f148a6c98ffecc8e4d50ec4e66; R5 WARNING d2ab72f24028f1cc5d8e9cb3a11d14744e46273f на предыдущую редакцию bb31d82b4aacebd6ccff8b6b343837d4443f8150. Уточнение W01 ещё не проходило независимую проверку; не подменять вывод акта.
- Следующее действие: принять claim последовательно в main по протоколу, предварительно проверив owner, отсутствие конкурирующих claims, срок и входы; после этого R4 fetch main, проверяет принятие/lease и оформляет входной акт. Проверка исходов и кода требует независимого R5.
- Реальные параметры REV и физические удержание, разгрузка, выдача и безопасность UNKNOWN; пробы и испытания NOT_RUN; G1 открыт. Капсула handoffs/T-r4-linked-01/r4-linked-20261111.md. Проверка registry --check-git PASS после штатной загрузки LFS-объектов.

## Предыдущая эстафета (история)

# Восстановление claim R1 по T-INIT — предложение

PR #29 принят в main `4c11d879f0f59b15fcc0ed75781e30b30a588fd0`; документальные постановки W01–W05 и акты доступны, сами замечания остаются OPEN до применимой методики. Прежний lease R1 `codex-01` истёк. Предложение восстановления оформлено в ISSUES_AND_TASKS.md: PROPOSED / PENDING_MAIN, до последовательного принятия не действует.

После принятия проверить main, владельца, срок и входы; подготовить конкретный инженерный план получения необходимых исходных данных на основе результатов PR #23, #25, #27 и #29. Пробы/испытания NOT_RUN, неизвестные значения UNKNOWN, B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Сверка claim R4 и блокеры synthetic-реализации

PR #31 принят в `76666e8eb1d11d51be144c59980587e4ffa6a1f1`; в принятом трекере оставались противоречивые поля PENDING_MAIN/NONE. В этой ветке R1 приводит их в соответствие с принятым claim `a90927a09d12e988e4bcfb6583cfd6c9a1d8866c`, owner `r4-linked-20261111`, lease до 2026-11-12T16:05:29Z; до интеграции этой записи R5-LINKED-CLAIM-W01 OPEN.

OUTPUT-review R5 `2f3c318813474d9c0ff850e83e15b659fc0e3f14` на `d11c3e0505d455cfdcf15847aea5b06180659e1b` — REJECT_WITH_BLOCKER. R4 следует исправить R5-LINKED-IMPL-B01…B03 и W01 по акту и опубликовать точный SHA для независимого RECHECK. До приёмки исправлений задача BLOCKED; G1 OPEN, физические испытания NOT_RUN.

## Предыдущая эстафета (история)

# Интеграция документальной постановки R3 W03/W04 — проект

Постановка `026bd890d7957526bfbee5ffb2745e9fe7b0c43e` и независимый акт R5 `644d74178fefb4cb40150276532b08c6a8381b98` сохранены в истории интеграционной ветки. По verification/r3_compaction_observability/disposition.md предложено принятие только как документального черновика с WARNING; до принятия PR задача IN_REVIEW. R5-COMP-W03/W04 OPEN до разработки и проверки применимой методики. Перед слиянием сверить main, owner, lease и входы. B01–B03 и G1 OPEN; пробы и испытания NOT_RUN.

## Предыдущая эстафета (история)

# R3 — постановка W03/W04 на независимый review

Claim `5f046982b59376eb26d89541adb81955b27e6ffb` принят PR #26 на `adaf5593edb7c374c112bbcc58c802d35bd4ccd3`; owner r3-safety-01, lease до 2026-11-12T12:29:35Z. Входной акт и постановка verification/r3_compaction_observability/ подготовлены, IN_REVIEW. Передать опубликованный точный SHA независимому R5 и профильным участникам; до интеграции проверить main, owner, lease и входы. R5-COMP-W03/W04, B01–B03 и G1 OPEN; физические работы NOT_RUN.

## Предыдущая эстафета (история)

# R3 — отдельный claim для W03/W04 после PR #25

На main `461a9abcc4bb0011291f6f7a1747524713b371ec` принят документальный черновик R2 с WARNING. Пользователь поручил R3 постановку измерительной модели и наблюдаемости R5-COMP-W03/W04. T-r3-compaction-measure-01 READY; claim r3-safety-01 PROPOSED / PENDING_MAIN, lease предложен до `2026-11-12T12:29:35Z`. Исследование NOT_STARTED: сначала принять claim последовательно в main, проверить owner/lease/входы и оформить входной акт. T-INIT R1 не перехватывать, его lease истёк. См. трекер и handoffs/T-r3-compaction-measure-01/r3-safety-01.md. B01–B03 и G1 OPEN, пробы/испытания NOT_RUN.

## Предыдущая эстафета (история)

# Эстафета — документальная интеграция проекта программы

- R1 оформил verification/compaction_program_r1_disposition.md по программе `48b339263d7ab9991cc5384d0b05d22e6dbaa879` и актам R2, R3 и R5; приёмка только как документального черновика с WARNING. R5-COMP-W01–W05 OPEN для будущей методики.
- Ветка интеграции восстанавливает запись и эстафету R2, утраченные в объединённом дереве review, сохраняя истории. Следующий шаг: последовательно интегрировать эту ветку в main после повторной сверки базы и claim; затем разработать постановку получения недостающих данных и методики без запуска испытаний.
- Методы и значения UNKNOWN, пробы и испытания NOT_RUN, B01–B03 и G1 OPEN; ТЗ и архитектура не утверждены.

## Предыдущая эстафета (история)

# Эстафета — уточнения программы по R3

- R2 RECHECK `15663157ad1bafc610d17be69f57b1ea5c2f883e` закрыл W01–W05 документально на `03290fe5e5392697303dd5eac552996e61df01ff`, WARNING; claim принят PR #22. Это не подтверждение новой редакции.
- R3 OUTPUT `097d1ce34e7f8c3ff53a62a1f69933c258339dec` проверил ту же редакцию, WARNING. R1 уточнил программу по R3-COMP-W01–W04; замечания OPEN до RECHECK. Акты относятся к прежней редакции и сохраняют исторические выводы.
- Следующее действие: передать точный SHA этой редакции R3 на независимый документальный RECHECK границ измерений, наблюдаемости фаз, времени и сравнения A/B; затем передать актуальную редакцию на независимую проверку R5. Claims и базу сверять по протоколу.
- Методы, приборы и значения UNKNOWN; пробы и испытания NOT_RUN; B01–B03, R5-OBS-01…04 и G1 OPEN. ТЗ и архитектура не утверждены.

## Предыдущая эстафета (история)

# Эстафета — предварительные замечания R2 к программе формования

- R2 `e98b8ef8-7302-453a-ac8d-1edbb7d8860c` подготовил акт `e939c146f51d4a40daba75b1bb21bd694e12bccc` по `89eded1ae0b6307052e89ea35a837967bb54ce7f`. Claim PROPOSED/PENDING_MAIN, акт не зарегистрирован и не принят; предлагаемая запись не содержит явных heartbeat/lease.
- R1 документально уточнил verification/compaction_measurement_program_draft.md по W01–W05 без объявления их закрытыми. Следующий шаг: R2 на актуальной main оформить полноценный отдельный claim с основанием, сроком, heartbeat и конкурентной сверкой, затем после принятия проверить актуальную редакцию и зарегистрировать review/RECHECK по протоколу; передать профильные вопросы R3/R5.
- Эта ветка и исправленный проект не интегрированы в main. Методы/значения UNKNOWN, пробы и испытания NOT_RUN; B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — проект программы измерений формования

- PR #21 принят в main `d03ebe790af22f65bae7d10110a9c92062dbf1fe`; инженерная карта и акты интегрированы, результат принят только документально с WARNING.
- R1 подготовил verification/compaction_measurement_program_draft.md: будущие измерительные границы, качество каналов, связь партий/доз/изделий и проект исследовательских блоков A/B. Параметры и критерии UNKNOWN; пробы и испытания NOT_RUN.
- Следующий шаг: независимый документальный review R2/R3 и R5 по полному SHA программы, затем исправить замечания и отдельно подготовить согласуемую методику/безопасные условия. Назначения/claims по протоколу; этот документ не разрешает физические работы.
- B01–B03, R5-OBS-01…04 и G1 OPEN; ТЗ/архитектура и оборудование не утверждены.

## Предыдущая эстафета (история)

# Эстафета — документальная приёмка карты инженерных входов

- RECHECK R3 `b14d1b2344396d08df81393d97e7198861e3fcd5`: W01–W04 CLOSED только документально на `0aeedf369f4a5e9953bbbe26334552271cc73484`, WARNING. R1 принял карту в ограниченной области по verification/engineering_input_map_acceptance.md.
- Следующий шаг: интегрировать карту, акты и решение R1 в main после повторной сверки базы и claim. Затем разработать отдельную программу/методику получения реальных исходных данных с профильной независимой проверкой; не запускать отложенные пробы и испытания.
- Выбор привода/архитектуры и ТЗ не утверждён; параметры/пригодность UNKNOWN, B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — уточнения инженерных входов после review R3

- Акт `59bdfeb0992645d4382070fa09c613c6de65901f` проверил `53a864de6fd9836f90ba10a04bc44b4edf5ecc22`, WARNING. Карта verification/engineering_input_map.md уточнена по R3-INPUT-W01…04; они OPEN до независимого RECHECK. Прежний акт STALE к изменённому файлу, история сохранена.
- Следующий шаг: опубликовать точный SHA новой редакции и передать reviewer R3/R5 на независимую сверку уточнений силы, потоков, баланса, измерений и сопоставимости A/B. Затем оформить документальную приёмку и интеграцию; до проверки не использовать формулы для подбора привода.
- Данные, размеры и пределы UNKNOWN; пробы/испытания NOT_RUN; B01–B03 и G1 OPEN. Архитектура/ТЗ не утверждены.

## Предыдущая эстафета (история)

# Эстафета — инженерные входы формования и гидропривода

- PR #20 принят в main `4b898c14338083deebc27d9d4ec45ba691b62808`. T-r3-norms-01 DONE только как документальная карта после принятия этой записи; нормативная применимость и актуальные редакции UNKNOWN/NOT_RUN.
- R1 подготовил verification/engineering_input_map.md: что нужно измерить для подачи, уплотнения, разгрузки и выдачи; условные зависимости цилиндра, расхода и мощности; сравнимые вопросы A/B. Значения UNKNOWN, испытания и пробы NOT_RUN.
- Следующий шаг: независимая документальная проверка R2/R3 с акцентом на физические зависимости, знаки, измерительные границы и неполноту данных; оформить назначение/claim по протоколу, если создаётся отдельная задача. После проверки конкретизировать будущую программу, не запускать испытания.
- B01–B03, R5-OBS-01…04 и G1 OPEN. Архитектура, ТЗ, параметры и средства защиты не утверждены.

## Предыдущая эстафета (история)

# Эстафета — документальный реестр нормативных источников R3

- Результат `77e78ee9e910132116e9f1e1e21bc4a3fa8b6e16` принят R1 как документальная карта с WARNING; см. verification/r3_normative_scope/r1_acceptance.md. OUTPUT-review `c96db4b456cad29d00da091a5c1fe3bb022e1fd6`, RECHECK `1531823ba62173d6fdd4173bed05811aff58b840`; R5-NORMS-B01 CLOSED только в проверенной области.
- Следующий шаг: интегрировать результат, акты и решение в main после повторной сверки актуальной базы и claim. T-r3-norms-01 IN_REVIEW до интеграции.
- Полные актуальные редакции, N05 регламент, N06 стандарт, юрисдикция и применимость UNKNOWN/NOT_RUN. Нужны профильные специалисты; B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# T-r3-norms-01 — на независимую проверку

Claim `3345b050966fc4e52b317e64381c0dd7bc087b2a` принят PR #19 в `d499216856b3bdbd65f7f23584be80ab6108576a`; owner r3-safety-01, lease до 2026-11-12T08:12:00Z. Входной акт и реестр кандидатов официальных источников — verification/r3_normative_scope/. Результат IN_REVIEW, независимая проверка фактической доступности, прочитанных частей, статусов и ограничений NOT_RUN; передать точный SHA R5 и профильным специалистам. Перед интеграцией сверить main, owner, lease и входы. Место эксплуатации UNKNOWN; B01–B03 и G1 OPEN, пробы/испытания NOT_RUN.

## Предыдущая эстафета (история)

# Предложение отдельного claim R3 — нормативная область

На main `2b26e56f0d35119631bba959da50b32cccaac621` PR #18 интегрировал документальную карту T-r3-safety-01-01 с WARNING; она DONE только в документальной области. Пользователь поручил отдельную задачу T-r3-norms-01 / r3-safety-01: реестр кандидатов официальных первоисточников. Claim PROPOSED / PENDING_MAIN, исследование NOT_STARTED. Сначала принять claim последовательно в main, сверить owner/lease и входы, оформить входной акт. Изготовление в РФ — подтверждённая цель; место эксплуатации UNKNOWN. Применимость и защитные решения не утверждать; B01–B03 и G1 OPEN, пробы/испытания NOT_RUN. См. ISSUES_AND_TASKS.md и handoffs/T-r3-norms-01/r3-safety-01.md.

## Предыдущая эстафета (история)

# Эстафета — приёмка предварительной карты опасностей R3

- R1 принимает результат `2d4791f83ac1f67b2b35c2971b0380301803f344` как ограниченную документальную карту с WARNING, см. verification/r3_press_safety/r1_acceptance.md. Независимый OUTPUT-review `ec5662a386aabbe894c94cb8b97897d182d55580` и RECHECK `94d50fb185286d2b258e005a8be5233682cac9bf`.
- Следующий шаг: последовательно интегрировать результат, оба акта с сохранением их коммитов и решение R1 в main после повторной сверки базы/claim. До интеграции задача IN_REVIEW.
- Это не законченный анализ риска, не утверждение защит и нормативной применимости. B01–B03 проекта, R5-OBS-01…04 и G1 OPEN; испытания/пробы NOT_RUN.

## Предыдущая эстафета (история)

# R3 — исправления на независимый RECHECK

Акт REV-R5-R3-SAFETY-01-001 из `ec5662a386aabbe894c94cb8b97897d182d55580` проверил `43c5a0f0e89b386fdf07600cc6ccf27c7e6fa63c`, REJECT_WITH_BLOCKER. R3 исправил B01 и дополнил W01–W05; независимая проверка нового опубликованного SHA NOT_RUN. R5-SAFETY-B01 и W01–W05 остаются OPEN до независимого RECHECK; проектные B01–B03, R5-OBS-01…04 и G1 OPEN. Пробы и испытания NOT_RUN. См. verification/r3_press_safety/ и verification/r5_r3_safety_output/review.md.

# Результат R3 — независимый review

Claim T-r3-safety-01-01 принят PR #17 в main `b28a99594e31bc6a34c35646e4717a2ccea5943a`; owner r3-safety-01, lease до 2026-11-12T04:14:00Z. После входного акта подготовлены документы verification/r3_press_safety/. Задача IN_REVIEW; независимый reviewer проверяет опубликованный SHA, область и пробелы; перед интеграцией сверить main, owner и срок. B01–B03, R5-OBS-01…04 и G1 OPEN; пробы и испытания NOT_RUN.

# Эстафета — после PR #15: проект анализа опасностей

- `main` `78f9d33061b55ea66e91e91f6f384b9e820a58bf` содержит результат исследования металла, акты R5 и решение R1; T-r2-metal-01 DONE в документальной области после принятия этой записи. R5-SRC-W01 по применимости и программе OPEN.
- Подготовлен проект задания `verification/press_risk_analysis_brief.md` по B03. Следующий шаг: после интеграции документа оформить отдельное назначение/claim R3 для документального реестра опасностей и нормативных вопросов с участием R1/R5/R6; до принятия claim работа не начинается. Роли предложены, не назначены.
- Числа и защитные решения UNKNOWN; физические проверки/пробы NOT_RUN; B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — документальная приёмка исследования металла

- Результат `39f54598e3ab9997ea60d34fd2b203a28bc44822` принят R1 только как документальное сравнение: verification/r2_metal_detection/r1_acceptance.md. Независимый акт и манифест — `973603eef49f553ea94681305eafbefc460935f3`; reviewer runtime `6af3e1ba-0700-8191-a54b-0e6076cdc076`.
- Следующий шаг: последовательно интегрировать результат R2, акты, регистрации review и решение R1 в main, перепроверив базу/claim. T-r2-metal-01 IN_REVIEW до интеграции.
- R5-SRC-W01 применимость/программа OPEN; прибор/метод не выбраны, реальные данные UNKNOWN, пробы/испытания/калибровки NOT_RUN. B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — уточнение M01/M02 по независимому акту R5

R2 объединил историю акта R5 `2a8d43b3b7ef181fadc768363e36f4f04de21559` с рабочей веткой и уточнил verification/r2_metal_detection/research.md. Передать точный commit R5 для сверки новой редакции. Документальная часть R5-SRC-W01 закрыта с WARNING по акту; применимость/программа/охват остаются OPEN. Прибор и метод не выбраны, пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

# Эстафета — исходные HTML M01–M06

R2 подготовил verification/r2_metal_detection/source_access.md: все первоначальные ответы локально сохранены, хэши совпадают с исследованием. Из-за неподтверждённых прав на распространение полные страницы не включены в Git; доступ R5 к локальным копиям или сайтам остаётся проверить. Передать точный commit R5; R5-METAL-B01 и R5-SRC-W01 OPEN до независимой сверки. Прибор и метод не выбраны; пробы/испытания/калибровки NOT_RUN, B01–B03 и G1 OPEN.

# Эстафета — исследование кандидатов контроля металла R2

T-r2-metal-01 / r2-material-01 IN_REVIEW. Входной акт, исследование источников и выдержки в verification/r2_metal_detection/. Передать точный commit независимому R5 на OUTPUT-review: проверить источники, границы заявлений, физическую область, редкие события и пробелы. Полные HTML-копии не сохранены, доступность R5 NOT_RUN. Прибор/метод не выбран, R5-SRC-W01, B01–B03 и G1 OPEN; пробы, испытания и калибровки NOT_RUN.

# Эстафета — после интеграции реестра первоисточников

- PR #12 принят в main `6055d85196ff1224837a6302f53315cd8dadfc3a`; T-r2-sources-01 DONE только как документальная карта с WARNING после интеграции этой записи. Методы и применимость не утверждены; спорные сведения UNKNOWN и исключены из использования.
- Следующий шаг: рассмотреть проект отдельной документальной задачи по физическим металлическим включениям `verification/metal_detection_research_brief.md`; оформить назначение и последовательный claim до выполнения. R5-SRC-W01 OPEN.
- Пробы и испытания NOT_RUN, B01–B03 и G1 OPEN; не выбирать средство/метод, не утверждать архитектуру или ТЗ.

## Предыдущая эстафета (история)

# Эстафета — приёмка документального реестра источников R2

- R1 принял реестр как документальную карту копий/пробелов с WARNING: verification/r2_primary_sources/r1_acceptance.md. R5 `r5-implementation-02` закрыл R5-SRC-B01 и R5-LAP-01/02 только в ограниченной области, R5-VERSION-B01 — по доступным Git-байтам.
- Следующий шаг: последовательно интегрировать документы R2, LFS-копии, независимые акты и решение R1 в main после проверки актуальных main/claim. T-r2-sources-01 IN_REVIEW до интеграции.
- Исходный временный файл R2 недоступен R5 (cmp NOT_RUN); внешнее происхождение и подлинность не удостоверены. Спорные даты/версии и правильное aspect ratio UNKNOWN, исключены из использования. Актуальность, применимость, лабораторная проверка и физический металл R5-SRC-W01 открыты; B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — исправление R5-VERSION-B01

R2 исправил полный SHA-256 openalex-src02.json в verification/r2_primary_sources/version_inquiry/report.md, сохранив прежнюю строку, Git blob и локальное подтверждение. Передать точный commit независимому R5 на сверку; прежний акт STALE относительно нового отчёта, R5-VERSION-B01 OPEN до RECHECK. Спорные даты, версия PDF и корректное значение aspect ratio UNKNOWN и исключены из проектного использования; пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

# Эстафета — исследование R5-LAP-01/02

R2 подготовил verification/r2_primary_sources/version_inquiry/report.md и сохранил ответы каталогов. Передать точный commit R5 для независимой проверки причин расхождений, доказательств и предложенного исключения неподтверждённых утверждений. Причина различия дат и связь карточки SRC-02 с конкретной версией PDF UNKNOWN; R5-SRC-B01 OPEN. Методы не утверждены, пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

# Эстафета — LAP NREL и карточка OSTI для R5

R2 передал три копии LAP и ответ OSTI для SRC-02 в verification/r2_primary_sources/lap_evidence/. Передать точный commit независимому R5: проверить LFS, хэши, титулы и нужные разделы; отдельно оценить атрибуты карточки и не предполагать связь с конкретной PDF-версией. R5-SRC-B01 OPEN до решения R5. Актуальность и применимость к REV NOT_RUN; методы не утверждены, пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

# Эстафета — уточнение реестра SRC-02…04

R2 уточнил verification/r2_primary_sources/registry.md по акту R5 `5bc8db4ba1aff28a62a41edcbbf5e950d0c5cb4f`. Передать commit результата независимому R5 на RECHECK прочитанных мест и происхождения метаданных; R5-SRC-B01 OPEN. Три LAP NREL повторно недоступны (CONNECT 403), тексты/редакции NOT_RUN; методы не утверждены, пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

# Эстафета — копии SRC-01…04 для R5

R2 передал первоначальные копии и манифест verification/r2_primary_sources/copies/ для независимого RECHECK акта b6841d90370b2746ef0dd70bb424e94a25ec6337. Проверить получение LFS-объектов, SHA-256 и указанные разделы реестра на 25745de1c69d2f0dd6adf8a6f10e8f7af59305a9; до решения R5-SRC-B01 OPEN. LAP NREL 42620/42621/42622 не получены и NOT_RUN; пригодность методов не утверждена, пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

# Эстафета — реестр первоисточников R2

T-r2-sources-01 IN_REVIEW. Входной акт и реестр: verification/r2_primary_sources/. Передать точный commit независимому reviewer для проверки фактически прочитанных разделов, ссылок, полноты пяти групп и ограничений. Документы NREL 42621/42620 остаются недоступными после CONNECT 403; подходящий первоисточник по физическому остатку металла не установлен. Полная проверка текстов, редакций и применимости с лабораторией NOT_RUN; пределы UNKNOWN, пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

# Эстафета — принят claim R2 по источникам

- PR #10 принят в main `123240e20604eec9f497ad8eb3bc29d46539905a`; claim `295ec1e3549a597a76619465eaa58b1746bcefb1`, owner `r2-material-01`, lease до 2026-11-12T00:36:14Z. Запись об этом подготовлена в ветке координатора и ещё требует интеграции.
- После сверки main, owner, срока и входов R2 оформляет входной акт и составляет реестр доступных первоисточников. Недоступное — NOT_RUN; методы не утверждать, пробы/испытания не проводить, B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — после интеграции сравнения R2

- PR #8 принят в main `3a725f82ae93c82c39ed7bb554d6f2449f47d92e`; сравнение R2, ответ на W01–04 и независимые акты сохранены в истории. T-r2-material-01 DONE только для документального сравнения после интеграции этой записи.
- Следующий шаг: подготовить отдельную задачу проверки доступных первичных источников, их редакций и области применения и сопоставления вариантов с компетентной лабораторией; задача, назначение и claim — отдельно по протоколу. Не объявлять недоступный NREL прочитанным и не выбирать метод без доказательств.
- Отложенные пробы и журналы не запрашивать; фактические испытания, квалификация и калибровка NOT_RUN, параметры UNKNOWN. B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — приёмка документального сравнения R2

- R1 принял документальное сравнение R2 с WARNING: verification/r2_material_methods/r1_acceptance.md. Акт R5 `921d17a46dcc2583ab1d8f84ac79209e0fe910a3` закрыл W01…04 только для документального ответа `fcbeefae46b4fd999c194bd214b5dda7c476b0ec`.
- Следующий шаг: последовательно интегрировать результат R2, акты R5 и решение R1 в main, повторно проверив owner и lease. До интеграции T-r2-material-01 IN_REVIEW.
- Методы/редакции/пригодность и лаборатория не проверены, NREL NOT_RUN; до выбора метода требуются первоисточники, компетентная лаборатория и независимая проверка программы. Пробы/испытания NOT_RUN, B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — ответ R2 на R5-MAT-W01…04

R2 r2-material-01 подготовил verification/r2_material_methods/response_r5_material_01.md к акту R5 `08d75ec9bc86afae14663a6037958e384b1965e0`. Передать точный SHA содержащего этот пакет коммита независимому R5 на RECHECK W01–W04; замечания остаются OPEN. Первоисточники и применимость NOT_RUN, численные пределы UNKNOWN; пробы/испытания NOT_RUN; B01–B03 и G1 OPEN.

# Эстафета — документальное сравнение методов R2

T-r2-material-01 IN_REVIEW; R2 r2-material-01, входной акт и сравнение пяти групп — verification/r2_material_methods/. Передать commit этого комплекта независимому R5/R1, не автору, для OUTPUT review физических оснований, формул, применимости, репрезентативности и пробелов. Внешние нормативные источники и редакции не подтверждены; попытка NREL вернула CONNECT 403. До принятия сравнение не становится выбранной методикой. Методы и пределы UNKNOWN, пробы и испытания NOT_RUN; B01–B03 и G1 OPEN.

# Эстафета — принятие claim R2 по PR #6

- `main` `6ccc31bef5a49a600d162cb7ab99fd0aed40d457` содержит claim `dd57126ae68fccddcfaeeef087efe07e995d0e60` для `T-r2-material-01`, owner `r2-material-01`, lease до `2026-11-11T23:45:21Z` без продления. Запись об этом подготовлена в ветке координатора; статус общей ветки перепроверять.
- R2 перед работой проверяет актуальные main/owner/lease/входы, оформляет входной акт и выполняет документальное сравнение пяти групп методов. Данные, нормы и критерии не утверждать; пробы и испытания NOT_RUN. B01–B03 и G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — после независимого RECHECK проекта ТЗ

- Акт `f1edde47c580308aed7c1308281fc3069e25ccd7` проверил `a02420fd3b100447550740a417d75c8608206cd7`: W01…04 CLOSED документально; B01…03 OPEN, REJECT_WITH_BLOCKER для ТЗ/G1. Исправлены только исторические ссылки rev1/rev2 на схему; акт STALE относительно редакционно изменённых файлов, без переоткрытия W01…04.
- OP-REV-07: оператор предварительно ориентируется на передачу после существующих дробления и просева; см. process/supply_boundary_options.md. Пригодность и окончательная граница UNKNOWN. OP-REV-08: оператор оставил транспорт и буфер UNKNOWN. OP-REV-09: оператор предварительно относит проверку остаточного металла и иных включений к существующей линии; методы, пределы и эффективность UNKNOWN. OP-REV-10: возможную доподготовку предварительно рассматривать на существующей линии, если она понадобится; необходимость и средства UNKNOWN. OP-REV-11: предварительный конец поставки — выход пресса; параметры и дальнейшее обращение UNKNOWN. R1 подготовил проект паспорта групп измерений process/input_material_measurement_passport.md, без отбора. Следующий шаг: передать точный SHA паспорта и исходных планов R2 с R1/R5 для документальной оценки возможных методов, оснований, ограничений и пробелов; назначение R2 и claim предварительно оформить по протоколу. Пробы и журналы отложены, B01…03 OPEN.
- Функции R2/R3/R5/R6 из плана предложены, отдельные назначения и claims не предполагаются. G1 OPEN, архитектура/ТЗ не утверждены; испытания и пробы NOT_RUN.

## Предыдущая эстафета (история)

# Эстафета — доработка после R5-TZ-REVIEW-01

- Основание: `b527c62ba9f1f37a5176dc9ed45b4b245bcdb49d`, акт проверяет `bff66903c4588321faf3b86bf0abb501c8a7c881`, R5 `r5-implementation-02`. B01/B02/B03 OPEN; W01…04 доработаны документально и ожидают независимого RECHECK. Старые акты помечены STALE только относительно изменённых файлов; блокеры и R5-OBS-01…04 сохраняются.
- Промежуточный план criteria и опасностей: verification/requirement_criteria_development.md; изменения в требованиях, матрице, плане функций и схеме F. Значения UNKNOWN, испытания/пробы NOT_RUN, G1 OPEN.
- Следующее действие: опубликовать точный commit изменений и передать R5 его SHA вместе с актом b527c62 для повторной проверки W01…04 и оценкой остаточных B01…03; до пользовательского утверждения ТЗ G1 не закрывать.

## Предыдущая эстафета (история)

# Эстафета — после принятия PR #2

- База main `672c835e201766a943927917f12875a9204b0b34` содержит модель `debfd085842ccae079cfd6faea1c41bca20f335d`, акт/probe R5 `b4d4af9325c5d24e093ec2d4dce5797581ebf6e1` и решение R1. T-codex-01-01 DONE только в synthetic AABB области, после принятия записи об интеграции в общую ветку.
- R1 выполнил документальную сверку и оформил `verification/g1_readiness_inventory.md`. Следующий шаг — передать точный опубликованный SHA проекта требований, матрицы и перечня независимому reviewer, не автору, для OUTPUT-review; затем устранить замечания и подготовить ТЗ к утверждению пользователем. Не объявлять виртуальные результаты испытаниями сырья или подтверждением VAL.
- Независимый review проекта требований/плана и утверждение ТЗ пользователем ещё нужны; G1 открыт, архитектура и реальные численные параметры не утверждены. Испытания не запускать без отдельной готовности. Перед продолжением сверить main и действующий claim.

## Предыдущая эстафета (история)

# Эстафета — решение R1 по T-codex-01-01

- R1 принял результат `debfd085842ccae079cfd6faea1c41bca20f335d` для ограниченной synthetic AABB области. Основание и ограничения: verification/t_codex_01_01_acceptance/r1_assessment.md; опубликованный акт R5 и probe — verification/r5_recheck_05.
- Рецензент `r5-implementation-02`; источник акта/probe `b4d4af9325c5d24e093ec2d4dce5797581ebf6e1`; SHA-256 probe `e7c2e004ced7bf7a25f62aa92904291e47bbf027111e7e1cb089fcf193b0aa80`. R1 повторил 8 мутаций, 20 тестов, benchmark 3000 и сверку отчётов.
- Следующий шаг: подготовить последовательную интеграцию model commit, акта и решения в общую ветку с повторной сверкой main и claim. Трекер IN_REVIEW до интеграции; архитектура не утверждена, G1 OPEN.

## Предыдущая эстафета (история)

# Эстафета — оценка R1 модели T-codex-01-01

- Оценка: verification/t_codex_01_01_acceptance/r1_assessment.md. Модель — кандидат на приёмку в synthetic AABB области, формально задача остаётся IN_REVIEW и не DONE; G1 OPEN.
- Следующий шаг: получить идентификатор независимой сессии R5 и исходный `probe.py` с неизменяемым commit/SHA-256 и результатами; сверить независимость и мутации, зарегистрировать review, повторно проверить main/claim и оформить решение о приёмке.
- На 2026-11-10 22:37 UTC main `2f463babdc84382a0ab2502f4acfa7a2047087df`, R4 `r4-model-01`, lease до 2026-11-11 16:52:25 UTC. Состояние необходимо перепроверить перед интеграцией.

## Предыдущая эстафета (история)

# Эстафета — дополнение RECHECK-05 с результатами

- На основании предоставленного пользователем verification/r5_recheck_05/execution_addendum.md: R5-IMPL-01 CLOSED только для synthetic AABB на `debfd085842ccae079cfd6faea1c41bca20f335d`, регрессия R5-IMPL-02 PASS в той же области. T-codex-01-01 IN_REVIEW, не DONE; G1 OPEN.
- R5 сообщает 20 тестов, 3000 сравнений и 8 независимых мутаций; R1 не воспроизводил эти дополнительные мутации. Скрипт probe.py и точный ID сессии не предоставлены, запрашивать при следующем удобном контакте для воспроизводимости; пользовательский commit b4d4af9325c5d24e093ec2d4dce5797581ebf6e1 не найден. См. verification/r5_recheck_05/disposition.md.
- Следующее действие R1: сверить актуальные main и task owner/lease, оценить комплект результата модели относительно исходных критериев T-codex-01-01 и оформить решение о приёмке или перечень недостающих доказательств; не утверждать архитектуру или G1.

## Предыдущая эстафета (история)

# Эстафета — предоставленный REV-R5-RECHECK-05-001

- Акт пользователя: verification/r5_recheck_05/submitted_review.md; code/results `debfd085842ccae079cfd6faea1c41bca20f335d`, эстафета `73541d22377fb2b97df0964762b5cdeca9711532`.
- Акт заявляет PASS/CLOSED IMPL-01 и PASS регрессии IMPL-02; подтверждение достаточности независимого RECHECK ожидает дополнения из-за усечённого пакета и отсутствия в акте команд и отдельных результатов обязательных негативных мутаций. IMPL-01 OPEN/HOLD, задача BLOCKED; прежнее закрытие IMPL-02 только для проверенного synthetic SHA. G1 OPEN.
- Дополнение R5, переданное пользователем, повторяет PASS, но не устраняет противоречие об усечённом пакете и не приводит команды и отдельные результаты мутаций. Следующее действие: обеспечить независимому R5 доступ к полным файлам в среде с Git или работающей передачей файлов и запросить воспроизводимые результаты и идентификатор сессии. Подробно: verification/r5_recheck_05/disposition.md.
- Обновлённый акт сохранён в verification/r5_recheck_05/submitted_review_updated.md: R5 прочитал дополнительные тексты, но все команды помечены NOT_RUN; идентификатор сессии отсутствует. См. решение R1 в disposition.md.
- R1 отдельно запустил 20 существующих тестов из изолированного git archive: OK; это не независимый RECHECK.

## Предыдущая эстафета (история)

# Эстафета — решение по REV-R5-RECHECK-04-001

- R1 / codex-01; 2026-11-10T18:33:28Z. Репозиторий narrateller/REV, ветка work/T-INIT/codex-01. C решения: 791d0ce8ccb31373b221d0b69063e2f835b442c0, опубликован.
- Предоставленный пользователем акт: verification/r5_recheck_04/submitted_review.md; проверяемый commit 576a17fc0b127cb7d377992c01d645a77bed42d4, ветка work/T-codex-01-01/r4-model-01; handoff 66fb9bd1d454d05eb7f32b77b9f442917de9b95c. Reviewer session/подпись в тексте акта UNKNOWN; новый независимый review в текущей сессии не проводился.
- На основании акта R5-IMPL-02 CLOSED только для проверенной synthetic AABB области указанного commit; R5-IMPL-01 OPEN, общий результат REJECT_WITH_BLOCKER. T-codex-01-01 BLOCKED для приёмки; G1 открыт, архитектура/ТЗ не утверждены.
- Решение для R4 и критерии независимого recheck: verification/r5_recheck_04/disposition.md. Три изменения: начальная позиция output_obstacle до baseline/стадий; учёт continuity в transition/READY с BLOCKED и INDETERMINATE; проверка непрерывности всех четырёх исходов в runner/tests и свежий linked_report.
- Первый шаг R4: получить C решения 791d0ce8ccb31373b221d0b69063e2f835b442c0, сверить main и claim/lease, зафиксировать C как вход. Далее внести исправления в своей ветке; R1 не менял код/fixtures R4.
- После исправления: новый неизменяемый code/results SHA, свежие отчёты, все 4 исхода A/B, мутации разрыва позиции/времени/lifecycle, UNKNOWN и регрессии закрытого R5-IMPL-02; независимый R5 не автор исправления. Только положительный новый RECHECK может закрыть R5-IMPL-01.
- Самопроверка R1: 5 SHA256 совпали с Git blobs 576a17fc; в сохранённом отчёте B/collision mismatches output_obstacle при matches_expected true; 8 существующих test_linked проходят во временной копии. Это не новый независимый review.
- Прежний claim R4 owner r4-model-01 до 2026-11-11T16:52:25Z, проверять заново; R1 codex-01 до 2026-11-11T12:06:09Z. Реальные данные/физика/безопасность REV UNKNOWN; параметры не менялись.

## Эстафета R4/R5 (историческая)

# Повторная проверка R5 — SYN-LINKED-EJECTION

- Задача T-codex-01-01; автор исправления r4-model-01 / R4. Точный code/results C: 576a17fc0b127cb7d377992c01d645a77bed42d4; ветка work/T-codex-01-01/r4-model-01. Следующий участник — независимый R5, не соавтор C; review NOT_RUN.
- Р1 решение ARB-R1-RECHECK-03 на 1283c9e6f3b14dbbe820dd06798399c611d34ce8; входной REJECT_WITH_BLOCKER REV-R5-RECHECK-03-001 на 9e12e8bd4f2325ae0e887d3f2e28eaa85c55205f; R5-IMPL-01/02 OPEN, consecutive_rejections=2. Изменённые артефакты делают акт STALE для новой версии, блокеры сохраняются.
- Перед началом проверить SHA ветки/C и хэши входов отчёта. Выполнить python3 models/kinematic_press/model.py; python3 models/kinematic_press/run_linked.py; python3 -m unittest discover -s models/kinematic_press -p 'test_*.py'; python3 verification/r5_model_02/independent_check.py; python3 scripts/check_registry.py --check-git.
- Отчёт models/kinematic_press/results/linked_report.json: четыре исхода на каждом из A/B (8/8 ожиданий), матрицы по стадиям, интерфейсы, непрерывность, жизненный цикл и READY. Отчёт results/report.json сохраняет старые 28 cases и полные пары для исходной сцены.
- CE-01 scalar против неподвижного продукта INVALID_INPUT, неподвижный A-OUT не CONSISTENT; CE-02 матрица B-EJECT находит punch/channel_wall [0,1] и блокирует переход. Авторские результаты: 17 unittest OK, benchmark R5 3000/3000, registry PASS, повторный запуск JSON воспроизводим.
- R5 должен независимо оценить метод контактной поверхности, парную полноту и мутации, геометрию и временные границы всех стадий, доказательство реального synthetic READY и ограничения, а также все критерии решения R1. Число совпадений само по себе не закрывает блокеры.
- Синтетические допущения о разгрузке/удержании/замке не являются данными REV; параметры и силы UNKNOWN, G1 открыт. Капсула handoffs/T-codex-01-01/r4-model-01.md.

## Выход независимого review ТЗ

REV-R5-TZ-REVIEW-01-001, reviewer `r5-implementation-02`, reviewed SHA `bff66903c4588321faf3b86bf0abb501c8a7c881`: REJECT_WITH_BLOCKER для утверждения ТЗ и G1. R1 обрабатывает R5-TZ-B01…03 и W01…04 согласно verification/r5_requirements_review/review.md, после проверки действующих claim/lease; затем передаёт новый SHA на независимый recheck. Пробы/журналы отложены, реальные неизвестные не назначать. G1 открыт, архитектура не утверждена.

## Результат ограниченного RECHECK ТЗ

REV-R5-TZ-RECHECK-01-001: W01…04 CLOSED в документальной области, B01…03 OPEN; reviewed commit a02420fd3b100447550740a417d75c8608206cd7. Результаты и условия дальнейшей проверки: verification/r5_tz_recheck_01/review.md. R1 проверяет действующие claim/lease и продолжает B01…03 без выдумывания UNKNOWN; G1 OPEN.

## Независимый OUTPUT-review R2

REV-R5-R2-MATERIAL-01-001, reviewer `r5-implementation-02`, проверенный SHA c78a745fb431b459bf6272b585d17a7fad977845: WARNING в пределах документального сравнения; R2/R1 рассматривают R5-MAT-W01…04 до выбора методики и программы, см. verification/r5_r2_material_review/review.md. Первоисточники/пригодность не подтверждены, пробы отложены. B01–B03 и G1 OPEN.

## Результат RECHECK ответа R2

REV-R5-R2-MATERIAL-RECHECK-01-001: W01–W04 CLOSED в области документального ответа на fcbeefae46b4fd999c194bd214b5dda7c476b0ec; WARNING. Перед выбором методик и утверждением программы необходимо проверить первоисточники, компетентность и применимость с лабораторией, обосновать охват/обнаруживаемость и потери; см. verification/r5_r2_material_recheck_01/review.md. Пробы и испытания NOT_RUN, B01–B03 и G1 OPEN.

## Независимый review реестра источников R2

REV-R5-R2-SOURCES-01-001: REJECT_WITH_BLOCKER для независимой сверки заявленных разделов на 25745de1c69d2f0dd6adf8a6f10e8f7af59305a9; OSTI и NREL в этой среде дали CONNECT 403. R5-SRC-B01 OPEN до получения проверяемых копий/доступа и независимого чтения; R5-SRC-W01/02 — дальнейшая работа. См. verification/r5_r2_sources_review/review.md. Пробы и испытания NOT_RUN, B01–B03 и G1 OPEN.

## RECHECK четырёх копий источников

REV-R5-R2-SOURCES-RECHECK-01-001: проверены четыре LFS PDF d9bc2f101ca001de763b5418dbe7cb2ad2ca5ab2 по реестру 25745de1; R5-SRC-B01 OPEN по отсутствующим трём LAP и неподтверждённым атрибутам. R2 уточняет SRC-03 и SRC-04 и проверяет библиографические атрибуты SRC-02, см. verification/r5_r2_sources_recheck_01/review.md. Актуальность и применимость REV NOT_RUN, B01–B03 и G1 OPEN.

## RECHECK исправленного реестра

REV-R5-R2-SOURCES-RECHECK-02-001 на c0a101a3471942e169599086365941bbaa67ce94: исправления SRC-03/04 приняты в документальной области; атрибуты SRC-02 разделены, карточка независимо NOT_RUN. R5-SRC-B01 OPEN: LAP 42620/42621/42622 не прочитаны, остаются библиографические атрибуты. verification/r5_r2_sources_recheck_02/review.md; B01–B03 и G1 OPEN.

## RECHECK LAP и карточки

REV-R5-R2-LAP-RECHECK-01-001: три копии и JSON пакета 3bc59174fb850e9cf818df23ec55f9bc9c8a23f6 получены, сверены и прочитаны в заявленной области. R5-SRC-B01 OPEN: R5-LAP-01 — 42620 2008/2010; R5-LAP-02 — связь версии SRC-02 и расхождение аннотаций. Подробнее verification/r5_r2_lap_recheck/review.md. Пробы/испытания NOT_RUN, актуальность и пригодность не утверждены; B01–B03 и G1 OPEN.

## Review исследования версий

REV-R5-R2-VERSION-REVIEW-01-001: R5-SRC-B01 CLOSED только в документальной области при исключении неподтверждённых данных; R5-VERSION-B01 OPEN из-за ошибочного SHA `openalex-src02.json` в отчёте R2. R2 сверяет происхождение и готовит исправление, затем независимый recheck; см. verification/r5_r2_version_recheck/review.md. История версий/правильное AR UNKNOWN; B01–B03 и G1 OPEN.

## RECHECK исправления SHA

REV-R5-VERSION-HASH-RECHECK-01-001: R5-VERSION-B01 CLOSED для проверенных Git-байтов на 4605f3435c5882550d540ff797e7322613723769; исходная временная копия недоступна R5 и внешнее происхождение не удостоверено. Подробности verification/r5_version_hash_recheck/review.md. История версий и правильное AR UNKNOWN, B01–B03 и G1 OPEN.

## OUTPUT-review исследования металла

REV-R5-R2-METAL-01-001: M01–M06 недоступны R5 (CONNECT 403), независимая сверка NOT_RUN; R5-METAL-B01 и R5-SRC-W01 OPEN, REJECT_WITH_BLOCKER для приёмки. R2 обеспечивает проверяемый доступ/полные копии с учётом условий распространения, далее R5 проверяет по verification/r5_r2_metal_review/review.md. Прибор не выбран, пробы и испытания NOT_RUN; B01–B03 и G1 OPEN.
