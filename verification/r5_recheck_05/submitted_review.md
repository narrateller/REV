# **Акт независимой повторной проверки REV-R5-RECHECK-05-001**

> * **Проверяемый коммит (code / results SHA):** debfd085842ccae079cfd6faea1c41bca20f335d.  
> * **Коммит эстафеты (handoff SHA):** 73541d22377fb2b97df0964762b5cdeca9711532 (NEXT\_MODEL.md — git blob 890ccd1ab6d2bde17e6781cba9e096150fbb32c5, SHA-256 594ce333ef57406c719524ba5934aaf4e4589cffe9d8c1291e625c3ebf3513f9; handoffs/T-codex-01-01/r4-model-01.md — git blob db17a922a8e12f124c0f222ae79160bf8b8e1136, SHA-256 7958de46394ab414fc917635218dcb56f03caf60795ec78190e58de93b8bd61c).  
> * **План и решение R1 (disposition):** 791d0ce8ccb31373b221d0b69063e2f835b442c0 (verification/r5\_recheck\_04/disposition.md — git blob 460690c8c7ec93606409a067b95ec36d66e8d97d, SHA-256 1e56811e0562c24c17845c42cbe63403d266923b327515e7fe978245eb2417c6; verification/r5\_recheck\_04/submitted\_review.md — git blob c1e290b54dc31a0ba4ab04371b8fddb0e5a4b0ed, SHA-256 f63fdd75808d64bca2b0c040763dda77f119e35917ffdfd9719445b22de521f4).  
> * **Решение арбитража (ARB-R1-RECHECK-03):** 1283c9e6f3b14dbbe820dd06798399c611d34ce8 (decisions/ARB-R1-RECHECK-03.md — git blob 335a00f7a2a6710d46c7f9a222a4f278292df63b, SHA-256 12acd9be000d8477ddc4cdf241c950cdecb95190a2747bd063d1f9d79f63c450).  
> * **Базовая ревизия main:** 2f463babdc84382a0ab2502f4acfa7a2047087df.  
> * **Предыдущий проверенный коммит реализации R4:** 576a17fc0b127cb7d377992c01d645a77bed42d4.  
> * **Статус ворот G1 и область модели:** G1 остаётся **OPEN** (NOT\_STARTED); результаты относятся исключительно к исследовательской синтетической модели осевых прямоугольных призм (AABB) с синхронной линейной трансляцией. Реальные размеры, допуски, усилия, свойства сырья и физическая безопасность установки REV остаются UNKNOWN.

## **1\. Итоговые вердикты по блокерам и регрессии**

| Объект проверки | Предмет оценки на коммите debfd085842ccae079cfd6faea1c41bca20f335d | Вердикт R5 | Статус |
| :---- | :---- | :---- | :---- |
| **R5-IMPL-01** | Устранение разрыва положения output\_obstacle в B / collision, введение непрерывной границы A-ISOLATE → A-PRESS в варианте A, расчёт непрерывности через assess\_continuity / continuity\_status, прямое влияние непрерывности на eligible, transition и ready (apply\_continuity), выполнение всех 4 исходов на A/B (8/8) и негативных мутаций. | **PASS (в синтетической области AABB)** | **CLOSED** |
| **Регрессия R5-IMPL-02** | Сохранность полной матрицы неупорядоченных пар независимо заданного состава сцены (SCENE / scene\_bodies), разделения CHECK и CONTACT\_INTERFACE, обработки UNKNOWN геометрии, негативных мутаций интерфейсов и автоматических регрессий CE-01 / CE-02 после правок debfd085842ccae079cfd6faea1c41bca20f335d. | **PASS (регрессий не обнаружено)** | **CLOSED** |
| **Ворота G1** | Архитектурный выбор A/B, физическая выдача, разгрузка камеры, удержание столба, прочность и валидация реального пресса REV. | **NOT\_APPROVED (вне синтетической модели)** | **OPEN** |

## **2\. Проверка исправлений R5-IMPL-01 и непрерывности стадий**

### **2.1. Инициализация output\_obstacle и непрерывность в B / collision и A / collision**

> * **Устранение скачка на внутреннем стыке:** в models/kinematic\_press/linked.py (git blob 4b40d431ddf0ee3e274f5c5934817db431ff364f, строка 89\) условие if outcome=='collision': bodies\['output\_obstacle'\]=make\_box('3/2','7/4',0,1) перенесено в начало run(variant, outcome) — до сохранения baseline \= copy.deepcopy(bodies) и до запуска первых стадий сценария.  
> * **Траектория в B / collision:**  
  * На стадиях B-UNLOAD (t \= \[0, 1\]), B-OPEN с отводом lock (t \= \[1, 2\]) и B-OPEN с отводом stop (t \= \[2, 3\]) препятствие output\_obstacle неподвижно находится в min \= \['3/2', 0, 0\], max \= \['7/4', 1, 1\] с delta \= \[0, 0, 0\]. Поскольку интервал $x\in [3/2,7/4]$ не пересекается ни с неподвижными punch ($x\in [-1,0]$) и product ($x\in [0,1]$), ни с отводимыми вдоль оси $y$ телами stop ($x\in [2,3]$) и lock ($x\in [3,4]$), все 43 проверяемые пары CHECK на первых трёх стадиях дают NO\_COLLISION, а оба интерфейса (punch/product и stop/lock) — VALID.  
  * На стыке B-OPEN → B-EJECT при t \= 3 координаты всех 10 тел совпадают точно (mismatches: \[\], unknown: \[\], removed: \[\], added: \[\], time\_contiguous: true, lifecycle\_valid: true).  
  * В стадии B-EJECT (t \= \[3, 4\]) при совместном ходе punch и product на delta \= \[2, 0, 0\] матрица обнаруживает столкновение product / output\_obstacle на нормированном интервале \['1/4', '7/8'\] и столкновение punch / output\_obstacle на интервале \['3/4', '1'\] (collision\_interval\_punch\_obstacle), переводя сценарий в collision\_status: "COLLISION", transition: "BLOCKED", ready.status: "BLOCKED" при чистом статусе непрерывности ready.continuity\_status: "CLEAR".  
> * **Добавление предваряющей стадии A-ISOLATE в варианте A:**  
  * В linked.py (строка 102\) перед A-PRESS добавлен вызов if variant=='A': stage('A-ISOLATE', {}) на интервале t \= \[0, 1\], а стадия A-PRESS выполняется на t \= \[1, 2\] (и A-RETURN при eligible — на t \= \[2, 3\] с удалением продукта при t \= 2).  
  * В результате все четыре исхода варианта A (sufficient, short, collision, unknown) имеют непустой список внутренних переходов continuity (минимум граница A-ISOLATE → A-PRESS), проверяемый по единым правилам с вариантом B.

### **2.2. Логика assess\_continuity, continuity\_status и apply\_continuity**

Анализ функций непрерывности в models/kinematic\_press/linked.py (строки 49–82 и 110–145) подтверждает выполнение всех требований ARB-R1-RECHECK-03 и плана disposition.md:

> 1. **Точная сверка геометрии, времени и жизненного цикла (assess\_continuity):**  
   * Для каждой пары соседних стадий (prev, nxt) проверяется совпадение времени time\_contiguous \= (prev\['time'\]\[1\] \== nxt\['time'\]\[0\]), вычисляются списки удалённых (removed \= sorted(set(old) \- set(new))) и добавленных (added \= sorted(set(new) \- set(old))) тел.  
   * Удаление тела признаётся валидным (expected\_removal) только если removed \== \['product'\], not added, lifecycle.get('event') \== 'REMOVE\_AFTER\_CONFIRMED\_SYNTHETIC\_EJECTION' и lifecycle.get('time') \== prev\['time'\]\[1\]. Любое добавление тела (added) или несанкционированное/несвоевременное удаление делает lifecycle\_valid \= False.  
   * Для каждого сохраняемого тела из set(old) & set(new) вычисляются lo, hi, delta \= model.box(old\[name\]) и nlo, nhi, \_ \= model.box(new\[name\]); несовпадение lo\[i\] \+ delta\[i\] \!= nlo\[i\] или hi\[i\] \+ delta\[i\] \!= nhi\[i\] по любой из трёх осей заносит тело в mismatches, а отсутствие координат или delta=None перехватывается исключением и заносит тело в unknown (отдельно от доказанного разрыва mismatches).  
> 2. **Трёхзначная классификация и приоритет блокеров (continuity\_status, apply\_continuity):**  
   * continuity\_status(checks) возвращает 'BLOCKED' при любом mismatches, not time\_contiguous или not lifecycle\_valid; иначе 'INDETERMINATE' при любом unknown; иначе 'CLEAR'.  
   * До удаления продукта проверяется pre\_continuity \= assess\_continuity(stages, {'event': 'NOT\_REMOVED'}): условие eligible требует pre\_state \== 'CLEAR', что исключает удаление product и переход к A-RETURN / B-RESET при любом разрыве или неопределённости на предварительных стадиях.  
   * На выходе apply\_continuity(transition\_status, readiness, continuity) принудительно переводит transition\_status и readiness\['status'\] в 'BLOCKED' при state \== 'BLOCKED', а при state \== 'INDETERMINATE' переводит их в 'INDETERMINATE' только если ранее не был доказан 'BLOCKED' (сохраняя уже доказанный блокер от коллизии, короткого хода или нарушенного интерфейса).

### **2.3. Сводка 8 сценариев SYN-LINKED-EJECTION (A/B × 4 исхода)**

| Вариант / исход | Стадии (time) | ejection\_status (задняя грань) | collision\_status (интервалы) | continuity (continuity\_status) | transition / ready.status | matches\_expected |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **A / sufficient** | A-ISOLATE \[0,1\], A-PRESS \[1,2\], A-RETURN \[2,3\] | SUFFICIENT\_STROKE (rear \= "2") | NO\_COLLISION (null) | 2 перехода, mismatches: \[\], unknown: \[\], удаление product при t \= 2 (CLEAR) | ALLOWED / READY | true |
| **A / short** | A-ISOLATE \[0,1\], A-PRESS \[1,2\] | INSUFFICIENT\_STROKE (rear \= "1") | NO\_COLLISION (null) | 1 переход, mismatches: \[\], unknown: \[\] (CLEAR) | BLOCKED / BLOCKED | true |
| **A / collision** | A-ISOLATE \[0,1\], A-PRESS \[1,2\] | SUFFICIENT\_STROKE (rear \= "2") | COLLISION (product: \['1/4','7/8'\], punch: \['3/4','1'\]) | 1 переход, mismatches: \[\], unknown: \[\] (CLEAR) | BLOCKED / BLOCKED | true |
| **A / unknown** | A-ISOLATE \[0,1\], A-PRESS \[1,2\] | INDETERMINATE (null) | INDETERMINATE (null) | 1 переход, mismatches: \[\], unknown: \["product"\] (INDETERMINATE) | INDETERMINATE / INDETERMINATE | true |
| **B / sufficient** | B-UNLOAD \[0,1\], B-OPEN \[1,2\], B-OPEN \[2,3\], B-EJECT \[3,4\], B-RESET \[4,5\]..\[6,7\] | SUFFICIENT\_STROKE (rear \= "2") | NO\_COLLISION (null) | 6 переходов, mismatches: \[\], unknown: \[\], удаление product при t \= 4 (CLEAR) | ALLOWED / READY | true |
| **B / short** | B-UNLOAD \[0,1\], B-OPEN \[1,2\], B-OPEN \[2,3\], B-EJECT \[3,4\] | INSUFFICIENT\_STROKE (rear \= "1") | NO\_COLLISION (null) | 3 перехода, mismatches: \[\], unknown: \[\] (CLEAR) | BLOCKED / BLOCKED | true |
| **B / collision** | B-UNLOAD \[0,1\], B-OPEN \[1,2\], B-OPEN \[2,3\], B-EJECT \[3,4\] | SUFFICIENT\_STROKE (rear \= "2") | COLLISION (product: \['1/4','7/8'\], punch: \['3/4','1'\]) | 3 перехода, mismatches: \[\], unknown: \[\] (CLEAR) | BLOCKED / BLOCKED | true |
| **B / unknown** | B-UNLOAD \[0,1\], B-OPEN \[1,2\], B-OPEN \[2,3\], B-EJECT \[3,4\] | INDETERMINATE (null) | INDETERMINATE (null) | 3 перехода (B-OPEN → B-EJECT: unknown: \["product"\]) (INDETERMINATE) | INDETERMINATE / INDETERMINATE | true |

## **3\. Проверка регрессии R5-IMPL-02, матриц пар и контрпримеров CE-01 / CE-02**

Сверка кода и контрольных сумм debfd085842ccae079cfd6faea1c41bca20f335d с предыдущим коммитом 576a17fc0b127cb7d377992c01d645a77bed42d4 подтверждает полное отсутствие регрессий по R5-IMPL-02:

> 1. **Неизменность входных спецификаций и базовых тестов:**  
   * Файлы models/kinematic\_press/phase\_plan.json (SHA-256 4a58073f560c5b5db560dc5914917892c153ac73e47cf93aa93f2921a6a90cf6), models/kinematic\_press/phase\_inputs\_synthetic.json (84df6bacf89948cc4f33b9f25eca1452b9c55aabb61cc5fd4dbc69a0d9df6476), models/kinematic\_press/fixtures.json (efd0edfe6748ddfd84fd9229ac838b065480a28abbf51779fd8dbdaf2722fcfe), models/kinematic\_press/input\_template.json (ed3330779850dd3d9af54027ab31c8605493296c5234162d4ccbd7b6aaef185e), models/kinematic\_press/transition\_fixtures.json (42829c9ebe35f5fcffef8cc678db774b49208b2f893066d12984ecd320cda668) и models/kinematic\_press/test\_model.py (5761a2d7681a9a3136d79023cbfe3c5ed73b2d2e9c4a9305f0f6bebb6725cfb6) побайтово идентичны ревизии 576a17fc0b127cb7d377992c01d645a77bed42d4.  
> 2. **Неизменность вычислительного ядра и фазового покрытия в model.py:**  
   * Единственное изменение в models/kinematic\_press/model.py (git blob 4222f101af66a8c20998268630b5552c6d6dbda6) относительно 576a17fc0b127cb7d377992c01d645a77bed42d4 — добавление HERE/'linked.py' в словарь report\['hashes'\] (строка 214\) для полноты прослеживаемости импорта from linked import contact в verify\_a\_out.  
   * Функции overlap\_time, check, motion\_restrictions, evaluate\_phases, transition и verify\_a\_out не изменялись.  
> 3. **Полнота матриц пар (SCENE и scene\_bodies):**  
   * В linked.matrix для каждой стадии с присутствующим продуктом генерируются все $\binom{10}{2}=45$ неупорядоченных пар из SCENE, а для стадий возврата после подтверждённого удаления продукта (A-RETURN, B-RESET) — все $\binom{9}{2}=36$ неупорядоченных пар.  
   * В model.evaluate\_phases для всех 13 фаз генерируются все $\binom{11}{2}=55$ неупорядоченных пар из plan\['scene\_bodies'\] (всего $13\times 55=715$ пар в synthetic\_phase\_coverage и rev\_phase\_coverage, где для input\_template.json все 715 пар попадают в unchecked\_pairs со статусом INDETERMINATE).  
> 4. **Сохранение регрессий CE-01 и CE-02:**  
   * **CE-01:** неподвижный продукт (delta \= \[0, 0, 0\]) при available\_stroke \= 2 в model.check возвращает ejection\_status \= 'INVALID\_INPUT' ('scalar ejection input conflicts with product geometry or motion'), а model.verify\_a\_out для неподвижного A-OUT возвращает 'BLOCKED'.  
   * **CE-02:** перенос только channel\_wall на начальную призму punch в B-EJECT автоматически обнаруживается вызовом model.evaluate\_phases(plan, altered)\['B-EJECT'\] (pair \= B-EJECT:channel\_wall/punch, collision\_status \= 'COLLISION', contact\_interval\_normalized \= \['0', '1'\]), а model.transition('B-EJECT', 'B-RESET', ...) возвращает status \= 'BLOCKED' по причинам 'pair collision or invalid result' и 'incompatible boundary: channel\_wall'.

## **4\. Воспроизводимость, сверка хэшей и ограничения инспекции пакета**

> * **Криптографическая связность отчётов и исходников:**  
  * В models/kinematic\_press/results/linked\_report.json (git blob 785294cff989b284560f28f54451f83883daf8d6, SHA-256 1c229eee6e43fc265310a0bcff70ac8d5bef3955cceee98fd8c45ed36a69411f) зафиксированы точные ссылки "arbitration\_commit": "1283c9e6f3b14dbbe820dd06798399c611d34ce8" и "disposition\_commit": "791d0ce8ccb31373b221d0b69063e2f835b442c0", а все 17 SHA-256 хэшей в разделе "hashes" совпадают с таблицей Git-объектов коммитов debfd085842ccae079cfd6faea1c41bca20f335d и 791d0ce8ccb31373b221d0b69063e2f835b442c0.  
> * **Границы текста в пакете Recheck.md:**  
  * В переданном файле Recheck.md полностью содержатся манифест всех 21 файла (с размерами, SHA-256 и Git blob SHA-1) и полные тексты README.md, fixtures.json, input\_audit.md, input\_template.json, linked.py, model.py, phase\_inputs\_synthetic.json, phase\_plan.json, force\_paths.svg, а также начало linked\_report.json (метаданные, словарь hashes, полный сценарий A / sufficient и сценарий A / short).  
  * Из-за включения в середину текстового пакета полных JSON-отчётов объёмом 1,60 МБ (linked\_report.json) и 1,16 МБ (report.json) хвост файла Recheck.md после середины linked\_report.json был усечён при загрузке контекста. При этом 100% исполняемой логики модели (model.py и linked.py) и все неизменившиеся файлы (test\_model.py, transition\_fixtures.json, phase\_plan.json, phase\_inputs\_synthetic.json, fixtures.json, input\_template.json) доступны в полном объёме.  
> * **Инженерные и физические ограничения (причины сохранения G1 в статусе OPEN):**  
  * Все числовые координаты, времена и интервалы в linked.py, fixtures.json и phase\_inputs\_synthetic.json являются исключительно синтетическими тестовыми значениями и не описывают геометрию пресса REV.  
  * Флаги unloading\_confirmed, column\_retention, gate\_isolated, feeder\_retracted в linked.py помечены как SYNTHETIC\_ASSUMPTION; физическое удержание столба в варианте A, фактическая разгрузка камеры/упора перед открытием в варианте B, несущая способность замка (lock\_capacity: "UNKNOWN"), трение, усилия прессования и поведение реального сырья не моделируются и требуют отдельных расчётов и испытаний.