# cross_check_log — акты межролевой проверки

Сохранены документальные OUTPUT-review эскизов и постановки модели с WARNING; инженерной приёмки нет. Шаблон ниже не является положительным заключением.
Один акт относится к неизменяемому набору файлов и параметров. Последующее исправление создаёт новый акт с `supersedes`; исходный акт сохраняется.

## Индекс актов

| Review ID | Проверяющий → авторы | Task / commit | Область | Вердикт | Актуальность | Блокер |
|---|---|---|---|---|---|---|
| REV-R5-REVIEW-01-001 | R5 r5-review-01 → codex-01 | T-INIT / 6fe0a417ed2fde165e2fc01d625ec86ab810346e | Документальные эскизы, без инженерной приёмки | WARNING | CURRENT для перечисленных артефактов | NONE |
| REV-R5-MODEL-REVIEW-01-001 | R5 r5-model-review-01 → codex-01 | T-codex-01-01 / 3aebae606011ded0f6d6e0a8d6ccc15094d88feb | Постановка rev2 и циклы rev1; не код | WARNING | CURRENT | NONE |

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

## REV-R5-MODEL-REVIEW-01-001 — проверка постановки первой модели

Акт оформлен координатором по заключению отдельного read-only R5.
Обязательных исправлений двух проверенных документов reviewer не обнаружил.
Отдельный вердикт: можно передать R4 исследовательскую реализацию на
изолированных synthetic данных после назначения/claim. Назначение и claim
этим актом не создаются. Код, fixtures и стенд не запускались; PASS внутри
checks означает документальную проверку требования, не выполнение модели.

```yaml
record_type: review
review_id: REV-R5-MODEL-REVIEW-01-001
kind: OUTPUT
task_id: T-codex-01-01
created_at_utc: '2026-11-10T16:17:13Z'
reviewer:
  role: R5
  session_id: r5-model-review-01
  model_label: Codex
reviewed_roles:
- R1
author_sessions:
- codex-01
independence:
  reviewer_not_author: true
  basis: Отдельный агент /root/independent_model_brief_review с fork_turns=none; только чтение immutable Git
    artifacts, без авторства/редактирования
independence_basis: Назначение и передача делегированы прямым поручением пользователя. Отдельная сессия не
  участвовала в авторстве codex-01; общий поставщик модели сохраняет возможность коррелированных ошибок.
reviewed_commit: 3aebae606011ded0f6d6e0a8d6ccc15094d88feb
parameter_refs: []
artifacts:
- path: models/first_digital_model_brief.md
  sha256: 3c86ed707f11ee5f9fa93409022c8250cc3582e6fb78363f85313d28733b79d1
- path: controls/press_variant_state_tables.md
  sha256: e4a5ac6e2da299554ed779670c6872af97ec8a48ace50ec5e4aa929fdd62e7fa
scope: 'DOCUMENTARY_OUTPUT_REVIEW: постановка rev2 и таблицы циклов rev1, достаточность контракта/ожидаемых
  synthetic результатов и границ передачи R4; без MODEL_VERIFICATION'
checks:
- id: CHK-01
  method: inspection
  expected: Границы модели/обе альтернативы без утверждения архитектуры
  observed: Brief 7–19,162–170; cycles 55–71
  reasoning: Геометрия/кинематика отделены от сырья, нагрузок и выбора A/B
  result: PASS
- id: CHK-02
  method: inspection
  expected: Точные входы/происхождение, UNKNOWN без догадок
  observed: Brief 15–19,39–52; cycles 3–7; immutable git show
  reasoning: Числа REV не назначены; ревизии исполнения фиксируются при claim
  result: PASS
- id: CHK-03
  method: inspection
  expected: Явные координаты/единицы/внеплоскостные данные/допуски
  observed: Brief 25–35,39–52,117–133
  reasoning: UNKNOWN не заменяется нулём, синхронизацией или произвольным допуском
  result: PASS
- id: CHK-04
  method: inspection
  expected: При наличии физических расчётов проверить формулы/балансы
  observed: Физические расчёты отсутствуют; brief 162–168 их исключает
  reasoning: Проверка физических балансов неприменима к этому объёму и не подтверждает будущую физику
  result: NOT_APPLICABLE
- id: CHK-05
  method: inspection
  expected: Гарантированная проверка всего хода/возврата/совместных движений
  observed: Brief 77–81,104–127
  reasoning: Непрерывный метод либо консервативная полнота; отсутствие гарантии ведёт к INDETERMINATE, не NO_COLLISION
  result: PASS
- id: CHK-06
  method: independent_derivation
  expected: Различить проекции/траектории/огибающие и одновременное столкновение
  observed: Brief 93–110,129–133
  reasoning: Перекрытие объединённых по времени областей не доказывает общего t; разнесённые интервалы z исключают
    пересечение экструзий независимо от проекции
  result: PASS
- id: CHK-07
  method: inspection
  expected: Переходы требуют физических разрешений, разгрузка до открытия B
  observed: Cycles 11–24,30–41,47–53; brief 44,112–123
  reasoning: Команда/геометрия не доказывают силовую готовность; B-UNLOAD отдельно от B-OPEN, A-OUT связан
    с A-PRESS
  result: PASS
- id: CHK-08
  method: inspection
  expected: Промежуточная коллизия при свободных концах требует COLLISION
  observed: SYN-MODEL-01; brief 149,155–160
  reasoning: Требуется свидетельство внутри интервала; INDETERMINATE безопасен, но эталон не проходит
  result: PASS
- id: CHK-09
  method: inspection
  expected: Overlap проекций при полном известном разнесении z даёт NO_COLLISION
  observed: SYN-MODEL-02; brief 150,129–133
  reasoning: Диагностика проекции отделена, вывод об объёмах доказан на всём интервале
  result: PASS
- id: CHK-10
  method: inspection
  expected: Пересечение траекторий в разные времена учитывает конечные размеры
  observed: SYN-MODEL-03; brief 151
  reasoning: Требуется отсутствие одновременного пересечения объёмов во всём ходе
  result: PASS
- id: CHK-11
  method: inspection
  expected: Недостающая необходимая геометрия/траектория даёт INDETERMINATE
  observed: SYN-MODEL-04; brief 152,121–127
  reasoning: Оба подслучая и список недостающего предусмотрены; по остальным данным вывод не доказан
  result: PASS
- id: CHK-12
  method: inspection
  expected: Корректный короткий ход — отдельный статус недостаточной выдачи
  observed: SYN-MODEL-05; brief 135–139,153
  reasoning: INSUFFICIENT_STROKE не подменяется INVALID_INPUT/COLLISION; NO_COLLISION требует отдельной полной
    проверки
  result: PASS
- id: CHK-13
  method: inspection
  expected: Результат геометрии не закрывает весь VAL/G1
  observed: Brief 65–89,143–170; REQ/VAL-05/06/09/11/12/16 есть в commit
  reasoning: Команды, файлы/хэши, статусы и независимая проверка заданы; реальные силы/сырьё/изделие за границей
  result: PASS
- id: CHK-14
  method: inspection
  expected: Реализация действительно обеспечивает полноту и проходит fixtures
  observed: Реализация NOT_STARTED, результатов исполнения нет
  reasoning: Проверена постановка/ожидаемые ответы, не выполнение или корректность будущего кода
  result: NOT_RUN
findings: []
verdict: WARNING
validity: CURRENT
allowed_downstream_scope: Передача R4 после отдельного назначения/claim для исследовательской реализации обеих
  альтернатив, UNKNOWN-шаблонов, символических схем и изолированных synthetic fixtures. Метод/код/результаты
  проверяются отдельным независимым review.
excluded_claims:
- Работоспособность кода и выполнение synthetic fixtures
- Отсутствие коллизий в реальном REV, реальная достаточность хода/сил/удержания/разгрузки
- Безопасность управления/защит и метрологическая пригодность
- Свойства сырья/уплотнение/качество/реальная выдача
- Прочность/ресурс/производительность/изготовимость/выпуск
- Выбор A/B, утверждение ТЗ и G1–G5
- Закрытие R5-OBS-01…04 предыдущего review
blocker_ids: []
warning_owner_and_due:
  owner_role: R1
  owner_session: codex-01
  due_at_utc: '2026-11-11T12:06:09Z'
  restriction: До реализации зафиксировать назначение/claim, immutable входы, этот акт и synthetic-only границу;
    срок не продлевает lease T-INIT. Инженерное использование/выпуск требуют отдельных доказательств.
closure_criteria:
- Для приёмки реализации предъявить точный commit метода/кода, входы и воспроизводимые результаты
- Независимо проверить полноту пространственно-временного метода и пять synthetic случаев
- Для переноса на REV определить применимую геометрию/движения/допуски/область
supersedes: null
```

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

## REV-R5-IMPL-02-001

```yaml
record_type: review
review_id: REV-R5-IMPL-02-001
kind: OUTPUT
task_id: T-codex-01-01
created_at_utc: '2026-11-10T17:12:05Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R4
author_sessions:
- r4-model-01
independence:
  reviewer_not_author: true
  basis: Новая сессия, прямое назначение пользователя; авторство R4 отсутствует, проверяемый
    код не изменялся.
independence_basis: Независимая текущая сессия; только чтение реализации и отдельный
  benchmark.
reviewed_commit: 5cb3e8ab274ae4d746ec016ecd11b6c2acd14edb
parameter_refs: []
artifacts:
- path: models/kinematic_press/model.py
  sha256: 985076a6e6e3caba956a2ee5b9d7d0f3fcb9d6fda387153af54e507d3b2462cf
- path: models/kinematic_press/phase_plan.json
  sha256: 3835120360e636762fd8eff48d8119ff1027ea5b51f29e4e20aad9c1fd5ea714
- path: models/kinematic_press/fixtures.json
  sha256: b4cbeef255009c450a75fa3917ff8437b8d244cf593dae65907c5a0c31ec9e52
- path: models/kinematic_press/phase_inputs_synthetic.json
  sha256: 7eba9d96abf278d5ae9fe7cffb5ced50a9a7c426fb0ade8325b70b4a98d47eeb
- path: models/kinematic_press/results/report.json
  sha256: dc19f7275ea806688463049511b732e014ee29d5a2daea6f2498cc7da64ce1d9
- path: models/kinematic_press/results/force_paths.svg
  sha256: 0248486fc2e1ee9068a4bfec18036b3cfb4db4959d334085f951d5380e80b7bb
scope: 'MODEL_VERIFICATION: ядро линейных AABB PASS; фазовая модель REJECT_WITH_BLOCKER;
  силовая топология WARNING; synthetic only'
checks:
- id: CHK-IMPL-01
  method: independent_derivation
  expected: Полное обнаружение контакта за интервал для синхронных линейных AABB
  observed: Аналитическое доказательство и 3000 независимых сравнений без расхождения
  result: PASS
  reasoning: verification/r5_model_02/review.md и independent_check.py
- id: CHK-IMPL-02
  method: rerun
  expected: Пять mandatory сценариев и неверные входы
  observed: 7 записей совпали; 6 unittest OK; provenance совпал
  result: PASS
  reasoning: Команды и область приведены в отдельном отчёте
- id: CHK-IMPL-03
  method: inspection
  expected: Полное synthetic покрытие фаз A/B и перечней пар
  observed: 2/62 пар; 11/13 фаз без вычисленной пары; пропущены пары и проверка переходов
  result: FAIL
  reasoning: R5-IMPL-01/02, конкретные дополнения в отчёте
findings:
- finding_id: R5-IMPL-01
  severity: BLOCKER
  evidence: verification/r5_model_02/review.md
  impact: Приёмка фазовой модели заблокирована
  owner_role: R4
  task_id: T-codex-01-01
- finding_id: R5-IMPL-02
  severity: BLOCKER
  evidence: models/kinematic_press/phase_plan.json
  impact: Полнота списка пар не доказана
  owner_role: R4
  task_id: T-codex-01-01
verdict: REJECT_WITH_BLOCKER
validity: CURRENT
allowed_downstream_scope: Использование проверенного ядра только для заданного класса
  synthetic пар; дополнение фаз R4.
excluded_claims:
- Полная приёмка задачи
- Реальная безопасность/прочность/выдача
- Закрытие G1 или R5-OBS-01…04
blocker_ids:
- R5-IMPL-01
- R5-IMPL-02
closure_criteria:
- Полные synthetic фазы и переходы A/B, обоснованная матрица пар, повторный независимый
  review
supersedes: null
```
