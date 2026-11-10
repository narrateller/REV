# cross_check_log — акты межролевой проверки

Принятых актов нет. Шаблон ниже не является положительным заключением.
Один акт относится к неизменяемому набору файлов и параметров. Последующее исправление создаёт новый акт с `supersedes`; исходный акт сохраняется.

## Индекс актов

| Review ID | Проверяющий → авторы | Task / commit | Область | Вердикт | Актуальность | Блокер |
|---|---|---|---|---|---|---|
| NONE | NONE | NONE | NONE | NONE | NONE | NONE |

## Форма акта

```yaml
record_type: review_template # заменить на review только при оформлении акта
review_id: null # REV-<session_id>-<local_id>
kind: INPUT # INPUT, OUTPUT, GATE, RECHECK
task_id: null
created_at_utc: null
reviewer: {role: null, session_id: null, model_label: null}
reviewed_roles: []
author_sessions: [] # все соавторы данной версии
independence:
  reviewer_not_author: false
  basis: null # не только смена роли или имени сессии
independence_basis: null # проверяемое обоснование отсутствия соавторства
reviewed_commit: null
parameter_refs: [] # id, revision, engineering_sha256
artifacts: [] # path, sha256; проверенные файлы в reviewed_commit
input_refs: [] # пути, SHA256 при необходимости, ID@revision
output_refs: []
scope: null # ARITHMETIC_ONLY, MODEL_VERIFICATION, PROCESS_VALIDATION и границы
checks: []
# Каждый элемент checks:
# id: CHK-<local_id>
# requirement_or_interface: REQ-ID либо описание границы
# method: independent_derivation / rerun / inspection / benchmark / experiment
# reference: путь и commit источника/скрипта
# command_and_environment: воспроизводимая команда, версии, настройки
# expected: критерий и ID параметра допуска
# observed: значение с единицей либо ссылка на полный результат
# result: PASS / FAIL / NOT_APPLICABLE / NOT_RUN
# reasoning: расчёт или логическое обоснование, границы применимости
dimensions_and_signs: null
balances_and_limit_cases: null
geometry_and_interfaces: null
uncertainty_and_sensitivity: null
traceability_and_revisions: null
reproduction_artifacts: []
findings: [] # finding_id, severity, evidence, impact, owner_role, task_id
verdict: null # PASS, WARNING, REJECT_WITH_BLOCKER
validity: CURRENT # STALE при изменении проверенной базы
allowed_downstream_scope: null
excluded_claims: []
blocker_ids: []
warning_owner_and_due: null
closure_criteria: []
supersedes: null
```

## Правила вердикта

- PASS: все обязательные проверки в заявленной области выполнены; результат сопоставлен с заранее заданным критерием; воспроизведение и независимая проверка различены.
- WARNING: обязательные для разрешённого исследования проверки выполнены, но остаётся явно ограниченная неопределённость; указаны владелец, срок, запрещённые выводы и блокируемый выпуск.
- REJECT_WITH_BLOCKER: ошибка, недоступная обязательная проверка, устаревшие входы, отсутствующая независимость или неустановленный определяющий критерий. До исправления зависимая работа заблокирована.
- Пустой лог, успешный запуск скрипта или мнение без расчётного/логического основания не являются PASS.
- Автор проверяемой версии может составить self-check, но он не заменяет этот акт. Сессия reviewer и её фактическая история авторства проверяются независимо от role.
- Для устранения блокера проверить исправление, его влияние на зависимости и повторные тесты; указать закрываемый blocker_id. Не переписывать прежний отрицательный вердикт.

Машинная схема: docs/SCHEMAS.md. Подстрока с review_id в тексте не считается актом.
Для VERIFIED необходим действующий PASS с совпадающими параметрами, авторами,
проверяющим и областью проверки. --check-git сверяет артефакты с reviewed_commit.
