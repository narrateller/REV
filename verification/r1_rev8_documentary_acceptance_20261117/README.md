# R1 — принятие rev8 только как предварительного DRAFT с WARNING

Target C8d1b45afa84eca078a8de0a9822d6925dd87745b / request H87f2f5889f9ba74e8eef3a3a040d936d13e0a011.
Новый независимый R5 C04502cfe2eb2eadae242690cfad8f414bd96bff2 /
H64ac3efbffcf77e50f2e867390cf141e580de644, reviewed_commit ровно target C.
Акт REV-R5-REQUIREMENTS-REV8-OUTPUT-01-001 CURRENT/WARNING, собственные3890 PASS/0FAIL,
22 REQ/VAL assessments,40 dispositions,16 qualitative assessments. Target не менялся.
Source act853a по f2c остаётся отдельным входом, не подменяет этот OUTPUT-review.

R5 session6afb0a73-b16c-8191-a539-9a6685e89034 вне author_sessions target R1
6afb300b-1540-8191-a5c4-be1a684c20e0. Upstream authorship раскрыт; собственные ранние
акты не переаттестованы независимо. Организационная независимость не удостоверяется.
Авторские358/source1250 и replay10 не считаются независимым review новой ревизии.

Решение decisions/R1-REQUIREMENTS-REV8-DRAFT-ACCEPTANCE.md: gate null,
APPROVED_WITH_LIMITATIONS только для дальнейшей документальной проработки.
Для ТЗ/G1 недостаточно: B01 критерии/допуски/режимы/владельцы, B02 программа/
метрология/неопределённость/полнота, B03 безопасность/нормативная применимость,
source power/pressure/moisture вопросы остаются OPEN. Неизвестные данные не заменены.
Task metadata получила фактический WARNING review; её прежний exact snapshot
сохранён в task_before_disposition.json. Operational task/state не меняют target.

История R5 включена обычным local no-ff merge в PR54 working branch: original
head87f является ancestor R5C→H; конфликтов нет, ours/theirs не применялись.
Новая C содержит решение/evidence и обоих родителей; следующая H добавляет
эстафету с exact C. Main bec317a4483e7f69c2af0aa1c52ef091bdef57b4 не меняется,
PR54 draft/OPEN; merge/auto-merge не выполняются. После пользовательской команды
main/head/CI/owner/срок проверяются заново. Новый claim/lease здесь не создаются.
R1 owner/исходный deadline2026-11-18T01:58:30.990734+00:00 подтверждены, intake released.

remote_preflight.json и R5_C/H_CI.json/summary: exact C/H publication, оба CI SUCCESS,
registry PASS и по100 тестов. Это R1 повторная проверка публикации, не новый R5 oracle.
Старый R5 check_publication.py закрепляет тогдашний PR head87f; после обновления
PR54 его head-assert относится к историческому checkpoint. Использовать новый
операционный receipt, не переписывать старое evidence для получения PASS.

verify_acceptance.py / integration_checks.json:280 PASS/0FAIL. Проверены exact target25,
formal review26 artifacts, R5 seals/files/identity/results, journal exact append,
54 старых pins,12 protected trees (только новый formal review в journal),59 LFS
materialized SHA/OID,44 full bindings/loads/strokes/CAD и полные52/42/84/15 объекты.
Это R1 consistency проверка сохранности, не независимый review или физический расчёт.
registry.log/status — фактический root --check-git; итоговый head CI проверяется после push.

handoff_typography_note.json сохраняет наблюдение об UNK<UTC>N template-токенах
в историческом R5 H STATE/NEXT. Core act, H capsule и оригинальные UNKNOWN данные
корректны; R5 H сохранён побайтно, новая R1 текущая сводка пишет UNKNOWN корректно.

40 scoped RAW не повышены,10 target proposals не approved параметры. BP500 primary,
площадка адаптируется, E55/WEIMA/ARS по релевантности; ARS допускает неметаллическое
сырьё, чужие уставки/свойства не REV. Старые REJECT/STALE/material2/четыре FAIL/
OBS01 exact-C closure сохранены; WHAT_IF applicability NOT_EVALUATED.
42 состояния не рассчитаны; §4/5/6 NOT_RUN, прочность/устойчивость/реальные реакции/
цикл не подтверждены. Архитектура/ТЗ NOT_APPROVED, G1 OPEN, W02/physical READY NO-GO.
Численный/физический этап, CAD-build/rebuild, физические испытания не разрешены.

Следующий документальный шаг описан в next_step_plan.md; это план без назначений
других сессий/сроков и без запуска новой инженерной стадии.
