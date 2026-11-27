# T‑2.5. Облегчение гидростанции, круг 2

**STOP по массе.** Выпущена ведомость эталонной станции T‑2.6 схемы A массой **1780,56 кг**. Зачтено **0,00 кг** из требуемых 170 кг. Подпор TF **0,60 ± 0,05 бар**, 80 л геометрически и 55 л масла, азот отделён мембраной. Расчётный запас масла TF 4,78 л. [t26](calc/T-2.6/results.json), [t26_replay](calc/T-2.6/run.py), [decisions](DECISIONS.md).

## База массы

Ведомость карточки 1655,33 + 76,23 = 1731,56 кг. Привод A4VSO и DFE1Z добавляет 19,00 кг к станции и уже входит в машину 4942,65 кг. База машины до силовых поправок с T‑2.6 5018,88 кг. В строку T‑1.6 «ГА обоих контуров» перешли LP 3047174 по 49 кг и прежний пилотный 3047166 по 15 кг. Схема T‑1.6 уже назначала AX 3047170. Приняты LP 63 кг по карточке артикула и AX 31 кг. Обе базы увеличены на +14 и +16 кг, итого **+30,00 кг**. Общая таблица HYDAC для LP показывает 49 кг, поэтому нужен паспорт поставки. SAL/SAX 24,8 кг за пару относятся к коллекторной строке. [legacy_accumulators](calc/T-1.4b/sources.yaml), [ax_lp](https://www.hydac.com.au/media/catalog/brochure/e/n/en30000-6-04-21_accumulatortechnology-productcatalogue.pdf), [modern_accumulators](https://www.hydac.com/download/accumulator-technology-product-catalogue-1000443492-en.pdf), [t26_inventory](calc/T-2.6/inventory.csv), [t21_mass](calc/T-2.1/results.json).

## Привод и охлаждение

У обоих кандидатов алюминиевый корпус, 30 кВт S1 и IE3 при 50 Гц. Неблагоприятный случай T‑2.6 добавляет 15 об/мин скольжения. Момент рассчитан при пике 38,31 кВт. Пределы 5,904 / 6,193 с и 29,987 кВт RMS применены до округления.

| Мотор | об/мин | Скольжение, % | Цикл, с | RMS, кВт | Пик, Н·м | Опрокид., Н·м |
|---|---:|---:|---:|---:|---:|---:|
| Brook | 1475 / 1460 | 1,67 / 2,67 | 5,904687 / 6,196875 | 29,973848 / 29,338384 | 248,0 / 250,6 | 504,4 |
| ABB при 400 В | 1484 / 1469 | 1,07 / 2,07 | 5,902812 / 6,190312 | 29,997149 / 29,380354 | 246,5 / 249,0 | 636,9 |

Brook превышает оба предела времени, ABB превышает номинальный RMS. Для Brook Ø300 / PCD 350 и вал Ø55×110 совпадают с OMEC B5. Колокол сопрягает их с ISO 3019‑2 NG180, посадка Ø160. Каталог Brook подтверждает 207 кг для семейства, публичный артикул 4P указан как B3. Заказные массы B5/B35, вылеты и комплектовочные чертежи открыты. В протоколе ABB 1481 об/мин приведены при 380 В. Сравнение выполнено для 400 В. [brook](https://brookcrompton.com/ukanditaly/wp-content/uploads/2023/11/2022-05_Series_30_Cat_iss1-3.pdf), [brook_mount](https://brookcromptonmotors.com/products/brook-crompton-we3-we4/), [omec](https://omec-poznan.pl/wp-content/uploads/2024/09/30kW_4P_B5-OMT3-IE3-200L-4.pdf), [a4vso](https://rextonhydraulic.com/wp-content/uploads/2024/09/A4VSO-series-1x-and-30-Data-Sheet.pdf), [bell](https://www.mpfiltri.com/product/bell-housing/), [abb](https://library.e.abb.com/public/7950d3d0f6c64994822e519131c69461/M3AA%20200MLA%204%20K%20400V%2050Hz%2030kW%20Ex%20tc.pdf), [abb_family](https://library.e.abb.com/public/7f63595b46d943c99e3875f44b46c545/Moteurs%20Process%20Performance_Catalogue_FR.pdf).

На валу эталона 28,139 / 27,007 кВт в среднем. Тепло по статьям T‑1.6 **20,01 / 19,34 кВт**. При 40 °C воздуха, 55 °C масла и 180 л/мин два ASA0567AA47 дают **26,49 кВт** после двух поправок по 15 % при требовании **26,43 кВт**. Установлено 34,068 кВт, запас вентиляторов 0,132 кВт.

Мера по охлаждению **0 кг**. При той же точке ASA0927 даёт 23,45 кВт, два Parker 058‑8 дают до 25,24 кВт, HYDAC AC‑LN10L до 25,10 кВт по верхней оценке. Более мощные Emmegi HPA Larger и Parker 112‑8 превышают лимит вентиляторов. Также проверены Emmegi HPA Compact, KTR и AKG. Один ASA0927 занимает 1170×1100×664 мм вместо 920×860×543 мм на модуль, оба используют ASA NG40. Parker 058‑8 имеет G2 и глубину 652 мм, HYDAC 10L имеет G1½ и глубину 766 мм. Полная таблица с расходами, допусками и массами в results.json. [thermal_method](calc/T-1.6/heat_balance.py), [asa_ports](https://www.asahydraulik.com/sites/default/files/2021-07/ASA-Standard-Ranges-2019.pdf), [parker_lac](https://www.parker.com/content/dam/Parker-com/Literature/Literature-Files/cz/images/download/Olaer/lac_parker_cz.pdf), [hydac_cooling](https://www.hydac.com.au/media/productattach/e/5/e5814-1-1-08-16_ac-ln_8-14_einzel.pdf&#63;20260209=), [emmegi](https://it.emmegi.group/wp-content/uploads/sites/8/2024/11/HPA-LARGER.pdf), [akg](https://www.akg-turkey.com/fileadmin/user_upload/Brochures/Standardcooler/AKG_T_Oil_Air_Cooling_Systems.pdf), [ktr_cooling](https://www.ktr.com/fileadmin/ktr/media/Tools_Downloads/kataloge/cooling_systems_ktr-kat00ek04.pdf).

## T0 и квалификация мер

По шагам штатной траектории T‑2.6 с моделью стопа минимальный уровень с резервом **166,85 л**. После закрытия TF/BAL, сброса LP и AX и снятия упругого объёма MA/MB верхняя оценка **201,39 л** при LT 205 л. Ход после снятия питания оценён с торможением штатной рампой. Скорости разряда, выбег и волна уровня требуют стенда.

Минимум номинальной заправки по LT 153,15 л, по 30 с деаэрации при общем пути возврата и охладителя 203,44 л, по заглублению условного всаса DN100 205,32 л. Определяет **заглубление всаса**. Верхняя уставка после стопа ограничивает заправку 193,61 л. При принятых условиях диапазон отсутствует. До квалификации в ведомости 190 л для T0 объёмом 252 л. Для A4VSO требуется ≥0,8 бар абс. на S, бюджет потерь 0,223 бар при фланце на высоте дна. Нужны фактические высоты, потери на холодном масле и подтверждение путей деаэрации. При +40 °C прогрев без охладителя до 55 °C занимает 3,9 мин, с загрязнёнными матрицами за 10 мин рост 10,9 К. [interlocks](design/hydraulics/T-1.6_interlocks.yaml), [iso4413](https://www.iso.org/standard/44781.html), [parker_diffuser](https://www.parker.com/content/dam/Parker-com/Literature/EMHFF/HFD_Catalog/HFD_Catalog_Reservoir_Accessories.pdf), [suction_screen](https://govtribe.com/file/government-file/fairbanks-submersible-pump-spec-sheet-dot-pdf), [a4vso](https://rextonhydraulic.com/wp-content/uploads/2024/09/A4VSO-series-1x-and-30-Data-Sheet.pdf).

Эскиз стенок T0 из S235JR даёт 45,5 МПа гидростатически и 127,5 МПа при транспортной огибающей заполненного бака. Дно и крышка 4 мм, четыре ребра 30×3 мм и существующие перегородки. Нагрузки идут в раму, расчётное натяжение стропа 16,1 кН. Для бака как основания нужны жёсткость, опоры и соосность. [tank_structure](https://industry.arcelormittal.com/catalogue/A30/EN), [transport](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/&#63;uri=CELEX%3A02014L0047-20220927), [lifting](https://www.asme.org/codes-standards/find-codes-standards/design-of-below-the-hook-lifting-devices/2020/pdf).

## Меры и масса машины

| Группа | Мера | Δм, кг | Проверка | Риск или условие | Источник |
|:---:|---|---:|---|---|---|
| A | Зачтённые меры | 0,00 | Подтверждённые замены отсутствуют. | — | Ведомость |
| C | Parker PWO B25TH×50 и вода от площадки | -148,99 + m | 79 кВт при ΔT 40 K, 150 л/мин масла | Тепло и обвязка на фактической воде. Для автономного контура добавить насос, охладитель, бак и заполнение. | [pwo](https://hymatik.com/en/pdfdownload/25081), [pwo_selection](https://hymatik.com/da/pdfdownload/25898) |
| B | Brook Crompton JP-DA200LA, заказное IM B5 | -71,00 | 207 кг семейства, фланец IEC 200 | Время цикла, паспорт B5 и колокол. | [brook](https://brookcrompton.com/ukanditaly/wp-content/uploads/2023/11/2022-05_Series_30_Cat_iss1-3.pdf), [brook_mount](https://brookcromptonmotors.com/products/brook-crompton-we3-we4/) |
| C | Интегрированная задняя крышка | -69,64 | Старая геометрия T‑1.6 | Силовая часть заморожена по D‑OP‑19. | [t16](calc/T-1.6/results.json), [decisions](DECISIONS.md) |
| B | ABB M3AA 200MLA 4, альтернативный мотор | -32,00 | 246 кг семейства, цикл при 400 В | RMS. Масса B5/B35 открыта. Вне суммы B. | [abb](https://library.e.abb.com/public/7950d3d0f6c64994822e519131c69461/M3AA%20200MLA%204%20K%20400V%2050Hz%2030kW%20Ex%20tc.pdf), [abb_family](https://library.e.abb.com/public/7f63595b46d943c99e3875f44b46c545/Moteurs%20Process%20Performance_Catalogue_FR.pdf) |
| B | Два Goetze 642 DN65 FKM вместо RTF | -19,06 | Резьбовые DN65 по 8,9 кг. Пересчёт с воды | Сброс HLP46, выходное давление и импульс в TET. | [t16](calc/T-1.6/results.json), [goetze](https://www.goetze-group.com/Series/642/goetze-642-datasheet-en.pdf) |
| B | LP Parker EHV 20-330/90-A25HC-200 | -14,00 | 20 л, 330 бар, G2, 49 кг | 17,8 вместо 18,4 л газа. Проверить цикл, SAF и крепление. | [parker_accumulator](https://www.parker.com/content/dam/Parker-com/Literature/Accumulator---Cooler-Division---Europe/catalogues/accumulator/bladder_accumulator/CADE_EHV_catalogue.pdf), [ax_lp](https://www.hydac.com.au/media/catalog/brochure/e/n/en30000-6-04-21_accumulatortechnology-productcatalogue.pdf) |
| C | Возврат к Parker PV180 FDV | -12,00 | Сравнение насосов по T‑2.1 | Другой регулятор. Нужны цикл и масса обвязки. | [t21_mass](calc/T-2.1/results.json), [decisions](DECISIONS.md) |
| B | Шесть DB30 → Sun RPIC | -11,88 | 125–270 л/мин при номинале до 380 | Внешний слив, противодавление, пик 315 бар. | [t16](calc/T-1.6/results.json), [sun](https://www.sunhydraulics.com/sites/default/files/media_library/tech_resources/Intl_SC2009relief.pdf) |
| B | T0, стенки 3 мм и четыре ребра | -8,92 | Лист, нагрузки и масса | Эскиз, швы, герметичность, опоры, габарит. | [tank_structure](https://industry.arcelormittal.com/catalogue/A30/EN), [lifting](https://www.asme.org/codes-standards/find-codes-standards/design-of-below-the-hook-lifting-devices/2020/pdf) |
| B | T0 как основание, две поперечины | -7,96 | Две RHS и четыре накладки | Опоры, подъём и соосность при листе 3 мм. | [t16](calc/T-1.6/results.json), [bell](https://www.mpfiltri.com/product/bell-housing/) |
| B | Объём T0 и воздушные охладители | 0,00 | Уровень, всас, нагрев, каталоги | Подтвердить всас и деаэрацию на геометрии. | [iso4413](https://www.iso.org/standard/44781.html), [asa_0567](https://asahydraulik.us/es/product/thermal-systemsoilair-coolersstandard-rangesauc-series/asa-0567-230400v-075kw-50hz) |
| B | Общие блоки | н/о | Сверены арматура и порты | Нужны эскиз, потери, масло и масса. Исключить корпуса RPIC. | [t16](calc/T-1.6/results.json), [t26_inventory](calc/T-2.6/inventory.csv) |

Для пары Goetze оценка при 2,09 бар на входе и 0,2 бар на выходе составляет 1544 л/мин. Консервативный сценарий TF по потоку MF T‑2.6 даёт 1589 л/мин. Для 642 производитель требует свободный сброс. У RPIC для суммы надбавки расхода и противодавления остаётся 15–17 бар до 315 бар. **m** в строке PWO — ещё не определённая масса штуцеров, арматуры и воды в аппарате. Уже включено 5,26 кг мокрых магистралей. Подача от площадки оценивается от 37,9 л/мин при нагреве воды на 10 К. [goetze_install](https://www.goetze-group.com/DAM/assembly-instructions/goetze-642-6420-645-6450-442-4420-445-4450-assembly-instruction.pdf), [sun](https://www.sunhydraulics.com/sites/default/files/media_library/tech_resources/Intl_SC2009relief.pdf), [pwo_selection](https://hymatik.com/da/pdfdownload/25898), [water_tube](https://www.rff.de/_uploads/files/produkte/kataloge/rff_Basics-2019_E.pdf).

Суммы по группам, кг **A 0,00**, **B 132,82**, **C до 230,63 − m**. Сценарий C включает старую оценку крышки вне станции. T‑2.2i считает нижнюю границу машины оптимистичной из-за полной замены передней щеки. [t22i_review](ops/reports/T-2.2i/GK_review.md).

| Сценарий | Экономия, кг | Машина по базе карточки, кг | Машина с поправкой ГА, кг |
|---|---:|---:|---:|
| A | 0,00 | 5223,28–5266,63 | 5253,28–5296,63 |
| A+B | 132,82 | 5090,46–5133,81 | 5120,46–5163,81 |
| A+B+C | 363,45 − m | 4859,83–4903,18 + m | 4889,83–4933,18 + m |

## Гейты и проект D‑GK

G‑PFACE **PASS**, 168,89 МПа. G‑DOSE **PASS**, 396 мм. G‑CYCLE FAIL, 8,719 с, справочно по D‑GK‑13 и D‑OP‑16. Эталон 5,904 / 6,193 с, RMS 29,987 кВт. [Гейты](gates.t25.json).

**Проект D‑GK.** Принять ведомость T‑2.5 с TF 80/55 л и 0,60 ± 0,05 бар. Зафиксировать STOP по облегчению. Станция 1780,56 кг, снижение A 0,00 кг. Передать оператору сценарии PWO, PV180 и задней крышки с указанными границами. Сохранить ограничения D‑OP‑09, D‑OP‑16 и D‑OP‑19 до отдельного решения.
