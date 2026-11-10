# Акт независимой повторной проверки `REV-R5-RECHECK-04-001`

* **Проверяемый коммит (code / results SHA):** `576a17fc0b127cb7d377992c01d645a77bed42d4` (ветка `work/T-codex-01-01/r4-model-01`).


* **Коммит эстафеты (handoff SHA):** `66fb9bd1d454d05eb7f32b77b9f442917de9b95c` (`NEXT_MODEL.md` — git blob `cc38230d49ec29aedef5496deae1e518494de884`; `handoffs/T-codex-01-01/r4-model-01.md` — git blob `8a165bd5b0fe934207677d0882bab5899f4a2ed2`).


* **Решение арбитража (`ARB-R1-RECHECK-03`):** `1283c9e6f3b14dbbe820dd06798399c611d34ce8` (`decisions/ARB-R1-RECHECK-03.md` — git blob `335a00f7a2a6710d46c7f9a222a4f278292df63b`, SHA-256 `12acd9be000d8477ddc4cdf241c950cdecb95190a2747bd063d1f9d79f63c450`).


* **Базовая ревизия `main`:** `2f463babdc84382a0ab2502f4acfa7a2047087df`.


* **Предыдущий акт R5 (`REV-R5-RECHECK-03-001`):** `9e12e8bd4f2325ae0e887d3f2e28eaa85c55205f`.


* **Проверенные отчёты и исходники целевого коммита:**
* `models/kinematic_press/results/linked_report.json` — git blob `fbac8116f31b00bc381590dea65d0727f19dd200`, SHA-256 `272f60e8fc30a45f84249340d97f6854ba87def443af3d8c59d7943ab45cdcb9`.


* `models/kinematic_press/results/report.json` — SHA-256 `e668fd31ace669a37ff73d50d6f7027979435c12e2f93b5462107851f50aea0d`.


* `models/kinematic_press/linked.py` — git blob `f7882fda58c5f09d7a06a1e3ae310c36ac466d28`, SHA-256 `a121c30bb465dfb2714454b914ae8182b743a37706f1b5b306f98c5ac889dafb`.


* `models/kinematic_press/run_linked.py` — git blob `eea49ad2c9f3b021ff8468d240d998c9b019c3f5`, SHA-256 `45083d84751c87927da1f6a1f8157373d60f32ade41d0a3cfd13d2111fcdde80`.


* `models/kinematic_press/model.py` — git blob `e376384788437c9bb040bca683ed45ffc441cdc4`, SHA-256 `d40e4806a5c0eed94108a411d0adb680277ebab4ade1c34cfc51315a49bfc00b`.




* **Область и ограничения:** только синтетическая геометрия осевых прямоугольных призм (AABB) с синхронной линейной трансляцией; реальные размеры, усилия, свойства сырья и физическая разгрузка/удержание для REV остаются `UNKNOWN`; ворота `G1` остаются открытыми.



---

## 1. Итоговая сводка и отдельные решения по блокерам

| Идентификатор блокера | Предмет проверки по `ARB-R1-RECHECK-03` | Решение R5 | Статус |
| --- | --- | --- | --- |
| **`R5-IMPL-01`** | Единый параметризованный сценарий связной выдачи `SYN-LINKED-EJECTION` для вариантов `A/B`, геометрический интерфейс `punch/product`, согласованность скалярного хода с геометрией (`CE-01`), непрерывность всех внутренних границ фаз для всех сохраняемых тел, жизненный цикл удаления продукта и проверяемый возврат в `READY`.

 | **`REJECT_WITH_BLOCKER`** | **`OPEN`** |
| **`R5-IMPL-02`** | Построение фазовой матрицы из всех неупорядоченных пар независимо объявленного состава сцены (`scene_bodies` / `SCENE`), разделение `CHECK` и `CONTACT_INTERFACE`, перевод неполной геометрии в `INDETERMINATE` с блокировкой полноты, негативные мутации интерфейсов и автоматическое обнаружение `CE-02` (`punch/channel_wall` в `B-EJECT`) с блокировкой зависимого перехода.

 | **`PASS` (в синтетической области AABB)** | **`CLOSED`** |

* **Общий статус приёмки задачи `T-codex-01-01`:** **`REJECT_WITH_BLOCKER`** (сохраняется один открытый блокер `R5-IMPL-01`; блокер `R5-IMPL-02` снят).



---

## 2. Специальная проверка: разрыв положения `output_obstacle` в сценарии `B / collision` и его допустимость по критерию непрерывности

### 2.1. Фактическая картина в коде и отчёте `linked_report.json`

1. **Начальное состояние и первые три стадии (`t = 0..3 с`):**
* В функции `initial()` (`models/kinematic_press/linked.py`) тело `output_obstacle` создаётся с координатами `min = [0, 20, 0]`, `max = [1, 21, 1]` и нулевым перемещением `delta = [0, 0, 0]`.


* В `run('B', 'collision')` сначала выполняются три стадии без изменения `output_obstacle`: `B-UNLOAD` на интервале `[0, 1]`, первая стадия `B-OPEN` (`lock` смещается на `(0, 2, 0)`) на интервале `[1, 2]` и вторая стадия `B-OPEN` (`stop` смещается на `(0, 2, 0)`) на интервале `[2, 3]`.


* На протяжении всех трёх стадий (`t` от `0` до `3 с`) `output_obstacle` неподвижно находится в `min = [0, 20, 0]`, `max = [1, 21, 1]` с `delta = [0, 0, 0]`.




2. **Мгновенный скачок («телепортация») на стыке `t = 3 с`:**
* После завершения `B-OPEN` (`t = [2, 3]`) и непосредственно перед вызовом `stage('B-EJECT', ...)` (`t = [3, 4]`) в строке 73 `linked.py` выполняется перезапись: `if outcome=='collision': bodies['output_obstacle']=make_box('3/2','7/4',0,1)`.


* В результате в стадии `B-EJECT` (`t = [3, 4]`) тело `output_obstacle` оказывается в `min = ["3/2", 0, 0]`, `max = ["7/4", 1, 1]` при `delta = [0, 0, 0]`.


* В отчёте `linked_report.json` (`B_collision.continuity[2]`) на переходе `from: "B-OPEN", to: "B-EJECT"` прямо зафиксировано нарушение непрерывности: `"mismatches": ["output_obstacle"]` при `"time_contiguous": true` и `"removed": []`.




3. **Маскировка ошибки в `linked.py` и `run_linked.py`:**
* В `linked.py` список `continuity` вычисляется в самом конце функции `run()` (после расчёта `prior_blocked`, `prior_unknown`, `eligible`, `readiness` и `lifecycle`) и **вообще не влияет** ни на `transition`, ни на `ready['status']`.


* В `run_linked.py` (строка 25) и `test_linked.py` (строка 17) проверка отсутствия разрывов `continuity` намеренно отключена для всех исходов, кроме `sufficient`, через условие `(r['outcome'] != 'sufficient' or continuity)`.


* За счёт этого ослабления `B / collision` получает в отчёте `"matches_expected": true`, несмотря на непустой список `"mismatches": ["output_obstacle"]`.





### 2.2. Оценка допустимости по критериям `ARB-R1-RECHECK-03`

**Вердикт по сценарию `B / collision`: НЕДОПУСТИМО (прямое нарушение критериев `ARB-R1-RECHECK-03`).**

Основания из `decisions/ARB-R1-RECHECK-03.md`:

* **Пункт 1 раздела «Исправление R5-IMPL-01»:** *«Участники сцены определены заранее: punch, product, feeder/gate, твёрдые стенки channel/guide/frame; для B — stop/lock. Общая временная база, линейные синхронные движения и все границы соседних фаз заданы явно»*. В `B / collision` начальная сцена `initial_scene` (`t = 0`) и стартовая сцена выдачи `ejection_start` (`t = 3`) противоречат друг другу по положению неподвижного препятствия `output_obstacle`.


* **Пункт 5 раздела «Исправление R5-IMPL-01»:** *«Непрерывность сохраняется для каждого сохраняемого тела и времени всех внутренних фаз/возврата. Удаление/замена product — явное событие жизненного цикла только после подтверждённой выдачи; материал не исчезает из камеры ради совпадения наборов тел»*. Критерий не допускает никаких исключений для «телепортации» твёрдых препятствий между внутренними фазами `B-OPEN` и `B-EJECT`. Единственное разрешённое дискретное изменение состава сцены — явное удаление `product` после подтверждённой полной беспрепятственной выдачи.


* **Раздел «Исправление R5-IMPL-02»:** *«Статическое разнесение можно исключить только при доказанной неподвижности и разнесении конкретных тел. Все такие доказательства пересчитываются после изменения геометрии/движения/фазы»*. Поскольку в `B / collision` препятствие `output_obstacle` подменяется только перед `B-EJECT`, фазовые матрицы `B-UNLOAD` (`[0, 1]`) и обеих стадий `B-OPEN` (`[1, 2]`, `[2, 3]`) проверялись для ложного положения препятствия `y = [20, 21]`, а не для `x = [3/2, 7/4], y = [0, 1]`.


* **Факт блокировки перехода (`transition: "BLOCKED"`) не легализует разрыв:** в сценарии `B / collision` переход `BLOCKED` должен быть следствием исключительно коллизии `product / output_obstacle` на интервале `['1/4', '7/8']` (и `punch / output_obstacle` на `['3/4', '1']`) во время `B-EJECT` при валидной непрерывной предыстории фаз `B-UNLOAD → B-OPEN → B-EJECT`, а не сопровождаться скрытым разрывом геометрии сцены на входе в `B-EJECT`.


* **Геометрическая проверка показывает отсутствие препятствий для честной инициализации при `t = 0`:** в варианте `B` при `t = 0..3` призма `x = [3/2, 7/4], y = [0, 1], z = [0, 1]` строго отделена по оси `x` и от неподвижного `product` (`x = [0, 1]`), и от `punch` (`x = [-1, 0]`), и от закрытого/отводимого `stop` (`x = [2, 3]`), и от `lock` (`x = [3, 4]`). Следовательно, задание `output_obstacle = make_box('3/2', '7/4', 0, 1)` до начала `B-UNLOAD` (`t = 0`) полностью сохраняет `NO_COLLISION` на фазах `B-UNLOAD` и `B-OPEN`, устраняет разрыв на границе `t = 3` и даёт требуемую коллизию `['1/4', '7/8']` в фазе `B-EJECT`.



---

## 3. Детальное решение по `R5-IMPL-01` (`OPEN, REJECT_WITH_BLOCKER`)

### Что выполнено корректно в `R5-IMPL-01`:

* **Единый параметризованный сценарий для `A` и `B`:** в `linked.py` реализована единая функция `run(variant, outcome)` с общей сценой `SCENE` и четырьмя исходами (`sufficient`, `short`, `collision`, `unknown`).


* **Геометрический контракт интерфейса `punch / product`:** функция `contact()` проверяет точное совпадение передней грани пуансона и задней грани изделия (`p1[0] == b0[0]`), равенство векторов линейного перемещения (`pd == bd`) и вхождение положительного заданного участка `patch_yz = [[0, 1], [0, 1]]` в обе грани на всём интервале без глобального отключения `touch_is_collision` для остальных пар.


* **Разделение стадий в варианте `B` и оверлей в варианте `A`:** для `A` выдача связана с `A-PRESS` (`a_out = 'SAME_INTERVAL_AS_A_PRESS'`), а `verify_a_out` проверяет `contact(punch, product)` и положительный ход `product` (`delta_x` больше `0`); для `B` последовательность включает `B-UNLOAD`, раздельный отвод `lock` (`t = [1, 2]`) и `stop` (`t = [2, 3]`) в `B-OPEN`, затем `B-EJECT` (`t = [3, 4]`).


* **Закрытие контрпримера `CE-01`:** в `model.py` скалярная проверка `ejection` сверяет `product_rear` и `available_stroke` с фактической геометрией и движением `bodies[0]`; при неподвижном продукте (`delta = [0, 0, 0]`) и `available_stroke = 2` возвращается `INVALID_INPUT` с ошибкой `'scalar ejection input conflicts with product geometry or motion'`, а при согласованном скалярном ходе без доказательства контакта пуансона возвращается `INDETERMINATE` (вместо прежнего `SUFFICIENT_STROKE`); неподвижный `A-OUT` возвращает `'BLOCKED'`.


* **Жизненный цикл `product` и проверка `READY` в исходе `sufficient`:** удаление изделия (`REMOVE_AFTER_CONFIRMED_SYNTHETIC_EJECTION`) происходит только при `eligible == True` в момент `t = 1` (вариант `A`) или `t = 4` (вариант `B`), после чего выполняются явные стадии возврата `A-RETURN` / `B-RESET`, проверка свободных объёмов запроса (`output`, `loading`), сверка с независимой спецификацией `ready_spec` и проверка смыкания `stop/lock`.



### Причины сохранения блокера `R5-IMPL-01`:

1. **Нарушение непрерывности внутренней границы в `B / collision` (`mismatches: ["output_obstacle"]`):** скачок `output_obstacle` при `t = 3` между `B-OPEN` и `B-EJECT` из `[0, 20, 0]..[1, 21, 1]` в `[3/2, 0, 0]..[7/4, 1, 1]` нарушает пп. 1 и 5 раздела «Исправление R5-IMPL-01» в `ARB-R1-RECHECK-03`.


2. **Игнорирование `continuity` в логике блокировки переходов и `READY` (`linked.py`) и в проверке ожиданий (`run_linked.py`, `test_linked.py`):**
* В `linked.py` поле `continuity` вычисляется после определения `eligible`, `transition` и `ready` и не блокирует переход или готовность при наличии `mismatches`, `not time_contiguous` или `not lifecycle_valid`.


* В `run_linked.py` (строка 25) проверка `continuity` ограничена условием `(r['outcome'] != 'sufficient' or continuity)`, что маскирует разрыв траектории в `B / collision`.





---

## 4. Детальное решение по `R5-IMPL-02` (`CLOSED, PASS`)

Все требования `ARB-R1-RECHECK-03` к построению полной матрицы пар от независимо заданного состава сцены выполнены и верифицированы:

1. **Генерация всех неупорядоченных пар из независимого состава сцены:**
* В `model.py` (`evaluate_phases`) при наличии `plan['scene_bodies']` (11 тел в `phase_plan.json`) автоматически перебираются все $\binom{11}{2} = 55$ неупорядоченных пар в каждой из 13 фаз (`itertools.combinations(scene, 2)`).


* В `linked.py` (`matrix`) из кортежа `SCENE` (10 тел) автоматически перебираются все $\binom{10}{2} = 45$ неупорядоченных пар на каждой стадии до удаления продукта и все $\binom{9}{2} = 36$ пар на стадиях возврата после подтверждённого удаления `product`.




2. **Разделение `CHECK` и `CONTACT_INTERFACE` без необоснованных пропусков:**
* В `linked.py` ни одна пара не отбрасывается без проверки: все пары вне явных интерфейсов (`punch/product` для `A/B` и `stop/lock` для `B`) проходят полную непрерывную проверку `model.check` с политикой `touch_is_collision`.


* Для обоих допустимых интерфейсов в `test_linked.py` присутствуют и проходят негативные мутации: `test_bad_contact_and_false_ready` (нарушение синхронности `punch/product` даёт `'BLOCKED'`) и `test_penetrating_stop_lock_is_not_excluded` (взаимное проникновение `stop` `x = [2, 3]` и `lock` `x = [5/2, 7/2]` даёт `'BLOCKED'` и `interface_invalid = True`).




3. **Обработка `UNKNOWN` / отсутствующей геометрии:**
* При отсутствии тела или координат (`input_template.json` в `evaluate_phases` либо удаление `channel_wall` в `test_missing_wall_is_unknown_and_all_pairs_are_generated`) затронутые пары получают статус `INDETERMINATE`, попадают в `unchecked_pairs` / `unknown`, сбрасывают флаг полноты (`complete = False`) и блокируют разрешение перехода.


* При одновременном наличии доказанной коллизии и неопределённой связи (`test_missing_contact_and_collision_coexist`) статус `COLLISION` сохраняется и не маскируется общей неопределённостью.




4. **Автоматическое обнаружение контрпримера `CE-02`:**
* В `run_linked.py` и `test_linked.py` (`test_ce02_matrix_finds_punch_channel_wall`) при переносе только `channel_wall` на начальную призму `punch` в `B-EJECT` функция `model.evaluate_phases(plan, altered)['B-EJECT']` без ручного вызова `check` обнаруживает коллизию пары `B-EJECT:channel_wall/punch` на всём нормированном интервале `['0', '1']`, а `model.transition('B-EJECT', 'B-RESET', ...)` возвращает `status: "BLOCKED"` по причинам `"pair collision or invalid result"` и `"incompatible boundary: channel_wall"`.





---

## 5. Требования к исправлению для закрытия `R5-IMPL-01`

Для снятия единственного оставшегося блокера `R5-IMPL-01` автору реализации (`r4-model-01`) необходимо внести следующие точечные исправления и перегенерировать `models/kinematic_press/results/linked_report.json`:

1. **Устранить разрыв положения `output_obstacle` в `models/kinematic_press/linked.py`:**
* Перенести установку `if outcome == 'collision': bodies['output_obstacle'] = make_box('3/2', '7/4', 0, 1)` в начало функции `run(variant, outcome)` — **до** сохранения `baseline = copy.deepcopy(bodies)` и **до** запуска стадий `B-UNLOAD` и `B-OPEN`, чтобы неподвижное препятствие находилось в `x = [3/2, 7/4], y = [0, 1], z = [0, 1]` на всём протяжении сценария `t = 0..4` без скачка на стыке `t = 3`.




2. **Включить проверку `continuity` в вычисление статусов в `models/kinematic_press/linked.py`:**
* Вычислять `continuity` по всем пройденным стадиям и учитывать нарушения непрерывности (`mismatches`, `not time_contiguous`, `not lifecycle_valid`) как блокирующий фактор для `transition` (`BLOCKED`) и `ready['status']` (`BLOCKED`), а наличие `unknown` в `continuity` — как основание `INDETERMINATE` (если нет `BLOCKED`).




3. **Убрать маскировку разрывов непрерывности в `models/kinematic_press/run_linked.py` и `models/kinematic_press/test_linked.py`:**
* Проверять отсутствие `mismatches`, `time_contiguous == True` и `lifecycle_valid == True` во всех записях `r['continuity']` для **всех четырёх исходов** (`sufficient`, `short`, `collision`, `unknown`), а отсутствие `unknown` в `r['continuity']` — для всех исходов с определённой геометрией (`sufficient`, `short`, `collision`).