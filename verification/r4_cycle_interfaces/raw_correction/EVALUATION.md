# Два независимых источника own assessment — до кода

ARB-R1-CI-SEMANTICS-05, SHA 3aa5ee100f57aa75315d429afef38f8a982b1afc.
Raw current evidence проверяется fixed frozen `_raw_value` независимо от
journal-dependent `evidence_value`. Frozen helper и snapshot admission не меняются.

Для каждого fixed own ENTRY guard сначала отдельно получить raw truth/reason/
validity, затем journal truth/status/reason. Исключения изолируются по источнику.
Raw FALSE подтверждён только после scope/action/guard/phase, exact relevant
integer revisions, provenance/method/source и operation interval checks helper.
Буквальное поле value не является доказательством. Caller records не чинятся.

| Raw source | Journal-dependent reader | Own result в новой exception ветви |
|---|---|---|
| подтверждённый FALSE | exception → UNKNOWN | FALSE, reason raw, journal error сохранён |
| подтверждённый TRUE | exception → UNKNOWN | UNKNOWN; отсутствие latched fault не доказано |
| UNKNOWN либо stale/foreign/invalid record | exception → UNKNOWN | UNKNOWN; не blanket FALSE |
| raw exception | подтверждённый own journal FALSE | прежний trusted FALSE сохраняется |
| raw exception | exception/UNKNOWN | UNKNOWN, кроме другого независимого обязательного FALSE |

Все пути по-прежнему идут через единый finish: любой достоверный обязательный
FALSE → BLOCKED; без FALSE и при необходимом UNKNOWN → INDETERMINATE.
В нормальной IN_DOMAIN области сохраняется прежняя frozen precedence;
поправка восстанавливает raw FALSE при journal exception, не вводит raw TRUE
как замену доверенному reader. Source confidence и исключения видны отдельно
от validation/reasons, own/scoped/causal значений и action gate.

Не ремонтировать/удалять foreign fault, не пересчитывать F-ID в caller,
не подставлять target/domain/revisions и не применять helper copy. Сохраняются
raw invalid controls, prior eight exits,220 gate/118 snapshot/244 type/36
differential/411 semantic/B01/B02, positive recovery/чужой fault/WORK запрет.
Повторить minimal witness, восемь вариаций и231 R5 cases, stale/foreign и
TRUE/FALSE/UNKNOWN controls, два own условия и raw-reader exceptions.
Шесть REJECT/interface6 и отдельный material2 сохраняются. Helper/norm53/84/18,
44bindings/4variants/calculations/CAD неизменны. W02/physical READY NO-GO,G1 OPEN.
