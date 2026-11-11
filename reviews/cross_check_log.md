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
