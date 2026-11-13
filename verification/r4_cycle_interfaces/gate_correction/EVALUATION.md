# Композиция B03 — схема до исправления кода

ARB-R1-CI-SEMANTICS-04, SHA 60eeddce71c9440a2fa08f7acbe6f1121c974b29.
Frozen definitions/helper и domain admission прежней итерации не меняются.

Поддерживаемое действие оценки — fixed RESTORE_B_CLOSURE. Поля action/guard
в предъявленном proof проверяют адресный результат, но не выбирают другое
действие для собственных ENTRY/state. Не-object proof не мешает оценить
достоверные собственные основания из context. Неизвестный contract/context
не даёт придуманного FALSE. Проверка malformed входов ничего не чинит.

Последовательность: fixed definitions → независимые собственные ENTRY/state
и history/freshness → достоверный target и адресные causal constraints →
proof/schema/domain admission → optional frozen recover → единая композиция.
Каждый путь завершения, включая unsupported/exception, идёт через один finish.
При недоступных definitions/context соответствующие основания остаются UNKNOWN.

Own raw evidence считается достоверным только при собственных fixed scope,
phase, interval и требуемых revision checks frozen policy. Latched own fault
и state используют подтверждённый контекст/историю; malformed данные сами по
себе не становятся обязательным FALSE. Причины и надёжность источников
сохраняются раздельно. Ни общий READY, ни DEPENDENCY_VALID не добавляются.

Causal FALSE требует существующего явно предъявленного F-ID, совпадающего
с immutable origin digest, поддержанного guard, подтверждённой history и
проверенных адресных причин. OPEN ancestor — запрет независимо от отсутствия
или чужого proof action/guard. Без target ID или при неизвестном/чужом target
causal UNKNOWN: произвольные чужие faults не подставляются как target.
RESOLVED и UNKNOWN ancestors проверяются отдельно. Causal history не чинится.

| Достоверные независимые основания | Scoped recovery | Итог |
|---|---|---|
| хотя бы один обязательный FALSE | любой, включая UNKNOWN/malformed | BLOCKED |
| FALSE нет, есть необходимый UNKNOWN | UNKNOWN | INDETERMINATE |
| собственные/causal основания TRUE, допустимый proof и frozen TRUE | TRUE | ALLOWED_ASSUMED (документально) |
| context/definition/target не подтверждены | UNKNOWN | не успех; FALSE не выдумывается |

Область compatibility из DOMAIN_SCHEMA.md сохраняется: одинаковые уровни
результатов сравниваются с frozen только IN_DOMAIN. OUT_OF_DOMAIN известный
запрет всё равно сохраняется в составном gate. Caller/proof/origin/expected/
history/rejected IDs не меняются, returned helper copy не применяется.

Регрессии: оба R5 witnesses и 19 вариаций; whole-proof types × TRUE/FALSE/UNKNOWN
own conditions, два собственных условия, latched faults/state; action/guard
omissions × OPEN/RESOLVED/UNKNOWN causal history и неизвестный target; все
return/schema/exception paths; положительный адресный recovery, minimal и
unused domains, чужие faults/обычная WORK блокировка; прежние 118 snapshot,
244 type/36 differential, 411 semantic и B01/B02, readonly/export/source checks.
Все пять REJECT и material counter2 сохраняются. Норматив/44bindings/4variants/
расчёты/CAD неизменны. W02/physical READY NO-GO, G1 OPEN.
