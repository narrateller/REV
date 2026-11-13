# Bounded OPEN journal admission — схема до кода

ARB-R1-CI-SEMANTICS-06: a85e69f3a495176c614202a518be6784be8f3b31.
Источник всех guard ID, scope kinds/domains и собственных условий — pinned
contract C0c4eb5d. Ни tags входа, ни subject_kind сами по себе не namespace.

Положительный admission требует существующей confirmed frozen history policy
и полного просмотра записей. Результат TRUE либо UNKNOWN, никогда FALSE от
malformed metadata. Unknown status не является RESOLVED. Все OPEN должны
получить семантическую классификацию; первая ошибка не завершает scan.

| Поле / отношение | Допустимая bounded схема |
|---|---|
| faults / record / status | dict / dict; exact str OPEN или RESOLVED; другой тип/статус UNKNOWN |
| OPEN key / fault_id / origin | canonical F-ID, exact identity с digest(origin); origin dict |
| origin.guard | exact nonempty str из всех fixed guard definitions; без coercion/normalization |
| origin.scope | exact fixed identity fields + subject_kind; nonempty strings; kind соответствует guard; variant/mode известны fixed definitions; non-material basis tags по fixed scope policy |
| origin.truth | exact TRUE/FALSE/UNKNOWN string; не физическая переоценка old evidence |
| origin.revisions / expected_revisions | objects собственного E_guard, exact integer>=0; bool/float/unknown values не допускаются; не сравниваются с current другого scope |
| revision_history | list адресных +1 events по fixed change_subject, typed fields; expected следует из immutable origin, без zero/current repair |
| cause_fault_ids | list canonical distinct существующих адресов со статусом OPEN/RESOLVED и coherent origin/F-ID; отсутствие/недоступность связи → UNKNOWN |
| RESOLVED вне используемой causal цепи | существующая frozen history policy; guard/current evidence заново не доказываются |
| historical evidence/provenance | opaque часть immutable origin/digest, не raw current validation и не повторное физическое доказательство |

Классификация выполняется после identity/schema validation. APPLICABLE: fixed
own ENTRY guard (для EVENT_FRESH — известный текущий operation_id), разрешённый
result guard или адресный causal ancestor предъявленного target. NOT_APPLICABLE:
поддержанная полная запись вне этих обязательств; в том числе known FEED_CLEAR
без причинной связи с target. UNCLASSIFIABLE: неизвестен guard, необходимое поле
или отношение. «Не равно own guard» без supported identity недостаточно.
Сам APPLICABLE не означает FALSE: truth/status и прежние источники оцениваются
отдельно; result/нижестоящий DEPENDENCY не добавляются к ENTRY и не создают тупик.

Сохранён прежний узкий scope EVENT_FRESH: для известного другого operation_id,
не являющегося causal ancestor, snapshot completeness не нужна для доказанного
operation-specific non-applicability. Такие maps обязаны оставаться objects с
known own domains и exact typed counters, events typed; они не доказывают success
acknowledgement старого event и не восстанавливаются. Это прежний admission scope
неиспользуемого snapshot, не исключение для неизвестного guard. Для применимых
records и остальных OPEN требуется полный E и согласованная revision_history.

Causal обход конечен: visited set по существующим IDs, без recursive execution,
ремонта, replay материального engine или оценки физических old events. Неизвестный
target не подставляется: известность namespace/own applicability не выбирает
target; positive recovery отдельно требует реальный адрес и proof прежней схемы.

При UNKNOWN admission journal не даёт положительного absence-of-latch результата,
raw TRUE не повышает его; вход OUT_OF_DOMAIN и scoped UNKNOWN. Результат scan,
каждая запись/роль/reasons и охват видны отдельно от raw/reader/own/state/causal.
Observed reader values можно сохранить диагностически, но не принять TRUE.
Достоверные raw/own/state/адресные causal FALSE сохраняют BLOCKED через прежний
finish. Неприменимая known FEED не создаёт blanket BLOCKED. Caller/F-ID/maps/
history/rejected IDs/pending observations readonly; helper copy не применяется.

План:732 R5 cases и36same-input false TRUE; missing/null/known-FEED controls;
tags/type/status/scope/revisions/causal/schema mutations, first/middle/last,
несколько malformed и известных записей; raw TRUE/FALSE/UNKNOWN и other FALSE;
known unrelated FEED/positive/minimal/WORK; exceptions и все8 exits; prior966/
220/118/type244+36/semantic411/B01-B02 и independent654/765/7/295/231. Helper,
норматив53/84/18/44bindings/4variants/calculations/CAD и7REJECT unchanged.
W02/physical READY NO-GO,G1 OPEN; independent exact-C R5 RECHECK pending.
