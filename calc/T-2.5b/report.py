"""Generate the T-2.5b station, metrics, and Russian engineering documents."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import yaml

import cooler
import mass
import measures


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STATION = ROOT / "design/hydraulics/station.t25b.yaml"
SITE = ROOT / "docs/site/cooling_water_requirements.md"
RESULTS = HERE / "results.json"
GATES = ROOT / "gates.t25b.json"
PARAMS = "calc/T-2.6/params/params.t26a.yaml"
CRITERIA = "ops/criteria/design_criteria.yaml"


def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_yaml(relative):
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8-sig"))


def write_text(path, content):
    path.write_text(content, encoding="utf-8", newline="\n")


def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n")


def fmt(value, places=2):
    return f"{value:.{places}f}".replace(".", ",")


def air_option(baseline, criteria, inputs):
    old = baseline["cooling"]
    width, height, depth = old["per_module_W_H_D_mm"]
    reserve = inputs["air_local_reserve"]
    box_mm = [
        width + 2 * reserve["lateral_clearance_each_mm"],
        depth + 2 * reserve["plenum_each_mm"],
        2 * height + reserve["stack_partition_mm"] + 2 * reserve["end_clearance_each_mm"],
    ]
    limit_mm = criteria["C-ENV-01"]["max_mm"]
    zone_start_mm = [(limit_mm[0] - box_mm[0]) // 2, limit_mm[1] - box_mm[1], 100]
    zone_end_mm = [start + size for start, size in zip(zone_start_mm, box_mm)]
    return {
        "model": old["model"], "module_W_H_D_mm": [width, height, depth],
        "fan_kW": old["fan_kW"], "rated_dirty_kW": old["cooling_dirty_kW"],
        "rated_oil_inlet_C": old["oil_limit_C"], "rated_air_inlet_C": old["air_C"],
        "branch_flow_L_min_range": old["branch_flow_L_min_range"],
        "installation": "Две матрицы одна над другой вдоль боковой панели станции. "
                        "Потоки воздуха разделены, маты извлекаются с сервисной стороны.",
        "reserve_box_XYZ_mm": box_mm, "reserve_lower_XYZ_mm": zone_start_mm,
        "reserve_upper_XYZ_mm": zone_end_mm, "machine_limit_XYZ_mm": limit_mm,
        "fits_outer_box": all(0 <= a < b <= c for a, b, c in zip(zone_start_mm, zone_end_mm, limit_mm)),
        "whole_machine_collision_verified": False,
        "oil_connections": "Два заглушённых отвода CP/CF, разъёмные фланцы, место под кабели двух вентиляторов. "
                           "Подключение воздушной сборки вместо водяной ветви при остановленной машине. "
                           "Сохраняются FT1/FT2 и параллельная гидравлика исходной опции.",
        "base_mass_row": "T25B-AO",
        "source_ids": ["asa", "baseline", "criteria", "t16"],
    }


def water_requirements(cooling, inputs):
    return {
        "boundary": "Два фланца DN40 PN16 W-IN/W-OUT на сервисном краю станции. "
                    "Заказчик обеспечивает подготовку воды, подачу, возврат и регулирование внешнего расхода.",
        "inlet_C": inputs["water_inlet_C"],
        "maximum_temperature_rise_K": inputs["water_max_rise_K"],
        "design_L_min": inputs["water_flow_L_min"],
        "pressure": cooling["water_pressure"],
        "quality": inputs["water_quality_project"],
        "quality_confirmation": "Bowman публикует pH и режим потока. Численные пределы химии и взвеси "
                                "являются проектными до письменного согласования анализа воды с Bowman.",
        "control": {
            "valve": "Danfoss EV220B 25, 032U7125, EPDM NC, катушка 24 V DC",
            "oil_open_C": 45, "oil_close_C": 42, "oil_hard_limit_C": inputs["oil_inlet_C"],
            "interlock": "При запросе охлаждения проверять поток воды после открытия клапана. "
                         "Потерю потока, обрыв TT и перегрев использовать для блокировки новых циклов и штатной остановки. "
                         "Контроль потока масла PC сохраняется при закрытом водяном клапане.",
        },
        "freeze": "При длительной остановке или риске замерзания закрыть подачу, сбросить давление, "
                  "открыть воздухоотводчик и полностью опорожнить трубную сторону и низкие точки.",
        "source_ids": ["bowman_profile", "bowman_manual", "water_valve", "strainer", "water_flowmeter"],
    }


def source_links(sources, ids):
    labels = {
        "bowman_profile": "Bowman GL", "bowman_catalog": "Каталог Bowman",
        "bowman_manual": "Руководство Bowman", "parker_pwo": "Parker PWO",
        "parker_curves": "Кривые Parker", "emmegi": "EMMEGI MG", "ktr": "Каталог KTR",
        "goetze": "Goetze 642", "lp_parker": "Parker EHV",
        "sun": "Sun RPIC", "brook": "Brook Crompton", "siemens": "Siemens D81.1",
        "weg_passport": "Паспорт WEG", "weg_family": "Каталог WEG",
        "htri_tema": "Отчёт HTRI/TEMA", "asa": "Каталог ASA",
    }
    return " · ".join(f"[{labels.get(key, key)}]({sources[key]['url']})" for key in ids)


def site_document(data):
    sources = data["sources"]
    water = data["site_water"]
    pressure, quality = water["pressure"], water["quality"]
    heat = data["cooling"]["heat"]
    controls = water["control"]
    return f"""# Вода охлаждения гидростанции REV, схема A

Проект приложения к КД и договору по D-OP-20. Расчёт относится к трёхходовому кожухотрубному {data['cooling']['selected']['model']} с трубками CuNi 90/10.

## Интерфейс поставки

{water['boundary']} На станции предусматриваются два отсечных крана, сетчатый фильтр, электромагнитный клапан, датчики расхода и температур, отборы давления и слив. Оборудование и вода снаружи фланцев входят в поставку площадки.

## Рабочая точка на фланцах станции

| Параметр | Требование или проектный предел |
|---|---:|
| Температура воды на входе, базовая | ≤{water['inlet_C']} °C |
| Расчётный предел при масле 55 °C и полном расходе | {fmt(heat['water_inlet_max_C'])} °C |
| Расход при открытом клапане | {water['design_L_min']} л/мин, 9 м³/ч |
| Нагрев воды при {fmt(heat['required_kW'])} кВт | {fmt(heat['water_rise_at_required_K'])} K |
| Допустимый нагрев | ≤{water['maximum_temperature_rise_K']} K |
| Перепад W-IN–W-OUT при расчётном расходе | ≥{fmt(pressure['interface_differential_min_bar'], 1)} бар |
| Избыточное давление W-OUT | 0…{fmt(pressure['return_gauge_range_bar'][1], 1)} бар |
| Избыточное давление W-IN | Давление W-OUT + минимум {fmt(pressure['interface_differential_min_bar'], 1)} бар, максимум {fmt(pressure['supply_gauge_max_bar'], 1)} бар, включая выбросы |
| Перепад в чистом аппарате при полном расходе | {fmt(pressure['cooler_clean_dp_bar'], 3)} бар |
| Перепад аппарата, предел для обслуживания | {fmt(pressure['cooler_dirty_dp_limit_bar'])} бар |
| Паспортный максимум рабочего давления воды в аппарате | {data['cooling']['selected']['max_water_working_bar']} бар |

Разность давлений требуется при протоке, совместно с расходом. Подобрать и отрегулировать внешний контур на 150 л/мин с учётом его потерь и изменения сопротивления фильтра. Предел перепада на загрязнённой станции по сумме компонентов {fmt(pressure['interface_dirty_dp_budget_bar'], 3)} бар. При превышении {fmt(pressure['strainer_dirty_dp_limit_bar'])} бар на фильтре очистить сетку. Минимум {fmt(heat['water_min_heat_balance_L_min'], 1)} л/мин следует только из баланса тепла при 10 K. Каталожная точка и требуемая мощность рассчитаны при 150 л/мин. {source_links(sources, ['bowman_profile', 'bowman_catalog', 'bowman_manual', 'strainer'])}

## Качество и контроль воды

| Показатель на W-IN | Требование | Основание |
|---|---:|---|
| pH | {fmt(quality['pH_range'][0], 1)}…{fmt(quality['pH_range'][1], 1)}, цель {fmt(quality['pH_target_range'][0], 1)}…{fmt(quality['pH_target_range'][1], 1)} | Bowman, руководство |
| Общая жёсткость | ≤{quality['hardness_max_mg_L_as_CaCO3']} мг/л в пересчёте на CaCO₃ | Проектный предел |
| Хлориды Cl⁻ | ≤{quality['chlorides_max_mg_L']} мг/л | Проектный предел |
| Взвешенные вещества | ≤{quality['suspended_solids_max_mg_L']} мг/л | Проектный предел |
| Фильтрация на станции | Ячейка ≤{quality['filtration_max_um']} мкм, сетка mesh 40 | Проектное требование к фильтру |
| Электропроводность | ≥{quality['conductivity_min_uS_cm']} мкСм/см | Проектный запас для SM9500 |

Для договора представить анализ технической пресной воды и согласовать с Bowman фактические жёсткость, хлориды, взвесь и применяемые реагенты. В открытом руководстве Bowman приведён pH, численная таблица остальных показателей для GL180 отсутствует. Перед пуском промыть линии площадки, проверить фильтр, полностью заполнить и развоздушить трубную сторону. {source_links(sources, ['bowman_manual', 'water_flowmeter'])}

## Регулирование и остановка

Клапан на входе открывается при {controls['oil_open_C']} °C и закрывается при {controls['oil_close_C']} °C по TT на горячем входе масла из T0 через PC. Предельные 55 °C относятся к этому входу. При запросе охлаждения подтвердить приход воды и контролировать температуру обратки. При отсутствии расхода или перегреве блокировать новые циклы и выполнить штатную остановку. В наладке подтвердить время открытия, перепады, отсутствие гидроударов и фактический расход при чистом и обслуживаемом фильтре.

{water['freeze']} При температуре помещения ниже {quality['freeze_drain_trigger_C']} °C выполнить слив до остывания аппарата либо обеспечить обогреваемое помещение и трубопроводы. После простоя подать свежую воду и удалить воздух. При переключении на воздушную опцию изолировать и осушить водяную ветвь. {source_links(sources, ['bowman_manual', 'water_valve'])}
"""


def report_document(data):
    m, c, a = data["mass"], data["cooling"], data["air_option"]
    h, p = c["heat"], c["oil_pressure"]
    s = data["sources"]
    summary = data["metrics"]
    variant_titles = {
        "with_collar_and_gross_old_front_removal": "Бурт, полное снятие старого литья",
        "with_end_collar": "С торцевым буртом",
        "without_end_collar": "Без торцевого бурта",
    }
    variants = "\n".join(
        f"| {variant_titles[key]} | {fmt(row['t25_corrected_kg'])} | {fmt(row['t25b_kg'])} | "
        f"{fmt(row['missing_to_5000_kg'])} | {fmt(row['missing_to_5080_kg'])} |"
        for key, row in m["machine_A_variants"].items()
    )
    proposal = "\n".join(
        f"| {row['measure']} | {row['status']} | {fmt(row['t25_potential_delta_kg'])} | "
        f"{fmt(-row['credited_saving_kg'] if row['credited_saving_kg'] else 0)} | {row['reason']} |"
        for row in data["measures"]
    )
    alternatives = c["alternatives"]
    comparisons = "\n".join(
        f"| {row['model']} | {fmt(row['dry_kg'])} / "
        f"{('≤' + fmt(row['wet_upper_bound_box_kg'])) if 'wet_upper_bound_box_kg' in row else 'н/д'} | "
        f"{fmt(row['catalogue_heat_kW'])} | {fmt(row['catalogue_delta_K'], 1)} | "
        f"{row['catalogue_oil_flow_L_min']} / {fmt(row['catalogue_water_flow_L_min'], 1)} | {row['material']} | "
        f"{row['finding']} |" for row in alternatives
    )
    selected = c["selected"]
    motor = data["measures"][0]["evidence"]
    tf = data["measures"][1]["evidence"]
    lp = data["measures"][2]["evidence"]
    curve = "\n".join(
        f"| {point['water_inlet_C']} | {fmt(point['dirty_kW'])} |"
        for point in h["curve"] if point["water_inlet_C"] % 5 == 0
    )
    return f"""# T-2.5b · гидростанция схемы A

**STOP по массе.** Расчёт T-2.5b даёт **{fmt(m['machine_A_kg_range'][0])}–{fmt(m['machine_A_kg_range'][1])} кг**. По верхней границе требуется ещё {fmt(m['missing_to_5000_kg'])} кг до 5000 и {fmt(m['missing_to_5080_kg'])} кг до 5080. Три эталонных гейта прошли.

| Вариант T-2.2i, nose_x225 | T-2.5 с ГА, кг | T-2.5b, кг | До 5000, кг | До 5080, кг |
|---|---:|---:|---:|---:|
{variants}

Станция {fmt(m['station_t25_kg'])} → {fmt(m['station_t25b_kg'])} кг. Из исправленной базы один раз сняты воздушные строки 165,4 и 8,0 кг. Взамен добавлено {fmt(m['cooling_additions_kg'])} кг с аппаратом, заполнением, креплением, местными трубами и арматурой, а также подготовкой воздушной опции. Чистая экономия от охлаждения {fmt(m['cooling_net_saving_kg'])} кг. ГА LP заменён по одной строке 63 → 49 кг, плюс 3 кг на стыковку. Поправка +30 кг введена в исходную массу машины один раз. [Ведомость](design/hydraulics/station.t25b.yaml)

## Водомасляное охлаждение

| Аппарат | Сухой / с водой, кг | Каталог, кВт | ΔT, K | Масло / вода, л/мин | Материал теплообмена | Δp и полнота данных |
|---|---:|---:|---:|---:|---|---|
| {selected['model']} | {fmt(selected['dry_kg'])} / {fmt(selected['wet_with_water_kg'])} | {fmt(selected['catalogue_heat_kW'])} | 30 | 180 / 150 | Трубки CuNi 90/10 | Масло {fmt(p['catalogue_cooler_dp_bar'], 3)} бар, вода {fmt(c['water_pressure']['cooler_clean_dp_bar'], 3)} бар по кривым |
{comparisons}

Знак ≤ в мокрой массе обозначает верхнюю оценку по внешнему объёму. Для KTR ΔT на входах восстановлена из теплового баланса при выходе масла 50 °C.

Старый тепловой баланс принят без перерасчёта, номинал 20,01 кВт, неблагоприятный 19,34, независимая оценка 19,8. Требование max(1,25 × 20,01, 25,0) = **{fmt(h['required_kW'], 4)} кВт**. Для GL180 каталожные 45,1 кВт при 60/30 °C приведены к маслу 55 °C на горячем входе из T0 через PC. При воде 30 °C чистый расчёт даёт {fmt(h['clean_kW_at_design'])} кВт. После двух коэффициентов 0,85 получается {fmt(h['method_a_kW'])} кВт, после пересчёта U получается {fmt(h['method_b_kW'])} кВт. Зачтён меньший результат **{fmt(h['dirty_kW'])} кВт**. TEMA-расчёт калибрует U по точке каталога на площади 2,1 м² методом ε–NTU. К 1/U добавлены 0,000350 для воды и 0,000176 м²·К/Вт для масла. Использован меньший из расчётов с противотоком и одним ходом кожуха. На границе {fmt(h['water_inlet_max_C'])} °C достигается Q_req, договорная температура 30 °C. {source_links(s, ['bowman_profile', 'ktr', 'parker_pwo', 'parker_curves', 'emmegi', 'htri_tema'])}

| Вода на входе, °C | Q_dirty при масле 55 °C, кВт |
|---:|---:|
{curve}

Вода площадки 150 л/мин, нагрев {fmt(h['water_rise_at_required_K'])} K при Q_req, перепад на фланцах ≥1,9 бар. Перепад масла по ветви PC {fmt(p['total_dp_bar'], 3)} бар при 180 л/мин против 1,25 бар, расчёт на валу {fmt(p['shaft_required_kW'], 3)} кВт против 0,55. Запас по Δp {fmt(p['limit_dp_bar'] - p['total_dp_bar'], 3)} бар требует подтверждения для точной сборки и HLP46 при наладке. В холодном режиме проверить пуск и существующий CB. Установка сохраняет PC, расход и точки CP/CF. Для воды жёсткость, хлориды и взвесь пока заданы проектными пределами, открытый документ Bowman подтверждает pH. [Требования к воде](docs/site/cooling_water_requirements.md) · {source_links(s, ['bowman_manual'])}

## Меры группы B и проверка

| Мера | Статус | Δ T-2.5, кг | Δ зачтено, кг | Основание |
|---|---|---:|---:|---|
{proposal}

Если применить все оставшиеся оценки T-2.5 к этой ведомости, включая гипотезу по мотору, верхняя масса составит {fmt(m['machine_high_with_remaining_T25_estimates_kg'])} кг. Эта оценка сохраняет 3 кг резерва LP.

TF получает по модели до {fmt(tf['max_gross_TF_inlet_L_min'], 1)} л/мин из поршневой полости через MF. Скрининг пары Goetze при 1,9 бар +10 % даёт {fmt(tf['calculated_HLP46_pair_L_min'], 1)} л/мин при коэффициенте вязкости 0,90 из T-2.5, обратном давлении 0,2 бар. Паспортная точка дана для воды. Штатная строка RTF из T-1.6 содержит 1293 л/мин, её квалификация на поток T-2.6 остаётся открытой. LP даёт {fmt(lp['available_usable_L'], 3)} л против максимального дефицита {fmt(lp['max_deficit_L'], 3)} л. Проверка чувствительности LP в памяти дала {fmt(lp['sensitivity_cycle_s'], 3)} с и RMS {fmt(lp['sensitivity_rms_kW'], 3)} кВт. Объём T0 190 л и подпор TF 0,60 ± 0,05 бар сохранены. У WEG {motor['order_number']} паспортный момент опрокидывания {fmt(motor['pullout_Nm'], 1)} Н·м. Интерфейс IEC 200 FF-350 совпадает по номинальным размерам. Диагностический гейт при 400 В изменял в памяти два поля частоты вращения. Потенциал WEG {fmt(motor['potential_delta_kg'], 0)} кг. {source_links(s, ['goetze', 'lp_parker', 'sun', 'weg_passport', 'weg_family'])}

**Воздушная опция.** Две ASA0567, {fmt(a['rated_dirty_kW'])} кВт при 40/55 °C. Предложен боковой объём {a['reserve_box_XYZ_mm'][0]} × {a['reserve_box_XYZ_mm'][1]} × {a['reserve_box_XYZ_mm'][2]} мм с двумя раздельными воздуховодами. Границы резерва укладываются в C-ENV-01. Доступ, расстояния для обдува и коллизии всей машины требуют сборочной модели. В базе учтено 9 кг на присоединения CP/CF и трассу кабеля. Установлено {fmt(summary['installed_kW'], 3)} кВт с водяным оборудованием и {fmt(summary['installed_with_air_option_kW'], 3)} кВт с опцией, предел 34,2 кВт. {source_links(s, ['asa'])}

**Гейты.** G-PFACE {fmt(data['cycle']['G-PFACE']['value'])} МПа, G-DOSE {data['cycle']['G-DOSE']['value']} мм, G-CYCLE {fmt(summary['cycle_gate_s'], 3)} с и RMS {fmt(summary['rms_kW'], 3)} кВт. Метод reference_model, параметры T-2.6. Приёмка охладителя и компоновки по гейтам цикла не оценивается. [Результаты гейтов](gates.t25b.json)

## Проект записи D-GK

T-2.5b STOP по C-MASS-01. Зафиксировать расчётную водяную ветвь Bowman GL180-1428-3 и ведомость для последующей компоновки, а также зачёт LP по паспорту Parker. Запросить решение оператора по дальнейшему ведению схемы A. Верхняя масса {fmt(m['machine_A_kg_range'][1])} кг превышает оба контрольных уровня. До выпуска КД подтвердить качество воды, перепад PC на сборке, унаследованный сброс TF и место воздушной опции. Решения по силовой части остаются за D-OP-19.
"""


def generate():
    catalogue = read_yaml(HERE / "sources.yaml")
    inputs, sources = catalogue["inputs"], catalogue["sources"]
    baseline = read_yaml(sources["baseline"]["url"])
    t25 = read_json(sources["t25"]["url"])
    sys.path.insert(0, str(ROOT / "ops/gates"))
    from calc_gates import evaluate_cycle, load_yaml, read_criteria

    criteria_bytes = (ROOT / CRITERIA).read_bytes()
    criteria = read_criteria(criteria_bytes)["criteria"]
    gate_data = read_json(GATES)
    assert gate_data["criteria_sha256"] == sha256(criteria_bytes).hexdigest()
    assert Path(gate_data["input"]).as_posix() == PARAMS
    params_path = ROOT / PARAMS
    params = load_yaml(params_path.read_bytes(), params_path)
    cycle = {row["id"]: row for row in gate_data["gates"]}
    assert set(cycle) == {"G-PFACE", "G-DOSE", "G-CYCLE"}
    assert all(row["status"] == "PASS" for row in cycle.values())
    assert cycle["G-CYCLE"]["details"]["method"] == "reference_model"
    assert abs(cycle["G-CYCLE"]["value"] - 5.905) < 1e-8
    assert cycle["G-CYCLE"]["details"]["rms_power_kW"] <= criteria["C-PWR-01"]["max_rms_kW"]

    cooling = cooler.calculate(inputs)
    assert cooling["heat"]["thermal_screen_pass"]
    assert cooling["oil_pressure"]["pass_at_design_point"]
    assert cooling["water_pressure"]["budget_pass"]
    proposals = measures.calculate(
        t25, read_json(sources["t26"]["url"]), inputs, params,
        read_yaml(sources["circuit"]["url"]), evaluate_cycle, criteria, cycle["G-CYCLE"],
    )
    ledger = mass.calculate(
        baseline, t25["machine_mass"], read_json(sources["t25_metrics"]["url"]),
        read_json(sources["t22i"]["url"]), cooling, proposals, inputs, sources,
        criteria["C-MASS-01"]["max_kg"],
    )
    air = air_option(baseline, criteria, inputs)
    water = water_requirements(cooling, inputs)
    with_air_kW = baseline["cooling"]["installed_kW"] + inputs["water_equipment_power_budget_kW"]
    installed_kW = with_air_kW - air["fan_kW"]
    assert with_air_kW <= criteria["C-PWR-01"]["max_installed_kW"]
    heat = cooling["heat"]
    metrics = {
        **{key: ledger[key] for key in (
            "station_t25_kg", "station_t25b_kg", "water_hardware_kg", "cooling_net_saving_kg",
            "credited_measures_kg", "credited_measures", "machine_A_kg_range", "mass_acceptance",
            "missing_to_5000_kg", "missing_to_5080_kg")},
        "status": "PASS" if ledger["mass_acceptance"] else "STOP_MASS",
        "cooler_model": cooling["selected"]["model"],
        "cooler_wet_kg": cooling["selected"]["wet_with_water_kg"],
        "cooling_required_kW": heat["required_kW"], "cooling_dirty_kW": heat["dirty_kW"],
        "water_inlet_design_C": heat["water_inlet_design_C"], "water_inlet_max_C": heat["water_inlet_max_C"],
        "water_flow_L_min": heat["water_flow_design_L_min"],
        "water_dp_bar": cooling["water_pressure"]["cooler_clean_dp_bar"],
        "oil_total_dp_bar": cooling["oil_pressure"]["total_dp_bar"],
        "installed_kW": installed_kW, "installed_with_air_option_kW": with_air_kW,
        "cycle_gate_s": cycle["G-CYCLE"]["value"], "rms_kW": cycle["G-CYCLE"]["details"]["rms_power_kW"],
        "machine_A_variants": ledger["machine_A_variants"],
    }
    compact_cycle = {key: {k: item[k] for k in ("value", "unit", "status")} for key, item in cycle.items()}
    compact_cycle["G-CYCLE"].update(method="reference_model", input=PARAMS, rms_kW=metrics["rms_kW"])
    data = {"task": "T-2.5b", "metrics": metrics, "sources": sources, "mass": ledger, "cooling": cooling,
            "site_water": water, "air_option": air, "measures": proposals, "cycle": compact_cycle}
    hydraulics = baseline["hydraulics"]
    for row in proposals:
        if row["status"] == "зачтено" and row["ledger_ids"] == ["T25-ALP"]:
            evidence = row["evidence"]
            hydraulics["accumulators"]["LP"].update(
                model=evidence["model"], order_number=evidence["order_number"], effective_gas_L=evidence["effective_gas_L"],
                source=sources["lp_parker"]["url"], interface_confirmation="Чертёж кронштейна и стыка SAF32E/G2 до заказа",
            )
    station = {
        "schema_version": 1, "task": data["task"], "status": metrics["status"],
        "mass_acceptance": ledger["mass_acceptance"], "mass_kg": ledger["station_t25b_kg"],
        "credited_reduction_kg": -ledger["station_delta_kg"], "mass_rows": ledger["mass_rows"],
        "base_reconciliation": {key: ledger[key] for key in (
            "station_t25_kg", "removed_rows", "added_rows", "t25_machine_A_corrected_kg_range", "machine_A_variants")},
        "hydraulics": hydraulics, "reservoirs": baseline["reservoirs"],
        "cooling": cooling | {
            "circuit": "T0 → PC → CP → GL180 → CF → FT → CT → CD → T0. CB остаётся. "
                       "TT на входе масла. Сохраняются контроль суммарного расхода и подтверждения работоспособности "
                       "ветвей охлаждения в выбранном режиме. Схему сигналов водяной ветви проверить при наладке.",
            "installed_base_kW": installed_kW, "installed_with_air_option_kW": with_air_kW,
            "installed_water_electrical_reserve_kW": inputs["water_equipment_power_budget_kW"],
        },
        "site_water": water, "air_option": air, "cycle": data["cycle"], "measures": proposals,
        "open_items": baseline["open_items"] + [
            "Подбор поставщика GL180 на фактическое HLP46 (горячий режим и холодный пуск), сверка потерь PC на сборке.",
            "Анализ воды, подтверждение совместимости материалов и режимов Bowman.",
            "Проверка взаимных коллизий и притока воздуха, доступа к извлечению трубного пучка и матов.",
            "Унаследованный RTF с исходной заявкой 1293 л/мин проверить против потока T-2.6.",
        ],
        "sources": sources,
    }

    write_json(RESULTS, data)
    write_json(ROOT / "metrics.json", metrics)
    write_text(STATION, yaml.safe_dump(station, allow_unicode=True, sort_keys=False, width=105))
    write_text(ROOT / "report.md", report_document(data))
    write_text(SITE, site_document(data))
    return data


def verify():
    command = ["-B", "ops/gates/calc_gates.py", "--params", PARAMS, "--criteria", CRITERIA, "--out", GATES.name]
    subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
    data = generate()
    check_paths = (RESULTS, STATION, ROOT / "metrics.json", ROOT / "report.md", SITE)
    first = {path: path.read_bytes() for path in check_paths}
    generate()
    equal = {path.relative_to(ROOT).as_posix(): first[path] == path.read_bytes() for path in check_paths}
    assert all(equal.values())
    report = (ROOT / "report.md").read_text(encoding="utf-8")
    assert "?" not in report and "\ufffd" not in report and "гидростанция" in report
    assert sum(path.stat().st_size for path in HERE.rglob("*") if path.is_file()) <= 5_000_000
    assert not list(HERE.rglob("__pycache__"))
    assert data["air_option"]["fits_outer_box"]
    assert data["cooling"]["heat"]["water_rise_at_clean_design_K"] <= 10
    check = {
        "task": data["task"], "python_version": sys.version.split()[0],
        "gate_command": [sys.executable, *command], "gates": data["cycle"],
        "motor_candidate_diagnostic": {
            key: data["measures"][0]["evidence"][key] for key in (
                "order_number", "gate_method", "gate_status", "cycle_s", "rms_kW", "failed_gate_checks")
        },
        "tests": {
            "baseline_within_0p1_kg_all_three_variants": "PASS",
            "single_removal_each_and_ledger_closed": "PASS",
            "heat_both_methods_and_oil_pc_design": "PASS",
            "site_water_pressure_and_temperature_rise_at_design": "PASS",
            "installed_power_with_air_option": "PASS",
            "air_local_reserve_inside_envelope": "PASS",
            "air_whole_machine_collision_check": "NOT_VERIFIED",
            "bowman_site_chemistry_confirmation": "PENDING",
            "mass_upper_limit_5000_kg": "PASS" if data["mass"]["mass_acceptance"] else "FAIL",
            "report_utf8_no_question_or_replacement_marks": "PASS",
            "calc_size_limit_and_no_temporary_files": "PASS",
        },
        "double_run_identical_bytes": equal,
        "sha256": {str(path.relative_to(ROOT).as_posix()): sha256(path.read_bytes()).hexdigest() for path in check_paths},
    }
    write_json(ROOT / "self_check.json", check)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="Run gate CLI and verify deterministic output")
    if parser.parse_args().verify:
        verify()
    else:
        generate()
