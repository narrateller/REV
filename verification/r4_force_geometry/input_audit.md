# Входной аудит §6 — T-r4-force-geometry-01

Акт AUD-R4-FORCE-GEOMETRY-INPUT-01; R4 / Codex (GPT-6 base; exact runtime ID недоступен) /
6afb4750-7918-8191-8569-77b5b0c41050. UTC 2026-11-16T19:06:35.347398+00:00. Author_sessions: только указанная сессия.
Прямое назначение и выполнение preflight/аудита разрешены пользователем.

Точная fetched main: `f731910273b47f46c6d45114cecd76de6fa8adf9`. PR49 acceptance:
`cd1c08efc4bcd3f50ceeb132a3e8747e9c8c38b9`, reviewed head
`70ab9a1926235170e449b85d558f135ddae90add`. Owner совпадает; срок до
`2026-11-17T17:44:00Z` не продлён. 138 preflight checks PASS;
54 pinned inputs/12 trees/44 full bindings, 706 materialized files (48 LFS) MATCH.
Точные версии каждого входа — input_manifest.json и preflight_20261116/checks/.
Источник административных документов — fetched main, не исторические proposal NONE/null.

**Вердикт WARNING.** Семь пунктов рассмотрены: 4 PASS / 0 FAIL /
0 NOT_APPLICABLE / 3 NOT_RUN. Аудит как документ завершён; это не полный PASS
инженерных входов. PASS в строках 1/2/3/7 относится только к явно описанной
проверке согласованности. UNKNOWN и непроверенные подпункты не получают PASS.

| §6 | Проверка | Статус | Основание и точные входы | Оставшееся ограничение |
|---|---|---|---|---|
| 1 | Требования и границы | PASS | Прочитаны точные task/DoD и решение R1: только условная постановка A-V1/A-V2/B-V1/B-V2, без выбора архитектуры, изменения baseline, CAD-rebuild или физического READY. Верификация согласованности отделена от физической валидации. Источники: task.md; verification/pr48_integration/R4_task_proposal.md; decisions/R1-FORCE-PATH-CONDITIONAL-ACCEPTANCE.md. | Полнота ТЗ/физическая пригодность изделия не подтверждены; архитектура/ТЗ NOT_APPROVED. |
| 2 | Источники и происхождение | PASS | 54 pinned файла, commit/blob/SHA256 и current main/worktree совпали. 44 полные строки совпали со snapshot, активным registry и source calculation inputs/outputs. Проверены source locators в определениях; источники — условные вычисления BASE_A/B, не измерения аналога. DEMO не подставляется. Источники: input_manifest.json; preflight_20261116/checks/preflight.json; preflight_20261116/checks/bindings.json; verification/r3_force_path/input_gaps.md. | Физические источники геометрии, фазовых нагрузок, материалов и паспортные COTS UNKNOWN; внешние первоисточники заново не валидировались. |
| 3 | Размерности, знаки, координаты и диапазоны | PASS | Для 44 привязок проверены value/unit/revision/lifecycle/validity/engineering hash, fixed-budget, NOT_APPLIED и размерности m, m/s, s, N. Приняты только объявленные оси +x к выходу, +y к цилиндру V2, +z вверх, N>0 растяжение. Давления в исходном registry остаются условными inlet/backpressure (обратная полость явно gauge), не реальным рабочим перепадом. Источники: preflight_20261116/checks/bindings.json; verification/r3_force_path/analysis/free_bodies.md; params/registry.yaml. | PASS только документальной согласованности. Фактические базы/нулевые положения, gauge/absolute для реальной установки, допуски, неопределённости и диапазоны эксплуатации UNKNOWN/NOT_RUN. V1 не получает нулевую несоосность. |
| 4 | Независимый пересчёт и физические балансы | NOT_RUN | Получен неизменённый независимый акт R5 на R3 C 93b4aead4983f88919d8e8b4165e29d7f3246600: исторические 26/26 и 204 checks только условной арифметики. Точная версия/хэши/ancestry акта сверены. Это входное доказательство R5, а не новый пересчёт R4. Источники: verification/r5_force_path_output_review/review.md; verification/r5_force_path_output_review/validation.json; verification/r3_force_path/analysis/free_bodies.md. | В этой поставке независимый пересчёт R4, новый расчёт геометрии/сил/балансов не запускались. Реальные F(q,t), инерция, трение, жёсткости/материалы и критерии UNKNOWN; физические балансы/прочность/устойчивость не имеют PASS. |
| 5 | Геометрия, связи и граничные условия | NOT_RUN | Перечень требуемых опор, e(q)/L_free(q), отдельных сечений, двусторонних joints и контактов прочитан. 12 защищённых деревьев/706 файлов, в том числе 48 LFS, совпали; существующий CAD не менялся. Источники: verification/r3_force_path/input_gaps.md; verification/r3_force_path/analysis/free_bodies.md; verification/r5_force_path_output_review/review.md. | Фактические e_y/e_z(q), свободные длины по всему ходу, опоры, люфты, закрепления, материалы/E, сечения, COTS и полный collision/sweep UNKNOWN. Геометрия не строилась; импорт FreeCAD не является такой проверкой. Реакции/запасы NOT_RUN. |
| 6 | Циклограмма, ресурсы и отказные состояния | NOT_RUN | Fixed-budget и source strokes/loads/speeds/times сохранены. Проверено, что все 42 строки — UNKNOWN с null actual_force/moment/joint_support_loads, а не решённые состояния. Источники: verification/r3_force_path/analysis/state_matrix.json; verification/r3_power_reconcile/results/BASE_A.json; verification/r3_power_reconcile/results/BASE_B.json; verification/r4_cycle_interfaces/proposal/R2_R3_requests.md. | Фазовые нагрузки/реакции и ресурсы/паузы/аварии не проверены физически. A startup/retention и B unload/unlock/open/reset, приёмник/остатки, полный цикл и READY NOT_RUN. Source peak не назначен каждой фазе; несовместимые производительности не суммируются. |
| 7 | Прослеживаемость и воспроизводимость | PASS | Для проверенной области цепочка task/ограничение R1 → точные R3/R5 C/H → ID@revision/hash/source → исходный результат/акт → критерий и статус сохранена. Новый аудит и команды отделены от исторических проверок; новые инженерные ID/размеры не вводились. Источники: input_manifest.json; preflight_20261116/checks/commands.json; preflight_20261116/checks/bindings.json; preflight_20261116/checks/preflight.json; verification/r5_force_path_output_review/review.md. | PASS не означает полноту физической трассировки или независимый review этого аудита. Будущий инженерный C требует независимого R5 вне author_sessions; C аудита будет закреплён отдельным H. |

## Граница дальнейшей работы

Достаточно только для документальной/символической условной постановки и перечня
недостающих входов A-V1/A-V2/B-V1/B-V2 по уже принятому WARNING task.md.
NOT_RUN в §4/5/6 блокируют зависимые физические/численные выводы: этот акт
не разрешает расчёт capacity/margins, фактической прочности/устойчивости/реакций,
collision CLEAR или физического цикла. В этой поставке геометрия/расчёты NOT_STARTED.
Для будущей численной оценки требуются доказанные либо отдельно зарегистрированные
ASSUMED входы с ID/revision/основанием/областью и повторная проверка применимых пунктов.
Новые гипотезы/численные размеры сейчас не регистрировались.

R4/R3: базы/оси узлов, e(q)/L_free(q)/опоры по полным и промежуточным позам;
R2/R3: фазовые силы/контакты/инерция, A startup/retention, B unload/reset, приёмник;
R3/R4/R6: двусторонние joints, COTS/материалы/люфты/жёсткости;
R5/R6/R1: применимость, критерии прочности/устойчивости и технология.
Это функциональные адресаты получения данных, не назначения чужих claims/сроков.

Все семь пунктов применимы: отсутствие проверки не названо NOT_APPLICABLE.
Исторический независимый R5 акт прочитан и сверены его байты; его oracle/авторские
скрипты/тесты здесь не запускались и их прошлые результаты не выдаются за новый run.
Самопроверка R4 не независимый OUTPUT review; новый инженерный C потребует exact
review независимого R5 вне author_sessions. Активный registry, scoped R3F, source
нагрузки/ходы/fixed-budget, существующий CAD и исторические акты не меняются.

42 состояния не рассчитаны, 84 RAW/null сохранены. SHORT_STROKE, A clamp contacts,
B reset/product collision, legacy UP, physical L/B opening, семь REJECT и
material history=2 не закрываются. G1 OPEN; W02/PLC/physical READY NO-GO;
архитектура/ТЗ NOT_APPROVED; общий CAD-rebuild/испытания/выпуск не разрешены.

## Доказательства и воспроизведение

- preflight_20261116/checks/preflight.json — 138 проверок с evidence и UTC.
- checks/bindings.json — все 44 исходные строки и ссылки/определения registry.
- checks/preservation.json — 706 SHA256, в том числе проверенные LFS байты/size.
- checks/competition.json — текущие main claims и live open PRs (пустой список);
  неопубликованные чужие работы не наблюдаемы, enforcement PROCEDURAL.
- checks/commands.json — команды/exit codes; input_audit.json — машинный акт.
- heartbeat_start.json и heartbeat_end.json — фактические записи R4, без продления.
- active_registry.log/status.json — отдельный текущий run проверки согласованности;
  его код не переносится с прежнего CI и не подтверждает инженерную пригодность.

Из /workspace/REV повторная проверка входов (новый output не перезаписывает evidence):

```bash
git fetch --no-tags origin main
.venv/bin/python verification/r4_force_geometry/preflight_20261116/verify_inputs.py --output /tmp/r4-force-geometry-preflight-new
.venv/bin/python scripts/check_registry.py --check-git
git diff --check
```

При иной main helper выдаёт FAIL для pinned audited base: сначала перечитать diff,
владельца/срок/конкуренцию и обновить аудит новой точной версии, не обходить проверку.
Оригинальный verify_claim.py — сохранённая проверка состояния до heartbeat/аудита;
он закономерно требует null heartbeat и не является валидатором новой стадии.
Его историю и evidence не переписываем.
