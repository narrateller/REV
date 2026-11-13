# REV-R5-CI-MINIMUM-RECHECK-01-001

**B03 OPEN — REJECT_WITH_BLOCKER. Стабильная документальная передача
объединённого CYC-02/03 пока NO-GO.** Сам нормативный минимум и прежние шесть
исправлений подтверждены, но проверка типов ревизий допускает новые ложные
MATCH/TRUE. Ни один результат не означает разрешения реального движения.

R5 / Codex / session **r5-ci-minimum-20261113**, 13 ноября 2026, МСК.
Прямое поручение пользователя. Reviewer не автор норматива, payload или checker;
проверены авторские сессии r4-linked-20261111, r4-cyc-fix-20261113,
r4-b03-semantics-20261113. Организационная независимость не удостоверяется.

| Неизменяемый вход | Точный SHA |
|---|---|
| Проверенный C | **bd7ce8a623d6a4ecdff1f106868a4c7086a8a27f** |
| Эстафета H | **0e519720d55b5b7b19d66b5a90c699b5d6697338** |
| Решение ARB-R1-CI-SEMANTICS-01 | **5fe510bbc55a052c360ab39a2491a061584b8fb7** |
| Предыдущий RECHECK | 5fb731182a2bdf6b11246558eca58962e48568d9 |
| Предыдущий исправленный C | 144941cbfc67002cbe81765e38c80e237473deff |
| Исходный OUTPUT | 13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2 |
| Frozen material contract/helper | 0c4eb5d9362b9ad89c61c1a85af96a5d7d3235ed |

C/решение/предыдущие акты — предки H. 72 файла интерфейсного пакета совпадают
в C/H/рабочем дереве. Роль R1, R4 ownership/lease, main merge не присваивались.

## Норматив и независимость ожидаемых ограничений

SHA256 minimum.json:
`b1c13c18c408120ae66d4995eac706e8dbf5842f35976494efb682c74e64d3df`.

minimum.json расположен вне --package. semantic_minimum.py загружает его по
закреплённой ревизии/SHA; проверка не запускает builder. Builder воспроизведён
в отдельной временной копии, результат побайтно совпал (authority.json).
Он использует фиксированные blobs C144941c, C0c4eb5d и решение R1; таблицы
FAMILY/COMMON заданы отдельно от текущего permissions.json. Это устраняет
прежнюю возможность вывести норму из самого mutable payload/renderer.

Независимый audit **53 действий / 84 пар действие–режим / 18 поз**:

- собственные критические ENTRY/COMMIT требования семейств сформулированы из
  решения R1 и отдельно сверены с нормой; состояния/режимы/parent topology —
  по неизменяемому принятому документальному B01/B02 входу;
- все 84 строки coverage CSV/JSON согласованы с нормой и допустимыми parent
  **конкретного режима**, а не со списком родителей всех режимов одновременно;
- outputs сопоставлены с completion guards и конечными/удерживаемыми позами,
  actual UNKNOWN; parent lifecycle и исключение двух B recovery стадий сохранены;
- собственный полиномиальный oracle по неизменяемым 44 bindings сверил P1/P2/P3/
  P_RETURN_END для A/B, сохраняя фазовую идентичность return, не подменяя её
  численно нулевым итогом. Единицы/базы/phase refs типизированы в таблице;
- подложенный package-local минимум вместе с новыми metadata/hashes не становится
  источником ожиданий checker: такая согласованная подмена отклонена.

Проверка норматива не утверждает физической достаточности перечисленных условий,
реальности координат или полноты W02. Обнаруженные ниже дефекты — в применении
типов/сравнений, а не основание менять норматив ради PASS.

## Воспроизведение

Рабочая директория `/workspace/REV`, Python 3.12.14 из `.venv`. Полные команды,
зафиксированные exit codes и raw evidence — commands.json и указанные там файлы.

| Команда после `.venv/bin/python -B` | Итог |
|---|---|
| `verification/r4_cycle_interfaces/proposal/check_package.py` | **3277 MATCH**, gate PASSED_DOCUMENTARY_ONLY |
| `verification/r4_cycle_interfaces/proposal/check_exports_reproduction.py` | **8 MATCH**, явный экспорт повторяем, checker readonly |
| `-m unittest discover -s verification/r4_cycle_interfaces/semantic_iteration -p 'test_*.py' -v` | **6 методов OK**, 411 cases: 410 ожидаемых отрицательных и 1 эквивалентный MATCH |
| `-m unittest discover -s verification/r4_cycle_interfaces/correction -p 'test_*.py' -v` | **7 прежних методов OK**, включая LOAD/FILL/RETURN/COMMIT и recovery B |
| `verification/r5_ci_semantic_minimum_recheck/authority_and_regressions.py` | Минимум побайтно воспроизведён; прежний неизменённый независимый probe **654/654**, включая исходные 17 и шесть прежних подмен |
| `verification/r5_ci_semantic_minimum_recheck/independent_probe.py` | **765 проверок: 759 совпадений / 6 FAIL**, подробности ниже |
| `scripts/check_registry.py --check-git` | PASS; это согласованность repository evidence, не приёмка B03 |
| `git diff --check`, `git lfs fsck` | PASS |

Прежний probe выполнен в временной копии всех materialized tracked files с
существующей Git object DB только для чтения, без Git worktree. Он пишет только
во временную копию своего evidence. Поле reviewed_C=144941c в его raw stdout
исторически зашито в код; actual new input установлен capture/manifest, оно
не выдаётся за новую подпись исходного reviewer. Оригинальный пакет R5 не изменён.

Собственные **122** согласованно переэкспортированные случая:
117 правильных отказов, 1 правильный эквивалентный MATCH, **4 ложных MATCH**.
Для всех 53 действий независимо удалялись обязательный ENTRY и output; отдельно
повторены шесть прежних пропусков и другие formula/source случаи. Формулы,
подписи, AST/CSV/SVG/manifest менялись совместно; все source/export hashes свежие.
Результаты checker и отсутствие его записей сохранены. Ожидания опираются на
фиксированные входы/независимые правила, не на изменённую копию или renderer.

captured_mutations.json сохраняет фактически исполненный sweep/exit/hash evidence;
`--reuse-mutations` повторно сверяет неизменность target checker/нормы и агрегирует
его с независимым rule audit, не выдавая повторное чтение за новый запуск CLI.
Полный fresh запуск остаётся командой без этой опции. Exit 0 probe означает
завершённый **сбор**, не PASS: failed содержит шесть несоответствий. Нормализуется
только случайный temp-prefix в сравнении missing_svg export-suite, raw stdout
сохранён без изменения.

## B03 — оставшиеся типовые несоответствия

### 1. Boolean/float как типизированная ревизия фазового источника

После полного re-export/обновления JSON/CSV/SVG/MD/hashes все четыре получили
**exit 0 / semantic_outcome MATCH / PASSED_DOCUMENTARY_ONLY**:

| Evidence в mutations/ | Подмена |
|---|---|
| B-work-bool-revision.json | B-MECH-WORK: phase time source ref revision `1 → true` |
| A-return-float-revision.json | A-RETURN: phase source revision `1 → 1.0` |
| B-P3-bool-AST.json | P3 / BASE_B: eject AST source_ref revision `1 → true` |
| A-phase-binding-bool.json | A-MECH-APPROACH: phase_pose_bindings stroke_source revision `1 → true` |

Ни один source ID, исходный численный каталог или норматив не менялся. Подмена
в других стадиях/сценариях осталась типовой ошибкой provenance, а не ослаблением
только одной из прежних шести строк. Независимый строгий JSON/type comparison
различает эти записи; текущие сравнения Python dict/list через `==` — нет:
`True == 1`, `1.0 == 1`. Expressions.node, сравнение phase bindings и старый
phase ref comparator используют такую равенство-проверку без строгой проверки
типа revision. Это не поддержанная линейная нормализация формулы.

Boolean не является ревизией integer. Для float требуется явная политика схемы/
канонизации, которой здесь не объявлено; молчаливое Python coercion недостаточно.
Нужен типизированный source/ref validator и сравнение с нормативом с учётом
типов, включая вложенные AST/phase bindings. Не менять ID/нагрузки/ходы/минимум,
чтобы сделать ошибочный payload допустимым.

### 2. Новый recovery_value расходится с frozen policy

На собственном конкретном fault B_RESET_CONFIRMED origin revision B_CLOSURE=0
валидный proof получает TRUE и согласуется с frozen helper. Затем меняется
**только** origin_revisions: значение 0 заменено на `false` либо `0.0`.

| Проверка | bool false | float 0.0 |
|---|---|---|
| Ожидание по типам exact origin frozen helper | UNKNOWN/не восстановлен | UNKNOWN/не восстановлен |
| semantic_minimum.recovery_value | **TRUE** | **TRUE** |
| Неизменённый helper.recover на том же proof | **INDETERMINATE**, fault OPEN | **INDETERMINATE**, fault OPEN |

Proof/context/actual/frozen outcomes — independent_results.json,
`typed-origin:boolean-False` и `typed-origin:float-zero`.
Причина: dict equality request.origin_revisions и fault.origin.revisions
не различает bool/float/int; `_raw_value` проверяет текущие revisions, но не
исправляет этот пропуск в original revisions. Frozen recover прямо проверяет
`type(origin_revision) is int` и отклоняет подмену.

recovery_value ничего не снимает и исходный context не меняет. Фактического
амнистирования fault, выдачи команды или физического разрешения **не было**.
Но TRUE reference predicate для запроса, не соответствующего принятому policy,
не подтверждает заявленный адресный контракт. Требуется согласовать строгую
проверку с frozen helper, сохранив readonly/историю/rejected IDs и положительный
корректный путь. Ранее закрытый B02 на C144941c не переоткрывается автоматически;
это дефект новой B03 reference-проверки.

## Отдельные вердикты и последующая передача

**B03 OPEN / REJECT_WITH_BLOCKER.** Независимость источника нормы, покрытие
53/84 и отказы шести прежних подмен подтверждены. Тем не менее типовые подмены
новых стадий не отвергнуты, а concrete predicate не эквивалентен frozen policy.

**Стабильная документальная передача CYC-02/03 — NO-GO до исправления B03 и
независимого RECHECK точного нового C.** Неизменяемый кандидат можно использовать
только для ограниченного документального анализа/R3 force-path study с WARNING.
B01/B02 сохраняют прежнее документальное закрытие: положительные LOAD/FILL/
RETURN/COMMIT и адресное восстановление B без общего dependency тупика прошли,
чужие faults и rejected IDs не очищаются, штатная WORK не получает обхода.

По R1 ARB-R1-CI-SEMANTICS-01 принят нормативный подход, но его требование строгого
типизированного соответствия ещё не выполнено. R1 follow-up — R1_followup.md,
тот же Q-R1-CI-SEMANTICS-ARBITRATION-01. Два прежних REJECT 13b0fc3/5fb7311
сохранены без переписывания; текущий после R1 — третий, counter=3, не сброс до 0.
По AGENT_PROTOCOL §6.1 следующая корректирующая итерация BLOCKED до записанного
R1 решения/уточнённого плана; reviewer не выбирает архитектуру и не исправляет
исходный checker сам. Отдельный material-contract counter=2 также сохранён.

## Сохранность и границы

1328 tracked файлов сохранены во время checks; 612 protected files, 7 frozen
packages, 11 protected trees и 17 input blobs сверены. 44 bindings, четыре
force-варианта и их SVG/MD/JSON побайтно прежние; frozen material helper,
расчёты/CAD/registry/источники/оба предыдущих R5/R1 акта неизменны. identity C/H
всех 72 файлов пакета сохранена. Поздние добавления review-meta только в четырёх
общих документах с полным старым текстом H (preservation.json).

Ни норматив, ни algebra/AST MATCH не доказывают прочность, устойчивость,
геометрическую согласованность, отсутствие нативных проникновений или сервисный
доступ. Native CAD/solver/rebuild/physical trials **NOT_RUN**, geometric pairs
checked **0**. Все четыре A-V1/A-V2/B-V1/B-V2 не выбраны и остаются WARNING для R3;
новая CAD-итерация/приёмка требует прежних R2/R3/geometry входов и отдельных актов.
**W02 OPEN/NOT_IMPLEMENTED, executable material/physical READY NO-GO; G1 OPEN.**
Архитектура/ТЗ не утверждены, прежние UNKNOWN/SHORT_STROKE/clamp/reset/UP BLOCKED
и B opening/L/полный физический цикл INDETERMINATE не закрываются.
