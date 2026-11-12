# Дозатор/гидростанция — результат к независимому OUTPUT review

База a5d5bad6dd8928045512bca16836fd1d2544b7ca, входной RECHECK c2e96a58d7efd64ea3364b2bcbfb3f0642bbc430. R4 r4-linked-20261111, T-r4-layout-build-01. ASSUMED rev8 зафиксирован до построения на 450e869, точный C результата — в следующем H/эстафете. Новая независимая проверка NOT_RUN; сборка не принята.

## Что изменено и что осталось

Все 14 статических native-проникновений исходного перечня устранены: четыре collar pocket/doser-floor и два doser-wall/hopper-floor стыка на вариант, а также tank/motor A/B. Для каждой из всех 20 исходных пар сохранены native before/after в **том же состоянии/времени**, причины и границы — cad/feed_power/change_plan.json и cad/build/feed_power/changes.json.

**Остались шесть подтверждённых native-пар на прежнем прямом подъёме/спуске дозатора.** В каждом A/B:

- doser_slide / hopper_R;
- doser_slide / hopper_floor_right;
- doser_slide / receiving_rim_right.

Их объёмы не обнулены маркировкой. Native collision = BLOCKED; все 12 положительных интервальных строк (UP/DOWN × три пары × A/B) сохранены в полном потоке. Это воспроизводимый отрицательный случай прежнего пути. Новый исследовательский сервис использует retract по Y → UP → DOWN → return Y; на нём нет положительного перекрытия. Реальная возможность дополнительного хода/расстыковки/подъёма **INDETERMINATE**, поскольку привод, крепёж, масса и оснастка UNKNOWN. Удалять элементы бункера или расширять throat ради старого straight-UP не стали: это потребовало бы нового конструктивного решения. Такой legacy сервис не принят.

Tank/motor разделены геометрически, сохранены ось/размеры мотора и добавлены его торцевые опоры. Tank смещён от ограждения и связан через балки/кронштейны с base_R. Новый support/guide дозатора поддерживается расширенными боковинами, имеет свободный коридор старого cap UP. Рабочие doser_slide/пуансон/шток/цилиндр/заслонка/lock/stop и все прежние config-параметры не менялись. В новых сервисах проверены motor отдельно, powerpack module и tank после подъёма/парковки motor/двух плит.

## Фактические проверки

- **102 unit tests**, шесть наборов, все exit 0: unit_tests.json.
- **638919** всех фаз/пар без пропусков/исключений. **507043** критических интервальных строки: 506934 без positive bound overlap, 97 INDETERMINATE controls, 12 positive legacy UP/DOWN. Все **878** прежних gate/portal target строк без регрессии; новая группа против прежних рамных/силовых/сервисных тел включена в полный перечень. Прежняя геометрия рамы и 58 её native интерфейсов сохранены.
- **22** сервисные последовательности continuous/restored, из них **8** новых FP-последовательностей без положительного перекрытия движущихся тел. Старые два doser-UP сервиса остаются BLOCKED, восстановление координат не исправляет их столкновения.
- **62** новых номинальных интерфейса: positive native contact face area и zero common solid volume, причины в interfaces.json. Силовая способность, радиальная фиксация, крепёж/стенка tank/допуски UNKNOWN. Полный raw classifier не получил новых разрешающих исключений; непредписанные касания остаются INDETERMINATE.
- Actual FCStd/STEP и все прежние canonical QueryVolumes проверены frozen native adapter, модели **A91/B89**, исходные A79/B77 body ID сохранены, 12 новых тел. Повтор native построения воспроизвёл semantic manifests и восемь PNG. **Все 34 прежних Python-модуля без изменений.** Новые cad/feed_power адаптеры/проверки требуют отдельного review.
- Два отдельных verifier после явной генерации дали одинаковый JSON/exit, все проверяемые файлы неизменны по SHA/size/mtime: read_only_repeat.json. Функциональный self-check: сохранён положительный сквозной XY throat; 152 горизонтальных этапа имеют положительную номинальную опорную/направляющую площадь. Точные дробные границы и минимальные площади в verify-1.json; реальное поведение сырья не моделируется.
- Изолированные readonly/fault regressions: regressions/results.json и commands.json. Включены missing/corrupt/stale и удаление остаточной native-пары/before-after/critical evidence с обновлёнными внешними хэшами. Verifier должен отказать без auto repair; fixture вводит/восстанавливает только тестовый harness.

Финальный перечень non-CLEAR: **557 пар** — 6 native penetration, 2 conditional envelope controls, 15 разрешённых прежней synthetic-policy касаний, 534 INDETERMINATE. Условные nominal сопряжения дополнительно обоснованы в interfaces.json, их не переносят в автоматическое разрешение контакта на любой фазе. Все исходные классы/контексты видимы.

Canonical FCStd QueryVolumes не менялись: CylinderRemoval и DoserRemoval на вариант. **DoserRemoval представляет прежний прямой UP и остаётся заблокированным.** Новый L-путь проверен полными posed body matrices и непрерывными линейными неравенствами, а не переименованием/перемещением старого query-volume. Новые нативные именованные query-примитивы в проверенный адаптер не добавлялись; физические сервисные зоны с инструментом/стропами/допусками UNKNOWN. Это предел CAD/сервисного доказательства.

## Воспроизведение

Сначала сохранить проверяемый C и materialize Git LFS; опубликованный verifier запускать до генерации. Пересборку — в отдельной копии:

```bash
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
# Явная генерация отдельно:
/usr/bin/python3 -B cad/feed_power/generate.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B cad/feed_power/verify_output.py
/usr/bin/python3 -B verification/r4_feed_power/regressions.py
```

Генерация пишет outputs/publication manifest; verifier только читает, stdout/exit. Логи/JSON сохранять вне проверяемого каталога. Полный отчёт/виды/FCStd/STEP — cad/build/feed_power/, source/ID — cad/feed_power/. Новый оркестратор — отдельный предмет проверки, прежняя приёмка 34 модулей не утверждает его автоматически.

Весь пресс не принят, READY INDETERMINATE. Реальные параметры UNKNOWN, условные размеры ASSUMED. Архитектура/ТЗ не утверждены; физические испытания NOT_RUN; G1 OPEN.
