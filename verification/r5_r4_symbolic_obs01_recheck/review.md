# REV-R5-R4-SYM-OBS01-RECHECK-01-001

**R5-SYM-OBS-01: CLOSED / PASS_DOCUMENTARY_EXACT_C** на
`beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe`.
**Общая поставка остаётся WARNING / DOCUMENTARY_SYMBOLIC_ONLY.**
Закрыто только замечание о четырёх межветочных ссылках; численная/физическая
стадия, CAD-build/rebuild, испытания и выпуск не разрешены.

## Точные версии, роль и независимость

| Объект | SHA |
|---|---|
| Новый target R4 C | beb4cf4ebcf6a99d3271a1560bdbd19caee8adfe |
| Новый request H | 47db9013c3cf3756987cdb480850cc0487c59b1e |
| База отдельной ветки R5 — coordination H | 1d5e2a8ed3c9be340897d6485c7a4383edf62152 |
| Команда R1 | 57e6cd452e3567f837bb95af041b3514e0ce437e |
| Correction authority R1 | e380f6d05fe58fe5125c940ac90a151c5bba546b |
| Исходный R4 C / H | b840dfd5444da2bf62483b7f4a6069d2bb255b71 / 9433ef749df14a3bbf8ea32331e2f895fd5bf7aa |
| Исходный R5 C / H | 4aa23509b45efc2c2c166935102ca5caa76f55e2 / 92230cef87b71aa7e2d51fe6f21c11360331dd37 |
| Observed main | f731910273b47f46c6d45114cecd76de6fa8adf9 |
| PR49 acceptance | cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9 |

R5 / Codex на базе GPT-6, exact runtime model ID недоступен. Фактические
CODEX_SESSION_ID/CODEX_THREAD_ID: **6afb0a73-b16c-8191-a539-9a6685e89034**.
Назначение — текущий прямой запрос пользователя продолжить R5. identity.json
записан до содержательных проверок. Инструменты: Git/GitHub API, Bash,
Python/PyYAML только для документов/хэшей; физический/численный решатель не запускался.

Это тот же reviewer, который выпустил исходный акт, не автор R4
6afb4750-7918-8191-8569-77b5b0c41050 и не координатор r1-pr48-integration-20261116.
Коррекцию R4/решение R1 я не создавал. Авторство прежнего upstream-акта R5
`db6b9774649f99ad1b157cba2a9c7cdeec570302` раскрыто повторно; его правильность
не подтверждается здесь заново независимо. Собственные исходные четыре
наблюдения — история review, а не соавторство исправления. Организационная
независимость не удостоверяется и не выводится из смены псевдонима/роли.

Прочитаны команда, STATE/NEXT, своя капсула, claim/запрос нового recheck,
исходный акт и correction authority. Новый H — прямой потомок target C.
Свежие main и PR49 прочитаны через Git/GitHub API. На неизменной main один
наблюдаемый ACCEPTED_MAIN claim этой задачи с прежним owner и lease
**2026-11-17T17:44:00Z**; открытых PR при проверке нет. Author start/end/precommit
и commit C зафиксированы до срока; lease не продлён. Неопубликованная работа
не наблюдаема; enforcement PROCEDURAL. R4-only preflight/session spoofing не
выполнялись. Review immutable C не возобновляет работу R4 и не меняет его claim.

## Независимый метод и четыре результата

Новый `recheck.py` сравнивает immutable старые/новые blobs. Исходный oracle не
редактируется и не получает простую подмену SHA. Ожидаемая новая структура
выводится как старый документ минус точно четыре выбранные ссылки; порядок,
все прочие поля и сериализация проверяются отдельно. Код автора не является oracle.
Финальный набор: **388 PASS / 0 FAIL**. Первичный собственный прогон 354 PASS
расширен проверками сохранности старых symbolic evidence и assertions verifier;
финальное evidence — independent_final.json, исходный прогон сохранён отдельно.

| row_key | Удалён чужой ID | Сохранён собственный ID | Итог |
|---|---|---|---|
| A-V1/datum_motion | CI-X_B_GATHER | CI-X_COLUMN_GATHER | PASS |
| A-V2/datum_motion | CI-X_B_GATHER | CI-X_COLUMN_GATHER | PASS |
| B-V1/datum_motion | CI-X_COLUMN_GATHER | CI-X_B_GATHER | PASS |
| B-V2/datum_motion | CI-X_COLUMN_GATHER | CI-X_B_GATHER | PASS |

В каждой строке удалён ровно один ref. Все оставшиеся refs (порядок/значения),
все остальные поля этих четырёх строк и остальные **48 полных строк** равны
старому C. 52 row keys/order и metadata неизменны. Полный interfaces.json
побайтно равен ожидаемой сериализации старого документа с четырьмя удалениями.
В interfaces.md изменены только те же четыре фрагмента; остальной текст прежний.
Генератор отличается только трёхстрочным фильтром datum_motion по семье.
Verifier только добавляет проверки: исходные assertions не удалены/не ослаблены.

Master unknown_inputs.json и source_catalog.json побайтно сохранены, оба CI ID
остаются в мастер-каталоге. Выбран режим удаления, а не comparison-only флаг.
Смысл CI-X_COLUMN_GATHER — создание столба A; CI-X_B_GATHER — partial gather B.
Исправление устраняет ровно исходную неоднозначность применения чужой ветви.
Ввода новых фазовых сил, контактов, чисел или разрешений движения нет.

## Отрицательные контроли и supplemental replay

Собственный тот же family-applicability predicate на старом C даёт четыре
**FAIL_EXPECTED**, на новом — четыре PASS. Row keys совпадают с четырьмя
историческими независимыми FAIL исходного independent.json (2422 PASS / 4 FAIL).
Исходный oracle/акт/доказательства R5 не менялись и не запускались на новом C
под видом готового recheck.

Авторский negative control даёт **1337 PASS / 8 FAIL**: на каждой из тех же
четырёх строк падают foreign_absent и only_one_ref_removed. Это восемь
предикатов про четыре прежних дефекта, не восемь новых независимых замечаний.
Его результат сопоставлен с историей и воспроизведён corrected verifier на
старых таблицах в temporary HERE, с ожидаемым returncode 1. Новый target
авторский verifier воспроизводит с **1341 PASS**, returncode 0. Эти проверки
вспомогательны и не заменяют 388 собственных PASS.

Детерминированный renderer с HERE в temporary directory даёт **7 MATCH** с
новым C; author-файлы не перезаписываются. document_replay.json содержит команды,
коды положительного/отрицательного control и контрольные хэши. Чужой
CODEX_SESSION_ID не подставлялся; session environment не менялось.

## Сохранность остального и обеих историй

- **54** pinned inputs: SHA256 исходного commit и bytes old/new/new H/coord H
  совпадают. **12 исходных trees** на old/new R4 C/H сохранены. Нагрузки, ходы,
  CAD, active registry, fixed-budget и **44 полных bindings** неизменны.
- **42 полных source-state objects** и добавленные NOT_RUN/null поля неизменны;
  состояния не решены. **84 RAW/null** сохранены без повышения зрелости.
- symbolic_dependencies, unknown_index, source_catalog, state_dependencies
  неизменны. Следовательно, обе плоскости/полный, частичный и промежуточный ход,
  A startup/retention, B unload/unlock/open/reset, ограничения GUIDE/EULER,
  отсутствие нулевой несоосности V1/деления силы V2 не ослаблены.
- Полный перечень 45 изменённых target-файлов соответствует change_manifest.
  Claim меняет только раскрытые служебные поля; owner/lease/scope/exclusions
  прежние, author OBS всё ещё OPEN/pending independent recheck как snapshot.
  Task/claim.md раскрывают именно эту ограниченную коррекцию, не расширение стадии.
- **8 архивных файлов** archive_b840dfd побайтно совпадают со старым C.
  Все прочие старые symbolic файлы/evidence и весь исходный reviewer package
  сохранены. Старые 2422 PASS/4 FAIL не ретушировались.
- Сам target R4 C сохранил исходный reviews. В coordination H прежний R5 record
  сохранён дословно в original_review_record.md; старый journal prefix прежний.
  Единственное изменение активной исторической записи — validity CURRENT→STALE.
  Verdict WARNING, checks и finding OPEN/P2 не изменены. Новый акт отдельно
  закрывает OBS-01; старая запись **остаётся STALE**, не легализует новый target.
- Исторический первый registry FAIL (artifact hash mismatch interfaces.json,
  returncode 1) и его timestamps сохранены. Это причина нормализации STALE,
  а не основание скрывать ошибку или считать замечание автоматически закрытым.

Новых FAIL/неоднозначностей или ослабленных ограничений в зависимом объёме
не обнаружено. Собственная проверка ограничена targeted delta/preservation;
она не объявляет всю физическую постановку заново проверенной.

## Реестр, CI и команды

Фактические команды/exit codes/хэши — validation.json. Root registry --check-git
запускается на review-ветке после добавления нового акта, старый STALE остаётся.
CI exact source C beb4cf4 и H 47db901 — completed/success по свежему GitHub API;
head_sha каждого check-run совпал с запрошенным SHA (source_C_H_CI.json).
Исторические author/R1 PASS не подменяют новые проверки. CI собственного
публикуемого C/H проверяется после push; не приписывается source-результатам.

Из /workspace/REV, с новыми --output путями:

```bash
.venv/bin/python verification/r5_r4_symbolic_obs01_recheck/recheck.py --output /tmp/r5-obs01-fresh.json
.venv/bin/python verification/r5_r4_symbolic_obs01_recheck/replay_documents.py --output /tmp/r5-obs01-replay-fresh.json --artifacts-dir /tmp/r5-obs01-artifacts-fresh
.venv/bin/python scripts/check_registry.py --check-git
git diff --check
```

Replay сохраняет author_positive.json/author_negative_old.json в --artifacts-dir;
используйте новый каталог при повторении. Renderer всегда получает temporary HERE,
поэтому авторские таблицы/evidence не перезаписываются.
Исторические файлы не перезаписываются. Registry/CI проверяют согласованность,
а не подтверждают физические реакции/прочность/устойчивость.

## Решение и передача R1

**OBS-01 CLOSED / PASS только на exact новом C. Общий WARNING сохраняется.**
R1 получает отдельные C/H этого акта и результаты по четырём строкам; main не
сливалась. Исправление даёт ясную семейную применимость row-local ссылок,
не автоматически исполнимый физический граф и не новую инженерную стадию.
Исторические OPEN/pending значения в неизменяемых старых C остаются историей.
Новые изменения исправленных строк потребуют проверки затронутого exact C.

42 состояния не рассчитаны; §4/5/6 NOT_RUN; реальные отсутствующие данные
UNKNOWN. Прочность, устойчивость, реальные реакции/capacity/margins и полный
цикл не подтверждены. Архитектура/ТЗ NOT_APPROVED; G1 OPEN; W02/PLC/physical READY
NO-GO. CAD-build/rebuild, численные/физические расчёты, испытания/выпуск запрещены.
Старые блокеры, семь REJECT и material history=2 не закрыты/не сброшены.
R4 не объявлена DONE/VERIFIED/LOCKED/PASSED; owner/срок не менялись.
