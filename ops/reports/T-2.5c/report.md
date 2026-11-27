# T-2.5c. Квалификация облегчения гидростанции

**STOP_MASS.** Станция 1654,19 кг, зачтено 32,00 кг. Верхняя масса схемы A 5170,25 кг, до 5000 кг не хватает 170,25 кг. D-OP-21 оставляет предел 5000 кг. Дальнейший пересчёт силовой части зависит от испытания сырья по D-OP-19.

## Ведомость и масса машины

Сумма исходных строк 1686,19 кг. В ведомости изменена строка T25-M1. Массу машины рассчитали вычитанием зачтённой экономии из каждого варианта T-2.2i в T-2.5b. Сборки колокола и муфты учтены в T16-06, Parker LP учтён в базе T-2.5b. [Ведомость T-2.5c](design/hydraulics/station.t25c.yaml), [массы базы](ops/reports/T-2.5b/metrics.json)

| Вариант схемы A | База, кг | Итог, кг | До 5000, кг | До 5080, кг | Все потенциалы T-2.5b, кг | Все меры с ABB, кг |
|---|---:|---:|---:|---:|---:|---:|
| С буртом и полным вычетом старого переднего узла | 5158,90 | 5126,90 | 126,90 | 46,90 | 5040,08 | 5079,08 |
| Без торцевого бурта | 5167,80 | 5135,80 | 135,80 | 55,80 | 5048,98 | 5087,98 |
| С торцевым буртом | 5202,25 | 5170,25 | 170,25 | 90,25 | 5083,44 | 5122,44 |

Сумма исходных потенциалов 118,82 кг включает 71 кг для мотора из T-2.5b. С паспортной экономией ABB и теми же остальными потенциалами получается 79,82 кг. Оба столбца со всеми мерами условные.

| Мера | Решение | Зачтённая Δм, кг | Потенциальная Δм T-2.5b, кг | Основание |
|---|---|---:|---:|---|
| Мотор Al IM B5 | зачтено | -32,00 | -71,00 | [Лист ABB](https://www.electricautomationnetwork.com/PDF/PIM/ABB/EN_3GAA202410-BDK.pdf), [G-CYCLE](gates.t25c.json) |
| Предохранитель TF | не зачтено | 0,00 | -19,06 | [Goetze 642](https://www.goetze-group.com/Series/642/goetze-642-datasheet-en.pdf), [Goetze 455](https://www.goetze-group.com/Series/455/goetze-455-datasheet-en.pdf), [расчёт жидкости](https://www.leser.com/-/media/files/engineering/leser_engineering.pdf) |
| Шесть DB30 → картриджи | не зачтено | 0,00 | -11,88 | [Sun RPIC](https://hydnet.se/wp-content/uploads/RPIC.pdf), [Parker R4V](https://www.parker.com/content/dam/Parker-com/Literature/Hydraulic-Valve-Division/hydraulicvalve/Service-Installation/Denison-Service-Literature---new/S3-ML2400-A---R4V.pdf), [RE 25802](https://device.report/m/243f441d86e129325758e54161c0343432c0f720809b6edae1b2fdf9d511a710) |
| Стенки T0 3 мм и рёбра | не зачтено | 0,00 | -8,92 | [NASA SP-160](https://ntrs.nasa.gov/api/citations/19700009156/downloads/19700009156.pdf), [расчёт T-2.5](calc/T-2.5/results.json) |
| T0 как основание | не зачтено | 0,00 | -7,96 | [Входы расчёта](calc/T-2.5c/sources.yaml), [допуски муфт SGE](https://www.mpfiltri.com/wp-content/uploads/2025/10/CAT_PT_EN-1.pdf) |

## Мотор и цикл

| Мотор, артикул и монтаж | Масса, кг | n ном., об/мин | M ном., Н·м | M опр., Н·м | η, % | I при 400 В, А |
|---|---:|---:|---:|---:|---:|---:|
| OMEC OMT3-IE3-200L-4 IM B5 | 278 | 1480 | 194,00 | 446,2 | 93,6 | 53,80 |
| ABB M3AA 200MLA 4 3GAA202410-BDK, IM B5 / IM3001 | 246 | 1481 | 193,42 | 618,9 | 93,6 | 55,10 |
| WEG W21 Aluminium Multimounting 12840024, B5T | 208 | 1475 | 194,00 | 659,6 | 93,6 | 57,10 |
| Brook Crompton JP-DA200LA-D 200J910402, IM B5 | 207 (семейство) | 1475 | 194,00 | 504,4 | 93,6 | 53,30 |
| Omega 3MAS 200L4 3M0SA3E-20LA40CL0, IM B35 | 223 | — | 194,30 | 621,8 | 93,6 | 53,18 |

ABB 30 кВт S1, IE3, 400 В 50 Гц, 4 полюса, Al. FF350 Ø400/350/300 и вал Ø55×110 с шпонкой 16 мм подходят к колоколу и полумуфте IEC 200. Паспортные 1481 об/мин допускают эталон с 1480 об/мин по карточке. В КД проверить зазор к клеммной коробке и настройку тепловой защиты по 55,1 А. [Лист ABB](https://www.electricautomationnetwork.com/PDF/PIM/ABB/EN_3GAA202410-BDK.pdf), [Каталожные таблицы](calc/T-2.5c/sources.yaml), [колокол](https://www.mpfiltri.com/FilesProdotti/rl1vm4_LMC-LDCEN.pdf)

G-PFACE 168,89 МПа, G-DOSE 396 мм, G-CYCLE 5,905 с и 29,987 кВт RMS. Все три PASS на params.t26a.yaml, метод цикла `reference_model`. WEG 1475 об/мин дал 5,90625 с и 30,075 кВт RMS в прогоне ГК T-2.5b. Для Brook отсутствует масса артикула B5. У Omega 1500 об/мин — синхронная частота, а геометрия установки лап B35 требует проверки. [Прогон](gates.t25c.json), [WEG](https://www.cenov-distribution.fr/wp-content/uploads/2025/05/weg_12840024_allDocuments.pdf), [прогон ГК](ops/reports/T-2.5b/gates.GK.weg1475.json), [Brook](https://brookcrompton.com/ukanditaly/wp-content/uploads/2023/11/2022-05_Series_30_Cat_iss1-3.pdf), [артикул B5](https://brookcromptonmotors.com/products/brook-crompton-we3-we4/), [Omega](https://omegamotor.com.tr/en/product/detail/836)

## TF, DB и бак

**TF.** При 1,9 бар +10 % и 0,2 бар на сливе, HLP46 580 мм²/с при 0 °C, пара 642 DN65 даёт 1507 л/мин, тройка 2261 л/мин, штатный 455 DN65/100 1714 л/мин. Требуется 1588,64 л/мин. Три 851 DN50 дают 1265 л/мин. Это оценки по перепаду и вязкости. Три фланцевых 642 весят 36 кг без коллектора и опор. У 455 исходная заявка 1293 л/мин. Допуск противодавления до 30 % уставки относится к 455 с металлическим сильфоном. Для квалификации нужны точное исполнение и характеристика TET. У LESER открыты исполнение и обвязка при 1,9 бар. Подпор 0,60 ± 0,05 бар, расчётное давление TF 3 бар. [LESER, формулы жидкости и Kv](https://www.leser.com/-/media/files/engineering/leser_engineering.pdf), [Паспорт Shell HLP46](calc/T-2.5c/sources.yaml), [Goetze 642](https://www.goetze-group.com/Series/642/goetze-642-datasheet-en.pdf), [Goetze 851](https://www.goetze-group.com/Series/851/goetze-851-datasheet-en.pdf), [монтаж 455](https://www.goetze-group.com/DAM/assembly-instructions/goetze-455-355-255-assembly-instruction.pdf), [LESER 441](https://www.leser.com/-/media/files/catalogue/english/leser-safety-relief-valve-high_performance_extended_catalog_en_07_2016.pdf)

**DB.** У Sun RPIC 350 бар, 380 л/мин и T-16A. Противодавление на выпуске прибавляется к уставке 1:1. Бюджет роста давления на расходе при проектном противодавлении 5–12 бар. Кривая Parker R4V06 с Y1 относится к корпусному исполнению. Rexroth DBC30-2-5X/350Y имеет внешнюю линию Y и чертёж полости. Для обоих открыты P(Q) установленного картриджа и масса блока. Испытание пиков ≤315 бар остаётся задачей образца по D-OP-11. [Sun RPIC](https://hydnet.se/wp-content/uploads/RPIC.pdf), [кривые Parker](https://www.parker.com/content/dam/Parker-com/Literature/Industrial-Systems-Division-Europe/Catalogues/Industrial-Valves-UK/04/R4V-R6V-TUEV-UK.pdf), [RE 25802](https://device.report/m/243f441d86e129325758e54161c0343432c0f720809b6edae1b2fdf9d511a710)

**T0.** Для стенок 3 мм получено 34,3 МПа в статике и 127,5 МПа с прогибом 6,74 мм в расчётном сценарии залитого бака при перевозке 0,8g вперёд и 0,5g поперёк. Сухие частоты рассчитаны для шарнирных пластин. Проверка отстройки от 24,7 и 49,3 Гц требует залитой сборки. Открыты швы, проушины, опоры, компоновка рёбер, прогиб плиты под приводом и допуск соосности точной муфты. Ведомость содержит бак 190 л, 900×700×400 мм, стенки 4 мм и самостоятельную раму. [Leissa, NASA SP-160](https://ntrs.nasa.gov/api/citations/19700009156/downloads/19700009156.pdf), [Входы перевозки](calc/T-2.5c/sources.yaml), [MP Filtri SGE](https://www.mpfiltri.com/wp-content/uploads/2025/10/CAT_PT_EN-1.pdf)

## Открытые пункты КД по охлаждению

Bowman GL180-1428-3. При 180 л/мин, 42–45 °C и Δp 1,33–1,36 бар вал PC требует 0,554–0,567 кВт при принятом КПД 0,72. CB 1,5 бар даёт 0,625 кВт при том же расходе ещё до запаса на открытие. Для 0,55 кВт расчётная граница 1,32 бар, проектная 1,25 бар. Нужны карта PC и измерение Δp и расхода по ветвям при холодном пуске и регулировании. Установленная мощность 32,603 кВт, с воздушной опцией 34,103 кВт при пределе 34,2 кВт. [разбор T-2.5b](ops/reports/T-2.5b/GK_review.md), [расчётные входы PC](calc/T-2.5b/sources.yaml)

**Запрос Bowman для КД.** Просим подтвердить наружную площадь теплообмена 2,1 м², тепловую мощность и Δp воды при 150 л/мин и до 30 °C, тепловую мощность и Δp масла при 180 л/мин HLP46 и 42, 45 и 55 °C, рекомендуемую минимальную температуру пуска и диапазон скорости воды. Для пучка CuNi 90/10 просим предельные pH, хлориды, NH₃ и сульфиды с единицами и условиями отбора пробы. [Профиль GL](https://ej-bowman.com/wp-content/uploads/2025/01/GL-Series-Product-Profile-4.pdf), [руководство Bowman](https://ej-bowman.com/wp-content/uploads/2025/01/HOC-IOMG-Issue-E-English-5.pdf)

## Проект строки D-GK

> T-2.5c STOP_MASS. ABB 3GAA202410-BDK IM B5 −32 кг. Станция 1654,19 кг, машина A 5126,90–5170,25 кг. До 5000 кг по верхней границе 170,25 кг. G-CYCLE 5,905 с и RMS 29,987 кВт, reference_model. TF, DB и меры по баку остаются открытыми. Подтверждение TF на 1588,64 л/мин и ветви PC остаётся в КД. Вопрос массы возвращается к результату испытания сырья по D-OP-19 и D-OP-21.
