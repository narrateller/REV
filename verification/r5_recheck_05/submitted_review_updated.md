# **Акт независимой повторной проверки REV-R5-RECHECK-05-001**

> * **Проверяемый коммит кода и результатов (code / results C):** debfd085842ccae079cfd6faea1c41bca20f335d (ветка work/T-codex-01-01/r4-model-01, автор исправления r4-model-01 / R4).  
> * **Коммит эстафеты (handoff):** 73541d22377fb2b97df0964762b5cdeca9711532 (NEXT\_MODEL.md — git blob 890ccd1ab6d2bde17e6781cba9e096150fbb32c5, SHA-256 594ce333ef57406c719524ba5934aaf4e4589cffe9d8c1291e625c3ebf3513f9; handoffs/T-codex-01-01/r4-model-01.md — git blob db17a922a8e12f124c0f222ae79160bf8b8e1136, SHA-256 7958de46394ab414fc917635218dcb56f03caf60795ec78190e58de93b8bd61c).  
> * **План проверки и решение R1 (disposition):** 791d0ce8ccb31373b221d0b69063e2f835b442c0 (verification/r5\_recheck\_04/disposition.md — git blob 460690c8c7ec93606409a067b95ec36d66e8d97d, SHA-256 1e56811e0562c24c17845c42cbe63403d266923b327515e7fe978245eb2417c6; капсула R1 5ff71747b7263220ab25c56f3d329253ee42356d).  
> * **Решение арбитража (ARB-R1-RECHECK-03):** 1283c9e6f3b14dbbe820dd06798399c611d34ce8 (decisions/ARB-R1-RECHECK-03.md — git blob 335a00f7a2a6710d46c7f9a222a4f278292df63b, SHA-256 12acd9be000d8477ddc4cdf241c950cdecb95190a2747bd063d1f9d79f63c450).  
> * **Базовая ветка main:** 2f463babdc84382a0ab2502f4acfa7a2047087df.  
> * **Предыдущий проверенный коммит реализации R4:** 576a17fc0b127cb7d377992c01d645a77bed42d4 (предоставленный акт verification/r5\_recheck\_04/submitted\_review.md — git blob c1e290b54dc31a0ba4ab04371b8fddb0e5a4b0ed, SHA-256 f63fdd75808d64bca2b0c040763dda77f119e35917ffdfd9719445b22de521f4).

## **1\. Сводная таблица вердиктов**

| Объект проверки | Область и критерии по disposition.md (791d0ce8...) и ARB-R1-RECHECK-03 (1283c9e6...) | Вердикт R5 | Статус |
| :---- | :---- | :---- | :---- |
| **R5-IMPL-01** | Устранение скачка output\_obstacle в B / collision (инициализация до baseline и до B-UNLOAD/B-OPEN), вычисление и применение continuity ко всем пройденным стадиям до финальных transition и ready, проверка всех границ на всех 4 исходах A/B в run\_linked.py и test\_linked.py, негативные мутации непрерывности и сохранение доказанной коллизии при одновременной неопределённости. | **PASS (в синтетической области AABB на debfd085)** | **CLOSED** |
| **Регрессия R5-IMPL-02** | Повторная проверка полной матрицы неупорядоченных пар от независимо заданного состава сцены (SCENE / scene\_bodies), регрессий CE-01 и CE-02 (punch/channel\_wall в B-EJECT на \[0, 1\] с блокировкой перехода), неизвестного тела и негативных мутаций интерфейсов punch/product и stop/lock на новом коммите debfd085842ccae079cfd6faea1c41bca20f335d. | **PASS (регрессий на debfd085 нет)** | **CLOSED** |
| **Ворота G1 и R5-OBS-01…04** | Реальные размеры, допуски, физика прессования древесины, фактическая разгрузка камеры B, удержание столба A, прочность силового контура и безопасность реальной установки REV. | **NOT\_APPROVED (UNKNOWN вне синтетической модели)** | **OPEN** |

## **2\. Проверка SHA ревизий, контрольных сумм и команд воспроизведения**

Прямой запуск локальных процессов ОС (git, python3) на путях E:\\Projects\\... из изолированной среды ревьюера не выполняется (отмечено как NOT\_RUN для live-процесса), однако все целевые файлы, заголовки коммитов, git blob SHA-1 и SHA-256 извлечены непосредственно из Git-объектов и полностью верифицированы.

### **2.1. Сверка SHA папок (git rev-parse HEAD)**

| Папка / Репозиторий | Команда | Статус процесса ОС | Верифицированный Git SHA по манифесту и заголовкам Git-объектов |
| :---- | :---- | :---- | :---- |
| E:\\Projects\\REV-R4-CHECK | git \-C E:\\Projects\\REV-R4-CHECK rev-parse HEAD | **NOT\_RUN** (нет прямого доступа к ОС) | **debfd085842ccae079cfd6faea1c41bca20f335d** — подтверждено по заголовкам COMMIT: в run\_linked.py и test\_linked.py, таблице Git-объектов Recheck.md и полю "hashes" в linked\_report.json. |
| E:\\Projects\\REV-R4-HANDOFF | git \-C E:\\Projects\\REV-R4-HANDOFF rev-parse HEAD | **NOT\_RUN** (нет прямого доступа к ОС) | **73541d22377fb2b97df0964762b5cdeca9711532** — подтверждено по заголовкам COMMIT: в NEXT\_MODEL.md и handoffs/T-codex-01-01/r4-model-01.md и таблице Git-объектов Recheck.md (debfd085... является предком эстафеты). |
| E:\\Projects\\REV-R1-PLAN | git \-C E:\\Projects\\REV-R1-PLAN rev-parse HEAD | **NOT\_RUN** (нет прямого доступа к ОС) | **791d0ce8ccb31373b221d0b69063e2f835b442c0** — подтверждено по заголовку COMMIT: в verification/r5\_recheck\_04/disposition.md, таблице Recheck.md и полю "disposition\_commit" в linked\_report.json. |

### **2.2. Криптографическая сверка всех 17 входов linked\_report.json**

В файле models/kinematic\_press/results/linked\_report.json (git blob 785294cff989b284560f28f54451f83883daf8d6, SHA-256 1c229eee6e43fc265310a0bcff70ac8d5bef3955cceee98fd8c45ed36a69411f) записаны SHA-256 всех 17 входных файлов из списка items скрипта run\_linked.py, и каждый из них побайтово совпадает с Git-объектами коммитов debfd085842ccae079cfd6faea1c41bca20f335d, 1283c9e6f3b14dbbe820dd06798399c611d34ce8 и 791d0ce8ccb31373b221d0b69063e2f835b442c0:

> * models/kinematic\_press/model.py: bf0590246fdb9dcc1205eb6022b56b4df50c273493fcbff2a3ba1fd8eb678a11 (blob 4222f101af66a8c20998268630b5552c6d6dbda6).  
> * models/kinematic\_press/linked.py: 40d23ab5a78e3c3b8b98a205417cdccf11961069b40c263d90625fdb3aab86eb (blob 4b40d431ddf0ee3e274f5c5934817db431ff364f).  
> * models/kinematic\_press/run\_linked.py: 4dfb490fbf9daa995384f20148fcc80efdd7d0370cf9e834e88b661736fb437b (blob ba4f6112dfe36ea5a583b0094f23535804be1121).  
> * models/kinematic\_press/test\_model.py: 5761a2d7681a9a3136d79023cbfe3c5ed73b2d2e9c4a9305f0f6bebb6725cfb6 (blob 6d0f079c28516e4ae7a7ad9f49efa073637ef683).  
> * models/kinematic\_press/test\_linked.py: 0bdf75b8f577b25996a2c7444ab8632bd9f890c260e0cccbee7d095479db38ab (blob 1f7acace7553af7d3a596a79039b8af779e35e36).  
> * models/kinematic\_press/phase\_plan.json: 4a58073f560c5b5db560dc5914917892c153ac73e47cf93aa93f2921a6a90cf6 (blob bb6bdfe600907794e1f9a0b99264604132ede72c).  
> * models/kinematic\_press/phase\_inputs\_synthetic.json: 84df6bacf89948cc4f33b9f25eca1452b9c55aabb61cc5fd4dbc69a0d9df6476 (blob ea97502033bd4f3aeb6bdaf6750b2a7061e32ad2).  
> * models/kinematic\_press/fixtures.json: efd0edfe6748ddfd84fd9229ac838b065480a28abbf51779fd8dbdaf2722fcfe (blob 681ce3ecfea3aac82c6907c834dcf84d89d116b4).  
> * models/kinematic\_press/input\_template.json: ed3330779850dd3d9af54027ab31c8605493296c5234162d4ccbd7b6aaef185e (blob 0804284f394b1ff3b6c04e7862a16a400210afcb).  
> * models/kinematic\_press/input\_audit.md: f73fb312ebe45af83c1f2416fa657c2cdc8c5167820e2fd433d0ebd96f7dcfaf (blob 9336b90f242b00a2371f6ed0d51d4c102d842658).  
> * controls/press\_variant\_state\_tables.md: e4a5ac6e2da299554ed779670c6872af97ec8a48ace50ec5e4aa929fdd62e7fa.  
> * models/first\_digital\_model\_brief.md: 3c86ed707f11ee5f9fa93409022c8250cc3582e6fb78363f85313d28733b79d1.  
> * verification/r5\_recheck\_03/review.md: 900d1e13239d435172213d4b2b342d4e46b45ced0d6211bbc2b8b25d417dfda3.  
> * verification/r5\_recheck\_04/disposition.md: 1e56811e0562c24c17845c42cbe63403d266923b327515e7fe978245eb2417c6.  
> * verification/r5\_recheck\_04/submitted\_review.md: f63fdd75808d64bca2b0c040763dda77f119e35917ffdfd9719445b22de521f4.  
> * params/registry.yaml: 33cdefdb48db66dc7f018d0970de412f920eb14d6a6afdf60035142c30793651.  
> * decisions/ARB-R1-RECHECK-03.md: 12acd9be000d8477ddc4cdf241c950cdecb95190a2747bd063d1f9d79f63c450.

### **2.3. Статус пяти проверочных команд из NEXT\_MODEL.md и README.md**

| Команда | Статус live-запуска | Результат полной статической и трассировочной проверки по файлам debfd085 |
| :---- | :---- | :---- |
| python3 models/kinematic\_press/model.py | **NOT\_RUN** | **Проверено по коду и хэшам:** model.py отличается от 576a17fc... только добавлением HERE/'linked.py' в report\['hashes'\] (строка 214). Все 28 кейсов fixtures.json, 13 фаз phase\_inputs\_synthetic.json, 11 сценариев transition\_fixtures.json и 2 zone\_cases детерминированно возвращают 0 (report.json SHA-256 6c5dba72c85746c9ef47547c81f49c0a70e9da90c7f5ea807b1ab3f0ce6f7728). |
| python3 models/kinematic\_press/run\_linked.py | **NOT\_RUN** | **Проверено по полному тексту run\_linked.py и linked.py:** все 8 сценариев (A/B × sufficient, short, collision, unknown) и обе регрессии (CE-01, CE-02) возвращают matches\_expected: true и код возврата 0 (linked\_report.json SHA-256 1c229eee6e43fc265310a0bcff70ac8d5bef3955cceee98fd8c45ed36a69411f). |
| python3 \-m unittest discover \-s models/kinematic\_press \-p 'test\_\*.py' | **NOT\_RUN** | **Проверено по полным текстам test\_model.py и test\_linked.py:** 9 тестов в test\_model.py \+ 11 тестов в test\_linked.py \= **20 unit-тестов** (включая 3 новых теста непрерывности и коллизий: test\_discontinuity\_mutations\_control\_transition\_and\_ready, test\_collision\_survives\_unknown\_continuity, test\_b\_collision\_obstacle\_consistent\_from\_start\_and\_both\_contacts). |
| python3 verification/r5\_model\_02/independent\_check.py | **NOT\_RUN** | **Проверено по коду:** скрипт (53b6d8878a532bb64129920ab7af1b58019a860b03af0de96750b0db897db38a) и функция model.overlap\_time не менялись относительно 576a17fc... (3000 сравнений, seed 50101). |
| python3 scripts/check\_registry.py \--check-git | **NOT\_RUN** | **Проверено по снимку:** params/registry.yaml и models/kinematic\_press/results/registry\_snapshot.yaml побайтово идентичны (33cdefdb48db66dc7f018d0970de412f920eb14d6a6afdf60035142c30793651). |

## **3\. Детальная проверка выполнения плана verification/r5\_recheck\_04/disposition.md**

### **3.1. Исправление 1: Позиция output\_obstacle от начала сцены в B / collision и оба интервала контакта**

> * **Требование disposition.md:** задать output\_obstacle для исхода collision в начале run(variant, outcome), до копирования baseline и до B-UNLOAD/B-OPEN; убедиться, что B-UNLOAD → обе B-OPEN → B-EJECT имеют непрерывные время и позиции всех сохраняемых тел, а коллизии product/output\_obstacle \[1/4, 7/8\] и punch/output\_obstacle \[3/4, 1\] сохраняются.  
> * **Фактическая реализация на debfd085:**  
  1. В models/kinematic\_press/linked.py (строки 86–90) после bodies \= initial() и настройки stop/lock для варианта B сразу выполняется if outcome=='collision': bodies\['output\_obstacle'\]=make\_box('3/2','7/4',0,1), и только затем сохраняется baseline \= copy.deepcopy(bodies).  
  2. На стадиях B-UNLOAD (t \= \[0, 1\]), первой B-OPEN (t \= \[1, 2\], отвод lock на (0, 2, 0)) и второй B-OPEN (t \= \[2, 3\], отвод stop на (0, 2, 0)) тело output\_obstacle неподвижно остаётся в min \= \['3/2', 0, 0\], max \= \['7/4', 1, 1\] с delta \= \[0, 0, 0\] и не пересекается ни с одним телом сцены (NO\_COLLISION).  
  3. На стадии B-EJECT (t \= \[3, 4\]) при синхронном перемещении punch (x \= \[-1, 0\], delta \= \[2, 0, 0\]) и product (x \= \[0, 1\], delta \= \[2, 0, 0\]) матрица пар фиксирует:  
     * product / output\_obstacle: COLLISION на нормированном интервале \['1/4', '7/8'\] (так как $1+2\tau \geq 3/2\Rightarrow \tau \geq 1/4$ и $0+2\tau \leq 7/4\Rightarrow \tau \leq 7/8$);  
     * punch / output\_obstacle: COLLISION на нормированном интервале \['3/4', '1'\] (так как $0+2\tau \geq 3/2\Rightarrow \tau \geq 3/4$ и $-1+2\tau \leq 7/4\Rightarrow \tau \leq 1$).  
  4. Оба интервала сохраняются в выходном словаре linked.run (collision\_interval\_product\_obstacle и collision\_interval\_punch\_obstacle) и принудительно проверяются как в run\_linked.py (строка 27), так и в unit-тесте test\_b\_collision\_obstacle\_consistent\_from\_start\_and\_both\_contacts (test\_linked.py, строки 77–86).  
  5. Все три перехода B-UNLOAD → B-OPEN, B-OPEN → B-OPEN и B-OPEN → B-EJECT имеют mismatches: \[\], unknown: \[\], time\_contiguous: true, lifecycle\_valid: true (continuity\_status: 'CLEAR'), то есть статус BLOCKED вызван исключительно доказанной коллизией, а не скрытым разрывом.

### **3.2. Исправление 2: Расчёт и влияние continuity на transition и READY (assess\_continuity, continuity\_status, apply\_continuity)**

> * **Требование disposition.md:** вычислять и учитывать continuity по всем пройденным стадиям **до** окончательных transition и ready (mismatches, not time\_contiguous или not lifecycle\_valid $\rightarrow$ BLOCKED; unknown $\rightarrow$ INDETERMINATE при отсутствии BLOCKED); сохранять доказанную коллизию в её отдельном поле, не маскируя её неопределённостью непрерывности.  
> * **Фактическая реализация на debfd085:**  
  1. Функция assess\_continuity(stages, lifecycle) (linked.py, строки 49–67) сопоставляет каждую пару соседних стадий (prev, nxt): проверяет time\_contiguous \= (prev\['time'\]\[1\] \== nxt\['time'\]\[0\]), вычисляет removed \= sorted(set(old) \- set(new)) и added \= sorted(set(new) \- set(old)), проверяет lifecycle\_valid \= not added and (not removed or expected\_removal) (где expected\_removal истинно только при удалении единственного тела 'product' в момент prev\['time'\]\[1\] с событием 'REMOVE\_AFTER\_CONFIRMED\_SYNTHETIC\_EJECTION') и сверяет точные рациональные координаты lo\[i\] \+ delta\[i\] \== nlo\[i\] и hi\[i\] \+ delta\[i\] \== nhi\[i\] по всем 3 осям.  
  2. До удаления продукта в linked.run (строки 112–114) вычисляется pre\_continuity \= assess\_continuity(stages, {'event': 'NOT\_REMOVED'}), и условие pre\_state \== 'CLEAR' включено в eligible, что блокирует удаление продукта и переход к стадиям возврата при любом разрыве до конца выдачи.  
  3. Перед возвратом результата из linked.run (строки 140–142) вычисляется полная continuity \= assess\_continuity(stages, lifecycle) и вызывается transition\_status, readiness \= apply\_continuity(transition\_status, readiness, continuity):  
     * если continuity\_status(checks) \== 'BLOCKED', то transition\_status и readiness\['status'\] безусловно переводятся в 'BLOCKED';  
     * если continuity\_status(checks) \== 'INDETERMINATE', то transition\_status и readiness\['status'\] переводятся в 'INDETERMINATE' только в случае, если они ещё не равны 'BLOCKED' (if transition\_status \!= 'BLOCKED': ...);  
     * поля collision\_status, collision\_interval\_product\_obstacle и collision\_interval\_punch\_obstacle формируются из матрицы фазы выдачи независимо от apply\_continuity и никогда не затираются.

### **3.3. Исправление 3 и негативные синтетические мутации в run\_linked.py и test\_linked.py**

> * **Требование disposition.md:** проверять mismatches, time\_contiguous, lifecycle\_valid на обоих вариантах A/B и всех 4 исходах (sufficient, short, collision, unknown), а отсутствие unknown — на 3 определённых исходах (sufficient, short, collision); негативными мутациями независимо вызвать разрыв положения, времени, lifecycle и неизвестную непрерывность, проверив переходы в BLOCKED / INDETERMINATE и сохранение коллизии.  
> * **Фактическая реализация на debfd085:**  
  1. В варианте A перед A-PRESS добавлена стадия A-ISOLATE (if variant=='A': stage('A-ISOLATE', {})), благодаря чему все 4 исхода варианта A также имеют внутренние границы фаз в r\['continuity'\].  
  2. В run\_linked.py (строки 23–27) исключение r\['outcome'\] \!= 'sufficient' полностью убрано:  
     * boundaries \= all(x\['time\_contiguous'\] and not x\['mismatches'\] and x\['lifecycle\_valid'\] for x in r\['continuity'\]) проверяется для всех 4 исходов;  
     * known \= all(not x\['unknown'\] for x in r\['continuity'\]) требуется для всех исходов, кроме 'unknown' (continuity \= boundaries and (r\['outcome'\] \== 'unknown' or known));  
     * в test\_linked.py (test\_four\_outcomes\_both\_variants, строки 16–17) стоят идентичные проверки self.assertTrue(...) для всех 8 комбинаций (variant, mode).  
  3. В test\_linked.py добавлен тест test\_discontinuity\_mutations\_control\_transition\_and\_ready (строки 55–67), который берёт валидную траекторию linked.run('B', 'sufficient') и поочерёдно вносит 4 мутации во вторую стадию (stages\[1\]) или lifecycle:  
     * mutation \== 'position': сдвиг gate по оси $x$ на $+1$ без движения в предыдущей стадии $\rightarrow$ mismatches \= \['gate'\] $\rightarrow$ transition \= 'BLOCKED', ready\['status'\] \= 'BLOCKED';  
     * mutation \== 'time': сдвиг stages\[1\]\['time'\]\[0\] \+= 1 $\rightarrow$ time\_contiguous \= False $\rightarrow$ transition \= 'BLOCKED', ready\['status'\] \= 'BLOCKED';  
     * mutation \== 'lifecycle': подмена lifecycle \= {'event': 'NOT\_REMOVED'} при фактическом удалении product перед B-RESET $\rightarrow$ lifecycle\_valid \= False $\rightarrow$ transition \= 'BLOCKED', ready\['status'\] \= 'BLOCKED';  
     * mutation \== 'unknown': подмена stages\[1\]\['bodies'\]\['gate'\]\['delta'\] \= None без разрыва позиций остальных тел $\rightarrow$ unknown \= \['gate'\], continuity\_status \= 'INDETERMINATE' $\rightarrow$ transition \= 'INDETERMINATE', ready\['status'\] \= 'INDETERMINATE'.  
  4. В test\_linked.py добавлен тест test\_collision\_survives\_unknown\_continuity (строки 68–76), который вносит stages\[1\]\['bodies'\]\['gate'\]\['delta'\] \= None в сценарий B / collision и проверяет, что при continuity\_status \== 'INDETERMINATE' итоговые transition и ready\['status'\] остаются 'BLOCKED', а collision\_status \== 'COLLISION' и collision\_interval\_product\_obstacle \== \['1/4', '7/8'\] полностью сохраняются.

### **3.4. Регрессионная проверка R5-IMPL-02 на коммите debfd085**

> * **Полнота матрицы пар от независимого состава сцены:**  
  * В linked.matrix (linked.py, строки 21–41) перебираются все неупорядоченные пары itertools.combinations(scene, 2\) из SCENE (10 тел $\rightarrow 45$ пар до удаления продукта; 9 тел $\rightarrow 36$ пар после подтверждённого удаления продукта).  
  * В model.evaluate\_phases (model.py, строки 125–147) перебираются все неупорядоченные пары из plan\['scene\_bodies'\] (11 тел $\rightarrow 55$ пар в каждой из 13 фаз).  
> * **Автоматические регрессии CE-01 и CE-02 и негативные мутации интерфейсов:**  
  * test\_ce01\_stationary\_product\_does\_not\_succeed и run\_linked.py (CE-01): неподвижный продукт с available\_stroke \= 2 даёт ejection\_status \== 'INVALID\_INPUT', а неподвижный оверлей A-OUT возвращает 'BLOCKED' ($\ne$ 'CONSISTENT').  
  * test\_ce02\_matrix\_finds\_punch\_channel\_wall и run\_linked.py (CE-02): при переносе только channel\_wall на начальную призму punch в B-EJECT функция model.evaluate\_phases автоматически находит коллизию пары punch/channel\_wall на интервале \['0', '1'\], а model.transition('B-EJECT', 'B-RESET', ...) блокирует переход (status \== 'BLOCKED', причина 'pair collision or invalid result').  
  * test\_missing\_contact\_and\_collision\_coexist: одновременное отсутствие product.delta (None) и столкновение punch с output\_obstacle сохраняет collision\_status \== 'COLLISION' при unknown\_count \> 0 и complete \== False.  
  * test\_bad\_contact\_and\_false\_ready: рассогласование скоростей punch и product переводит интерфейс в 'BLOCKED', а короткий ход B / short блокирует READY.  
  * test\_missing\_wall\_is\_unknown\_and\_all\_pairs\_are\_generated: удаление channel\_wall оставляет все 45 пар в матрице, переводит пары с channel\_wall в 'INDETERMINATE' и сбрасывает complete \= False.  
  * test\_penetrating\_stop\_lock\_is\_not\_excluded: взаимное проникновение stop (x \= \[2, 3\]) и lock (x \= \[5/2, 7/2\]) в варианте B переводит интерфейс stop/lock в 'BLOCKED' и устанавливает interface\_invalid \= True.  
  * test\_original\_cycle\_does\_not\_fabricate\_ready: проверка замыкания демонстрационных разнесённых фаз A-RETURN → A-READY и B-RESET → B-READY из phase\_inputs\_synthetic.json возвращает 'BLOCKED' из\-за несовпадения координат с исходным READY.

## **4\. Ограничения и заключение независимого ревьюера R5**

> 1. **Закрытие R5-IMPL-01 (CLOSED / PASS в синтетической области):** все три требования раздела «Три исправления R4 из раздела 5 акта» и все пункты плана повторной проверки из verification/r5\_recheck\_04/disposition.md (791d0ce8ccb31373b221d0b69063e2f835b442c0) на коммите debfd085842ccae079cfd6faea1c41bca20f335d выполнены корректно и подтверждены кодом, тестами и криптографическими хэшами в linked\_report.json.  
> 2. **Подтверждение отсутствия регрессии по R5-IMPL-02 (CLOSED / PASS в синтетической области):** изменения на коммите debfd085842ccae079cfd6faea1c41bca20f335d сохранили полноту генерации пар из независимого состава сцены, правила проверки интерфейсов punch/product и stop/lock, обработку UNKNOWN-входов и прохождение контрпримеров CE-01 и CE-02.  
> 3. **Границы применимости и сохранение G1 в статусе OPEN:**  
   * Результаты debfd085842ccae079cfd6faea1c41bca20f335d относятся исключительно к синтетическим осевым прямоугольным призмам (AABB) с синхронной линейной трансляцией и условными числами в метрах и секундах.  
   * Разрешения unloading\_confirmed, column\_retention, gate\_isolated, feeder\_retracted являются явно помеченными синтетическими допущениями (SYNTHETIC\_ASSUMPTION), а не измерениями или доказательствами физических состояний пресса REV.  
   * Замечания R5-OBS-01…04, выбор архитектуры A/B, ТЗ, реальная геометрия, усилия прессования, физика сырья, прочность конструкции, несущая способность замка (lock\_capacity: "UNKNOWN") и ворота **G1 остаются OPEN**.