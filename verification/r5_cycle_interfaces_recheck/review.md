# REV-R5-CYC0203-RECHECK-01-001

**B01 CLOSED; B02 CLOSED — только документальный протокол на точном C.**
**B03 OPEN. Общий вердикт REJECT_WITH_BLOCKER** для принятия объединённого
интерфейсного пакета и его semantic checker как стабильного входа следующей
CAD-итерации. Прежние 17 замечаний исправлены, но новые независимые мутации
показали шесть оставшихся пропусков B03.

R5 / Codex / session ID **r5-ci-recheck-20261113**, 13 ноября 2026, МСК.
Назначение — прямое поручение пользователя; timestamps команд — UTC.
Авторы исправления R4 r4-linked-20261111 / r4-cyc-fix-20261113; reviewer не автор
проверяемого кода/документов. Собственные fixtures/ожидания отделены от авторских.
Организационная независимость не удостоверяется.

| Вход | Точный SHA |
|---|---|
| Новый C | **144941cbfc67002cbe81765e38c80e237473deff** |
| Новый H | **7ee1c8f16eca515a3e21f64177152b4e7b93ce92** |
| Исходный OUTPUT-акт | **13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2** |
| Старый OUTPUT C | ed8272ce6ebc2047bb0d896db5951d02c42d5208 |
| Accepted main / PR45 | 3a9258c57e4bc15d6de98f1d17e8412ad6e8899a |
| Frozen material helper | 0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed |

C — предок H; все 50 файлов интерфейсного/correction пакета побайтно соответствуют
C/H. Авторские owner/lease не переназначались и не продлевались reviewer.

## Команды, воспроизведение, независимые результаты

Рабочая директория `/workspace/REV`, Python 3.12.14 из `.venv`.
Полные argv/UTC/exit codes — commands.json; raw stdout/stderr — command_01…07.

```sh
.venv/bin/python -B verification/r5_cycle_interfaces_recheck/historical_replay.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_package.py
.venv/bin/python -B verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py
.venv/bin/python -B -m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v
.venv/bin/python -B verification/r5_cycle_interfaces_recheck/independent_probe.py
.venv/bin/python -B scripts/check_registry.py --check-git
git diff --check
git lfs fsck
```

| Проверка | Итог |
|---|---|
| Исторический неизменённый OUTPUT probe на точном старом C | Полный JSON совпал с 13b0fc3: **1345 = 1328 PASS + 17 FAIL** |
| Новые критерии каждого прежнего замечания | **17/17 исправлены**, соответствие исходным ID сохранено в historical_17 |
| Авторский document checker | **2376 MATCH**, 53 строки = 31 inherited +22 mechanical, 44 bindings, 6 SVG |
| Авторская export suite | **8 MATCH**, повторные readonly проверки и явные экспорты; отсутствие автоисправления |
| Авторские unittest | **7 методов OK**, включая 28 мутаций внутри одного метода; это не 28 отдельных методов |
| Собственные проверки | **654: 648 совпадений, 6 FAIL**, все FAIL — новый semantic mutation rejection B03 |
| Геометрия | **0 пар проверено**, 16 фаз/2933 пары остаются будущим планом |

Exit 0 независимого probe означает завершённый сбор evidence, **не приёмку**.
JSON явно содержит failed и фактические exit codes mutant checker. Файлы
исторического probe и исходный отрицательный акт не переписаны; его старые
assertions на новом ABI не выдавались за критерии исправления.

historical_replay.py использует временную копию старых документов/612 unchanged
inputs и существующую Git object DB только для чтения. Git worktree не создаётся.
Случайный temp-prefix в ошибке missing_svg авторской export-suite нормализован
только при сравнении; исходный stdout сохранён без изменения.

## B01 — CLOSED в проверенной документальной области

Пять LOAD/REFILL и шесть допустимых mode bindings независимо проверены по новому
протоколу. D0→D1 заканчивает локальное перемещение, но не LOAD. FILL-CONFIRM в D1
даёт адресное историческое наблюдение; только затем разрешён D1→D0. Parent commit
один раз после возврата, с текущим D_HOME_CURRENT и FILL_COMPLETE/DOSE_DELIVERED;
текущий D1 не требуется одновременно с текущим D0. Исходная неоднозначность снята.

FILL_COMPLETE сравнивает variant/mode, subject/dose/material/batch/epoch/basis,
load action/operation и transfer operation. Проверены все адресные поля с чужим
значением и null, отсутствующие данные, команда/таймер вместо наблюдения,
неверная поза получения, UNKNOWN dose_delivered и непокрытый интервал.
Прежняя квитанция не допускает новую дозу/REFILL даже при том же остатке/партии.

Без подтверждения RETURN INDETERMINATE; в D1 commit BLOCKED по текущей позе.
После подтверждения и возврата commit условно допустим. До committed successor
FEED-ISOLATE не получает подтверждённого FILL_COMPLETE. После commit сопоставлены
receipt ID, исходные и текущие revisions: только MATERIAL/FEED +1, прочие без
изменения. Дополнительная смена любой из семи ревизий не переносит TRUE.
Неверные boundary/current_doser/receipt ID/value не признаются commit.
Протокол не переписывает квитанцию и не удаляет retained inventory.

Для каждого mode перебраны 27 сочетаний FILL_COMPLETE / D_PATH_CLEAR / ресурса:
FALSE доминирует UNKNOWN; отсутствующее подтверждение не разрешает продолжение.
Аннулирование после возврата не превращается в допустимую старую квитанцию.
Три прежние A_STARTUP строки теперь согласованы с доступным родителем.

Это проверка reference comparator/условий документа. Подлинность реального
наблюдения, реализация durable transaction/lifecycle и материальный баланс
**не доказаны**; они не появляются из условного TRUE и остаются за W02.
B03 ещё должен защищать обязательные producer/return predicates от потери.

## B02 — CLOSED в проверенной документальной области

STOP-CLOSE/RELOCK теперь имеют явные позы упора/замка, собственные условия и
адресную привязку к RESTORE_B_CLOSURE / B_RESET_CONFIRMED. DEPENDENCY_VALID
не требуется как достигнутая цель до восстановительного движения. RELOCK
требует текущего закрытого упора. Результат closure, targeted recovery и history
reconciliation разделены.

Независимый путь на неизменённом frozen helper: отказ B-NEXT по reset → новая
адресная recovery operation → own-guard допуск движения → targeted closure
result → dependency остаётся OPEN → новый NEXT всё ещё BLOCKED → reset commit →
отдельный RECONCILE_HISTORY каждой причины → новый NEXT ALLOWED_ASSUMED.
Исходный отвергнутый ID остаётся BLOCKED, rejected IDs и остаток сохранены.

Для каждого собственного условия двух восстановительных стадий проверены FALSE
и UNKNOWN. Отдельно зафиксированы latched LEDGER_VALID, RESOURCES_READY и
RECEIVER_DEFINED faults: независимый closure audit не удаляет их; механическое
восстановление с нарушенным own guard BLOCKED; обычные LOAD/COMPACT не обходят
отказ свежим TRUE или другим state. У обычной механической WORK удаление
DEPENDENCY_VALID отклонено semantic checker после re-export.

Снятие зависимого блокера ограничено документальной причинностью. Физические
разгрузка/закрытие/замыкание и достаточность наблюдений не подтверждены.
Существующая правильная recovery_binding не оправдывает её ослабление: это
один из оставшихся пропусков защиты B03.

## B03 — OPEN, REJECT_WITH_BLOCKER

Прежние пять semantic mutations теперь отклонены **после** законного экспорта:
неопределённая поза, WORK P0→P2, отсутствие G_ISOLATED_CURRENT, привязка A к
BASE_B и parent A у B. Дополнительные неправильный режим, phase source и
удаление DEPENDENCY_VALID у штатной WORK также отклонены с semantic: reason.
Это существенное исправление, но критерий сохранения обязательных условий
после re-export ещё выполнен не полностью.

Новые собственные мутации изолированы в temp copies, код checker/exporter не
меняется. Для каждой проверено совпадение **всех обновлённых source/export
хэшей**, затем readonly проверка; файлы не исправляются. Все шесть ниже дали
**exit 0 / document_checks MATCH**, хотя ожидался семантический отказ:

| Случай / evidence | Подмена | Что осталось непроверенным |
|---|---|---|
| `mutations/P1-coordinate.json` | poses.P1.coordinate = `x_P0 + S_eject` вместо S_approach | Тип тела/ID сохраняется, но формула не соответствует исходной фазе; видимый SVG продолжает печатать P1=P0+S_approach |
| `mutations/feed-open-without-path.json` | Из extra_entry A-MECH-FEED-OPEN удалён G_PATH_CLEAR | Открытие G1→G0 теряет опубликованное условие полного безопасного хода |
| `mutations/return-without-doser-path.json` | Из extra_entry A-MECH-DOSER-RETURN удалён D_PATH_CLEAR | Возврат дозатора больше не защищён собственным обязательным sweep predicate |
| `mutations/confirm-without-current-D1.json` | D_DELIVERY_CURRENT удалён из entry и completion FILL-CONFIRM | Текущая поза производителя квитанции остаётся только декларацией строки |
| `mutations/recovery-any-fault.json` | recovery_binding.target_fault_id = `ANY_FAULT` | Не проверяется требование точной адресации target metadata |
| `mutations/relock-without-lock-result.json` | Из completion RELOCK удалены LOCK_CLOSED_CURRENT и B_STOP_LOCK_CLOSED | Исчезновение обязательных подтверждений результата замыкания не отклонено |

Предъявлены **ошибочные документы**, не выполненные движения/PLC и не новые
native collisions. Нельзя трактовать MATCH как ALLOWED physical permission.
Текущее немутированное содержимое B01/B02 не содержит этих подмен: положительные
частные выводы сохраняются, но checker всё ещё пропускает их регрессию.

Необходимо согласовать проверяемый минимум predicates/outputs для каждой стадии,
типизированные pose/source formula relations и обязательные поля addressed
recovery. Проверять эти ограничения независимо от свежести хэшей и результата
того же renderer. Имена поз/наличие ссылочного каталога не доказывают правильности
формулы; синхронное обновление CSV/embedded data не устраняет противоречие.
Не требуется угадывать размеры/COTS, реализовывать PLC или расширять W02.

## Второй возврат и передача R1/R3/R4

Это второй последовательный REJECT по интерфейсному B03: OUTPUT 13b0fc3 и
настоящий RECHECK на C144941c. По **AGENT_PROTOCOL.md §6.1** корректирующая B03
итерация **BLOCKED** до решения R1 и записанного плана новой проверки.
Сохранён вопрос **Q-R1-CI-SEMANTICS-ARBITRATION-01**, arbitration_request.md;
reviewer не назначает себе R1 и не выбирает архитектуру/остаточный риск.
interface_consecutive_rejections=2. Прежняя история двух отказов material
contract B01 — отдельная, также сохранена; закрытие C0c4eb5d не переоткрывается.

- **R3:** четыре A-V1/A-V2/B-V1/B-V2 по-прежнему только WARNING для условной
  силовой постановки; нагрузки/ходы/D/d не уменьшены. Носитель/соединения,
  устойчивость, опоры, F·e/направляющие V2, возможное передаточное отношение,
  возврат/монтаж/сервисы требуют прежних расчётных входов и отдельных reviews.
- **R4:** исправленные документальные B01/B02 можно использовать в указанной
  области анализа; объединённый interface/checker не принят. Следующая B03
  итерация после R1; новая CAD-итерация также требует R3/R2 входов, а её native
  геометрия проверяется заново. Настоящий акт не разрешает rebuild.

## Сохранность и исключённые утверждения

preservation_during_checks.json: **1249 tracked files** неизменны во время проверок.
612 защищённых файлов, 7 frozen packages, 11 protected trees и 17 source blobs
сверены. Все **44 bindings**, baseline MD/JSON, force_variants MD/JSON и четыре
силовых SVG совпадают побайтно с исходным OUTPUT; расчёты/CAD/registry/checked
helpers/старый R5 probe неизменны. Поздние добавления review-meta допускаются
только в четырёх общих документах с сохранением полного старого H (preservation.json).

Численные расчёты, прочность/устойчивость, нативная геометрическая согласованность,
действительные clearance/контакты/монтаж/сервис, работа механизма, физический
баланс/продукт/выход/остаток не принимаются. CAD/solver/rebuild и физические
испытания **NOT_RUN**; проверенных геометрических пар **0**.
**W02 OPEN/NOT_IMPLEMENTED; executable material/physical READY NO-GO. G1 OPEN.**
Архитектура и ТЗ не утверждены; прежние SHORT_STROKE/clamp/reset/UP BLOCKED и
B opening/L/полный физический цикл INDETERMINATE сохраняются.
