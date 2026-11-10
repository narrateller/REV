# cross_check_log — акты межролевой проверки

Сохранён документальный OUTPUT-review эскизов с WARNING; инженерной приёмки нет. Шаблон ниже не является положительным заключением.
Один акт относится к неизменяемому набору файлов и параметров. Последующее исправление создаёт новый акт с `supersedes`; исходный акт сохраняется.

## Индекс актов

| Review ID | Проверяющий → авторы | Task / commit | Область | Вердикт | Актуальность | Блокер |
|---|---|---|---|---|---|---|
| REV-R5-REVIEW-01-001 | R5 r5-review-01 → codex-01 | T-INIT / 6fe0a417ed2fde165e2fc01d625ec86ab810346e | Документальные эскизы, без инженерной приёмки | WARNING | CURRENT для перечисленных артефактов | NONE |

## REV-R5-REVIEW-01-001 — независимая проверка эскизов

ID нормализован в uppercase согласно схеме валидатора; идентификатор сессии
проверяющего и содержание вердикта не изменены.
Акт оформлен координатором codex-01 по полученному заключению отдельного
проверяющего r5-review-01; технический вердикт и ограничения сохранены.
Проверяющий не редактировал эскизы/новые таблицы циклов и не соавторствовал
в них. Текущие таблицы циклов и задание модели этим актом НЕ проверены.
Существенных противоречий в рамках документального эскиза не найдено;
четыре замечания фиксируют признанные пробелы, не доказанные дефекты.

```yaml
record_type: review
review_id: REV-R5-REVIEW-01-001
kind: OUTPUT
task_id: T-INIT
created_at_utc: '2026-11-10T14:41:13Z'
reviewer:
  role: R5
  session_id: r5-review-01
  model_label: Codex
reviewed_roles:
- R1
author_sessions:
- codex-01
independence:
  reviewer_not_author: true
  basis: Отдельный агент /root/independent_sketch_review с fork_turns=none, только чтение immutable blobs,
    без авторства/редактирования
independence_basis: Назначение делегировано прямым поручением пользователя передать эскизы на независимую проверку.
  r5-review-01 не участвовал в авторстве codex-01. Общий поставщик модели не исключает коррелированных ошибок.
reviewed_commit: 6fe0a417ed2fde165e2fc01d625ec86ab810346e
parameter_refs: []
artifacts:
- path: concepts/press_functional_alternatives.md
  sha256: 2fb610359d9e65775844ffa01e8c0dcc10238fc4c1ca239f84cd415dd605f1be
- path: verification/feed_dosing_rig_scheme.md
  sha256: 3c10edeaffe65bd72181768fc76845dd2e8ad6bd8d8f27763996a639b625771d
- path: sources/function_realization_comparison.md
  sha256: 65081e7085080bbbe4b4497420d97d338bf68fbe17adede6cecdfa94501f492c
scope: 'DOCUMENTARY_OUTPUT_REVIEW: логическая согласованность эскизов/намерений, пути материала, движений/стыка/силовых
  гипотез, разгрузки двери и качества F; без физической верификации'
checks:
- id: CHK-01
  method: inspection
  expected: Оба варианта содержат приём/дозирование/уплотнение/выдачу; стенд доз отделён от камеры
  observed: 'Эскизы: строки 11–21,34–41,93–99; дозирующая схема: 33–50,191–203'
  reasoning: Путь материала прослеживается; сопротивление камеры и Dose_ID/Briquette_ID не выданы за воспроизведённые
  result: PASS
- id: CHK-02
  method: inspection
  expected: Заполнение отделено от силового хода, дозатор не является проверенным силовым затвором
  observed: 'Эскизы: 55–76,114–133'
  reasoning: Опирание, пересечения и нагрузки обозначены UNKNOWN; проверена постановка, не реализация
  result: PASS
- id: CHK-03
  method: inspection
  expected: Цепь реакций возвращается через конструкцию к креплению цилиндра
  observed: 'Эскизы: 23–28,42–49,79–83,100–108,135–145'
  reasoning: Для A через канал/зажим/раму, для B через упор/замок/раму; это не векторная диаграмма и не доказательство
    прочности
  result: PASS
- id: CHK-04
  method: inspection
  expected: Разгрузка предшествует отпиранию; давление масла не равно остаточному усилию
  observed: 'Эскизы: 114–119,127–141'
  reasoning: B-UNLOAD перед B-OPEN, но способ подтверждения разгрузки отсутствует; исполнительная логика не
    верифицирована
  result: PASS
- id: CHK-05
  method: inspection
  expected: Неутверждённость архитектуры и границы источников явны
  observed: 'Эскизы: 3–7,85–87,143–165; сравнение: 9–12,23–28,32–49,53–56'
  reasoning: NOT_SELECTED/UNKNOWN согласованы; сами PDF и их характеристики повторно не проверялись
  result: PASS
- id: CHK-06
  method: inspection
  expected: NO_MOTION требует достоверного наблюдения, потеря F не является пропуском
  observed: 'Дозирующая схема: 54–94,142–156,267–270'
  reasoning: Качество отделено от наблюдения; SIGNAL_LOSS/INVALID даёт UNKNOWN и EVT-MEASURE, не валидацию
    датчика
  result: PASS
- id: CHK-07
  method: independent_derivation
  expected: Масса содержимого равна брутто минус тара при согласованных условиях
  observed: 'Дозирующая схема: 76,96–108,120–128,153–156'
  reasoning: Из определения брутто = тара + содержимое следует m_dose = m_gross - m_tare; численных значений
    и реализации нет
  result: PASS
- id: CHK-08
  method: inspection
  expected: Для инженерной верификации нужны геометрия, нагрузки, свойства сырья, расчёты и результаты
  observed: Численные параметры UNKNOWN, расчётных/натурных результатов нет
  reasoning: По качественным схемам нельзя доказать баланс реакций, прочность, удержание, ход выдачи и работу
    процесса; исключено из документального разрешения
  result: NOT_RUN
findings:
- finding_id: R5-OBS-01
  severity: MEDIUM
  evidence: concepts/press_functional_alternatives.md:55–61,114–119
  impact: Конструктивное отсечение загрузочного окна и опирание не решены; силовой интерфейс не готов
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-OBS-02
  severity: MEDIUM
  evidence: concepts/press_functional_alternatives.md:121–133,152–158
  impact: Для B не определены подтверждение разгрузки и геометрия открытия/выдачи
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-OBS-03
  severity: MEDIUM
  evidence: concepts/press_functional_alternatives.md:67–83,152–158
  impact: Для A не доказаны старт пустого канала, удержание, очистка и отделение продукта
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-OBS-04
  severity: MEDIUM
  evidence: verification/feed_dosing_rig_scheme.md:69–94,138–156,288–296
  impact: Метрологические диапазоны/чувствительность/синхронизация/окна F не обоснованы
  owner_role: R1
  task_id: T-INIT
verdict: WARNING
validity: CURRENT
allowed_downstream_scope: Только документальная проработка альтернатив, неизвестных, разрешений и будущих критериев
  без принятия архитектуры и запуска оборудования
excluded_claims:
- Прочность, безопасность, ресурс, реальные силовые/кинематические характеристики
- Пригодность сырья и качество брикета
- Метрологически проверенные L/F/M и классификация реальных событий
- Производительность, изготовимость/локализация и выбор архитектуры
- Утверждение ТЗ и прохождение G1–G5
- Повторная проверка PDF и документов, созданных после reviewed_commit
blocker_ids: []
warning_owner_and_due:
  owner_session: codex-01
  owner_role: R1
  due_at_utc: '2026-11-11T12:06:09Z'
  restriction: До срока оформить неизвестные и план проверки; инженерная реализация/выпуск требуют собственных
    доказательств и независимой проверки независимо от срока
closure_criteria:
- Для стыка представить конструктивное отсечение/опирание/нагрузки и проверку движений
- Для B обосновать разгрузку/замыкание и геометрию открытия/хода выдачи
- Для A обосновать старт/удержание/завершение/очистку и связь доз с выдачей
- Определить и независимо проверить метрологические правила F и интервалы/обработку недостоверных данных
- Изменённые артефакты предъявить новому review; настоящий акт привязан к неизменным blobs
supersedes: null
```

Хэши вычислены проверяющим по байтам git show <commit>:<path>; координатор
повторно сверил хэши Git blobs и неизменность текущих файлов.

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
