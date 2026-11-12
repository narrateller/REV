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
validity: STALE
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
validity: STALE
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

## REV-R5-RECHECK-03-001

```yaml
record_type: review
review_id: REV-R5-RECHECK-03-001
kind: RECHECK
task_id: T-codex-01-01
created_at_utc: '2026-11-10T17:31:46.757730+00:00'
reviewer:
  role: R5
  session_id: r5-recheck-03
  model_label: Codex
reviewed_roles:
- R4
author_sessions:
- r4-model-01
independence:
  reviewer_not_author: true
  basis: Прямое поручение пользователя; текущий reviewer не участвовал в авторстве
    проверяемой реализации и не менял код R4.
independence_basis: Независимая проверка immutable SHA, аналитическая сверка границ
  и отдельные контрпримеры.
reviewed_commit: 36cda8132dcf9dbb7193b01e98bdfff2ba5e2a7b
parameter_refs: []
artifacts:
- path: models/kinematic_press/model.py
  sha256: c3275cf68c83f129844e7cc5ebe91bf639ba7bd384b431cf1d18502f83152825
- path: models/kinematic_press/phase_plan.json
  sha256: 989dfe7c276a35c9590aa1bb2e168ed206277ee393c24d0cd4e8851f5b3cf403
- path: models/kinematic_press/phase_inputs_synthetic.json
  sha256: 84df6bacf89948cc4f33b9f25eca1452b9c55aabb61cc5fd4dbc69a0d9df6476
- path: models/kinematic_press/fixtures.json
  sha256: 08f24f52df5955685efcaafb2528e913ae7627798c67be2098fa56cf78204fc0
- path: models/kinematic_press/transition_fixtures.json
  sha256: 42829c9ebe35f5fcffef8cc678db774b49208b2f893066d12984ecd320cda668
- path: models/kinematic_press/results/report.json
  sha256: 49aa411cb4c109c3cfbd83fd64e182e789e22e52a985f1e15a4c636c7ed428f8
- path: models/kinematic_press/input_template.json
  sha256: ed3330779850dd3d9af54027ab31c8605493296c5234162d4ccbd7b6aaef185e
scope: 'MODEL_VERIFICATION: synthetic only; ядро линейных AABB PASS; фазовая приёмка
  REJECT_WITH_BLOCKER'
checks:
- id: CHK-RECHECK-01
  method: rerun
  expected: Воспроизводимость и ограниченное ядро
  observed: 28 fixtures; 9 model tests; 3000 independent comparisons; 71 repository
    tests PASS; fresh report совпал
  result: PASS
  reasoning: verification/r5_recheck_03/review.md и probe_results.json
- id: CHK-RECHECK-02
  method: rerun
  expected: Непрерывность соседних фаз
  observed: Точные границы и время всех внутренних переходов совпадают
  result: PASS
  reasoning: verification/r5_recheck_03/review.md и probe_results.json
- id: CHK-RECHECK-03
  method: inspection
  expected: Связь выдачи и рабочего повторного READY
  observed: Скаляр выдачи независим от тел; равенство overlay не доказывает связь;
    READY создан копированием конца
  result: FAIL
  reasoning: verification/r5_recheck_03/review.md и probe_results.json
- id: CHK-RECHECK-04
  method: inspection
  expected: Обоснованная полнота пар
  observed: 127/127 заявленных; punch/channel_wall отсутствует в B-EJECT, контрпример
    обходит coverage
  result: FAIL
  reasoning: verification/r5_recheck_03/review.md и probe_results.json
findings:
- finding_id: R5-IMPL-01
  severity: BLOCKER
  evidence: verification/r5_recheck_03/review.md
  impact: Полная приёмка T-codex-01-01 заблокирована
  owner_role: R4
  task_id: T-codex-01-01
- finding_id: R5-IMPL-02
  severity: BLOCKER
  evidence: verification/r5_recheck_03/review.md
  impact: Полная приёмка T-codex-01-01 заблокирована
  owner_role: R4
  task_id: T-codex-01-01
verdict: REJECT_WITH_BLOCKER
validity: STALE
allowed_downstream_scope: Только заданные synthetic пары поддержанного ядра; следующая
  итерация после решения R1 по арбитражу.
excluded_claims:
- Полная фазовая приёмка
- Реальная выдача, безопасность, прочность
- Закрытие R5-OBS-01…04 или G1
blocker_ids:
- R5-IMPL-01
- R5-IMPL-02
closure_criteria:
- Связный synthetic сценарий A/B с доказанной связью выдачи, непрерывностью и рабочим
  READY
- Обоснованная матрица пар/исключений, новый независимый recheck точного SHA
reproduction_artifacts:
- verification/r5_recheck_03/probe.py
- verification/r5_recheck_03/probe_results.json
- verification/r5_recheck_03/review.md
supersedes: REV-R5-IMPL-02-001
```

## Регистрация предоставленного дополнения RECHECK-05

```yaml
record_type: review
review_id: REV-R5-RECHECK-05-001
kind: RECHECK
task_id: T-codex-01-01
created_at_utc: '2026-11-10T22:40:56Z'
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
  basis: Идентификатор и отсутствие соавторства подтверждены предоставленным пользователем
    сообщением R5; существующий REV-R5-IMPL-02-001 фиксирует отдельную сессию.
independence_basis: Сообщение R5, переданное пользователем, и предшествующий реестр
  сессий; R1 зарегистрировал полученный акт без выдачи его за свой review.
reviewed_commit: debfd085842ccae079cfd6faea1c41bca20f335d
parameter_refs: []
artifacts:
- path: models/first_digital_model_brief.md
  sha256: 3c86ed707f11ee5f9fa93409022c8250cc3582e6fb78363f85313d28733b79d1
input_refs:
- verification/r5_recheck_04/disposition.md @ 791d0ce8ccb31373b221d0b69063e2f835b442c0
input_refs_code_git_objects:
- path: models/kinematic_press/linked.py
  sha256: 40d23ab5a78e3c3b8b98a205417cdccf11961069b40c263d90625fdb3aab86eb
- path: models/kinematic_press/results/linked_report.json
  sha256: 1c229eee6e43fc265310a0bcff70ac8d5bef3955cceee98fd8c45ed36a69411f
output_refs:
- verification/r5_recheck_05/published_review.md
- verification/r5_recheck_05/probe.py
scope: MODEL_VERIFICATION; только объявленные synthetic сцены, AABB и синхронная линейная
  трансляция.
checks:
- id: CHK-RECHECK-05
  method: rerun
  expected: 'План RECHECK-04: 8 исходов, непрерывность, CE-01/02, мутации, полный
    состав сцен'
  observed: По опубликованному акту R5 8/8 исходов, 20 тестов, 3000 сравнений, 8/8
    мутаций; R1 отдельно воспроизвёл probe, тесты и benchmark.
  reasoning: Результат ограничен проверенным SHA и объявленной синтетической областью.
  result: PASS
findings: []
verdict: PASS
validity: CURRENT
allowed_downstream_scope: Исследование синтетической модели на указанном SHA.
excluded_claims:
- Реальная геометрия, материал, силы, безопасность и качество
- Выбор архитектуры и прохождение G1
blocker_ids: []
warning_owner_and_due: null
closure_criteria: []
supersedes: null
traceability_and_revisions: Зарегистрировано R1 по опубликованному акту b4d4af9325c5d24e093ec2d4dce5797581ebf6e1
  и сообщению пользователя с идентификатором автора; created_at_utc — время регистрации,
  не время исходного запуска.
reproduction_artifacts:
- verification/r5_recheck_05/published_review.md
- verification/r5_recheck_05/probe.py
```

## REV-R5-RECHECK-05-001 — дополнение

Независимый R5 для `debfd085842ccae079cfd6faea1c41bca20f335d`: PASS по плану в заданной synthetic AABB области; R5-IMPL-01 может быть закрыт на этом SHA, регрессия R5-IMPL-02 PASS в той же области. Подробности, команды и ограничения: verification/r5_recheck_05/review.md. G1 открыт.

## REV-R5-TZ-REVIEW-01-001 — проект ТЗ

```yaml
record_type: review
review_id: REV-R5-TZ-REVIEW-01-001
kind: OUTPUT
task_id: T-INIT
created_at_utc: '2026-11-10T22:59:39Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R1
author_sessions:
- codex-01
independence_basis: Текущая сессия R5 не автор шести документов R1; ранее проверяла
  модель и оформляла связанные результаты. Независимость ограничена данной областью;
  оператор проверяет фактическое авторство.
reviewed_commit: bff66903c4588321faf3b86bf0abb501c8a7c881
parameter_refs: []
artifacts:
- path: requirements/system_requirements.md
  sha256: 5941c1b17505fda259dec66034308a9266fbe39dec2d615c1640edb82a99c9c9
- path: requirements/verification_matrix.md
  sha256: ca71ca3273507f72a1a099dfaf0874f26af3fb064a67474a428fdd09ffcae6ed
- path: process/feedstock.md
  sha256: 826bfbab4ba938b8ae4e9dbeb604eb4719c042215a1e8b3b325d356e3c97ddda
- path: process/sampling_plan.md
  sha256: 0ed4415b20157ae43d8ee27cc543ed83f6bd9a3bb58317a0c8916e2571ea962d
- path: verification/press_function_test_plan.md
  sha256: 6fa70b7f108efee2cc7d1ed60634c33c2d6751ccd627f08753cfa17d5c73702f
- path: verification/g1_readiness_inventory.md
  sha256: ce5a5c33a0a67e0d22fdae65450ed13982c5623df70ce49c5212229e14142d57
scope: 'DOCUMENTARY_OUTPUT: требования, REQ–VAL, данные оператора как записанные в
  репозитории, прослеживаемость и границы модели; не результаты испытаний'
checks:
- id: CHK-TZ-01
  method: inspection
  expected: Данные OP-REV-01…06 не подменяются измерениями
  observed: Соответствуют карточке в репозитории; исходная стенограмма недоступна
  reasoning: feedstock.md и ISSUES_AND_TASKS.md; предел источника указан
  result: PASS
- id: CHK-TZ-02
  method: inspection
  expected: Каждый REQ связан с VAL
  observed: 22 уникальных REQ и 22 пары; отсутствующих и несовпадающих нет
  reasoning: Структурный подсчёт строк не подтверждает критерии
  result: PASS
- id: CHK-TZ-03
  method: inspection
  expected: Измеримые согласованные критерии и исполнимая программа приёмки
  observed: Значения, пределы, методики, охват и условия UNKNOWN
  reasoning: B01–B03; не выдавать пробелы за действительные значения
  result: FAIL
- id: CHK-TZ-04
  method: inspection
  expected: Масса дозы отделена от повторяемости изделия и выдачи; отсутствие движения
    от потери сигнала
  observed: TEST-F-02 вход; TEST-F-03/04 отдельно; SIGNAL_LOSS не NO_MOTION
  reasoning: Фактические опыты и метрология канала не выполнены
  result: PASS
- id: CHK-TZ-05
  method: inspection
  expected: Синтетическая модель не утверждает физику REV
  observed: Границы в инвентаре сохранены, OBS-01…04 OPEN
  reasoning: Прочность, удержание и реальные параметры не доказаны
  result: PASS
findings:
- finding_id: R5-TZ-B01
  severity: BLOCKER
  evidence: verification/r5_requirements_review/review.md
  impact: Препятствует утверждению проверяемого ТЗ и решению G1
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-TZ-B02
  severity: BLOCKER
  evidence: verification/r5_requirements_review/review.md
  impact: Препятствует утверждению проверяемого ТЗ и решению G1
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-TZ-B03
  severity: BLOCKER
  evidence: verification/r5_requirements_review/review.md
  impact: Препятствует утверждению проверяемого ТЗ и решению G1
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-TZ-W01
  severity: WARNING
  evidence: verification/r5_requirements_review/review.md
  impact: Требует уточнения в указанной там области
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-TZ-W02
  severity: WARNING
  evidence: verification/r5_requirements_review/review.md
  impact: Требует уточнения в указанной там области
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-TZ-W03
  severity: WARNING
  evidence: verification/r5_requirements_review/review.md
  impact: Требует уточнения в указанной там области
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-TZ-W04
  severity: WARNING
  evidence: verification/r5_requirements_review/review.md
  impact: Требует уточнения в указанной там области
  owner_role: R1
  task_id: T-INIT
verdict: REJECT_WITH_BLOCKER
validity: STALE
blocker_ids:
- R5-TZ-B01
- R5-TZ-B02
- R5-TZ-B03
allowed_downstream_scope: Документальная и исследовательская доработка; проект может
  быть представлен пользователю как незавершённый с открытыми решениями
excluded_claims:
- Фактические измерения и испытания
- Утверждение ТЗ или архитектуры
- Закрытие G1 и R5-OBS-01…04
closure_criteria:
- Обоснованные проверяемые критерии и входная область
- Подготовленная применимая программа и безопасные условия
- Проработанная нормативная и риск-область
- Независимый recheck изменённых артефактов
supersedes: null
```

## REV-R5-TZ-RECHECK-01-001

```yaml
record_type: review
review_id: REV-R5-TZ-RECHECK-01-001
kind: RECHECK
task_id: T-INIT
created_at_utc: '2026-11-10T23:07:44Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R1
author_sessions:
- codex-01
independence_basis: Автор предыдущего акта R5; не автор исправлений R1. Независимость
  относится к проверяемым исправлениям.
reviewed_commit: a02420fd3b100447550740a417d75c8608206cd7
scope: Ограниченный документальный RECHECK W01–W04, B01–B03, REQ/VAL и UNKNOWN; не
  испытания и не gate decision
parameter_refs: []
artifacts:
- path: requirements/system_requirements.md
  sha256: 32b8ff810c7809324d68ebc8fb1450f0326099a7b0e2553adbce027c24865e41
- path: requirements/verification_matrix.md
  sha256: 6cdc62bf853cfdc98bba64a1e940de3b86f07897297d2c7ffbdbee1e1374bac3
- path: verification/feed_dosing_rig_scheme.md
  sha256: 7725d89f70f6dfeeff8fdea66c0192842a7d36c66f4f5ef0035ee7e7f695e35f
- path: verification/press_function_test_plan.md
  sha256: 6755d36a5acf3596e332597fe6f50c4399d845c60c4f7dde523e284e1b2b0a31
- path: verification/requirement_criteria_development.md
  sha256: 55ffcee6847dd0e0cd0e69b30bc62eee89911d258b4e2dfef3d67b7c8c5ed609
checks:
- id: CHK-W01
  method: inspection
  expected: Устранено документальное замечание без выдуманных данных
  observed: Граф событий и связей many-to-many с UNKNOWN
  reasoning: Подробности и ограничения в verification/r5_tz_recheck_01/review.md
  result: PASS
- id: CHK-W02
  method: inspection
  expected: Устранено документальное замечание без выдуманных данных
  observed: G1 и будущие результаты VAL-20 разделены
  reasoning: Подробности и ограничения в verification/r5_tz_recheck_01/review.md
  result: PASS
- id: CHK-W03
  method: inspection
  expected: Устранено документальное замечание без выдуманных данных
  observed: REQ-03 разделён на подусловия; проектные работы разграничены
  reasoning: Подробности и ограничения в verification/r5_tz_recheck_01/review.md
  result: PASS
- id: CHK-W04
  method: inspection
  expected: Устранено документальное замечание без выдуманных данных
  observed: Пригодность F, LOSS/INVALID и INDETERMINATE определены документально
  reasoning: Подробности и ограничения в verification/r5_tz_recheck_01/review.md
  result: PASS
- id: CHK-B01-B03
  method: inspection
  expected: Готовые обоснованные критерии, программа и анализ риска
  observed: Есть только план и первичная карта, блокеры открыты
  reasoning: План получения данных не является доказательством готовности
  result: FAIL
- id: CHK-TRACE
  method: inspection
  expected: Каждому из 22 REQ соответствует VAL
  observed: 22 уникальных REQ и 22 уникальные пары; пропусков и несовпадений нет
  reasoning: Структурный подсчёт не доказывает достаточность VAL
  result: PASS
findings:
- finding_id: R5-TZ-B01
  severity: BLOCKER
  evidence: verification/r5_tz_recheck_01/review.md
  impact: Блокирует утверждение ТЗ и G1
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-TZ-B02
  severity: BLOCKER
  evidence: verification/r5_tz_recheck_01/review.md
  impact: Блокирует утверждение ТЗ и G1
  owner_role: R1
  task_id: T-INIT
- finding_id: R5-TZ-B03
  severity: BLOCKER
  evidence: verification/r5_tz_recheck_01/review.md
  impact: Блокирует утверждение ТЗ и G1
  owner_role: R1
  task_id: T-INIT
verdict: REJECT_WITH_BLOCKER
validity: STALE
blocker_ids:
- R5-TZ-B01
- R5-TZ-B02
- R5-TZ-B03
allowed_downstream_scope: Документальная доработка и подготовка исследований в рамках
  действующих указаний оператора
excluded_claims:
- Утверждение ТЗ и архитектуры
- Закрытие G1 или R5-OBS-01…04
- Испытания и измерения сырья
closure_criteria:
- Проверенные критерии и входная спецификация
- Подготовленная применимая программа
- Проверенные риск и нормативная область
supersedes: null
```

## REV-R5-R2-MATERIAL-01-001

```yaml
record_type: review
review_id: REV-R5-R2-MATERIAL-01-001
kind: OUTPUT
task_id: T-r2-material-01
created_at_utc: '2026-11-11T00:09:19Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: Сессия R5 не автор входного акта и сравнения R2; ранее проверяла
  ТЗ. Независимость ограничена текущим результатом.
reviewed_commit: c78a745fb431b459bf6272b585d17a7fad977845
scope: Документальное сравнение пяти групп кандидатов и аналитическая проверка формул;
  стандарты, редакции, испытания и реальная применимость вне области
parameter_refs: []
artifacts:
- path: verification/r2_material_methods/input_audit.md
  sha256: 0ba1bf9b2d303983510adb7a567b22b0ba53d62752e872764565b105edcb0104
- path: verification/r2_material_methods/comparison.md
  sha256: 83e3a2af17ab027202f3aa0bf4416f5f4f9188e382d60e88ad97e4373d2ba86e
- path: process/input_material_measurement_passport.md
  sha256: 0594773a7bc60ad6eeba57cb826edc8aee50021e52bb85a03e2997d65d391e56
- path: process/feedstock.md
  sha256: 826bfbab4ba938b8ae4e9dbeb604eb4719c042215a1e8b3b325d356e3c97ddda
- path: process/sampling_plan.md
  sha256: 0ed4415b20157ae43d8ee27cc543ed83f6bd9a3bb58317a0c8916e2571ea962d
checks:
- id: CHK-MAT-01
  method: inspection
  expected: Исходный паспорт и план отбора сохранены, известное отделено от UNKNOWN
  observed: Три blob совпали с базой, SP-REV-06 кандидат, результаты NOT_RUN
  reasoning: Сверены репозиторные источники; исходная стенограмма не проверена
  result: PASS
- id: CHK-MAT-02
  method: independent_derivation
  expected: Пересчёт влажности и пределы математически согласованы
  observed: Четыре рациональных примера, прямой и обратный переход согласованы; нулевые
    знаменатели исключаются
  reasoning: Формулы для потери массы, доказательство в отчёте
  result: PASS
- id: CHK-MAT-03
  method: inspection
  expected: Ограничения для неоднородной смеси и источников явно указаны
  observed: Представительность, потери, редкие металлы и отсутствие нормативных источников
    отражены; W01–W04 на дальнейшую разработку
  reasoning: Это сравнение кандидатов, а не квалификация метода
  result: PASS
- id: CHK-MAT-04
  method: inspection
  expected: Подтверждение стандартов и фактической пригодности для REV
  observed: Первоисточники и лабораторная валидация недоступны или не выполнены
  reasoning: Вне области данной документальной оценки, нормативные выводы исключены
  result: NOT_RUN
findings:
- finding_id: R5-MAT-W01
  severity: WARNING
  evidence: verification/r5_r2_material_review/review.md
  impact: Требует проработки до выбора метода и утверждения программы
  owner_role: R2
  task_id: T-r2-material-01
- finding_id: R5-MAT-W02
  severity: WARNING
  evidence: verification/r5_r2_material_review/review.md
  impact: Требует проработки до выбора метода и утверждения программы
  owner_role: R2
  task_id: T-r2-material-01
- finding_id: R5-MAT-W03
  severity: WARNING
  evidence: verification/r5_r2_material_review/review.md
  impact: Требует проработки до выбора метода и утверждения программы
  owner_role: R2
  task_id: T-r2-material-01
- finding_id: R5-MAT-W04
  severity: WARNING
  evidence: verification/r5_r2_material_review/review.md
  impact: Требует проработки до выбора метода и утверждения программы
  owner_role: R2
  task_id: T-r2-material-01
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: Документальная проработка методов и подготовка программы
  с ограничениями; без отбора и выбора утверждённых методов
excluded_claims:
- Применимость или актуальность стандартов
- Реальная представительность и пригодность приборов
- Закрытие B01–B03, R5-OBS-01…04 или G1
- Физические испытания
warning_owner_and_due:
  owner_role: R2
  owner_session: r2-material-01
  due: До выбора методик и утверждения программы
  restriction: Ни методы ни требования не утверждаются данным review
closure_criteria:
- Разработать условия влажности и интерпретации потери массы
- Обосновать обнаружение редких металлов и представительность
- Обеспечить контроль потерь и пересчёт баз
- Проверить доступные первоисточники и пригодность с компетентной лабораторией
supersedes: null
```

## REV-R5-R2-MATERIAL-RECHECK-01-001

```yaml
record_type: review
review_id: REV-R5-R2-MATERIAL-RECHECK-01-001
kind: RECHECK
task_id: T-r2-material-01
created_at_utc: '2026-11-11T00:28:46Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: Автор исходного review R5 не является автором проверяемого ответа
  R2; независимость ограничена ответом.
reviewed_commit: fcbeefae46b4fd999c194bd214b5dda7c476b0ec
scope: Документальный RECHECK ответа на W01–W04 и аналитика формул; применимость методов,
  первоисточники и испытания вне объёма
parameter_refs: []
artifacts:
- path: verification/r2_material_methods/response_r5_material_01.md
  sha256: e9b445fe58c83c36f00fc45c452dccf868b05e8572f04d364781dffe8f2f303a
- path: verification/r2_material_methods/comparison.md
  sha256: 83e3a2af17ab027202f3aa0bf4416f5f4f9188e382d60e88ad97e4373d2ba86e
- path: verification/r5_r2_material_review/review.md
  sha256: 13f2c69717d0adfa7ba68c5c5cd998c3f0ece28de20acbf5959a5d43e8249a81
checks:
- id: CHK-MAT-W01
  method: inspection
  expected: Документальный ответ на замечание с сохранением неопределённости
  observed: Условия влажности и проверка границ оформлены; вода и потеря массы различаются
  reasoning: Проверено по исходному акту; план не является выполнением
  result: PASS
- id: CHK-MAT-W02
  method: inspection
  expected: Документальный ответ на замечание с сохранением неопределённости
  observed: Объект вывода, отбор, охват и обнаруживаемость редких событий разграничены
  reasoning: Проверено по исходному акту; план не является выполнением
  result: PASS
- id: CHK-MAT-W03
  method: inspection
  expected: Документальный ответ на замечание с сохранением неопределённости
  observed: Потери и баланс по стадиям, сегрегация и пересчёт баз предусмотрены
  reasoning: Проверено по исходному акту; план не является выполнением
  result: PASS
- id: CHK-MAT-W04
  method: inspection
  expected: Документальный ответ на замечание с сохранением неопределённости
  observed: Порядок проверки текстов и лаборатории описан, непроверенное остаётся
    NOT_RUN
  reasoning: Проверено по исходному акту; план не является выполнением
  result: PASS
- id: CHK-MAT-ARITH
  method: independent_derivation
  expected: Формулы влажности и пересчёта долей корректны при заданных предпосылках
  observed: Три пары и двухклассовый пример сошлись в точной рациональной арифметике
  reasoning: Подробности и предельные случаи в review.md
  result: PASS
- id: CHK-MAT-SOURCES
  method: inspection
  expected: Фактическая проверка первоисточников и подтверждение пригодности
  observed: Недоступные источники, методики и проверка лабораторией не проверялись
  reasoning: За пределами документального RECHECK; не подтверждаются
  result: NOT_RUN
findings: []
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: Документальная подготовка выбора методов и программы; W01–W04
  закрыты только по ответу
excluded_claims:
- Подтверждение действующих стандартов и методик
- Реальная пригодность лаборатории и средств
- Закрытие B01–B03 и G1
- Результаты отбора или испытаний
warning_owner_and_due:
  owner_role: R2
  owner_session: r2-material-01
  due: До выбора методик и утверждения программы
  restriction: Проверить первоисточники и пригодность с лабораторией; данные и методы
    остаются UNKNOWN
closure_criteria:
- Получить и проверить доступные тексты и редакции
- Согласовать представительность, чувствительность и методику с компетентной лабораторией
- Подготовить и независимо проверить программу
supersedes: null
```

## REV-R5-R2-SOURCES-01-001

```yaml
record_type: review
review_id: REV-R5-R2-SOURCES-01-001
kind: OUTPUT
task_id: T-r2-sources-01
created_at_utc: '2026-11-11T00:50:28Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: R5 не автор входного акта и реестра R2; ранее проверял предшествующие
  документы. Независимость относится к текущему результату.
reviewed_commit: 25745de1c69d2f0dd6adf8a6f10e8f7af59305a9
scope: Документальный OUTPUT-review реестра и попытки доступа к источникам; чтение
  источников, лаборатория и методики не проверены
parameter_refs: []
artifacts:
- path: verification/r2_primary_sources/input_audit.md
  sha256: 156163594860133e8d23a3fe00cbd6a654a719b6371e520ae19e84a60819a1f8
- path: verification/r2_primary_sources/registry.md
  sha256: 726c7185438e6a59d033caed3deff90f622f3c1a95c9abb8790784bd05c7b928
checks:
- id: CHK-SRC-01
  method: inspection
  expected: Установить доступность и независимо проверить прочитанные R2 разделы SRC-01…04
  observed: Четыре запроса OSTI CONNECT 403, документы не получены
  reasoning: Описания, SHA PDF и редакции независимо сверить невозможно
  result: NOT_RUN
- id: CHK-SRC-02
  method: inspection
  expected: Независимо прочитать три NREL LAP
  observed: Три запроса CONNECT 403
  reasoning: Полные тексты и их редакции недоступны в текущей среде
  result: NOT_RUN
- id: CHK-SRC-03
  method: inspection
  expected: Пробел по физическим включениям отделён от анализа растворённых металлов
  observed: В реестре явно указан UNKNOWN/NOT_RUN и различие с химическим анализом
  reasoning: Вывод относится к формулировке реестра; поиск OSTI самостоятельно не
    проверен
  result: PASS
- id: CHK-SRC-04
  method: inspection
  expected: Данные других материалов не присвоены REV
  observed: Реестр маркирует другие матрицы, ограничения и неизвестную пригодность
  reasoning: Оценён текст реестра, не недоступные документы
  result: PASS
findings:
- finding_id: R5-SRC-B01
  severity: BLOCKER
  evidence: verification/r5_r2_sources_review/review.md
  impact: Независимая сверка прочитанных разделов и редакций не выполнена из-за CONNECT
    403
  owner_role: R2
  task_id: T-r2-sources-01
- finding_id: R5-SRC-W01
  severity: WARNING
  evidence: verification/r5_r2_sources_review/review.md
  impact: Нет подтверждённого метода физических металлических включений
  owner_role: R2
  task_id: T-r2-sources-01
- finding_id: R5-SRC-W02
  severity: WARNING
  evidence: verification/r5_r2_sources_review/review.md
  impact: Требуется проверка редакций и лабораторной пригодности
  owner_role: R2
  task_id: T-r2-sources-01
verdict: REJECT_WITH_BLOCKER
validity: STALE
blocker_ids:
- R5-SRC-B01
allowed_downstream_scope: Документальная работа с явно непроверенными ссылками и ограничениями,
  получение первоисточников
excluded_claims:
- Подтверждение заявленных R2 разделов, хэшей PDF или редакций
- Утверждение методов, стандартов или лабораторной пригодности
- Физические испытания, закрытие B01–B03 и G1
closure_criteria:
- Получить доступные копии, проверить хэши, названия, версии и прочесть конкретные
  заявленные разделы
- Независимо повторить сверку и зафиксировать недоступные части
supersedes: null
```

## REV-R5-R2-SOURCES-RECHECK-01-001

```yaml
record_type: review
review_id: REV-R5-R2-SOURCES-RECHECK-01-001
kind: RECHECK
task_id: T-r2-sources-01
created_at_utc: '2026-11-11T00:59:23Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: Reviewer автор предыдущего акта, но не автор реестра R2 или переданного
  пакета; независимость относится к этой сверке.
reviewed_commit: d9bc2f101ca001de763b5418dbe7cb2ad2ca5ab2
scope: Сверка LFS копий SRC-01…04 и реестра 25745de1; три LAP, действительность редакций
  и применимость REV NOT_RUN
parameter_refs: []
artifacts:
- path: verification/r2_primary_sources/registry.md
  sha256: 726c7185438e6a59d033caed3deff90f622f3c1a95c9abb8790784bd05c7b928
- path: verification/r2_primary_sources/copies/README.md
  sha256: 9bedf66d0a6ea870ea877d4a4b1562a4fcc71a14e63e2634860fa41cd25147b6
- path: verification/r2_primary_sources/copies/SRC-01.pdf
  sha256: 7556a16ba04626ced124b698cd02fc6c35a6871aaabc9f083ecdd266a6827200
- path: verification/r2_primary_sources/copies/SRC-02.pdf
  sha256: d5ddb2e3cf0ac960cdec843df5917d46046c3bc77b47c7a13454105245b6e8c4
- path: verification/r2_primary_sources/copies/SRC-03.pdf
  sha256: c9ffd5e57941e397b9d30d49e2baddc302f0a182736af2f0f08a3cbe7579736b
- path: verification/r2_primary_sources/copies/SRC-04.pdf
  sha256: 1bd9adaf21a3a7691ec18382a3cf02156ee1ba2ad4e7d93e905bfd6ee0b3a6b3
checks:
- id: CHK-SRC-01
  method: inspection
  expected: Проверить копию, титул и заявленные места в источнике
  observed: Хэш, титул, даты версии и §§1–5 проверены; область водоросли
  reasoning: PDF-страницы и ограничения в verification/r5_r2_sources_recheck_01/review.md
  result: PASS
- id: CHK-SRC-02
  method: inspection
  expected: Проверить копию, титул и заявленные места в источнике
  observed: Хэш и титул/аннотация/введение/§§2.1–2.3 проверены; дата OSTI, DOI и статус
    рукописи в копии не подтверждены
  reasoning: PDF-страницы и ограничения в verification/r5_r2_sources_recheck_01/review.md
  result: PASS
- id: CHK-SRC-03
  method: inspection
  expected: Проверить копию, титул и заявленные места в источнике
  observed: Хэш, титул и препринт проверены; детали плотности/влажности в §2.3, просев
    §2.4, требуется уточнение реестра
  reasoning: PDF-страницы и ограничения в verification/r5_r2_sources_recheck_01/review.md
  result: FAIL
- id: CHK-SRC-04
  method: inspection
  expected: Проверить копию, титул и заявленные места в источнике
  observed: Хэш, титул, §1.3 и библиография проверены; номера ссылок ash/lignin в
    источнике противоречат списку
  reasoning: PDF-страницы и ограничения в verification/r5_r2_sources_recheck_01/review.md
  result: PASS
- id: CHK-LAP
  method: inspection
  expected: Проверить три NREL LAP и их редакции
  observed: Три текста отсутствуют в пакете и непрочитаны
  reasoning: Библиография в SRC-04 не заменяет тексты LAP
  result: NOT_RUN
findings:
- finding_id: R5-SRC-B01
  severity: BLOCKER
  evidence: verification/r5_r2_sources_recheck_01/review.md
  impact: Четыре копии получены, но три LAP и некоторые атрибуты остаются непроверенными
  owner_role: R2
  task_id: T-r2-sources-01
- finding_id: R5-SRC-R01
  severity: WARNING
  evidence: SRC-03 §§2.1–2.4 и реестр SRC-03
  impact: Требуется явно исправить ссылки на разделы в реестре
  owner_role: R2
  task_id: T-r2-sources-01
- finding_id: R5-SRC-R02
  severity: WARNING
  evidence: SRC-04 §1.3 и список references
  impact: Номера 5 и 6 в тексте выглядят перепутанными; сверять по названию
  owner_role: R2
  task_id: T-r2-sources-01
verdict: REJECT_WITH_BLOCKER
validity: STALE
blocker_ids:
- R5-SRC-B01
allowed_downstream_scope: Документальная работа с подтверждёнными разделами и указанными
  ограничениями; получение и сверка недостающих LAP
excluded_claims:
- Актуальность редакций и нормативных документов
- Пригодность методов к REV или квалификация лаборатории
- Эксперименты и закрытие B01–B03 или G1
closure_criteria:
- Уточнить реестр SRC-03 и атрибуты SRC-02
- Получить и независимо прочитать три LAP; проверить версию и содержание
- Сохранить ограничения на актуальность и применимость
supersedes: null
```

## REV-R5-R2-SOURCES-RECHECK-02-001

```yaml
record_type: review
review_id: REV-R5-R2-SOURCES-RECHECK-02-001
kind: RECHECK
task_id: T-r2-sources-01
created_at_utc: '2026-11-11T01:09:23Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: R5 автор предыдущего review, не автор исправленного реестра R2;
  независимость относится к проверяемым исправлениям.
reviewed_commit: c0a101a3471942e169599086365941bbaa67ce94
scope: Ограниченный RECHECK реестра SRC-02…04 и R5-SRC-B01; отсутствующие LAP и актуальность
  методов вне проверенной области
parameter_refs: []
artifacts:
- path: verification/r2_primary_sources/registry.md
  sha256: 6eec6aa5f45ad8b1715973e3ce2a9affbb6679c6388e6ffce452665d0931d346
- path: verification/r2_primary_sources/copies/SRC-02.pdf
  sha256: d5ddb2e3cf0ac960cdec843df5917d46046c3bc77b47c7a13454105245b6e8c4
- path: verification/r2_primary_sources/copies/SRC-03.pdf
  sha256: c9ffd5e57941e397b9d30d49e2baddc302f0a182736af2f0f08a3cbe7579736b
- path: verification/r2_primary_sources/copies/SRC-04.pdf
  sha256: 1bd9adaf21a3a7691ec18382a3cf02156ee1ba2ad4e7d93e905bfd6ee0b3a6b3
checks:
- id: CHK-03
  method: inspection
  expected: Разделы SRC-03 перечислены в соответствии с текстом
  observed: §§2.1–2.2 план/площадка; §2.3 плотность и влажность; §2.4 просев
  reasoning: Сверены PDF-страницы 7–11 и обновлённый реестр
  result: PASS
- id: CHK-04
  method: inspection
  expected: Оговорка о номерах ссылок соответствует оригиналу
  observed: В §1.3 ash5/lignin6, в references №5 lignin/№6 ash
  reasoning: Предупреждение сохранено без исправления первоисточника
  result: PASS
- id: CHK-02
  method: inspection
  expected: Атрибуты из карточки отделены от атрибутов PDF
  observed: Источник атрибутов указан, подтверждение R5 и связь с версией PDF NOT_RUN
  reasoning: Независимый запрос карточки CONNECT 403
  result: PASS
- id: CHK-B01
  method: inspection
  expected: Прочитать три LAP и проверить все необходимые источники
  observed: Три LAP отсутствуют; карточка OSTI SRC-02 не получена
  reasoning: Не полученные тексты и атрибуты не могут быть подтверждены
  result: NOT_RUN
findings:
- finding_id: R5-SRC-B01
  severity: BLOCKER
  evidence: verification/r5_r2_sources_recheck_02/review.md
  impact: Три LAP и атрибуты карточки SRC-02 не проверены независимо
  owner_role: R2
  task_id: T-r2-sources-01
verdict: REJECT_WITH_BLOCKER
validity: CURRENT
blocker_ids:
- R5-SRC-B01
allowed_downstream_scope: Использование сверенных разделов с ограничениями и получение
  недостающих источников
excluded_claims:
- Подтверждение действующих редакций и применимости к REV
- Прочтение отсутствующих LAP
- Закрытие B01–B03 или G1
- Физические пробы и испытания
closure_criteria:
- Получить и независимо прочитать LAP 42620, 42621 и 42622
- Проверить либо явно разрешить оставшиеся библиографические атрибуты SRC-02
supersedes: null
```

## REV-R5-R2-LAP-RECHECK-01-001

```yaml
record_type: review
review_id: REV-R5-R2-LAP-RECHECK-01-001
kind: RECHECK
task_id: T-r2-sources-01
created_at_utc: '2026-11-11T01:41:01Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: R5 не автор пакета R2; ранее проверял реестр и является автором
  предыдущих актов. Независимость относится к новой передаче.
reviewed_commit: 3bc59174fb850e9cf818df23ec55f9bc9c8a23f6
scope: Сверка конкретных трёх LAP копий и сохранённой карточки SRC-02; не нормативная
  актуальность и не пригодность REV
parameter_refs: []
artifacts:
- path: verification/r2_primary_sources/lap_evidence/README.md
  sha256: 95f004a3436f2f448c42ae998108e451757e855aa7af55d9be6bc76aff598fb4
- path: verification/r2_primary_sources/lap_evidence/NREL-42620.pdf
  sha256: e3d3afc47572ff3fa28dff1258da31348f217b8a9d127a68132a603371786e1c
- path: verification/r2_primary_sources/lap_evidence/NREL-42621.pdf
  sha256: bca9e0a067a83a8ed2a092bbf5ef7a594b63db86596a6da883aedaff1e41e8c3
- path: verification/r2_primary_sources/lap_evidence/NREL-42622.pdf
  sha256: ae20ddf840f27d11297e8960fe1c7abbb47cf074f355602eab131b358d24bda6
- path: verification/r2_primary_sources/lap_evidence/osti-1328338.json
  sha256: 7073a0d546e63902e4c6c7a156c84d302263b38be5811fde34d4940e2a64f4ea
- path: verification/r2_primary_sources/copies/SRC-02.pdf
  sha256: d5ddb2e3cf0ac960cdec843df5917d46046c3bc77b47c7a13454105245b6e8c4
checks:
- id: CHK-LAP-HASH
  method: inspection
  expected: Скачать и сверить SHA трёх PDF и JSON
  observed: Все четыре SHA совпадают с манифестом
  reasoning: sha256sum и git lfs pull, точные хэши в отчёте
  result: PASS
- id: CHK-LAP-CONTENT
  method: inspection
  expected: Прочитать титулы и необходимые разделы трёх копий
  observed: Титулы и указанные §§ прочитаны; 42620 титул 2008, SRC-04 библиография
    2010
  reasoning: Конкретные страницы и границы в отчёте, статус 2010 не установлен
  result: PASS
- id: CHK-LAP-CARD
  method: inspection
  expected: Прочитать карточку и оценить связь с конкретным PDF SRC-02
  observed: Поля и fulltext URL подтверждены в сохранённом JSON; конкретная версия
    и байтовая связь не доказаны; аннотации расходятся
  reasoning: Совпадение URL и заголовка не заменяет идентификатор файла или сверку
    версий
  result: FAIL
- id: CHK-LAP-CURRENT
  method: inspection
  expected: Установить действующие редакции и пригодность REV
  observed: Актуальность и лабораторная оценка не проверены
  reasoning: Вне области и без необходимых доказательств
  result: NOT_RUN
findings:
- finding_id: R5-SRC-B01
  severity: BLOCKER
  evidence: verification/r5_r2_lap_recheck/review.md
  impact: Три копии и карточка прочитаны; конкретная связь карточки с PDF и расхождение
    дат LAP 42620 остаются неразрешёнными
  owner_role: R2
  task_id: T-r2-sources-01
- finding_id: R5-LAP-01
  severity: WARNING
  evidence: LAP 42620 титул и SRC-04 библиография
  impact: 2008 на титуле против 2010 в библиографии; происхождение версии неизвестно
  owner_role: R2
  task_id: T-r2-sources-01
- finding_id: R5-LAP-02
  severity: WARNING
  evidence: osti-1328338.json description и SRC-02 PDF abstract
  impact: Противоположные формулировки aspect ratio не позволяют приписать PDF конкретной
    версии
  owner_role: R2
  task_id: T-r2-sources-01
verdict: REJECT_WITH_BLOCKER
validity: CURRENT
blocker_ids:
- R5-SRC-B01
allowed_downstream_scope: Работа с прочитанными разделами только как с данными конкретных
  копий; уточнение происхождения и версий
excluded_claims:
- Актуальность редакций или применимость стандартов REV
- Подлинность источников и версия SRC-02 доказаны
- Испытания, отбор, закрытие B01–B03 или G1
closure_criteria:
- Независимо разрешить библиографическое расхождение 42620 или установить достаточное
  обоснование пределов идентификации
- Проверить происхождение и версию SRC-02 и объяснить расхождение аннотаций либо документально
  ограничить доказательство на согласованном основании
supersedes: null
```

## REV-R5-R2-VERSION-REVIEW-01-001

```yaml
record_type: review
review_id: REV-R5-R2-VERSION-REVIEW-01-001
kind: OUTPUT
task_id: T-r2-sources-01
created_at_utc: '2026-11-11T01:52:15Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: R5 автор прежнего акта, не автор проверяемого исследования R2;
  независимость ограничена данным исследованием.
reviewed_commit: cec689d77087d912ebfe34425cb8d288768637c2
scope: Сверка сохранённых копий и исследования дат/версий, исключение неподтверждённых
  выводов; не действительность стандартов и пригодность REV
parameter_refs: []
artifacts:
- path: verification/r2_primary_sources/version_inquiry/report.md
  sha256: ba0cfc2fd5283ac2b0a4242b00533d9daf4c55c74979d60538846fac4440e952
- path: verification/r2_primary_sources/version_inquiry/openalex-42620.json
  sha256: 62fd29dc0950d6e540e0fafd24bb02d721da169a968e5ed8a2bff96c33d8779c
- path: verification/r2_primary_sources/version_inquiry/openalex-src02.json
  sha256: 3877bc34cbdf94f20170d82a506dd9a960a0aeb633bd7f1208be8fd33a43e443
- path: verification/r2_primary_sources/version_inquiry/crossref-src02.json
  sha256: 195cbb4e30c020e19eadc039866bd7e9796d3ccefa38726a4ec938b53e618754
- path: verification/r2_primary_sources/lap_evidence/NREL-42620.pdf
  sha256: e3d3afc47572ff3fa28dff1258da31348f217b8a9d127a68132a603371786e1c
- path: verification/r2_primary_sources/lap_evidence/osti-1328338.json
  sha256: 7073a0d546e63902e4c6c7a156c84d302263b38be5811fde34d4940e2a64f4ea
- path: verification/r2_primary_sources/copies/SRC-02.pdf
  sha256: d5ddb2e3cf0ac960cdec843df5917d46046c3bc77b47c7a13454105245b6e8c4
- path: verification/r2_primary_sources/copies/SRC-04.pdf
  sha256: 1bd9adaf21a3a7691ec18382a3cf02156ee1ba2ad4e7d93e905bfd6ee0b3a6b3
checks:
- id: CHK-LAP-01
  method: inspection
  expected: Сверить свидетельства разных дат и не утверждать неизвестную историю
  observed: Титул 2008, PDF metadata 08/08/2008, библиография SRC-04 2010; причина
    UNKNOWN
  reasoning: Сохранена только область конкретной копии 2008, открытая история исключена
    из использования
  result: PASS
- id: CHK-LAP-02
  method: inspection
  expected: Проверить внутреннее расхождение SRC-02 и исключить неподтверждённое отношение
  observed: Аннотация и §3.4/заключение противоположны; версия и правильный результат
    UNKNOWN
  reasoning: Карточка поддерживает направление текста, но не идентифицирует байты
  result: PASS
- id: CHK-HASH
  method: inspection
  expected: SHA каждой сохранённой копии совпадает с отчётом
  observed: 'openalex-src02.json: в отчёте 55 символов и не совпадает; Git blob и
    файл имеют SHA 3877bc34cbdf94f20170d82a506dd9a960a0aeb633bd7f1208be8fd33a43e443'
  reasoning: Две независимые проверки сохранённых байтов, другие проверенные хэши
    совпали
  result: FAIL
- id: CHK-ACTUAL
  method: inspection
  expected: Подтвердить актуальность стандартов и пригодность REV
  observed: Не исследовались, данных нет
  reasoning: Не входят в документальную область
  result: NOT_RUN
findings:
- finding_id: R5-VERSION-B01
  severity: BLOCKER
  evidence: verification/r5_r2_version_recheck/review.md
  impact: В отчёте R2 ошибочный и неполный SHA OpenAlex JSON; полная прослеживаемость
    пакета не принята
  owner_role: R2
  task_id: T-r2-sources-01
verdict: REJECT_WITH_BLOCKER
validity: STALE
blocker_ids:
- R5-VERSION-B01
allowed_downstream_scope: Ограниченное документальное использование проверенных копий
  с исключением спорных дат и AR; R5-SRC-B01 закрыт в этой области
excluded_claims:
- Действительность редакций и пригодность к REV
- Правильное AR и происхождение версий
- Закрытие B01–B03 и G1
- Физические пробы и испытания
closure_criteria:
- R2 сверяет происхождение OpenAlex JSON и исправляет контрольную сумму в новой ревизии
- Независимо сверить новый SHA с Git blob и предоставленной копией
supersedes: null
```

## REV-R5-VERSION-HASH-RECHECK-01-001

```yaml
record_type: review
review_id: REV-R5-VERSION-HASH-RECHECK-01-001
kind: RECHECK
task_id: T-r2-sources-01
created_at_utc: '2026-11-11T02:04:03Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: R5 автор предыдущего review, не автор исправленного отчёта R2;
  независимость относится к этому исправлению.
reviewed_commit: 4605f3435c5882550d540ff797e7322613723769
scope: 'Ограниченный RECHECK R5-VERSION-B01: сумма, локальная копия, история и оговорка;
  без подтверждения внешнего происхождения'
parameter_refs: []
artifacts:
- path: verification/r2_primary_sources/version_inquiry/report.md
  sha256: 6c5b2df19889e97886e0be9c5b1ac5d48ffbf282a7c65481f3595b8f7cdd6e3b
- path: verification/r2_primary_sources/version_inquiry/openalex-src02.json
  sha256: 3877bc34cbdf94f20170d82a506dd9a960a0aeb633bd7f1208be8fd33a43e443
checks:
- id: CHK-HASH-01
  method: inspection
  expected: SHA исправленного отчёта совпадает с Git-байтами и доступной копией
  observed: 'Все три SHA рабочего файла, исходного и нового Git blobs совпали: 3877bc34cbdf94f20170d82a506dd9a960a0aeb633bd7f1208be8fd33a43e443'
  reasoning: sha256sum и git show | sha256sum; данные не изменялись
  result: PASS
- id: CHK-HASH-02
  method: inspection
  expected: История исправления и предыдущий акт сохранены
  observed: Предыдущий акт предок; исходная строка сохранена в Git и процитирована;
    акт STALE к новому результату
  reasoning: git merge-base, git show и diff
  result: PASS
- id: CHK-HASH-03
  method: inspection
  expected: Внешнее происхождение не утверждается без доказательства
  observed: Отчёт оговаривает отсутствие независимого подтверждения; R2 сообщает о
    cmp в своей среде
  reasoning: Оговорка корректна и не устанавливает подлинность
  result: PASS
- id: CHK-HASH-04
  method: inspection
  expected: Независимый повтор сравнения с первоначальным временным файлом
  observed: Файл /tmp/rev_src02_openalex.json отсутствует в среде R5
  reasoning: Заявленный R2 cmp не воспроизведён, источник сетевого ответа не удостоверен
  result: NOT_RUN
findings: []
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: R5-VERSION-B01 CLOSED по сохранённым Git-байтам и доступной
  копии; документальное исследование с ограничениями
excluded_claims:
- Независимая проверка отсутствующей временной копии и сетевого происхождения
- Актуальность редакций и пригодность REV
- Закрытие B01–B03 или G1
warning_owner_and_due:
  owner_role: R2
  owner_session: r2-material-01
  due: До использования внешних данных в качестве подтверждённого источника
  restriction: Внешнее происхождение и подлинность требуют независимого подтверждения
closure_criteria:
- Для внешнего источника — независимое подтверждение происхождения и применимости
  при необходимости
supersedes: null
```

## REV-R5-R2-METAL-01-001

```yaml
record_type: review
review_id: REV-R5-R2-METAL-01-001
kind: OUTPUT
task_id: T-r2-metal-01
created_at_utc: '2026-11-11T02:36:28Z'
reviewer:
  role: R5
  session_id: r5-implementation-02
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: R5 ранее оформлял R5-SRC-W01, но не является автором проверяемых
  документов R2. Независимость относится к ним.
reviewed_commit: 4dfcec6829fda861886aaa9a0e89cb63214cc894
scope: Документальный OUTPUT-review кандидатов физических включений и попытки независимой
  сверки источников; не выбор метода и не испытания
parameter_refs: []
artifacts:
- path: verification/metal_detection_research_brief.md
  sha256: 3ea1877d5efb3a998d598f0bd9ce93ac8b4c34d8d1f25966cdff5f7e3c965854
- path: verification/r2_metal_detection/input_audit.md
  sha256: b1dcf6c81c8242e4d9e7592e6c18f1d4cf3bb52639f046a8a08a4c4c2f5aafb4
- path: verification/r2_metal_detection/research.md
  sha256: 25f2b110b4ec1fe8a81592b09849b6093b1a902ec025778cb3e519aadad4f94e
- path: verification/r2_metal_detection/source_excerpts.md
  sha256: 925da34b688dc0c61cbed3048ca2d786ff631fb2b68a3e9dba4f195657766c6d
checks:
- id: CHK-METAL-01
  method: inspection
  expected: Сохранить постановку и разделить обнаружение и удаление
  observed: В исследовании сигнал и удаление различаются; входной blob brief совпал
  reasoning: Проверен текст документов, не технические утверждения сайтов
  result: PASS
- id: CHK-METAL-02
  method: inspection
  expected: Различать магнитные/немагнитные объекты, редкие случаи и нулевые находки
  observed: Ограничения и неопределённости изложены; нулевой остаток не утверждён
  reasoning: Достаточно для документального разграничения, не для чувствительности
    REV
  result: PASS
- id: CHK-METAL-03
  method: inspection
  expected: Независимо сверить первичные страницы M01–M06
  observed: Все шесть URL CONNECT 403; полные страницы не получены
  reasoning: Короткие выдержки и хэши R2 не подменяют независимое прочтение
  result: NOT_RUN
- id: CHK-METAL-04
  method: inspection
  expected: Не назначать параметры изготовителей REV
  observed: Указаны UNKNOWN и ограничения; перенос численных параметров не обнаружен
  reasoning: Документальная проверка не подтверждает свойства приборов
  result: PASS
findings:
- finding_id: R5-METAL-B01
  severity: BLOCKER
  evidence: verification/r5_r2_metal_review/review.md
  impact: 'Сверка шести первичных страниц и их утверждений не выполнена: CONNECT 403'
  owner_role: R2
  task_id: T-r2-metal-01
- finding_id: R5-METAL-W01
  severity: WARNING
  evidence: verification/r5_r2_metal_review/review.md
  impact: Охват/обнаружение и независимое подтверждение эффективности требуют будущей
    программы
  owner_role: R2
  task_id: T-r2-metal-01
verdict: REJECT_WITH_BLOCKER
validity: STALE
blocker_ids:
- R5-METAL-B01
allowed_downstream_scope: Документальное исследование с явно не подтверждёнными источниками;
  получение проверяемых копий
excluded_claims:
- Независимая проверка M01–M06
- Закрытие R5-SRC-W01, B01–B03 и G1
- Выбор прибора/метода, физические пробы и испытания
closure_criteria:
- Получить и независимо прочитать доступные полные страницы M01–M06 или проверяемые
  копии, сопоставить каждый тезис и обозначить ограничения
- Оценить достаточность документальной области R5-SRC-W01 отдельным актом
supersedes: null
```

## Регистрация независимой сверки M01–M06

```yaml
record_type: review
review_id: REV-R5-METAL-INDEPENDENT-01-001
kind: RECHECK
task_id: T-r2-metal-01
created_at_utc: '2026-11-11T04:00:45Z'
reviewer:
  role: R5
  session_id: 6af3e1ba-0700-8191-a54b-0e6076cdc076
  model_label: Codex
reviewed_roles:
- R2
author_sessions:
- r2-material-01
independence_basis: По акту новая runtime-сессия не участвовала в создании R2 по доступной
  истории; идентификаторы не удостоверяют личность и неизвестное участие. Регистрирует
  R1, без приписывания ID к акту 2a8d43b.
reviewed_commit: 39f54598e3ab9997ea60d34fd2b203a28bc44822
parameter_refs: []
artifacts:
- path: verification/r2_metal_detection/research.md
  sha256: d47c287635a8abe0f9b627a2bffc52e3be3df16c4a588e5daa47cec9c71b472b
- path: verification/r2_metal_detection/source_excerpts.md
  sha256: 925da34b688dc0c61cbed3048ca2d786ff631fb2b68a3e9dba4f195657766c6d
scope: Документальная сверка утверждений по M01–M06 и ограничений; пригодность REV
  и эксперимент вне области.
checks:
- id: CHK-METAL-SOURCES
  method: inspection
  expected: Независимо прочитать шесть страниц и сопоставить с утверждениями и областью
  observed: По опубликованному акту все шесть HTTP 200, хэши совпали; утверждения
    сверены в контексте.
  reasoning: Данные — заявления изготовителей, а не независимая валидация или пригодность
    REV.
  result: PASS
findings: []
verdict: WARNING
validity: CURRENT
allowed_downstream_scope: Документальная подготовка программы и изучение кандидатов.
excluded_claims:
- Применимость, обнаруживаемость и эффективность для REV
- Выбор метода или прибора; безопасность и G1
- Пробы и испытания
blocker_ids: []
warning_owner_and_due:
  owner_role: R2
  owner_session: r2-material-01
  due: До выбора метода и утверждения программы
  restriction: Реальные свойства потока, область и проверка обнаружения UNKNOWN; независимая
    оценка программы обязательна.
closure_criteria:
- Определить условия потока и охват, обосновать вероятность обнаружения
- Согласовать и независимо проверить программу до выбора метода
traceability_and_revisions: R1 регистрирует предоставленный акт без изменения его
  содержания; ID записи присвоен при регистрации.
reproduction_artifacts:
- verification/r5_r2_metal_independent_recheck/review.md
- verification/r5_r2_metal_independent_recheck/access_manifest.json
supersedes: null
```

## Регистрация OUTPUT-review R3

```yaml
record_type: review
review_id: REV-R5-R3-SAFETY-01-001
kind: OUTPUT
task_id: T-r3-safety-01-01
created_at_utc: '2026-11-11T08:05:54Z'
reviewer:
  role: R5
  session_id: r5-r3-safety-output-20261111-0740
  model_label: Codex
reviewed_roles:
- R3
author_sessions:
- r3-safety-01
independence_basis: На основании опубликованного акта reviewer не автор проверяемой
  редакции; ID не удостоверяет организационную независимость или профессиональную
  компетентность. Запись зарегистрирована R1 по опубликованному акту.
reviewed_commit: 43c5a0f0e89b386fdf07600cc6ccf27c7e6fa63c
parameter_refs: []
artifacts:
- path: verification/r3_press_safety/input_audit.md
  sha256: 7a53ae522a3ba682cbe718600abca401a9f617fb26fc95a637ddb0d924cbce3a
- path: verification/r3_press_safety/preliminary_hazards.md
  sha256: 016fa3703232c36176d63ea1350f5ff5564d1a704ac8b190e2cb2478dafe71cd
- path: verification/r3_press_safety/traceability.md
  sha256: 018143d72710cd9b49efad4c9221c491e2b2ac85d1374fa8eca967e4bd6ed577
- path: verification/r3_press_safety/normative_scope_questions.md
  sha256: c1dcfeb34966367ffb9445868a803335fa19e921fc640d424faa10b57f32cd47
scope: Документальная проверка входного акта, карты опасностей, REQ/VAL и нормативных
  вопросов; физическая безопасность и применимость норм вне области.
checks:
- id: CHK-SAFETY-REGISTRATION
  method: inspection
  expected: Воспроизводимая ревизия входа VAL
  observed: Акт R5 выявил rev6 в аудите при rev7 в файле
  reasoning: Несоответствие входной базы требует исправления и независимого RECHECK.
  result: FAIL
findings: []
verdict: REJECT_WITH_BLOCKER
validity: STALE
blocker_ids:
- R5-SAFETY-B01
allowed_downstream_scope: Только документальная подготовка и независимая проверка,
  без утверждения защит или ТЗ.
excluded_claims:
- Исчерпывающий анализ риска и эффективность защит
- Нормативная применимость и прохождение G1
- Реальные измерения и испытания
warning_owner_and_due: null
closure_criteria:
- Исправить ревизию VAL и независимо проверить влияние различий
traceability_and_revisions: Запись оформлена R1 при интеграции по опубликованному
  акту; created_at_utc — время регистрации, а не исходного запуска review.
reproduction_artifacts:
- verification/r5_r3_safety_output/review.md
supersedes: null
```

## Регистрация RECHECK R3

```yaml
record_type: review
review_id: REV-R5-R3-SAFETY-RECHECK-01-001
kind: RECHECK
task_id: T-r3-safety-01-01
created_at_utc: '2026-11-11T08:05:54Z'
reviewer:
  role: R5
  session_id: r5-r3-safety-recheck-20261111-0800
  model_label: Codex
reviewed_roles:
- R3
author_sessions:
- r3-safety-01
independence_basis: На основании опубликованного акта reviewer не автор проверяемой
  редакции; ID не удостоверяет организационную независимость или профессиональную
  компетентность. Запись зарегистрирована R1 по опубликованному акту.
reviewed_commit: 2d4791f83ac1f67b2b35c2971b0380301803f344
parameter_refs: []
artifacts:
- path: verification/r3_press_safety/input_audit.md
  sha256: 34e28facd0a6f8bf744647f3eafe6422455d35498fa84fe7a6fc2157d144b003
- path: verification/r3_press_safety/preliminary_hazards.md
  sha256: 4092d921f50492f91523fe742725bcb360e163bdd7f56c9ad29d5e6b41d14a85
- path: verification/r3_press_safety/traceability.md
  sha256: 501b152e0deb7a6d43fee034e45e163f50c30e066da55c5ba40b6d43191c5ed1
- path: verification/r3_press_safety/normative_scope_questions.md
  sha256: 58adf3ea4b7afe6b00421215aa23405662d89b5bbbdf954ca9c4b60ee8d89e16
scope: Документальная проверка входного акта, карты опасностей, REQ/VAL и нормативных
  вопросов; физическая безопасность и применимость норм вне области.
checks:
- id: CHK-SAFETY-REGISTRATION
  method: inspection
  expected: Проверить ревизии, влияние изменений и обработку B01/W01–W05
  observed: Акт R5 сообщает B01 и W01–W05 CLOSED документально
  reasoning: Это не оценка полноты инженерного риска, защит и нормативной применимости.
  result: PASS
findings: []
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: Только документальная подготовка и независимая проверка,
  без утверждения защит или ТЗ.
excluded_claims:
- Исчерпывающий анализ риска и эффективность защит
- Нормативная применимость и прохождение G1
- Реальные измерения и испытания
warning_owner_and_due:
  owner_role: R3
  owner_session: r3-safety-01
  due: До утверждения ТЗ и выбора мер
  restriction: Разработать с профильными специалистами недостающие инженерные данные,
    оценку риска и применимость нормативных источников.
closure_criteria:
- Сохранить UNKNOWN и провести отдельную профильную инженерную и нормативную оценку
traceability_and_revisions: Запись оформлена R1 при интеграции по опубликованному
  акту; created_at_utc — время регистрации, а не исходного запуска review.
reproduction_artifacts:
- verification/r5_r3_safety_recheck/review.md
supersedes: null
```

## Регистрация OUTPUT-review нормативных источников

```yaml
record_type: review
review_id: REV-R5-R3-NORMS-01-001
kind: OUTPUT
task_id: T-r3-norms-01
created_at_utc: '2026-11-11T08:39:47Z'
reviewer:
  role: R5
  session_id: r5-r3-norms-output-20261111-0823
  model_label: Codex
reviewed_roles:
- R3
author_sessions:
- r3-safety-01
independence_basis: По опубликованному акту reviewer не указан среди авторов R3; Git
  и session ID не удостоверяют личность, организационную независимость или юридическую
  квалификацию. Зарегистрировано R1 по акту.
reviewed_commit: 77e78ee9e910132116e9f1e1e21bc4a3fa8b6e16
parameter_refs: []
artifacts:
- path: verification/r3_normative_scope/input_audit.md
  sha256: 5fce6cef4078750d7d3e3325165701f487e4d4aecef0a325a89f3158443b5e58
- path: verification/r3_normative_scope/source_registry.md
  sha256: 5a759215335f2a553ff5b36188424a6bbdd6af71d6395525b156091f4091c398
scope: Документальная проверка доступности и заявленных фрагментов, не нормативное
  заключение.
checks:
- id: CHK-NORMS-ACCESS
  method: inspection
  expected: Независимо прочитать источники
  observed: Официальные сайты вернули CONNECT 403
  reasoning: Недоступность текстов не доказывает ошибку автора.
  result: NOT_RUN
findings: []
verdict: REJECT_WITH_BLOCKER
validity: CURRENT
blocker_ids:
- R5-NORMS-B01
allowed_downstream_scope: Только подготовка вопросов и документальной карты источников.
excluded_claims:
- Актуальность, обязательность и применимость норм
- Юридическое заключение, безопасность и G1
warning_owner_and_due: null
closure_criteria:
- Проверить официальные источники и заявленные фрагменты
traceability_and_revisions: Запись R1 по опубликованному акту; created_at_utc — время
  регистрации, не исходного запуска.
reproduction_artifacts:
- verification/r5_r3_normative_output/review.md
supersedes: null
```

## Регистрация RECHECK нормативных источников

```yaml
record_type: review
review_id: REV-R5-R3-NORMS-RECHECK-01-001
kind: RECHECK
task_id: T-r3-norms-01
created_at_utc: '2026-11-11T08:39:47Z'
reviewer:
  role: R5
  session_id: r5-r3-norms-recheck-20261111-0835
  model_label: Codex
reviewed_roles:
- R3
author_sessions:
- r3-safety-01
independence_basis: По опубликованному акту reviewer не указан среди авторов R3; Git
  и session ID не удостоверяют личность, организационную независимость или юридическую
  квалификацию. Зарегистрировано R1 по акту.
reviewed_commit: 77e78ee9e910132116e9f1e1e21bc4a3fa8b6e16
parameter_refs: []
artifacts:
- path: verification/r3_normative_scope/input_audit.md
  sha256: 5fce6cef4078750d7d3e3325165701f487e4d4aecef0a325a89f3158443b5e58
- path: verification/r3_normative_scope/source_registry.md
  sha256: 5a759215335f2a553ff5b36188424a6bbdd6af71d6395525b156091f4091c398
scope: Документальная проверка доступности и заявленных фрагментов, не нормативное
  заключение.
checks:
- id: CHK-NORMS-ACCESS
  method: inspection
  expected: Сверить указанные фрагменты и хэши
  observed: По акту R5 фрагменты N01–N05 и карточка ISO доступны и сверены
  reasoning: Полная редакция, применимость и нормативная обязательность остаются NOT_RUN.
  result: PASS
findings: []
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: Только подготовка вопросов и документальной карты источников.
excluded_claims:
- Актуальность, обязательность и применимость норм
- Юридическое заключение, безопасность и G1
warning_owner_and_due:
  owner_role: R3
  owner_session: r3-safety-01
  due: До принятия нормативных требований
  restriction: Проверить полные актуальные тексты, изменения и применимость с компетентными
    специалистами.
closure_criteria:
- Отдельно подтвердить действующие редакции и применимость с компетентными специалистами
traceability_and_revisions: Запись R1 по опубликованному акту; created_at_utc — время
  регистрации, не исходного запуска.
reproduction_artifacts:
- verification/r5_r3_normative_recheck/review.md
supersedes: REV-R5-R3-NORMS-01-001
```

## Независимая проверка карты инженерных входов

```yaml
record_type: review
review_id: REV-R3-ENGINEERING-INPUT-01-001
kind: OUTPUT
task_id: T-INIT
created_at_utc: '2026-11-11T10:48:00Z'
reviewer:
  role: R3
  session_id: r3-safety-01
  model_label: Codex
reviewed_roles:
- R1
author_sessions:
- codex-01
independence_basis: По проектным записям reviewer не автор проверяемого документа; организационная независимость и профильная квалификация этим не удостоверяются.
reviewed_commit: 53a864de6fd9836f90ba10a04bc44b4edf5ecc22
parameter_refs: []
artifacts:
- path: verification/engineering_input_map.md
  sha256: 5c1d66b4720269fb0a7d9e8a79c23b3dab75d9eb7924ecd1e2eedca8ed6093bb
scope: Документальная проверка условных формул, знаков, границ энергии и пробелов данных; реальные свойства, безопасность и оборудование не проверялись.
checks:
- id: CHK-R3-INPUT-FORMULAS
  method: inspection
  expected: Согласовать силу, расходы, направления, мощность и работу на оговорённых границах.
  observed: Зависимости согласуются в идеальной модели при уточнённых внешней базе давления и знаках; реальный баланс требует потерь и накопления.
  reasoning: Проверены проекции сил, изменения объёма, размерности и баланс мощности без чисел изделия.
  result: PASS
- id: CHK-R3-INPUT-BOUNDARIES
  method: inspection
  expected: Определить границы применимости и отсутствующие данные для привода и A/B.
  observed: Уточнения и ограничения R3-INPUT-W01–W04 перечислены в отдельном акте; данные и критерии UNKNOWN.
  reasoning: Документ предназначен для постановки вопросов, а не выбора привода или подтверждения физики.
  result: PASS
findings: []
verdict: WARNING
validity: STALE
blocker_ids: []
allowed_downstream_scope: Ограниченная документальная постановка будущих измерений при соблюдении уточнений акта.
excluded_claims:
- Выбор оборудования, архитектуры и параметров
- Безопасность, физическая применимость и приёмка G1
warning_owner_and_due:
  owner_role: R1
  owner_session: codex-01
  due: До применения зависимостей для подбора привода или принятия решений
  restriction: Уточнить знаки, базу давлений, границы и методы независимой проверки с R2/R3/R5.
closure_criteria:
- Проверить границы и знаки будущей методики, задать измерения и независимую оценку неопределённости
traceability_and_revisions: Проверен точный commit; независимый пересчёт выполнен аналитически без данных REV.
reproduction_artifacts:
- verification/r3_engineering_input_review/review.md
supersedes: null
```

## Ограниченный RECHECK карты инженерных входов R3

```yaml
record_type: review
review_id: REV-R3-ENGINEERING-INPUT-RECHECK-01-001
kind: RECHECK
task_id: T-INIT
created_at_utc: '2026-11-11T10:52:00Z'
reviewer:
  role: R3
  session_id: r3-safety-01
  model_label: Codex
reviewed_roles:
- R1
author_sessions:
- codex-01
independence_basis: Reviewer не указан автором карты, но является автором исходного акта; организационная независимость и квалификация не установлены.
reviewed_commit: 0aeedf369f4a5e9953bbbe26334552271cc73484
parameter_refs: []
artifacts:
- path: verification/engineering_input_map.md
  sha256: 48615e35aab2bb1d89f9aa66e27766d358f1052f4dd67d999a49037d544aed98
scope: Ограниченная документальная проверка исправлений R3-INPUT-W01–04, без проверки физической схемы и испытаний.
checks:
- id: CHK-R3-INPUT-RECHECK
  method: inspection
  expected: Проверить обработку знаков, границ мощности, измерений и сопоставления A/B.
  observed: W01–W04 обработаны документально; статусы и оставшиеся ограничения указаны в акте.
  reasoning: Сверены diff и аналитические зависимости на явно определённых границах; данных о реальной машине нет.
  result: PASS
findings: []
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: Подготовка будущей методики в условной документальной области.
excluded_claims:
- Выбор привода и численных параметров
- Подтверждение физической модели, безопасности или закрытия G1
warning_owner_and_due:
  owner_role: R1
  owner_session: codex-01
  due: До использования зависимостей для выбора привода
  restriction: Определить фактические входы и согласованные измерительные границы и провести независимую профильную проверку.
closure_criteria:
- Подготовить и независимо проверить пригодную методику и данные в установленной области
traceability_and_revisions: Сравнены исправленный и исходный commits; статусы закрыты только документально.
reproduction_artifacts:
- verification/r3_engineering_input_recheck/review.md
supersedes: REV-R3-ENGINEERING-INPUT-01-001
```

## Документальный RECHECK программы формования R2

```yaml
record_type: review
review_id: REV-R2-COMPACTION-RECHECK-01-001
kind: RECHECK
task_id: T-r2-compaction-review-01
created_at_utc: '2026-11-11T11:16:00Z'
reviewer:
  role: R2
  session_id: e98b8ef8-7302-453a-ac8d-1edbb7d8860c
  model_label: Codex
reviewed_roles:
- R1
author_sessions:
- codex-01
independence_basis: По доступным проектным записям данная сессия не автор проверенной программы; организационная независимость и квалификация не удостоверены.
reviewed_commit: 03290fe5e5392697303dd5eac552996e61df01ff
parameter_refs: []
artifacts:
- path: verification/compaction_measurement_program_draft.md
  sha256: 8d8228e34272a56aaa2e41b3f9c27eb98332097bac25b9781189529aa36a12aa
scope: Документальная проверка обработки предварительных замечаний W01–W05, без приёмки методики, безопасности и физических свойств.
checks:
- id: CHK-R2-COMP-W01-W05
  method: Сопоставление пяти замечаний с исправленной редакцией и diff.
  expected: Документально адресовать область вывода, величины, связи, потери и сопоставимость.
  observed: Все пять замечаний обработаны в ограниченной документальной области; конкретные условия и методы остаются UNKNOWN.
  reasoning: Основания и ограничения для каждого замечания приведены в отдельном акте.
  result: PASS
findings: []
verdict: WARNING
validity: STALE
blocker_ids: []
allowed_downstream_scope: Подготовка проекта методики и дальнейшая профильная проверка.
excluded_claims:
- Представительность реальных партий и фактический материальный баланс
- Утверждение методов, безопасности, архитектуры и закрытие G1
warning_owner_and_due:
  owner_role: R1
  owner_session: codex-01
  due: До согласования и применения будущей методики
  restriction: Установить отсутствующие данные, методы и условия, получить оценки R3 и R5.
closure_criteria:
- Согласовать пригодную методику и провести необходимые независимые профильные проверки.
traceability_and_revisions: Проверен точный commit вне main; предварительный акт e939c146f51d4a40daba75b1bb21bd694e12bccc является историей и не был принятым review.
reproduction_artifacts:
- verification/r2_compaction_program_recheck/review.md
supersedes: null
```

## Регистрация независимого OUTPUT-review постановки R3 W03/W04

```yaml
record_type: review
review_id: REV-R5-R3-COMPACTION-OBS-01-001
kind: OUTPUT
task_id: T-r3-compaction-measure-01
created_at_utc: '2026-11-11T13:01:00Z'
reviewer:
  role: R5
  session_id: 14e665ff-a763-4bc9-95cf-c4c3a999177e
  model_label: Codex
reviewed_roles:
- R3
author_sessions:
- r3-safety-01
independence_basis: По акту reviewer не указан автором постановки; организационная независимость и профильная квалификация не удостоверяются.
reviewed_commit: 026bd890d7957526bfbee5ffb2745e9fe7b0c43e
parameter_refs: []
artifacts:
- path: verification/r3_compaction_observability/specification.md
  sha256: de28dabee909e9fa1ea33f680f6e345f384ab702da5ec2b754f8eceaaf528805
- path: verification/r3_compaction_observability/input_audit.md
  sha256: c8cda946c2b7d233898f76deaee862ebed697d22cca101ca36f5271a0fde1340
scope: Документальная проверка измерительной модели и наблюдаемости по R5-COMP-W03/W04; пригодность реальной установки и безопасность не проверялись.
checks:
- id: CHK-R5-R3-OBS-DOCUMENT
  method: inspection
  expected: Проверить обработку W03/W04 и точность входов.
  observed: По акту R5 документально обработаны границы, неопределённость, синхронизация и наблюдаемость; реальные каналы и критерии UNKNOWN.
  reasoning: Постановка является черновиком, перечисление полей не доказывает применимости методики.
  result: PASS
findings: []
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: Дальнейшая документальная разработка и независимая профильная проверка.
excluded_claims:
- Применимая методика, выбор средств, безопасность и подтверждение состояний
- Закрытие R5-COMP-W03/W04, B01–B03 или G1
warning_owner_and_due:
  owner_role: R3
  owner_session: r3-safety-01
  due: До согласования и применения будущей методики
  restriction: Установить фактические данные, модель и бюджет измерений, пригодность каналов и независимые основания наблюдаемости.
closure_criteria:
- Разработать и независимо проверить применимую методику в установленной области
traceability_and_revisions: Регистрация R3 по независимому акту R5 в commit 644d74178fefb4cb40150276532b08c6a8381b98; не самостоятельный R5 review.
reproduction_artifacts:
- verification/r5_r3_compaction_observability_review/review.md
supersedes: null
```

## Независимый OUTPUT-review постановки компоновки всего пресса

```yaml
record_type: review
review_id: REV-R5-LAYOUT-01-001
kind: OUTPUT
task_id: T-r4-layout-01
created_at_utc: '2026-11-11T17:57:49Z'
reviewer:
  role: R5
  session_id: 01a1c552-4e0c-75cf-86ba-2922ccdb30f3
  model_label: Codex
reviewed_roles:
- R4
author_sessions:
- r4-linked-20261111
independence_basis: Текущая сессия не автор проверенного документа, но ранее как R1 участвовала в разработке его проектных входов; организационная независимость и квалификация не удостоверены.
reviewed_commit: 32481da99f436d260e9af6f0bcc9b0979b952cff
parameter_refs: []
artifacts:
- path: cad/layout/whole_press_layout_brief.md
  sha256: 30175b4865bfe977436f2dbe888b466bfc090d14af1d632c39b3aede87d8a0c4
scope: Документальное рассмотрение полноты постановки и условий исследовательской условной компоновки без CAD, физических расчётов или приёмки REV.
checks:
- id: CHK-LAYOUT-DOC-01
  method: Сопоставление интерфейсов, фаз, требуемых входов и условий проверки с эскизами, операторскими данными и проверенными границами synthetic.
  expected: Охватить весь пресс и варианты A/B, отметить UNKNOWN и различить условную геометрию и физические доказательства.
  observed: Постановка охватывает заявленные области; предварительные ориентиры оператора и учёт claim требуют уточнения; данные и реальная проверка отсутствуют.
  reasoning: Ограничения, основания и три замечания указаны в акте.
  result: PASS
findings: []
verdict: WARNING
validity: STALE
blocker_ids: []
allowed_downstream_scope: Отдельная исследовательская компоновка A/B с явно условными ASSUMED-входами после постановки задачи и claim.
excluded_claims:
- Реальные геометрия, нагрузки, удержание, разгрузка, выдача, безопасность и изготовимость
- Утверждение ТЗ, архитектуры и прохождение G1 G2 G3
warning_owner_and_due:
  owner_role: R4
  owner_session: r4-linked-20261111
  due: До использования интерфейсов как проектной базы и приёмки компоновки
  restriction: Уточнить предварительные границы оператора, учёт claim и воспроизводимость условной модели.
closure_criteria:
- Для W01 уточнить и независимо сверить ориентиры OP-REV-07 и OP-REV-09…11 с сохранением UNKNOWN.
- Для W02 последовательно сверить и исправить поля принятого claim.
- Для W03 до новой модели определить conditional inputs, формат, покрытие и независимую проверку.
traceability_and_revisions: Акт проверяет точный C; эстафета H содержит C; 19 входов manifest сверены с Git blobs и SHA-256 базы.
reproduction_artifacts:
- verification/r5_whole_press_layout_review/review.md
supersedes: null
```

## REV-R4-FRAME-MOUNT-OUTPUT-01 — запрос независимой проверки

- Автор R4 r4-linked-20261111, T-r4-layout-build-01, 2026-11-11T22:52:59.303177Z. Входной акт R5 04efe5703e339112b7d007665b9f3672f0572d37 (закрытие B01/B02 в его ограниченной области); он не принимает новую геометрию.
- Результат: cad/frame_mount/README.md, review_request.md; cad/build/frame_mount/assessment.md, geometry_evidence.json и publication_manifest.json. Точный неизменяемый code/results C — в следующем H/NEXT_MODEL/капсуле. Проверять C отдельно от H.
- R4 self-check PASS в указанной ограниченной области; независимый reviewer/result NOT_ASSIGNED/NOT_RUN. Все прежние code/review/probe и CAD/evidence сохранены, 23 модуля неизменны. Остальные 20 native penetration пар и unknown interfaces OPEN, whole press READY INDETERMINATE. Задача IN_REVIEW, не принятие. G1 OPEN.

Неизменяемый объект запроса REV-R4-FRAME-MOUNT-OUTPUT-01: C `5198e0184b35978701ed1ce762d9e4fcd44997b3`, REMOTE. Author r4-linked-20261111, независимый reviewer/result NOT_ASSIGNED/NOT_RUN; точный запрос и критерии cad/frame_mount/review_request.md. Следующий H только эстафета, не новая модель и не приёмка.

## REV-R4-FRAME-FIX-OUTPUT-01 — запрос RECHECK R5-FRAME-NEW-B01

- Автор R4 r4-linked-20261111, T-r4-layout-build-01; входной независимый акт 0b4788dd36f811e4acb202b96d6a76a6a06b63ad. Новый reviewer/result NOT_ASSIGNED/NOT_RUN; B01 OPEN, не закрыт автором.
- Readonly verifier/явная генерация, 95 tests и 18 release-regression случаев PASS. 23 frozen модуля и 35 геометрических/evidence хэшей unchanged, 18 устранённых и 20 оставшихся native-пар сохранены. Полные факты verification/r4_frame_fix/final_checks.json и regressions/, команды README, запрос recheck_request.md.
- Точный C сообщается следующей документальной эстафетой. Весь пресс READY INDETERMINATE, физические испытания NOT_RUN, архитектура/ТЗ не утверждены, G1 OPEN.

Неизменяемый объект REV-R4-FRAME-FIX-OUTPUT-01: C `a5d5bad6dd8928045512bca16836fd1d2544b7ca`, REMOTE. Новый независимый reviewer/result NOT_ASSIGNED/NOT_RUN, R5-FRAME-NEW-B01 OPEN. Следующий H только эстафета.

## REV-R4-FEED-POWER-OUTPUT-01 — запрос независимого review

- Автор R4 r4-linked-20261111; новый reviewer/result NOT_ASSIGNED/NOT_RUN. Входной RECHECK c2e96a58d7efd64ea3364b2bcbfb3f0642bbc430 закрывает прежний B01 в его области. Новая геометрия/FP wrappers не принимаются автоматически.
- 14 static native pairs removed, 6 legacy doser-UP BLOCKED retained; proposed actual service INDETERMINATE (UNKNOWN actuator/rigging). Все 34 checked модуля unchanged, 102 tests/18 package regression cases PASS. Сводка verification/r4_feed_power/final_checks.json, запрос review_request.md; точный C следующей эстафетой. Whole press READY INDETERMINATE, физические испытания NOT_RUN, G1 OPEN.

Неизменяемый объект REV-R4-FEED-POWER-OUTPUT-01: C `8fbbef00023e146e32cb6ff290a0c19408ca13b5`, REMOTE. H только эстафета, reviewer/result NOT_ASSIGNED/NOT_RUN. Область 14 static fixes, 6 legacy BLOCKED, proposed actual service INDETERMINATE. G1 OPEN.

## REV-R4-FP-SEMANTIC-FIX-OUTPUT-01 — запрос RECHECK

- Автор r4-linked-20261111, входной R5 акт 2592b470940cea886e033a999c889c15a92889f6. Новый reviewer/result NOT_ASSIGNED/NOT_RUN; R5-FP-NEW-B01 OPEN до независимого решения.
- Пять исходных false PASS воспроизведены; исправленные CLI отклоняют их со fresh BLOCKED/INDETERMINATE, связаны calculation→aggregation→report→verifier, негативное ожидание отделено от path success. 110 tests и 25 цепочечных команд PASS, compound/unknown покрыты, readonly сохранён.
- 34 frozen модуля и исходная геометрия unchanged, L physical feasibility INDETERMINATE, 6 legacy BLOCKED/14 static fixes сохранены. Полные результаты verification/r4_fp_fix/, точный C следующим H, запрос recheck_request.md. G1 OPEN, физические испытания NOT_RUN.

Неизменяемый объект REV-R4-FP-SEMANTIC-FIX-OUTPUT-01: C `7d1bd1c92c7cedc4282e3a903463e88205b86fa3`, REMOTE. H только эстафета. Reviewer/result NOT_ASSIGNED/NOT_RUN, R5-FP-NEW-B01 OPEN до независимого RECHECK.

## REV-R5-R3-PARAMETRIC-OUTPUT-01-001 — независимый OUTPUT-review

Полный акт и воспроизводимые доказательства: [review.md](../verification/r5_r3_parametric_review/review.md).
Прежние акты/ограничения и G1 OPEN сохранены; численные входы/выходы автора не изменены.

```yaml
record_type: review
review_id: REV-R5-R3-PARAMETRIC-OUTPUT-01-001
kind: OUTPUT
task_id: T-r3-parametric-sizing-01
created_at_utc: '2026-11-12T09:22:23Z'
reviewer:
  role: R5
  session_id: 6af41aff-4210-8191-94a3-5d9c4bd75076
  model_label: Codex
reviewed_roles: [R3]
author_sessions: [r3-sizing-20261112]
independence_basis: Reviewer не автор расчёта; отдельный Decimal-пересчёт и новые граничные случаи, организационная независимость не удостоверена.
reviewed_commit: 8a1ad4199fea09d1157972d7aa28eaad1e8e0337
parameter_refs: []
artifacts:
- path: evidence/snapshots/2487e579b9d0948af41da836350f390472cb2bf1c4ecfa7211e75da9586babe1.yaml
  sha256: 2487e579b9d0948af41da836350f390472cb2bf1c4ecfa7211e75da9586babe1
- path: evidence/snapshots/2a6ac4279a6228120c9c486c21ea59ddf3a9ed37f306305c1a1a39f3a8c3dd2c.yaml
  sha256: 2a6ac4279a6228120c9c486c21ea59ddf3a9ed37f306305c1a1a39f3a8c3dd2c
- path: evidence/snapshots/3d74e2f1f580a64c39ecfd8e1c675c113a47dc4f6b3a0b1b5b64daa45aff0e45.yaml
  sha256: 3d74e2f1f580a64c39ecfd8e1c675c113a47dc4f6b3a0b1b5b64daa45aff0e45
- path: evidence/snapshots/729b99da8dcd9e1646731efa0ea62d18c52ea32589403057f8a23660e3f46ac3.yaml
  sha256: 729b99da8dcd9e1646731efa0ea62d18c52ea32589403057f8a23660e3f46ac3
- path: evidence/snapshots/963e4aaeee8a936c0f7a029182e1c4ecfd27e75777e22ceb61c995e5c03e18bd.yaml
  sha256: 963e4aaeee8a936c0f7a029182e1c4ecfd27e75777e22ceb61c995e5c03e18bd
- path: evidence/snapshots/a1c61c20931540d94505352af7b9eafafdcc4db0ddf01d7ff0862bad7a54619d.yaml
  sha256: a1c61c20931540d94505352af7b9eafafdcc4db0ddf01d7ff0862bad7a54619d
- path: evidence/snapshots/b9981ba8923eae1d11150a7fa5e6760adc21c80822fb6a49e9b6f1058aeebbb0.yaml
  sha256: b9981ba8923eae1d11150a7fa5e6760adc21c80822fb6a49e9b6f1058aeebbb0
- path: evidence/snapshots/bbdcb13634ae6b114b24683006f28756c8a32e9b39b240d561e179b6e65c1a7c.yaml
  sha256: bbdcb13634ae6b114b24683006f28756c8a32e9b39b240d561e179b6e65c1a7c
- path: params/registry.yaml
  sha256: 8f68bc7a49148c622c1063e0118b766f5d0907605d1489f2adaa6bef00e93ce8
- path: scripts/repo_support.py
  sha256: ca9c504e798a287a9fb1870675dc342c5b69098944e38e4f527679a5d250173c
- path: scripts/rev_parametric.py
  sha256: df8aa4678035f7c90b56cbe1d8a4cf450f4ef552d95b21fd8cf423de96819e59
- path: tests/test_rev_parametric.py
  sha256: beeeecf703206bf22b5ed5dda6c500e4b10a34f09ebb5649505cc88ee123792b
- path: verification/r3_parametric_sizing/README.md
  sha256: 0685ea2da4f6d9a7bf543de6c9d90d4f08ada55725accc15a78c89de0b898c6b
- path: verification/r3_parametric_sizing/cases.json
  sha256: 0e34159de8b1e7f98d7d1d9c6fc645d55b721545a9e69a3f7775d24c476a2a7d
- path: verification/r3_parametric_sizing/claim.md
  sha256: fae3223d79de397e0c6ebf472910dcb906eb6524253ee747dc0a96210ba77710
- path: verification/r3_parametric_sizing/input_audit.md
  sha256: 79996d1c04dc668a664ee75add3f77cb3ddfbaeefaa4521913a2303cd3a07cac
- path: verification/r3_parametric_sizing/inputs/r2_design_basis.txt
  sha256: fcf3627b5512c66860769222784a9198dfa5ad1590089405cf0a7563e4c2c87d
- path: verification/r3_parametric_sizing/inputs/r2_input_audit.txt
  sha256: 2c4f3079a998ed0526dda91c48a6b55e1b247253103c355d82dbb66902895928
- path: verification/r3_parametric_sizing/inputs/r2_registry.yaml
  sha256: b2920a4e315f748ea2d19172c6d64a4a89c0c46a3e51deccc39d4419c61cf3bb
- path: verification/r3_parametric_sizing/inputs/r2_script.txt
  sha256: 2e902658e17ffa25bc0963cc9ffa073f503d88df62b535b33f07b245fcdb22c3
- path: verification/r3_parametric_sizing/inputs/r5_review.txt
  sha256: 60f92521591b5e1d8cb4b489452a6bada82e16da87392ed363c2619d64fc5f98
- path: verification/r3_parametric_sizing/model.md
  sha256: 028d36898cd85cc49f692d489de7410d6725cea3ad0a65d3f268291fb4b984b5
- path: verification/r3_parametric_sizing/phases.md
  sha256: aa3ebea34a2be06bc29aca1a9acf3f078d3af137c10cb9e74ae1d83256f4b385
- path: verification/r3_parametric_sizing/preflight.json
  sha256: d569521316f2c54c68a5d903b6349a8375157523cfda3c144d28f12b56987d7f
- path: verification/r3_parametric_sizing/r4_inputs.md
  sha256: 98b709d9657ec58d3fb9dcaba01e54a651bf25ca35be4a2c8566342ddcb1394c
- path: verification/r3_parametric_sizing/registry_check.log
  sha256: f18008b12f04ec977f502d918a3a8b404f3c7e141b6d5becc8515bbc405b2cda
- path: verification/r3_parametric_sizing/repeatability.json
  sha256: 21e9ff73de1791407228da28da2a9a0f345e5907f8e9d12501bb1734a9ddc5ea
- path: verification/r3_parametric_sizing/report.md
  sha256: 126b90f2a8e69f8194e35d9307ca864da2c10b13fc7002b1e5732301a6d443d5
- path: verification/r3_parametric_sizing/results/BACK_HIGH_A.json
  sha256: ceda3d0dd098792a58a0d9467b5a8788fd4786ee10fd2f1351d385f4a45fd01f
- path: verification/r3_parametric_sizing/results/BASE_A.json
  sha256: f2015d9ff6e068c3858198208c151c1b9aeb3342ea8f99b54ce7e598b188f69d
- path: verification/r3_parametric_sizing/results/BASE_B.json
  sha256: 81073745b7cf218f63b3a036224d1095955dd7045d0afc6ce684513278c2195a
- path: verification/r3_parametric_sizing/results/EJECT_DOUBLE_B.json
  sha256: aa2a75bbef17cd1814beabf29121dc3b542b1e89f10ca3834f6062fa79e952e4
- path: verification/r3_parametric_sizing/results/LOAD_DOUBLE_A.json
  sha256: b997fbb579addac81fd6a00bd840736f4fe4b38d5a4c283b6d75a8a50c102e18
- path: verification/r3_parametric_sizing/results/LOAD_HALF_A.json
  sha256: 0a56cc32a8e84151abf0c4eda36bed4c0e793fcecd6a546afb70998abd7d7063
- path: verification/r3_parametric_sizing/results/RHO_HALF_A.json
  sha256: 02d77b03648fe924bc82b499001730a78a31b5a4f919c30fa7da47ba579d0a84
- path: verification/r3_parametric_sizing/results/TIME_HALF_A.json
  sha256: c14e1b3a4566681e1b981fea2f00bc1d984c14702d335451430f6b425a0953a6
- path: verification/r3_parametric_sizing/scenarios.csv
  sha256: 65c37e4b7fa8d7ac307a15e4fee30567f139a02e47782d2ec7e00ab8a44848d8
- path: verification/r3_parametric_sizing/software_tests.log
  sha256: 4527afc272fe578ad20364a85d5c2c02cfee4136b93f68e71d75e9cb95b8b157
- path: verification/r3_parametric_sizing/validation.json
  sha256: 70ca81058b4b06ba0df676ed2e94e0fe71c9ecc86acebe0d97f69a0aa8f7ba45
scope: Арифметика восьми условных сценариев, формулы и границы; передача R4 только для отдельного условного исследования.
checks:
- id: CHK-SIZING-ARITHMETIC
  method: Независимые Decimal-балансы, интеграл нагрузки, неравенства обеих полостей, чувствительность и новые пробы.
  expected: Совпадение сохранённых чисел и явная несовместимость назначенных режимов с условным пределом мощности.
  observed: 696 чисел и CSV совпали, 80 табличных и 24 фазовых округления верны; 12 граничных и 10 недопустимых наборов проверены.
  reasoning: Ожидания не получены вызовом авторского solve; физические свойства не проверены.
  result: PASS
findings:
- id: R5-SIZING-W01
  status: OPEN
  description: При утечке выше бюджета конечный lower bound времени не является допустимой циклограммой; до расширения API нужен отдельный машинный статус.
- id: R5-SIZING-W02
  status: OPEN
  description: До реального подбора или циклограммы нужны согласованный электрический бюджет, потребители, физические входы и новый режим.
verdict: WARNING
validity: STALE
blocker_ids: []
allowed_downstream_scope: Передать R4 ID/revision/snapshot вместе с условными параметрами и ограничениями для исследовательской модели.
excluded_claims:
- Подтверждённые оборудование, мощности, цикл, силовой контур и работоспособность A/B
- Разрешение открытия упора B без подтверждённой разгрузки
- Архитектура, ТЗ, безопасность, нормативная применимость и прохождение G1
warning_owner_and_due:
  owner_role: R3
  owner_session: r3-sizing-20261112
  due: До соответствующего расширения использования, в пределах принятого lease или нового назначения
  restriction: Восемь сценариев с нулевой утечкой приняты только как условная арифметика, не подбор.
reproduction_artifacts:
- verification/r5_r3_parametric_review/review.md
- verification/r5_r3_parametric_review/reproduction.json
- verification/r5_r3_parametric_review/independent_results.json
- verification/r5_r3_parametric_review/power_analysis.json
supersedes: null
```



Административная актуализация индекса при подготовке PR #39: STALE относится к привязке исторического акта к полному файлу registry исходного C (после добавления нового слоя его полный SHA иной), не к пересмотру принятой арифметики восьми исходных сценариев. Исходный verdict/checks/artifacts/reviewed_commit не изменены. Полная исходная запись с CURRENT сохранена в commit d92cebd5a539d6845fe114515154e79c639bcb7e и побайтной копии verification/pr39_integration/original_review_index.txt. Текущий RECHECK c115f75 остаётся CURRENT в своей ограниченной области; исторические OPEN не переоткрывают W01/W02.

## REV-R5-R3-POWER-RECHECK-01-001 — ограниченный RECHECK W01/W02

Полный акт: [review.md](../verification/r5_r3_power_recheck/review.md). Предыдущий акт d92cebd5a539d6845fe114515154e79c639bcb7e сохранён; настоящее решение не заменяет его остальные выводы.

```yaml
record_type: review
review_id: REV-R5-R3-POWER-RECHECK-01-001
kind: RECHECK
task_id: T-r3-parametric-sizing-01
created_at_utc: '2026-11-12T11:51:38Z'
reviewer:
  role: R5
  session_id: 6af41aff-4210-8191-94a3-5d9c4bd75076
  model_label: Codex
reviewed_roles:
- R3
author_sessions:
- r3-sizing-20261112
independence_basis: Reviewer не автор расчёта; независимые Decimal-балансы и новые граничные/составные случаи. Организационная
  независимость не удостоверена.
reviewed_commit: c115f75fd900525d9ddc89d85e097ac5a0f00bc1
parameter_refs: []
artifacts:
- path: evidence/snapshots/2487e579b9d0948af41da836350f390472cb2bf1c4ecfa7211e75da9586babe1.yaml
  sha256: 2487e579b9d0948af41da836350f390472cb2bf1c4ecfa7211e75da9586babe1
- path: evidence/snapshots/2a6ac4279a6228120c9c486c21ea59ddf3a9ed37f306305c1a1a39f3a8c3dd2c.yaml
  sha256: 2a6ac4279a6228120c9c486c21ea59ddf3a9ed37f306305c1a1a39f3a8c3dd2c
- path: evidence/snapshots/31f4bba602b0dc22938f8d84c9a6724a6d10e61c1ea8e10a06a13e54738d872e.yaml
  sha256: 31f4bba602b0dc22938f8d84c9a6724a6d10e61c1ea8e10a06a13e54738d872e
- path: evidence/snapshots/3d74e2f1f580a64c39ecfd8e1c675c113a47dc4f6b3a0b1b5b64daa45aff0e45.yaml
  sha256: 3d74e2f1f580a64c39ecfd8e1c675c113a47dc4f6b3a0b1b5b64daa45aff0e45
- path: evidence/snapshots/46573a6c3055727f65fa5cb5caf383ed213eb130ff1690e70077ff166cbef99c.yaml
  sha256: 46573a6c3055727f65fa5cb5caf383ed213eb130ff1690e70077ff166cbef99c
- path: evidence/snapshots/523f416bd07d436d8100b4aa3cf89ade21d3cd7e80a74e6ee9996152a902dc18.yaml
  sha256: 523f416bd07d436d8100b4aa3cf89ade21d3cd7e80a74e6ee9996152a902dc18
- path: evidence/snapshots/729b99da8dcd9e1646731efa0ea62d18c52ea32589403057f8a23660e3f46ac3.yaml
  sha256: 729b99da8dcd9e1646731efa0ea62d18c52ea32589403057f8a23660e3f46ac3
- path: evidence/snapshots/7798ef1191827362184e796d388e959abe6fc6f6681437180cf10bfb2eb1a8e5.yaml
  sha256: 7798ef1191827362184e796d388e959abe6fc6f6681437180cf10bfb2eb1a8e5
- path: evidence/snapshots/963e4aaeee8a936c0f7a029182e1c4ecfd27e75777e22ceb61c995e5c03e18bd.yaml
  sha256: 963e4aaeee8a936c0f7a029182e1c4ecfd27e75777e22ceb61c995e5c03e18bd
- path: evidence/snapshots/a1c61c20931540d94505352af7b9eafafdcc4db0ddf01d7ff0862bad7a54619d.yaml
  sha256: a1c61c20931540d94505352af7b9eafafdcc4db0ddf01d7ff0862bad7a54619d
- path: evidence/snapshots/b9981ba8923eae1d11150a7fa5e6760adc21c80822fb6a49e9b6f1058aeebbb0.yaml
  sha256: b9981ba8923eae1d11150a7fa5e6760adc21c80822fb6a49e9b6f1058aeebbb0
- path: evidence/snapshots/bbdcb13634ae6b114b24683006f28756c8a32e9b39b240d561e179b6e65c1a7c.yaml
  sha256: bbdcb13634ae6b114b24683006f28756c8a32e9b39b240d561e179b6e65c1a7c
- path: evidence/snapshots/d9c234f48756a02485dd3d215eff967639b863dd4915f8903048ee0ccbf91fe6.yaml
  sha256: d9c234f48756a02485dd3d215eff967639b863dd4915f8903048ee0ccbf91fe6
- path: evidence/snapshots/e9de37953c914228eebe9a0542eb23dca6d797c57faac18ae4fc77b0b3b03797.yaml
  sha256: e9de37953c914228eebe9a0542eb23dca6d797c57faac18ae4fc77b0b3b03797
- path: evidence/snapshots/f7f8683fa6a5bd7d9da2ccec4de6972e0f6a16a565c5ddcb6eea72709c8ba5c6.yaml
  sha256: f7f8683fa6a5bd7d9da2ccec4de6972e0f6a16a565c5ddcb6eea72709c8ba5c6
- path: evidence/snapshots/fb8390db0e386e6e27965fd65acecf9b8d5abb791c85ffca845eb2c93efcb598.yaml
  sha256: fb8390db0e386e6e27965fd65acecf9b8d5abb791c85ffca845eb2c93efcb598
- path: params/registry.yaml
  sha256: f52f6a52cf84831b714c037521bede8ada33e45d93d8b7251aa30b0b8a0d4d44
- path: scripts/repo_support.py
  sha256: ca9c504e798a287a9fb1870675dc342c5b69098944e38e4f527679a5d250173c
- path: scripts/rev_parametric.py
  sha256: df8aa4678035f7c90b56cbe1d8a4cf450f4ef552d95b21fd8cf423de96819e59
- path: scripts/rev_power_reconcile.py
  sha256: 9ba269eb6f7a773cab1ad6eeb0ed6f6d82a0559c33246dac9a24e644337297dd
- path: tests/test_rev_parametric.py
  sha256: beeeecf703206bf22b5ed5dda6c500e4b10a34f09ebb5649505cc88ee123792b
- path: tests/test_rev_power_reconcile.py
  sha256: eaca300ae27f82288f31b340a489bc49469d0f0be8d0d4bce8f35558af5fa976
- path: verification/r3_parametric_sizing/cases.json
  sha256: 0e34159de8b1e7f98d7d1d9c6fc645d55b721545a9e69a3f7775d24c476a2a7d
- path: verification/r3_parametric_sizing/results/BACK_HIGH_A.json
  sha256: ceda3d0dd098792a58a0d9467b5a8788fd4786ee10fd2f1351d385f4a45fd01f
- path: verification/r3_parametric_sizing/results/BASE_A.json
  sha256: f2015d9ff6e068c3858198208c151c1b9aeb3342ea8f99b54ce7e598b188f69d
- path: verification/r3_parametric_sizing/results/BASE_B.json
  sha256: 81073745b7cf218f63b3a036224d1095955dd7045d0afc6ce684513278c2195a
- path: verification/r3_parametric_sizing/results/EJECT_DOUBLE_B.json
  sha256: aa2a75bbef17cd1814beabf29121dc3b542b1e89f10ca3834f6062fa79e952e4
- path: verification/r3_parametric_sizing/results/LOAD_DOUBLE_A.json
  sha256: b997fbb579addac81fd6a00bd840736f4fe4b38d5a4c283b6d75a8a50c102e18
- path: verification/r3_parametric_sizing/results/LOAD_HALF_A.json
  sha256: 0a56cc32a8e84151abf0c4eda36bed4c0e793fcecd6a546afb70998abd7d7063
- path: verification/r3_parametric_sizing/results/RHO_HALF_A.json
  sha256: 02d77b03648fe924bc82b499001730a78a31b5a4f919c30fa7da47ba579d0a84
- path: verification/r3_parametric_sizing/results/TIME_HALF_A.json
  sha256: c14e1b3a4566681e1b981fea2f00bc1d984c14702d335451430f6b425a0953a6
- path: verification/r3_parametric_sizing/scenarios.csv
  sha256: 65c37e4b7fa8d7ac307a15e4fee30567f139a02e47782d2ec7e00ab8a44848d8
- path: verification/r3_power_reconcile/README.md
  sha256: 0216cb1f150ed401d0a995c7f2d62af2598b799d6c882d2967e06d2a85a5f232
- path: verification/r3_power_reconcile/W01_counterexample.json
  sha256: 2625c95c21565e7186ec1d7f928fc96ba1bcf02f8080b0821ebcaa2923c8c6de
- path: verification/r3_power_reconcile/allocation.json
  sha256: 01656df8ad1b655bb63f42ab5e0b5cf4ed6fb60fb304560273b09380f94e237c
- path: verification/r3_power_reconcile/input_audit.md
  sha256: 044ab59401805df0cbf5aba36f1debac57bd918afa2cca0374829ead11351580
- path: verification/r3_power_reconcile/inputs/identity.json
  sha256: 866b0989d8c557c3ab95c4d95efece31f93beab49c8cfaef8c18d6bc65a7afb2
- path: verification/r3_power_reconcile/inputs/r5_review.txt
  sha256: ba1db9977fa7c94a2e6c51bb9502a087fc3ed18b5217b323ce5eab54fa7f2e41
- path: verification/r3_power_reconcile/model.md
  sha256: 47970c7f7574e877492851d54dd0ea1b43475836790c8c05672ae8746d03da02
- path: verification/r3_power_reconcile/r4_inputs.md
  sha256: ca24980ada1cbd7e39e5880374b5e02c604ef252faa5d31587ab729ac8d5ee1b
- path: verification/r3_power_reconcile/registry_check.log
  sha256: f18008b12f04ec977f502d918a3a8b404f3c7e141b6d5becc8515bbc405b2cda
- path: verification/r3_power_reconcile/repeatability.json
  sha256: 75e767ac066ee6a9cedb3751c51f02936b0ab91752a3fd4bb068a2ce86e5e53a
- path: verification/r3_power_reconcile/report.md
  sha256: b6a58b9981eccc665a2a395af46029c8f2c4f0a97bc0405f8383b71baa5ed9ce
- path: verification/r3_power_reconcile/response_to_r5.md
  sha256: bfaa8811f48a9556282ffef88a5bb4e27e00ea43e6c5905ce9dd428fe8ca2593
- path: verification/r3_power_reconcile/results/BACK_HIGH_A.json
  sha256: 0ed31fb9d42eabf2bcc9ed9bf8e468c6f9f29faa035949eecbd5b38d0ff63a7d
- path: verification/r3_power_reconcile/results/BASE_A.json
  sha256: 0ff30e2bc2a3f8fd00f0a58dc0c3c78d15d3af62b1f3dd8a25b05e4722e624f9
- path: verification/r3_power_reconcile/results/BASE_B.json
  sha256: f655b8630f32cf64e367fb24e2176e626e982515f748bc60df8ffe74f6df5f81
- path: verification/r3_power_reconcile/results/EJECT_DOUBLE_B.json
  sha256: 857bfa30ba4b7e8470fd8cbef419e49b8e6ca6f9d934ebfda4d6acf0be5df3a4
- path: verification/r3_power_reconcile/results/LOAD_DOUBLE_A.json
  sha256: bac6850a5e1b16cb5ab0e9e44f5efb2bb80401901bd04f9849fd8817a6d293e9
- path: verification/r3_power_reconcile/results/LOAD_HALF_A.json
  sha256: 933b1182fc4b7cb3a2d82e4342fb62dd3f460dcabf729d15ab5fd196fe2f9a9a
- path: verification/r3_power_reconcile/results/RHO_HALF_A.json
  sha256: 4c3de769f31f9d54f3d3869aa2afb94045bb4080260ff1ecc7ac385ff1454acb
- path: verification/r3_power_reconcile/results/TIME_HALF_A.json
  sha256: d1893f6d8701ada52907bc5fea45ef9bc13aea7caf6bdfea642ef79adc383caf
- path: verification/r3_power_reconcile/scenarios.csv
  sha256: 80784384c84102449b3d48867929018f0ac0c9e87344ba663cf7aa62b3439479
- path: verification/r3_power_reconcile/software_tests.log
  sha256: 269f4777676f0c4407d4d8b13701b266b392949f9cff004276fda63256398ac7
- path: verification/r3_power_reconcile/validation.json
  sha256: 096d6fbd02201c80097ca23b64d038cc3f217723c1f0c385abc1f586b7cfb6fd
scope: 'Ограниченный RECHECK W01/W02: новый power/timing слой и условная передача R4; не полный цикл и не оборудование.'
checks:
- id: CHK-POWER-INDEPENDENT
  method: Независимый Decimal-пересчёт расхода/скорости из неравенства мощности, времён, энергии и peak/average
    по фазам.
  expected: Согласование двух отдельных условных вариантов, без подмены старого бюджета/времён или UNKNOWN.
  observed: 376 значений и CSV, 348 отображаемых чисел совпали; 26 reconcile + 11 hold + 12 invalid случаев проверены;
    старые 753 определения сохранены.
  reasoning: Ожидания не получены авторскими solve/reconcile; расчёт условен при непроверенных envelopes.
  result: PASS
- id: CHK-HOLD-DEFICIT
  method: Точный прежний W01, дефицит подпитки, неизвестные компоненты, работающий насос при нулевой утечке, нарушения
    allocation.
  expected: Дефицит не исправляется длинными движениями; недопустимый цикл/rate null, UNKNOWN не ноль.
  observed: Новый API даёт BLOCKED/null при известном дефиците или немоделированной ненулевой утечке; actual totals
    null при неизвестных компонентах.
  reasoning: Прежний Tlower сохранён только для истории и исключён из роли планировщика.
  result: PASS
findings:
- id: R5-SIZING-W01
  status: CLOSED_IN_LIMITED_NEW_API_SCOPE
  description: Проверено исправление численного/статусного представления; фактическая схема выдержки не подтверждена.
- id: R5-SIZING-W02
  status: CLOSED_FOR_CONDITIONAL_CALCULATION_HANDOFF_ONLY
  description: Два условных режима и границы передачи документально обработаны; требования к подтверждённому циклу/подбору
    остаются открытыми.
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: 'R4 — отдельная условная размерная модель: fixed-budget с условными caps и новыми временами
  либо fixed-times как ресурсная альтернатива; не смешивать режимы.'
excluded_claims:
- Реальная полная циклограмма, производительность, силовой контур, оборудование и безопасность
- Разрешение открытия B без доказанной разгрузки
- Архитектура, ТЗ и прохождение G1
warning_owner_and_due:
  owner_role: R3
  owner_session: r3-sizing-20261112
  due: До подтверждённого цикла/подбора и расширения области; в пределах принятого lease или нового назначения
  restriction: Схема выдержки, фактические power envelopes/одновременность/пуск/тепло и физика процесса UNKNOWN.
reproduction_artifacts:
- verification/r5_r3_power_recheck/review.md
- verification/r5_r3_power_recheck/reproduction.json
- verification/r5_r3_power_recheck/independent_results.json
supersedes: null
rechecks:
- REV-R5-R3-PARAMETRIC-OUTPUT-01-001
```

## Предложение нового R4 claim — расчётно связанная компоновка после PR #39

2026-11-12T13:17:33Z, R4 r4-linked-20261111. T-r4-calculated-layout-01 READY / owner NONE / PROPOSED_PENDING_MAIN. База c0053ff7f22fbc10e93efff2691ca6aa1ef90a06, точные входы/каталог и постановка verification/r4_calculated_layout/. Это предложение задачи и сверка источников, **не акт независимой проверки и не результат CAD**. Новый OUTPUT review NOT_RUN. Роль действует по пользователю, claim ждёт принятия main; прежняя ограниченная приёмка/история/геометрия не меняются. G1 OPEN, B opening/L physical INDETERMINATE, физические испытания NOT_RUN.


## REV-R5-R3-CYCLE-TRACE-01-001 — сквозная карта и приоритеты R4

Акт: [review.md](../verification/r5_r3_cycle_trace_review/review.md). Предыдущие акты сохранены; источник/CAD review NOT_AVAILABLE не заменён предположением о его содержании.

```yaml
record_type: review
review_id: REV-R5-R3-CYCLE-TRACE-01-001
kind: OUTPUT
task_id: T-r3-cycle-trace-01
created_at_utc: '2026-11-12T17:18:16.982822Z'
reviewer:
  role: R5
  session_id: 6af41aff-4210-8191-94a3-5d9c4bd75076
  model_label: Codex
reviewed_roles:
- R3
author_sessions:
- r3-sizing-20261112
independence_basis: Reviewer не автор карты/приоритетов/CAD; отдельно прочитаны 25 первичных страниц и выполнены
  Fraction-проверки Git-координат. Организационная независимость не удостоверена.
reviewed_commit: 43f03359fabe2b664935b17f9ac7851504093ece
parameter_refs:
- id: R3P_BASE_A_APPROACH_POWER_TOTAL_BOUND
  revision: 1
  engineering_sha256: c6a2f18ff66a2d06b003c7b9d7c87b5a27f529f1bae71505ba27b39ec07071f8
- id: R3P_BASE_A_APPROACH_QIN
  revision: 1
  engineering_sha256: 10d1ff9f114f0b3820dc81952ae75c23a3fd16a83d39d9fc5edd8e5cd09941a1
- id: R3P_BASE_A_APPROACH_QOUT
  revision: 1
  engineering_sha256: 46f324a7fcc0b9a040eb92b3f0935ce69a1d0e0d59ca7f2a81c1e0078047cd04
- id: R3P_BASE_A_APPROACH_SPEED
  revision: 1
  engineering_sha256: c81b3ac419dd00fbd6ecc411f44553d919fdf2e199dd150cb92aae3b613a6745
- id: R3P_BASE_A_APPROACH_TIME
  revision: 1
  engineering_sha256: d49efe65d0373fabf7760047d5b4d44fcac69fb8e807cf4f7c8d1339adff3def
- id: R3P_BASE_A_EJECT_POWER_TOTAL_BOUND
  revision: 1
  engineering_sha256: 59d34d3a365d182d39dd7ff7a379c26df1ea0994aba1907d55855f95362099c3
- id: R3P_BASE_A_EJECT_QIN
  revision: 1
  engineering_sha256: a42ac71c62cd3971ddf24abfd967b085dd560d35fac9d7b00ceb7f85f29f622c
- id: R3P_BASE_A_EJECT_QOUT
  revision: 1
  engineering_sha256: eaab18a6d5f8955017ad3769ef7aee11896ebef855e090cb44a28b0bf7176f46
- id: R3P_BASE_A_EJECT_SPEED
  revision: 1
  engineering_sha256: 1f653c9e94740b4f8f089d3b6669436d36c140a67d31888afbbe74d94c0fd1ab
- id: R3P_BASE_A_EJECT_TIME
  revision: 1
  engineering_sha256: 018ee8fe4ee0bda143e892541e7706fecce5dda89a06dccc260f160630f60e5a
- id: R3P_BASE_A_FIXED_BUDGET_AVERAGE_BOUND
  revision: 1
  engineering_sha256: 85fe46d12739df3afb077c6cad01558a100b1ee119484d5bf68b4ab86994774f
- id: R3P_BASE_A_FIXED_BUDGET_CYCLE
  revision: 1
  engineering_sha256: 32284da21f90846684c5077a51dedf89a93f50450eddb51fb1ab3c56046dcfbe
- id: R3P_BASE_A_FIXED_BUDGET_ENERGY_BOUND
  revision: 1
  engineering_sha256: 059951875d3e21e1265a76f8a554ada0e54c6625471cd2dcc2586ef7c13b6185
- id: R3P_BASE_A_FIXED_BUDGET_MASS_RATE
  revision: 1
  engineering_sha256: 562d99c8f8f2f9c5e5ecc3ad5ada2602e9910f1eb7cbb98dd2ae031f6f361e02
- id: R3P_BASE_A_FIXED_BUDGET_PEAK_BOUND
  revision: 1
  engineering_sha256: b5bb4c9c9bc53454ff62f9065e6ca2dea313900c26fafcba8cc1dc3dd39243e4
- id: R3P_BASE_A_FIXED_TIMES_AVERAGE_BOUND
  revision: 1
  engineering_sha256: f6105c18421d6e84fdafa77aa057fab434bbc03d4d712566e7c18c1b6c8aa639
- id: R3P_BASE_A_FIXED_TIMES_CYCLE
  revision: 1
  engineering_sha256: 083ff4dd5e59919bacf674168f24b04f9a18b6338eab84bd3ceee4eb0ebac26c
- id: R3P_BASE_A_FIXED_TIMES_ENERGY_BOUND
  revision: 1
  engineering_sha256: afd28ee7cf20f42dd43116d2582c1888f8cc8c400ee5afa4631605d332e5094b
- id: R3P_BASE_A_FIXED_TIMES_MASS_RATE
  revision: 1
  engineering_sha256: 6f151caf5cef728d72a24f6c35d3a1a0f47d3e4430c43052ad8af28539b02f75
- id: R3P_BASE_A_FIXED_TIMES_REQUIRED_PEAK_BOUND
  revision: 1
  engineering_sha256: 93149db843a28df3e181f3ed87bebe8b01ddde69f5a9c4a395c2fdb84d41ce1e
- id: R3P_BASE_A_RETURN_POWER_TOTAL_BOUND
  revision: 1
  engineering_sha256: 90795ca54d97938ec090c6e3034b451e50349398b77e8e585ccb67055112dbed
- id: R3P_BASE_A_RETURN_QIN
  revision: 1
  engineering_sha256: 5b21d02379b2da6222e1e4451780fa3748243310ada79dfd72344fd0da7df67c
- id: R3P_BASE_A_RETURN_QOUT
  revision: 1
  engineering_sha256: 5fc81e710759bde9d1f7d961686f6eaa455b40be4ec76cf4fd849ee8062b6d78
- id: R3P_BASE_A_RETURN_SPEED
  revision: 1
  engineering_sha256: 1758645969aa4a904e76672b406d1890fb6924e816f260446ec3d40c3600274e
- id: R3P_BASE_A_RETURN_TIME
  revision: 1
  engineering_sha256: 32be25dfee1d0f807df5ee37b02150f12c171665be5ca06c70b7fc742c899442
- id: R3P_BASE_A_WORK_POWER_TOTAL_BOUND
  revision: 1
  engineering_sha256: 1ed2040c2f2a8caf0c0f382696583c938b3a9baedc8649dc1b0c251c4a9a963b
- id: R3P_BASE_A_WORK_QIN
  revision: 1
  engineering_sha256: 44cb39ebd18b36f9c9e79a3115a8401e82e63f045e330dd277f1f4abe1ac8d73
- id: R3P_BASE_A_WORK_QOUT
  revision: 1
  engineering_sha256: 9d5e81d839245ecd2de86f4dc3628843eeda96bdc074e986b9d677ed88383b91
- id: R3P_BASE_A_WORK_SPEED
  revision: 1
  engineering_sha256: 957728504d3e7dcc9994e7299b5e9088a3cbc6ae98288771c59b13840af3b8a5
- id: R3P_BASE_A_WORK_TIME
  revision: 1
  engineering_sha256: fa8fad8df323521564c5b189e08afe07f077b31f5075444bb2e90616fee73951
- id: R3P_BASE_B_APPROACH_POWER_TOTAL_BOUND
  revision: 1
  engineering_sha256: 5d9d964f328962c87e664dd23ff956f49c1fbbc03cbf904c57486606582f15ea
- id: R3P_BASE_B_APPROACH_QIN
  revision: 1
  engineering_sha256: 62dd818e2d57cb3a8b3d7550b566b2375a4a87db8b56a2cb825babd68162f7d8
- id: R3P_BASE_B_APPROACH_QOUT
  revision: 1
  engineering_sha256: 8cfb081f258f53a031fa1702ab2359f71b780312254bd73e8670cfb22e2e6b0c
- id: R3P_BASE_B_APPROACH_SPEED
  revision: 1
  engineering_sha256: e83b60e6f2c6023d9d1a1eedf1698a5f57704c4bab6bc0348497904f7ce885f8
- id: R3P_BASE_B_APPROACH_TIME
  revision: 1
  engineering_sha256: 7b83c36a5cde6c9f1339485dedaddd9da6330515377e45412da843b494a8728e
- id: R3P_BASE_B_EJECT_POWER_TOTAL_BOUND
  revision: 1
  engineering_sha256: fa77693baaf12f26858a9194f5fb25bfd00359a31553ba2dddae3e673183eaed
- id: R3P_BASE_B_EJECT_QIN
  revision: 1
  engineering_sha256: eeb1739d1d0661ad1cd5c35adc2cecd03b43c630ecc2454c30f1dcedca1b409a
- id: R3P_BASE_B_EJECT_QOUT
  revision: 1
  engineering_sha256: b2136ec245e3a197bcedb1a981fa5b12c60ec9631ebfc757a9a3c8b23da05f7e
- id: R3P_BASE_B_EJECT_SPEED
  revision: 1
  engineering_sha256: f841f4a1a5b5b3449416a87f1e23e9569ebc9466c352b41842f6a47b7a18da97
- id: R3P_BASE_B_EJECT_TIME
  revision: 1
  engineering_sha256: 156773d856d6edfa2cb22a0799a26b0d863c540d2cead81c93cc33950fe5d045
- id: R3P_BASE_B_FIXED_BUDGET_AVERAGE_BOUND
  revision: 1
  engineering_sha256: 0c5ce99753454b1e1d2e525c9aa0bd0ec36d084d93ee7ddbb130d8f7740748cc
- id: R3P_BASE_B_FIXED_BUDGET_CYCLE
  revision: 1
  engineering_sha256: 2508d013863a8bc6255b074ca5b3b639ad62f273198df077e6eb940e5d7833c1
- id: R3P_BASE_B_FIXED_BUDGET_ENERGY_BOUND
  revision: 1
  engineering_sha256: 1bd0242c81e632ae45d536b6dddf8170c7acfa13f5b679bcb8074f2943714aa4
- id: R3P_BASE_B_FIXED_BUDGET_MASS_RATE
  revision: 1
  engineering_sha256: b67370e036a582e44a3feee37d928a47002c9ddb535edc824ace0ea8ffbcd5c9
- id: R3P_BASE_B_FIXED_BUDGET_PEAK_BOUND
  revision: 1
  engineering_sha256: ff02cdcaa778fd0a2499bfea662da9bd1f05208bac8ace6dfbdca83398672222
- id: R3P_BASE_B_FIXED_TIMES_AVERAGE_BOUND
  revision: 1
  engineering_sha256: 3d340e15bcedc61387d475d7063326005fee1cbea70bd178efb2a003e09113dd
- id: R3P_BASE_B_FIXED_TIMES_CYCLE
  revision: 1
  engineering_sha256: dfd14da08f91f33820909f3962cf8e657958000c1c9fff62419ad73f99567c33
- id: R3P_BASE_B_FIXED_TIMES_ENERGY_BOUND
  revision: 1
  engineering_sha256: 78bbe3fb28b4030203afb7613f5d8331ae5c0f2050ded4fccc540a262d03405a
- id: R3P_BASE_B_FIXED_TIMES_MASS_RATE
  revision: 1
  engineering_sha256: ebc058b1aaf1fb7f58b35db1cdb23cf2ee76547ec280eb165c8e3d2cccadf59e
- id: R3P_BASE_B_FIXED_TIMES_REQUIRED_PEAK_BOUND
  revision: 1
  engineering_sha256: 512a55f015b883589b33eecda6bb707d1e5fde72f6343ad2ad12e613a81f8f7b
- id: R3P_BASE_B_RETURN_POWER_TOTAL_BOUND
  revision: 1
  engineering_sha256: bb64ef6bc6f01be112407345baf56466e6a8ebfb250342d2bc18c088f35eca79
- id: R3P_BASE_B_RETURN_QIN
  revision: 1
  engineering_sha256: 5d796c71559f18f1d78696392f19726770480eb085f4e3b92588884feb167c06
- id: R3P_BASE_B_RETURN_QOUT
  revision: 1
  engineering_sha256: 409793acb2622eed26ca77ab4d03956d4036ee51b2845b909a5522efcdb12418
- id: R3P_BASE_B_RETURN_SPEED
  revision: 1
  engineering_sha256: 121e9bbef7dc38ba1b1fb583d49e80ac8c3066a961271a8ce4a3f343252c464b
- id: R3P_BASE_B_RETURN_TIME
  revision: 1
  engineering_sha256: 362d13390bd29b93356c508ae6d4c8fd2ee7127850a7b3be535a4a8bb8875a1f
- id: R3P_BASE_B_WORK_POWER_TOTAL_BOUND
  revision: 1
  engineering_sha256: f8783cce4d7f9b3928ef030e467e44a59c80a4024b23afd21dbd8b1056af70f1
- id: R3P_BASE_B_WORK_QIN
  revision: 1
  engineering_sha256: 01075ee9a8585ada9bb22a6a64285ac8ac77d022a1cd8b7fa6b911aa811f2248
- id: R3P_BASE_B_WORK_QOUT
  revision: 1
  engineering_sha256: 29a8b483a5839be773e0a7ef0be092f93690157dc0b719c27c561a683c68f3b6
- id: R3P_BASE_B_WORK_SPEED
  revision: 1
  engineering_sha256: 0ccd27122b0d9514a51d7ea257a5901c904f3f8cea522333168e0e470388cb29
- id: R3P_BASE_B_WORK_TIME
  revision: 1
  engineering_sha256: 6ab18b2b58bcd4c53ffa195920bf89f0703375ccffdf90c78f1137176a4acd00
- id: R3P_IN_HOLD_TOTAL_CAP
  revision: 1
  engineering_sha256: 92d23c9caa32885462cb5fef459c5a8edde09fedaeb3020d395795f31a09a1b4
- id: R3P_IN_MOTION_EXTRA_CAP
  revision: 1
  engineering_sha256: 1fff9a8de90b09e298da53ca1d44640d358bac92237a02b42f0a5ab1c4e0b966
- id: R3P_IN_PAUSE_TOTAL_CAP
  revision: 1
  engineering_sha256: 610a152a7bc2c14bf067a71a9477c0b24daf1ee5e1b1db8e0586d57eb38785d9
- id: R3P_REAL_HOLD_POWER
  revision: 1
  engineering_sha256: e111056fec081e5d158f7e8be735bca9c02f8626e929495ac2261b97024b171f
- id: R3_BASE_A_APPROACH_STROKE
  revision: 1
  engineering_sha256: 98645adfda66bebe880adbcad38da8445316135aee160f0d249fb299feb0cbb9
- id: R3_BASE_A_BORE
  revision: 1
  engineering_sha256: 05c64eda07ec93be6a28869a8cf129fa5b9d6a9998fb741dd7806675de6c9159
- id: R3_BASE_A_CHAMBER_VOLUME
  revision: 1
  engineering_sha256: 4adf0f8da919afff37a402744a64c00a748e03ba9a6928d3e42a6e6a66b90e75
- id: R3_BASE_A_EJECT_STROKE
  revision: 1
  engineering_sha256: dd5af41f3ff553043ed5cc115b13b7b46171fc92be4feeac5c7f5bac074df1de
- id: R3_BASE_A_FORCE_WORK_PEAK
  revision: 1
  engineering_sha256: 14f8433c2fbfb8841177e205fc5f6a4d933419e488ccab8b7fb71bba7fdb6a02
- id: R3_BASE_A_OCCUPIED_LENGTH
  revision: 1
  engineering_sha256: 6eddd8be3b045acb0a6bf36ac09a4f0f45e271cb93ddff2d6286755dec6f4c65
- id: R3_BASE_A_RETURN_STROKE
  revision: 1
  engineering_sha256: f699ed8cbe193f4b9717ea08c17d133d734971d115e735d304a25554a1e813d5
- id: R3_BASE_A_ROD
  revision: 1
  engineering_sha256: 8d8593ad3c342c40c90463b94d9674ea45052aeafa1bc06ff660de3cf4b67474
- id: R3_BASE_A_WORK_STROKE
  revision: 1
  engineering_sha256: 4da9871b7b734d5e25c85b83740d4ec54277a98be55265ce4b284e38993d0a32
- id: R3_BASE_B_APPROACH_STROKE
  revision: 1
  engineering_sha256: be79a8938a64066768edfa201035e4a3b7efce29c7560006721ddd71487352ed
- id: R3_BASE_B_BORE
  revision: 1
  engineering_sha256: 995a9fd66907509880e3d3306f53feeb249b8915a4a79baac6eedf5716237c16
- id: R3_BASE_B_CHAMBER_VOLUME
  revision: 1
  engineering_sha256: a3ae27188d2df4cb54813156c4108f7a16651c1da2b0edeba9402f2ac907ec6f
- id: R3_BASE_B_EJECT_STROKE
  revision: 1
  engineering_sha256: 0a3586ecb9e6c8710b89c06daa825c729b64df7d2427abbe0768a4ee51e5f809
- id: R3_BASE_B_FORCE_WORK_PEAK
  revision: 1
  engineering_sha256: 561b8a3724234fada0e6c6753832ccf319875f71dbf3cb9528fdd8ac486a2016
- id: R3_BASE_B_OCCUPIED_LENGTH
  revision: 1
  engineering_sha256: 4deb2f14d824e5d9ae04c9b153d771415f1d3bc87f2ae9ba8f34bfe04e6f2da8
- id: R3_BASE_B_RETURN_STROKE
  revision: 1
  engineering_sha256: aac701db499dd41fd2342d71f77e4f945d15d7f6a588d7fb75ab3e549514ea90
- id: R3_BASE_B_ROD
  revision: 1
  engineering_sha256: 26738f42950bd1441dffe72011b6c64408ea198c0c980d4ad96c9cc914435549
- id: R3_BASE_B_WORK_STROKE
  revision: 1
  engineering_sha256: a469e88240f61257c770eb9eaca4557409ae1c5cd00dbfc945c70a47983816b0
- id: R3_IN_CHANNEL_HOLD
  revision: 1
  engineering_sha256: 8be165d6478377713e10c8c18afc0943af819939ff07b220f9cf7771e121d326
- id: R3_IN_CHANNEL_SLIDE
  revision: 1
  engineering_sha256: 8f9ec5d66ecde7f8d6cf7abf93339e3d5257482d386411f833344727670881b0
- id: R3_IN_CLEARANCE
  revision: 1
  engineering_sha256: 9f5eacf192d08b9cddde95c48aac7b3ba47cf72bfd4a87ad82191845d4101560
- id: R3_IN_ELECTRIC_LIMIT
  revision: 1
  engineering_sha256: f0caad98ee0195b86491b90f5854031e0003469d369ec91522ff5e6ec5c5ed48
- id: R3_IN_HEIGHT
  revision: 1
  engineering_sha256: 8c5c16ec5d1055417f306b176bffd22fff62ba9be27c36132ccf54da49581c8a
- id: R3_IN_MASS
  revision: 1
  engineering_sha256: bcce4f5bc3c904d5dc9c299a5e5d5d70e4729ae22c092e4d63eb4b4eb60cfc7d
- id: R3_IN_PHI
  revision: 1
  engineering_sha256: 9e7bdce5d57581a516de1c3799e5266adc403f3fca84977b2bfb9a86275d4a43
- id: R3_IN_PRODUCT_LENGTH
  revision: 1
  engineering_sha256: 6de1c62bb4e3ce436ad93e909cfce9c5450f0f6f3684026969677b1f23aed6b3
- id: R3_IN_REBOUND
  revision: 1
  engineering_sha256: d3bfd9e06e08695b6ead63098e4e6c38040f218c9a0dd7f1ea8ad89ef6697687
- id: R3_IN_RHO
  revision: 1
  engineering_sha256: 08e0f1b501432130a0dd803fb2d16c2b369597777ad73fb23bc37b5354e17150
- id: R3_IN_SIGMA_END
  revision: 1
  engineering_sha256: e7d4a43a42e621ac77a3a1404bd1e4f879530e44732244069019427294694f83
- id: R3_IN_T_HOLD
  revision: 1
  engineering_sha256: f0759326148cfebf7dc4337ae2e5ef1b79b962c953b566b395a4316be136cf72
- id: R3_IN_T_OPEN_B
  revision: 1
  engineering_sha256: 85fa59de19c77ee71a01adfd23d779ea0a627df960bf1df8af8235a6ecce4da8
- id: R3_IN_T_UNLOAD_B
  revision: 1
  engineering_sha256: 7221e500e68e688fd7f36cb421ee6b9bd9fccf32b25f86e8d93a7a901dbb0f0c
- id: R3_REAL_OTHER_ACTUATORS_ENERGY
  revision: 1
  engineering_sha256: 4acbad67449b40b4d09e200a8ef7726ff1b98e7373a269b149b1738731ef5d69
- id: R3_REAL_RESIDUAL_CHANGE
  revision: 1
  engineering_sha256: e8a58b56dae1ac5a357961175076758fd7a948ff9d7668999819d916ea69ec87
- id: R3_REAL_STOP_OPEN_LIMIT
  revision: 1
  engineering_sha256: 9f2439481bc97ed6bb90f177ef9dbdc4f03999a61d409b3e8dd6e9688c24f7df
- id: R3_REAL_STOP_RESIDUAL
  revision: 1
  engineering_sha256: 2355d0d869d9d8622de906b801be4d99bc0bc334d0b90eb69042b4d4eccd4727
artifacts:
- path: params/registry.yaml
  sha256: f52f6a52cf84831b714c037521bede8ada33e45d93d8b7251aa30b0b8a0d4d44
- path: sources/raw/Target_object_BP500.pdf
  sha256: bf7276191a73b3d9a22ef516316bc59aac5d12fd708a7adc454bd6d9da4bec0c
- path: sources/raw/additional_Ars_Rst_500.pdf
  sha256: 631b7186c7f2d38251625b77a70e790d2c257cdeb1dd3343befe3783cd983c40
- path: sources/raw/additional_Prodeco_E55.pdf
  sha256: 27d27b7e41247e1098531204581953e6cba388ec918418fa2ee64891bda4cc87
- path: sources/raw/additional_Weima200.pdf
  sha256: 477fcb54af5f7210afc9640137391fbb97a950be41daa52cc7d8b601e4f5e135
- path: verification/r3_cycle_trace/README.md
  sha256: aaac6e5aa5faa9d997b7a2dac2a74407c0f8a51a5a43c9767f0cd12aa100df35
- path: verification/r3_cycle_trace/cad_evidence.json
  sha256: 36ebd59127674a8295b5d0d3cac0a89387be955d551437b230e51f0fb79ca890
- path: verification/r3_cycle_trace/checks.json
  sha256: 4c65bee49dea39fae4c4cb86fb2866f4210526633907cb7ddcd53de564196b56
- path: verification/r3_cycle_trace/claim.md
  sha256: 4d1f71429694b5942c3f37b7ab7a88c5d6d36031d294db3cd27c7a1acc4d04ad
- path: verification/r3_cycle_trace/cycle_index.csv
  sha256: 3406904ef6100268f49318ecb571b835a58751cbae885a270cdf25886802301f
- path: verification/r3_cycle_trace/cycle_table.json
  sha256: 29fa0a8b49ba36e54f7bfe8a70d36eca6ba07129c2291b8a04b8bd647cb4033f
- path: verification/r3_cycle_trace/cycle_table.md
  sha256: be3f5191db8d502c5af95cb88daff56208c91d5347ca754c9d6e4efed6ea16f5
- path: verification/r3_cycle_trace/input_acceptance.json
  sha256: 6797d8d74afd69913c243a56fd2f59269d482712806b78fe9eb1a69d212e008c
- path: verification/r3_cycle_trace/input_audit.md
  sha256: 6a104838c0766ac7ed81ec8b5e4a71f4ffda7a3a3de92831143a2c87ad3d5287
- path: verification/r3_cycle_trace/preflight.json
  sha256: 6403cf5147a70a1a5e0fd0ddefd8f8673861c0b581479970eda62d9dc4ab2c5f
- path: verification/r3_cycle_trace/r4_backlog.json
  sha256: 5cb95fd2b15f8a4f0abd6e49a416eacccf17a12894c2e564ab5650ea5ea4897a
- path: verification/r3_cycle_trace/r4_priorities.md
  sha256: 9973f7862a523dbea9aa1fb284d956c10b9efcd77b0e19761a6358016883d13a
- path: verification/r3_cycle_trace/registry_check.log
  sha256: f18008b12f04ec977f502d918a3a8b404f3c7e141b6d5becc8515bbc405b2cda
- path: verification/r3_cycle_trace/render_documents.py
  sha256: c642998715e7c5074155ebb39d5dd76a63f0bf408d1426210544b5e94f8774b5
- path: verification/r3_cycle_trace/result_checks.json
  sha256: e68de2ae9cee51981b366ade3d1ad12b0b861110b21f3eeee7695812dabd5b88
- path: verification/r3_cycle_trace/result_original_replay.log
  sha256: 1a6788ef0618508100983a5f760fbd5575761ff4bb75ee9e055d6b73f800ac74
- path: verification/r3_cycle_trace/result_power_replay.log
  sha256: 0f74e832c1b2bf06f7a217b86a3ea0f1c8f4121e13e1c996277e32ebcc5a46f8
- path: verification/r3_cycle_trace/result_preservation.json
  sha256: 8e4f24621c66437c183231f85bda546e93965e466342842848babd7b9b375c1a
- path: verification/r3_cycle_trace/result_registry.log
  sha256: f18008b12f04ec977f502d918a3a8b404f3c7e141b6d5becc8515bbc405b2cda
- path: verification/r3_cycle_trace/result_render.log
  sha256: 0f6ce8196bb0f4744902f17c08a5d3cc911e5733ff2f7ea09a39f574ad28c288
- path: verification/r3_cycle_trace/result_trace.log
  sha256: 5075566c106edaabc37d581b5a73afeb0997c62be6e4e7cec92e2f6973c9bdc4
- path: verification/r3_cycle_trace/review_request.md
  sha256: 717e3203727dd55b8db1678cb7ac9da23ab8dffb414a89858082a4aac4a7fcb8
- path: verification/r3_cycle_trace/source_ledger.md
  sha256: 4fc0b65f7c081a08fc3ab1937f9705a6192dcc4daa25c84eccacb149e6675825
- path: verification/r3_cycle_trace/sources.json
  sha256: 8401a54e1516bc6ea3bb2467804977f8d5289cc82c29f3d64c6e1d8cb1e28aaf
- path: verification/r3_cycle_trace/task.md
  sha256: 9d8aa3349500ba2f88f50a1443747a0121051ad2bd42fa8823b73de72760a113
- path: verification/r3_cycle_trace/verify_trace.py
  sha256: 704a061526c9c720e77c1fcacfd32571f114d8012dfaa69c2eb4c54bc94485ed
scope: Документальный OUTPUT-review 20 цепочек и девяти приоритетов; CAD review NOT_AVAILABLE, независимый native
  replay NOT_RUN.
checks:
- id: CHK-CYCLE-SOURCES
  method: Визуальное чтение конкретных страниц/схем BP500/WEIMA/PRODECO/ARS с проверкой PDF хэшей.
  expected: Источник подтверждает только собственную функцию/условия, без переноса механизма/чисел/применимости
    на REV.
  observed: 17 claims и 25 страниц сверены; ошибочного цитирования в проверенной области не выявлено; применимость
    REV не подтверждена.
  reasoning: Страницы покрывают источники всех 20 цепочек; OEM редакции и остальные страницы не проверены.
  result: PASS
- id: CHK-CYCLE-CAD-LINKS
  method: Независимые Fraction-вычисления исходных stages/poses и сверка 100 параметров с точным CALC.
  expected: Сохранить различие nominal R3 exit, declared CAD exit, retained material и tool return; не доказывать
    BRep по bounds.
  observed: SHORT_STROKE и RESET противоречия объявленной модели воспроизведены; 2156 стыков координат проверены,
    вне main-axis A5/B7 секунд.
  reasoning: Это документально-координатная область; actual FCStd/STEP/native и truth author witnesses NOT_RUN.
  result: PASS
- id: CHK-CYCLE-NATIVE
  method: Независимый нативный геометрический review.
  expected: Точная геометрическая верификация перед закрытием CAD-дефектов.
  observed: NOT_AVAILABLE акт CAD review; новый native replay NOT_RUN.
  reasoning: Пользователь явно поручил разделить подтверждённые документальные противоречия и непроверенные геометрические
    замечания.
  result: NOT_RUN
findings:
- id: R5-CYCLE-W01
  status: OPEN
  description: Начать черновые ресурсный граф и READY predicates вместе с материальным контрактом; окончательная
    сверка после геометрических предложений.
- id: R5-CYCLE-W02
  status: OPEN
  description: Нативные замечания CYC03/04/07 передавать с evidence grade и отдельным критерием независимой проверки;
    не объявлять доказанными actual CAD-дефектами.
verdict: WARNING
validity: CURRENT
blocker_ids: []
allowed_downstream_scope: Все CYC01…09 как условные interface/investigation proposals по уточнённому порядку; общий
  rebuild как девять доказанных исправлений NOT_READY.
excluded_claims:
- Согласованный физический полный цикл, производительность, удержание A, разгрузка/открытие B, безопасность
- Доказанные reviewer нативные CAD-дефекты или их устранение
- Утверждение оборудования, архитектуры, ТЗ и G1
warning_owner_and_due:
  owner_role: R3/R4
  owner_session: r3-sizing-20261112 для ответа R3; R4 по отдельному принятому назначению
  due: До следующего общего rebuild/закрытия геометрических замечаний
  restriction: Сначала материальный и черновые событийный/ресурсный контракты; native evidence не подтверждено.
reproduction_artifacts:
- verification/r5_r3_cycle_trace_review/review.md
- verification/r5_r3_cycle_trace_review/source_checks.json
- verification/r5_r3_cycle_trace_review/independent_results.json
- verification/r5_r3_cycle_trace_review/reproduction.json
- verification/r5_r3_cycle_trace_review/object_identity.json
supersedes: null
```

## Предложение отдельного R4 claim — CYC-01 + ранние CYC-08/09

2026-11-12T18:16:39Z; автор r4-linked-20261111 / R4, T-r4-cycle-contract-01 READY / owner NONE / PROPOSED_PENDING_MAIN. База b1a4e398741b84d482c96f00a605e98b720ff929, карта 43f03359fabe2b664935b17f9ac7851504093ece, акт e69a8afbe4df3d53c4cc8b5883319e00eb8130af. Постановка и защита источников verification/r4_cycle_contract/. Это административная подготовка, не контракт/не независимый review. Новый OUTPUT review NOT_RUN; R5-CYCLE-W01/W02 и CYC OPEN, G1 OPEN. Расчёты/CAD/их код/registry не меняются, solver/rebuild/физические испытания NOT_RUN. Точный C предложения — в следующем H.

## R4 CYC-01 / ранние CYC-08/09 — авторский результат, не независимый review

2026-11-12T19:14:28.746890+00:00; T-r4-cycle-contract-01 / r4-linked-20261111. Main d22542f1fb9c3ac932fadd12dceeed5b1f9c8ad9, claim принят PR #43, lease до 2026-11-13T18:16:39Z. Входы/акт input_audit.md и input_acceptance.json в verification/r4_cycle_contract/. ASSUMED_INTERFACE_PROPOSAL: материальный ledger/состояния/переходы, ранний resource/READY контракт, 59 примеров и 2 условные трассы. Документальная проверка не подтверждает числа/физику/контроллер/CAD. Запрос независимого OUTPUT review review_request.md; полный C в следующем H. CYC-01…09/R5-CYCLE-W01/W02 OPEN; G1 OPEN. Чужие акты/расчёты/CAD не изменены, numerical solver/CAD/rebuild/physical tests NOT_RUN.
