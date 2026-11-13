# ARB-R1-CI-SEMANTICS-04 — композиция gate без потери известного запрета

R1 / codex-01; Q-R1-CI-SEMANTICS-ARBITRATION-01; T-r4-cycle-interfaces-01.
База main `3a9258c57e4bc15d6de98f1d17e8412ad6e8899a`.
R1 lease до 2026-11-13T22:14:32Z, R4 до 2026-11-14T00:13:12.404899Z;
продления этим решением нет. Уточнение решения
`39826eb2f5dbd1f83d81882022e6f59313ebe5d5` в той же области и полномочиях.

## Доказательства и причина

Акт `88a34f8b7d2d6dbf236101f207e206efb0e3c747` на C
`e30b4b7caf3040905cc23c79ca696af2871c958a`, H
`ff050572f88f108c2092827e98cd4d98bd874737`: предыдущие четыре false TRUE
исправлены, domain admission подтверждена, но ранние returns теряют known
BLOCKED общего gate. Это пятый REJECT, counter=5; прежние акты и отдельная
история material-contract counter=2 сохраняются без обнуления.

R1 в изолированной копии H акта
`f0c9fa423cf50c776db7f6355af8a0f06f7e9306` выполнил unchanged R5:
`reproduce_blocked.py` (два минимальных свидетеля, 0/2 ожидаемых BLOCKED) и
`independent_probe.py` (295 случаев: 276 совпадений, 19 неверных gate).
Воспроизведены те же две ветви и варианты R5:

- proof целиком null/array/string/bool/number возвращает initial INDETERMINATE
  до оценки доказанного собственного resource/state запрета;
- missing/foreign proof action/guard возвращает finish до оценки известного
  OPEN causal ancestor уже достоверно адресованного fault.

В обоих минимальных случаях scoped recovery UNKNOWN корректен; общий gate
должен BLOCKED. Caller/proof не менялись. Никаких новых ложных TRUE не найдено
в этой матрице. Это не 19 различных физических неисправностей и не новая
независимая приёмка исправления. Evidence: `verification/r1_ci_gate_arbitration/`.

## Решение

Выбран вариант A из follow-up R5: независимая оценка достоверных own ENTRY/state
и адресных causal prohibitions и **единая финальная композиция на всех путях**.
Вариант объявлять весь gate UNKNOWN из-за любого malformed proof отклонён как
ослабляющий уже принятый критерий. Frozen helper, норматив 53/84, нагрузки,
расчёты/CAD и W02 не изменяются.

R4 разрешена узкая корректирующая итерация B03 после чтения точного SHA решения,
записи в капсуле и проверки main/owner/lease/входов. Приёмка BLOCKED, стабильный
CYC-02/03 handoff и новый CAD-rebuild NO-GO до независимого RECHECK. R1 не
закрывает B03. B01/B02 и прежние type/domain исправления сохраняются с областью
исходных SHA и регрессиями новой версии.

## Обязательная структура оценки

1. Разделить входную пригодность proof, оценку собственных ENTRY/state,
   адресные causal constraints, scoped recovery value и action_gate. Повреждение
   одного входа не уничтожает уже доступное независимое доказательство запрета.
   Поля/reasons и надёжность источников сохраняются отдельно.
2. Достоверный контекст и фиксированная поддерживаемая action позволяют оценить
   её собственные state/guard условия **независимо от формы proof**. Для
   отсутствующего/не-object proof scoped recovery UNKNOWN, но known resource
   record, latched own fault или неподходящее состояние по этому action
   сохраняют общий BLOCKED. Не вызывать небезопасные обращения к полям proof;
   ошибка schema не заменяет уже известные результаты общим default UNKNOWN.
3. Causal оценка возможна только по достоверному target ID и проверенной
   causal history. Если target достоверно найден и его causal ancestor OPEN,
   missing/wrong action/guard proof не скрывает этот запрет. Если target
   отсутствует или неидентифицируем, не придумывать fault, не сканировать
   произвольные чужие faults как основание causal BLOCKED: causal UNKNOWN.
4. Сохранить границы собственных guards: наличие любого постороннего fault не
   запрещает автоматически любой восстановительный аудит. Использовать fixed
   action conditions и адресные связи, уже согласованные B01/B02 и frozen
   policy. Не вводить общий READY/DEPENDENCY_VALID до восстановления его цели.
5. Провести все ветви результата через одно логически эквивалентное завершение
   оценки. Ранние schema/dispatch отказы допустимы лишь если они всё равно
   сохраняют независимые известные запреты; отдельный первоначальный result
   не может обходить итоговую композицию. Исключения/неподдержанные данные не
   дают успеха, но сами по себе не превращаются в доказанный физический отказ.

| Независимые обязательные основания | Proof/scoped recovery | Общий action gate |
|---|---|---|
| Есть достоверный собственный или адресный causal FALSE | Любой, включая UNKNOWN/malformed | BLOCKED с сохранением всех причин |
| Достоверного FALSE нет, хотя бы одно необходимое основание UNKNOWN | Не подтверждён | INDETERMINATE |
| Все необходимые основания подтверждены и proof допустим, recovery TRUE | TRUE | ALLOWED_ASSUMED только в объявленной документальной области |
| Нельзя достоверно оценить контекст/action/target | Неизвестно | Не успех; не выдумывать known FALSE |

Использовать UNKNOWN как диагностический scoped/input результат и одновременно
BLOCKED как составной gate допустимо и требуется для показанных случаев.
Это не противоречие и не необходимость менять нормы snapshots. Согласование
с frozen policy сохраняет прежнюю IN_DOMAIN-область; для внеобластных proof
составной критерий известного запрета действует отдельно от equality policy.

## План независимого RECHECK

R4 публикует точный C, схему оценки/ветвей и матрицу покрытия. Не ограничиваться
исправлением двух конкретных return: проверить все пути выхода, exception и
schema-branches в объявленной области. Независимый R5 проверяет:

- два минимальных witnesses и все 19 вариаций: known FALSE сохраняет gate BLOCKED;
- proof null/array/string/bool/number × own TRUE/FALSE/UNKNOWN, включая resource
  record, latched own fault, состояние, сочетания двух собственных условий;
- known target+OPEN causal ancestor × missing/foreign action/guard; RESOLVED и
  UNKNOWN ancestors отдельно, unknown/missing target без фиктивной адресации;
- malformed snapshot/неполный proof с known prohibition и без него; FIELD
  omission/permutation не меняет deny-dominance при тех же обязательствах;
- собственный положительный адресный recovery, valid minimal domains,
  отсутствие неиспользуемых доменов, независимый recovery с чужим fault,
  сохранение histories/rejected IDs и обычных WORK-запретов;
- отсутствие новых false TRUE, четыре прежних incomplete snapshots, все type/
  semantic/source/нормативные/B01/B02 регрессии и readonly поведение;
- unchanged helper, 53/84 minimum, 44 bindings, 4 variants, расчёты и CAD.

B03 закрывает R5 по точному новому C. W02, исполняемый material engine и physical
READY NO-GO; ни полный цикл, ни движения, прочность, геометрия или безопасность
этим документальным gate не доказаны. R3 force studies WARNING остаются отдельной
разрешённой ветвью при действующих полномочиях. Архитектура/ТЗ/оборудование не
утверждены; CAD/rebuild/физические испытания NOT_RUN, G1 OPEN.
