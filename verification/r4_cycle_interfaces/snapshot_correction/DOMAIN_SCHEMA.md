# Схема допуска recovery snapshots — до исправления кода

Основание ARB-R1-CI-SEMANTICS-03, commit
39826eb2f5dbd1f83d81882022e6f59313ebe5d5. Узкая B03 итерация, не новая
версия material helper или норматива. Схема записана перед реализацией.

Источник: frozen C0c4eb5d, contract.json SHA256
5ea62e56fd2d95a7e87df81187e8e0a93a93891513b12c8e10b1a5911f84377c,
permission_examples.py e4bce420b1cec04e65600d5caf979287797d255d5a718b769f7490d50b4e8ac3.
Переданный contract обязан соответствовать этой закреплённой версии. Поддержана
пара RESTORE_B_CLOSURE / B_RESET_CONFIRMED. Для неизвестного определения или
другой пары результат UNSUPPORTED/UNKNOWN, никогда не «E пусто» по умолчанию.

E целевого guard = {B_CLOSURE}. U — явно перечисленные evidence_policy.domains
того же pinned contract: MATERIAL, FEED, AXIS, RETENTION, B_CLOSURE,
EXIT_RECEIVER, HYDRAULIC, EVIDENCE, RESOURCES. D_entry — объединение доменов
отдельных entry_guards RESTORE_B_CLOSURE: MATERIAL, AXIS, B_CLOSURE,
EXIT_RECEIVER, HYDRAULIC, EVIDENCE, RESOURCES. FEED/RETENTION не обязательны.
Все значения используемых maps — точные integer >=0, без bool/float/coercion.

| Snapshot | Требуется | Extra-key policy |
|---|---|---|
| fault.origin.revisions | точный E, immutable origin/F-ID/history сохранены | extras запрещены даже если известны |
| fault.expected_revisions | точный E, выводится из origin только проверенной revision_history | extras запрещены |
| proof.origin_revisions | точный E, typed equality с origin | extras запрещены |
| proof.revisions | содержит E, подтверждает expected/current в E | известные U разрешены как отдельные typed annotations, не доказывают чужой guard |
| context.revisions | содержит E ∪ D_entry | известные U разрешены; отсутствие/корректное изменение неиспользуемых FEED/RETENTION не блокирует B_CLOSURE |
| context.evidence[g].revisions для ENTRY | содержит fixed evidence_domains собственного guard g | известные U разрешены; значение в используемом scope сверяет frozen policy |
| origin/expected используемых ENTRY/causal faults | собственный exact E_g из fixed определения | extras запрещены; не используется глобальный E для всех faults |

ENTRY faults выбираются так же, как frozen evidence_value: OPEN нужного guard;
для EVENT_FRESH только текущего operation_id. Старый EVENT_FRESH другого запроса
не добавляет snapshot obligations нового recovery. Общий history_valid остаётся
отдельным неизменённым условием; причинно используемые faults проверяются адресно.
Дополнение при регрессиях: malformed structures, на которых frozen ENTRY не
может оценить guard, не допускаются к recover; required completed_operations и
target resolution_attempts, а также optional recovered_evidence имеют типы
dict/list/dict соответственно. Они не создаются и не исправляются в caller.

Неизвестный ключ не заменяет обязательный домен. Empty допустим только если
фиксированный guard явно объявляет evidence_domains=[]. B_RESET таким guard
не является. Отсутствующие snapshots/поля/состав не восстанавливаются из current,
нулём, setdefault или readdress. Coherent F-digest не заменяет проверку полноты.

revision_history — существующая адресная история конкретного fault: список
строго типизированных {domain, from_revision, to_revision}, domain ∈ E_g;
последовательность начинается с immutable origin, каждое событие соответствует
fixed change_subject (+1), итог точно равен expected. Нет событий — expected
равен origin. Origin не приравнивается к current. Имена/causal IDs/origin/F-ID
не переписываются. Доверие к истории остаётся в рамках frozen history_valid/
history_confirmed; схема не доказывает внешнюю физическую истинность журналов.

## Диагностика и compatibility

Возвращаются отдельно admission status/reasons, подтверждённость revision bindings,
scoped policy result, scoped recovery value и общий action gate. Структурно
полные domain/type/history inputs находятся IN_DOMAIN; stale/scope/revision
evidence может быть корректно отклонено frozen policy. Unknown/unsupported или
неполные maps — OUT_OF_DOMAIN, legacy recover не используется как достаточное
доказательство. В частности четыре опубликованных false-acceptances дают
UNKNOWN/NOT_EVALUATED с явной причиной и могут отличаться от legacy TRUE.

Известные FALSE собственного ENTRY/состояния/causal gate рассматриваются
независимо от полноты recovery proof. Общий gate BLOCKED при любом таком FALSE,
даже если scoped recovery UNKNOWN. При отсутствии FALSE и невалидном proof
общий gate INDETERMINATE. Совместимость сравнивает одинаковые уровни результатов
только в объявленном домене; не обещает unconditional equality для malformed
contexts. Внутри допустимой области результаты/известные отказы сохраняют
frozen semantics; никакой вызов не применяет возвращённый state к caller.

Чужой неустранённый fault не очищается closure recovery. Если он нарушает
собственные условия действия, общий gate BLOCKED; иначе остаётся отдельным
fault и продолжает запрещать свои зависимые штатные действия. Это не global
READY. Readonly input/proof/fault/history/rejected IDs проверяются тестами.
W02/PLC/CAD/расчёты вне scope, physical READY NO-GO, G1 OPEN.
