# Q-R1-CI-SEMANTICS-ARBITRATION-01 — follow-up типизированных ревизий

QUESTION P1 @R1, parent T-r4-cycle-interfaces-01; REOPENED.
Решение 5fe510bbc55a052c360ab39a2491a061584b8fb7 по нормативному минимуму реализовано:
53/84, независимая от payload закреплённая норма и старые шесть rejects подтверждены.
Новый C bd7ce8a623d6a4ecdff1f106868a4c7086a8a27f ещё не закрывает B03.

Два прежних REJECT 13b0fc30248167d7a3a73d1c47b89b58b1a3b7c2 и
5fb731182a2bdf6b11246558eca58962e48568d9 сохранены. Настоящий RECHECK — третий,
interface_consecutive_rejections=3; material_contract_consecutive_rejections=2 отдельно.
Точный SHA нового акта фиксируется отдельной H-эстафетой, без самоссылочного C.
По AGENT_PROTOCOL §6.1 следующая B03 итерация BLOCKED до записанного решения/плана.

Четыре свежих полной CLI мутации revision bool/float в phase/AST/binding refs
ошибочно MATCH; два concrete origin_revision false/0.0 дают TRUE при frozen
INDETERMINATE и fault OPEN. См. review.md, independent_results.json, mutations/.
Это ошибки документальной типовой проверки; движения/физического снятия не было.

| Вариант | Соответствие | Физика/CAD/производство | Риск | Цена/срок | Рекомендация |
|---|---|---|---|---|---|
| Считать Python numeric equality допустимой нормализацией provenance | Не соответствует объявленному typed/frozen policy, bool не integer revision | Не меняет расчёты, но не доказывает работу | Ложный MATCH/TRUE | UNKNOWN | Отклонить |
| Строго проверять типы ревизий и сравнивать typed refs; concrete recovery сверить с frozen policy | Сохраняет принятый нормативный подход и B01/B02 | Новых расчётов/CAD/изменений ТЗ не требует | Нужны позитивные и негативные integer/bool/float случаи по всем полям | UNKNOWN | Рекомендуется bounded correction + RECHECK |
| Расширить до W02/PLC или изменить loads/геометрию | Не требуется для дефекта проверки типов | Выход за текущую документальную область | UNKNOWN | UNKNOWN | Отложить отдельно |

Неподлежащие ослаблению входы: 44 source bindings, 4 force variants, frozen helper,
условия LOAD/recovery, история faults/rejected IDs, неподдерживаемое не MATCH.
Новые значения изделия не применяются. R1 согласует правило типов/план; R4 после
решения исправляет валидатор/тесты; независимый R5 проверяет точный новый C.
Арбитраж не закрывает B03 вместо RECHECK. Отдельные R3 force studies WARNING
допустимы; стабильный документальный handoff/CAD/rebuild пока NO-GO.
W02/physical READY NO-GO, G1 OPEN; архитектура и ТЗ не утверждаются.
