"""Revise the T-1.6 functional circuit and guards for scheme A."""
from copy import deepcopy
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DESIGN = ROOT / "design/hydraulics"
CAP = ["cap1_bar <= 3", "cap2_bar <= 3"]
NOSE = ["nose1_seated", "nose2_seated"]
CLEAR = ["nose1_clear", "nose2_clear"]
PRESS = [*NOSE, "gate_closed", "zsf_closed", "mf_locked", "mbt_locked"]
RAPID = ["rg_open_proven", "rt_closed_proven"]


def read(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write(path, data):
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
                    encoding="utf-8", newline="\n")


def circuit_model():
    circuit = read(DESIGN / "T-1.6_circuit.yaml")
    station = read(DESIGN / "station.t25c.yaml")
    e, lines, functions = (circuit[k] for k in ("elements", "lines", "functions"))
    circuit["status"] = "functional_review_hold"
    circuit["sections"]["pre"] = "Подпрессовка и нос башмака"
    circuit["sections"]["water"] = "Вода площадки и охладитель"
    circuit["sections"]["air"] = "Опция масло–воздух"
    circuit["design_limits"].update(
        roof_X_mm=90, transfer_force_kN=35.2514, shoe_working_force_kN=163,
        shoe_at_relief_force_kN=170.972, main_stroke_mm=396,
        cooling_option=station["air_option"],
    )

    def line(name, kind, dn_mm, flow_L_min, pressure_bar, **fields):
        lines[name] = dict(kind=kind, DN_mm=dn_mm, Q_L_min=flow_L_min,
                           p_design_bar=pressure_bar, **fields)

    def component(tag, like, **fields):
        e[tag] = deepcopy(e[like])
        e[tag].update(fields)

    e["M1"].update(manufacturer="ABB", series="M3AA 200MLA 4 / 3GAA202410-BDK",
                   size="30 кВт S1, 400 В, 1481 об/мин, IM B5", source="ABB_T25C")
    e["P1"].update(manufacturer="Bosch Rexroth", series="A4VSO180 /30 DFE1Z",
                   source="DFE1Z", L_max_bar=0.5,
                   note="Внешнее Z от AX через XZD. Нужен проходной привод PX/PXA, предварительно U04 RE 92050; стыковку и массу подтвердить.")
    e["P1"]["ports"]["Z"] = "XZ"
    e["P1"]["port_rated_bar"] = {"Z": 50, "L": 4}
    e["EC1"].update(manufacturer="Bosch Rexroth", series="DFE1Z + VT5041-3X/3", size="DFE1Z",
                    source="DFE1Z", setpoint={"shaft_kW": 33.25, "combined_shaft_kW": 36},
                    control_law="Ограничение T-2.6 33,25 кВт главного насоса / 36 кВт в сумме на переходах. AX заряжается по приоритету; блокировать движение при потере Z.")
    for tag in ("PX", "PXA"):
        e[tag]["series"] = e[tag]["series"].split(",")[0] + ", тандем A4VSO180"
        e[tag]["note"] = "Привод от M1 через A4VSO180. Заряд AX по давлению и запасу момента."
    line("XZ", "pilot", 10, 40, 50)
    component("XZD", "XGFR", type="pressure_reducing", label="Редуцирование AX → Z DFE1Z",
              series="PRFB-CBN, трёхлинейный редуктор", size="T-2A, 35 бар",
              manufacturer="Sun Hydraulics", source="SUN_PRFB", DN_mm=10, Q_L_min=40,
              ports={"P": "X150", "A": "XZ", "T": "DR"}, states={"reduce": ["P>A"], "relief": ["A>T"]},
              default_state="reduce", setpoint={"nominal_bar": 35, "permitted_range_bar": [20, 50]})
    e["XZD"].pop("catalog_max_L_min", None)
    component("PTZ", "PTPA", section="pilot", label="Давление внешнего Z",
              series="Датчик 0…60 бар по ТЗ", size="0…60 бар", source="project",
              p_design_bar=50, p_rated_bar=60, ports={"M": "XZ"}, sensor="dfe_z_bar")
    component("RVZ", "RVA", section="pilot", label="Независимая защита порта Z",
              series="Прямой сброс, уставка по характеристике", size="DN10, 40 л/мин",
              source="project", Q_L_min=40, DN_mm=10, ports={"P": "XZ", "T": "DR"},
              setpoint={"max_inlet_at_design_flow_bar": 50},
              note="До выпуска КД подобрать кромку ≤50 бар при полном притоке; отвод не совмещать со слабым дренажом насоса.")
    del e["RVZ"]["catalog_max_L_min"]
    line("TZ", "tank", 16, 40, 3)
    e["RVZ"]["ports"]["T"] = "TZ"
    e["T0"]["ports"]["EZ"] = "TZ"
    functions["pump_30_kW"] = functions.pop("pump_36_kW")
    functions["external_pilot"] += ["XZD", "PTZ", "RVZ"]

    e["CYM"].update(size="Ø280/200 × 396", stroke_mm=396)
    e["XM1"]["size"] = "ход 0…396 мм"
    e["TF"].update(size="80 л / 55 л", DN_mm=125, Q_L_min=1589,
                   setpoint={"oil_gauge_bar": 0.60, "band_bar": 0.05, "max_bar": 3},
                   note="Эластичный разделитель, двунаправленное регулирование N₂. Газовый расход до 811 л/мин при TF, подтверждение по переходу.")
    e["NG1"].update(size="0,60 ± 0,05 бар", setpoint={"outlet_gauge_bar": 0.60, "band_bar": 0.05},
                    note="Проход и расход регулятора квалифицировать в обоих направлениях.")
    e["ZSF"].update(Q_L_min=1552, note="RE 20478, случай 2, 1600 л/мин при 0,30 бар. A: 16 бар; B: 350 бар. Труба TF→A ID125, целевая длина 0,5 м.")
    e["MF"].update(series="2WRCE NG50–2K7L Double-B WK E, внеш. X/Y", Q_L_min=1589,
                   catalog_flow_at_5bar_L_min=3900, dual_radial_B_ports=True)
    e["MF"]["ports"]["B2"] = "MA"
    e["MF"]["states"]["open"] += ["B2>A"]
    e["MBT"].update(series="2WRCE NG40–1K8L WK E, внеш. X/Y", Q_L_min=760)
    e["MC"].update(series="LC80 A00 + LFA80", Q_L_min=779)
    e["RTF"].update(Q_L_min=1589, p_rated_bar=24,
                    note="Goetze 455 DN65/100 F, 1,9 бар, TET; подтвердить 1589 л/мин HLP46 при 3 бар и противодавлении до 0,2 бар.")
    lines["PF"].update(DN_mm=125, Q_L_min=1589)
    lines["PF"]["wall_mm"] = 4
    lines["PF"]["target_length_m"] = .5
    lines["MA"].update(Q_L_min=1589)
    lines["MB"].update(Q_L_min=779)
    lines["TET"].update(Q_L_min=1589)
    for tag in ("P0", "HP", "MH", "MA", "MB", "MRA", "PF", "D1", "D2", "D3"):
        lines[tag]["construction"] = "Жёсткий стальной тракт, EN 10305-4 или эквивалент по давлению и усталости; сверить мёртвый объём."

    e["VR"].update(Q_L_min=329, catalog_flow_at_5bar_L_min=400)
    e["ALP"].update(manufacturer="Parker", series="EHV 20-330/90-A25GC-200 (10837101125)",
                    size="20 л, газовый объём 17,8 л", source="PARKER_EHV", effective_gas_L=17.8)
    e["LR"].update(label="Дозированная подпитка A быстрых при выталкивании",
                   series="2WRCE NG32–1K1L K, внеш. X/Y", Q_L_min=180)
    e["LRC"].update(label="Отсечка обратного потока из RA", Q_L_min=180)
    e["LRC"]["ports"]["B"] = "RA"
    line("RG0", "work", 28, 222, 315)
    component("RG", "RFA", label="Регенерация быстрых — кромка B→A", source="LC2A",
              series="LC25 + LFA25, пилот 4WE6", size="NG25", DN_mm=25, Q_L_min=222,
              ports={"A": "RB", "B": "RG0", "X": "XR", "Y": "DR"}, states={"open": ["A>B"]})
    component("RGC", "RC", label="Отсечка обратного потока RA→RB", size="T-16A", DN_mm=25,
              series="CXHAXAN", manufacturer="Sun Hydraulics", source="SUN_CXHA",
              Q_L_min=222, ports={"A": "RG0", "B": "RA"}, p_rated_bar=350)
    component("RT", "RFA", label="Открывает слив быстрых при прямом ходе и возврате",
              series="LC25 + LFA25, пилот 4WE6", size="NG25", DN_mm=25, Q_L_min=329,
              ports={"A": "RGT", "B": "TR", "X": "XR", "Y": "DR"}, states={"open": ["A>B"]})
    line("RGT", "tank", 40, 329, 315)
    e["VR"]["ports"]["T"] = "RGT"
    for tag, sense, monitors in (("ZRG", RAPID[0], "RG"), ("ZRT", RAPID[1], "RT")):
        component(tag, "ZMF", section="rapid", label="Подтверждение кромки " + monitors,
                  manufacturer="Проект REV", series="Контроль положения по ТЗ", source="project",
                  sensor=sense, monitors=monitors)
    functions["rapid_drive"] += ["RG", "RGC", "RT", "ZRG", "ZRT"]

    line("LG0", "work", 25, 180, 315)
    line("GH", "pressure", 32, 265, 315)
    component("LG", "PBA", section="lp", label="Дозированная подпитка шибера из ГА НД",
              series="2WRCE NG32–1K1L K, внеш. X/Y",
              ports={"B": "LP", "A": "LG0", "X": "XLG", "Y": "DR"}, Q_L_min=180)
    line("XLG", "pilot", 16, 16, 160)
    component("XGLG", "XGLR", label="Разрешение дозирования LG",
              ports={"1": "X150", "2": "XLG"}, Q_L_min=16)
    component("LGC", "RC", section="lp", label="Отсечка шибера от ГА НД", size="NG25", DN_mm=25,
              Q_L_min=180, ports={"A": "LG0", "B": "GH"})
    component("GHC", "RC", section="gate", label="Отсечка подпитки шибера в HP",
              ports={"A": "HP", "B": "GH"})
    for tag in ("LGC", "GHC"):
        e[tag].update(series="CXHAXAN", size="T-16A", manufacturer="Sun Hydraulics",
                      source="SUN_CXHA", p_rated_bar=350)
    e["VG"]["ports"]["P"] = "GH"
    # Keep the inlet relief downstream of the new isolating check.
    component("RVGH", "RGA", label="Термозащита запертого входа VG",
              series="Sun RBAA, проверить подъём Q–p", size="T-3A, 2 л/мин",
              manufacturer="Sun Hydraulics", source="SUN_RBAA", DN_mm=6, Q_L_min=2,
              ports={"P": "GH", "T": "TR"})
    del e["RVGH"]["catalog_max_L_min"]
    functions["tail_priority"] += ["LG", "LGC", "GHC", "RVGH", "XGLG"]
    e["PRIO"]["note"] = "Порядок T-2.6: eject/return, gate_close, pre_up. LP дозируется на eject, шибер и башмак; давление общего напора может исключить отдельный маршрут."

    e["PCY"].update(label="Цилиндр башмака с носом", note="Силовая геометрия заморожена D-OP-19.")
    e["RVA"]["setpoint"] = {"max_inlet_at_design_flow_bar": 139,
                            "note": "Предел 171 кН из площади Ø125 без зачёта трения; подобрать пружину и характеристику с учётом противодавления."}
    e["PPA"]["note"] = "Ограничить фактическое pA ≤132 бар при опускании (162 кН по полной площади). Задать показание с учётом ошибки PTPA."
    e["XB"]["note"] = "shoe_mm: положительное вниз, ноль вверху; отдельно контролируются посадка и отход самого носа."
    for tag, signal, label in zip(("ZA1", "ZA2", "ZB1", "ZB2"), NOSE + CLEAR,
                                  ("Посадка носа 1", "Посадка носа 2", "Нос освобождён 1", "Нос освобождён 2")):
        e[tag].update(label=label, manufacturer="Schmersal", series="AZ 16-12ZVRK-M16",
                      source="SCHMERSAL", size="НЗ контакт прямого размыкания",
                      sensor=signal, note="Отдельная мишень на носе и независимый ввод; крепление вне силового сечения.")

    e["PC"]["note"] = "Открыто: решение оператора по PC. Установленный резерв 0,55 кВт."
    e["PC"]["label"] = "Циркуляция · открыто решение по PC"
    e["CB"]["setpoint"] = {"crack_bar": None, "max_bar": 8,
                            "requirement": "Выше потерь горячей загрязнённой ветви с учётом допуска; ниже потерь холодной; проверить полный расход с учётом пружины и мощности."}
    e["FT"]["label"] = "Суммарный расход через выбранный охладитель"
    e["TT"].update(label="Температура масла на CP",
                   type="temperature_sensor", ports={"M": "CP"})
    for tag in ("E1", "E2", "FT1", "FT2"):
        e[tag]["section"] = "air"
    for tag in ("WC0", "WC1", "AC0", "AC1"):
        line(tag, "cooling", 50, 180, 8)
    for tag, upstream, downstream, section in (
        ("WCP", "CP", "WC0", "cool"), ("WCF", "WC1", "CF", "cool"),
        ("ACP", "CP", "AC0", "cool"), ("ACF", "AC1", "CF", "cool"),
        ("CAPA", "AC0", "ACM", "air"), ("CAPB", "AOM", "AC1", "air"),
    ):
        component(tag, "CB", section=section, type="manual_isolation",
                  manufacturer="Проект REV", series="Запирается в положении", size="DN50",
                  label="Отсечка " + tag if tag.startswith(("W", "A")) else "Разъём с глухой заглушкой",
                  ports={"P": upstream, "T": downstream}, states={"open": ["P>T"]},
                  default_state="open" if tag.startswith("W") else "closed")
        e[tag].pop("setpoint", None)
    for tag in ("ACM", "AOM"):
        line(tag, "cooling", 50, 180, 8)
    for tag in ("E1", "E2"):
        e[tag]["ports"]["A"] = "ACM"
    for tag in ("FT1", "FT2"):
        e[tag]["ports"]["B"] = "AOM"
    for tag in ("WI", "WIF", "WIV", "WGL", "WO"):
        line(tag, "water", 40, 150, 16)
    component("WBR", "T0", section="water", type="boundary", label="Границы воды площадки",
              size="DN40 PN16", DN_mm=40, Q_L_min=150, p_design_bar=16, p_rated_bar=16,
              ports={"IN": "WI", "OUT": "WO"}, note="150 л/мин, ≤30 °C; условия площадки в docs/site.")
    component("WF", "CD", section="water", type="filter", label="Фильтр воды",
              size="DN40, ≤500 мкм", DN_mm=40, Q_L_min=150, p_design_bar=16, p_rated_bar=16,
              ports={"P": "WI", "T": "WIF"})
    component("WV", "CB", section="water", type="poppet_2_2", label="Вода, НЗ, TT 45/42 °C",
              manufacturer="Danfoss", series="EV220B 25 032U7125 EPDM, 24 V DC",
              source="WATER_VALVE", size="DN25 / проверить DN40", DN_mm=25, Q_L_min=150,
              p_design_bar=16, p_rated_bar=16, ports={"P": "WIF", "T": "WIV"},
              states={"open": ["P>T"]}, default_state="closed",
              setpoint={"open_C": 45, "close_C": 42})
    component("WFT", "FT", section="water", label="Подтверждение расхода воды",
              size="DN40, 150 л/мин", DN_mm=40, Q_L_min=150, p_design_bar=16, p_rated_bar=16,
              ports={"A": "WIV", "B": "WGL"}, sensor="water_flow_ok")
    component("GL", "E1", section="cool", label="Водомасляный охладитель",
              manufacturer="Bowman", series="GL180-1428-3 CuNi 90/10", source="BOWMAN_GL",
              size="2,1 м²; вода 150 л/мин", DN_mm=40, Q_L_min=180, p_design_bar=8, p_rated_bar=12,
              ports={"A": "WC0", "B": "WC1", "WI": "WGL", "WO": "WO"},
              port_rated_bar={"WI": 16, "WO": 16}, states={"through": ["A>B", "WI>WO"]},
              note="Воду площадки ограничить по паспорту аппарата, отдельно подтвердить рабочие условия.")
    component("ZCOOL", "ZKM", section="cool", label="Исправность выбранного режима охлаждения",
              sensor="selected_cooling_ok",
              note="TT/FT общие; вода требует WFT по запросу, воздух требует оба FT1/FT2. Проверить положение отсечек перед пуском.")
    component("ZQF", "ZCOOL", section="fill", type="controller",
              label="Разрешение квалифицированного быстрого хода", sensor="rapid_hydraulics_proven",
              note="Конфигурация по проверенному диапазону температуры, уровню TF, Q(t) и останову. По умолчанию сброшено.")
    functions["prefill_and_deaeration"].append("ZQF")
    functions["conditioning"] += ["GL", "WF", "WBR", "WV", "WFT", "WCP", "WCF",
                                  "ACP", "ACF", "CAPA", "CAPB", "ZCOOL"]
    circuit["open_items"] = {
        "PC": "Решение оператора; сопоставить карты мощности, фактический холодный пуск, CB и расход GL.",
        "Bowman": ["Площадь 2,1 м² и точка воды 150 л/мин.",
                   "Q и Δp масла чистого/загрязнённого аппарата на HLP46 при 42/45/55 °C.",
                   "Холодный пуск, вязкость, скорость в трубках, CuNi 90/10, NH₃, сульфиды.",
                   "Режим воды с EV220B 40 вместо 25, давление и переходы."],
        "TF": "Подтвердить нижнюю границу 0,55 бар и газовый расход; снять Q(t)/p(A) на аварийной отсечке. До доказательства допуска холодный и быстрый ход запрещены.",
        "KD": "Масса обвязки, проходной привод тандема, напорные потери LG/GHC, давления RVA/RVZ, монтаж мишеней и подтверждение PL.",
    }
    circuit["flexible_sections"] = read(HERE / "sources.yaml")["flexible_sections"]
    return circuit


def interlock_model(params):
    logic = read(DESIGN / "T-1.6_interlocks.yaml")
    logic["reference"] = "calc/T-2.9/params/params.t29.yaml"
    mechanics = params["cycle_model"]["mechanics"]
    gate_face_mm = params["chamber"]["approach_stroke_mm"] + mechanics["feed_length_mm"] + mechanics["roof_mm"]
    close_mm = gate_face_mm - mechanics["gate_close_inset_mm"]
    close = f"ram_mm <= {close_mm:g}"
    release = f"ram_mm >= {gate_face_mm:g}"
    logic["position_origin"] = "Пуансон: x=0 в начале цикла. Координаты берутся из модели T-2.6 A; башмак y=0 в верхнем положении."
    logic["geometry"] = dict(gate_face_x_mm=gate_face_mm, gate_close_x_mm=close_mm,
                             installed_main_stroke_mm=396, roof_X_mm=90)
    logic["guard_policy"] = ("Each input is valid and live. For a true 3 bar cap limit, use calibrated independent "
                             "channels and cap*_bar as upper bounds including instrument error. Faults latch; manual reset.")
    service = logic["guard_library"]["service"]
    service.remove("cooler_1_flow_ok")
    service.remove("cooler_2_flow_ok")
    service += ["selected_cooling_ok", "dfe_z_bar >= 20", "dfe_z_bar <= 50"]
    press = logic["guard_library"]["press_chain"]
    press[:] = [*PRESS, "dumps_ready"]
    logic["guard_library"]["fill_chain"][0] = "prefill_bar >= 0.55"
    phases = logic["phases"]
    for tag in ("prefill", "closed_ports", "unload", "gate_open"):
        guards = phases[tag]["conditions"]
        guards[:] = [g for g in guards if not g.startswith("bolt")]
        guards.extend(NOSE)
    phases["closed_ports"]["conditions"].append("zsf_closed")
    logic["faults"]["nose_loss"] = logic["faults"].pop("bolt_loss")
    logic["faults"]["nose_loss"].update(
        sensors=NOSE, actions="Потеря любого подтверждения посадки снимает момент M1, ZUP и силовые разрешения. Башмак удерживается PL1."
    )
    for phase in phases.values():
        if phase["on_loss"].startswith("bolt"):
            phase["on_loss"] = "nose_loss_if_nose_signal_else_stop"
    for fault in logic["faults"].values():
        fault["commands"].update(RG="closed", RT="closed", LG="closed", XGLG="closed")
    logic["transitions"].update(
        pre_down_to_prefill="Два независимых подтверждения посадки носа; шибер закрыт.",
        prefill_to_closed_ports="Торможение пары VR/RG по эталонному профилю. До MP подтвердить останов и затворы ZSF/MF/MBT и плавание RA/RB.",
        tail=f"Начать pre_up при {release} и открытом шибере. Закрыть шибер на возврате при {close}. Разрешение хода башмака защёлкивать до окончания, cap_safe контролировать непрерывно.",
    )
    logic["safety_outputs"]["start_proof"]["sequence"] += (
        " При разгруженном P1 подтвердить давление Z 20…50 бар по PTZ до допуска рабочих фаз.")
    phases["pre_down"]["conditions"] += CAP
    phases["pre_down"]["conditions"].remove("pre_a_bar < 294")
    phases["pre_down"]["conditions"].append("pre_a_bar <= 132")
    phases["pre_up"]["conditions"] += CAP
    phases["pre_up"]["entry_conditions"] = [release, "gate_open", "shoe_mm >= 12", *CAP]
    phases["pre_up"]["movement_window"].update(require_by_deadline=CLEAR,
        behavior="Разрешить отрыв при безопасном давлении ГЦ. Контролировать усилие отрыва по PTPB/PTPA и освобождение носа до 12 мм / 0,25 с. При несовпадении останов.")
    phases["pre_up"]["unlock_pressure"] = {
        "source": "P1", "assist": "LP", "stage": "first_12_mm",
        "minimum_net_equivalent_bar": 35.0, "fallback": "stop_if_no_motion_or_bad_pressure",
        "reference": "calc/T-2.9/unlock.py",
    }
    phases["gate_close"]["conditions"] = [close]
    phases["return"]["conditions"] = ["ram_mm <= 396"]
    phases["feed"]["conditions"] = ["gate_closed", "ram_mm <= 1", "shoe_mm <= 1", *CLEAR, "doser_ready"]
    for tag, conditions in {
        "press": PRESS, "eject": ["gate_open"], "gate_close": [close],
        "pre_down": CAP, "pre_up": CAP, "feed": CLEAR,
    }.items():
        logic["mechanical_permissions"][tag] = {"conditions": conditions, "enforcement": "live_stop_on_loss"}

    phases["prefill"]["commands"].update(RG="open", RT="closed")
    phases["prefill"]["conditions"] += RAPID
    phases["prefill"]["transfer_subphase"] = {
        "ram_start_mm": params["chamber"]["approach_stroke_mm"],
        "ram_end_mm": params["chamber"]["approach_stroke_mm"] + mechanics["roof_mm"],
        "nominal_axial_resistance_kN": 35.2514,
        "roof": "fixed",
    }
    phases["prefill"]["routes"][2:4] = [
        ["CYR1.B", "CYR1.A", ["RG", "RGC"]], ["CYR2.B", "CYR2.A", ["RG", "RGC"]],
    ]
    phases["prefill"]["forbidden_routes"] = [["CYR1.B", "T0.T"]]
    for tag in ("prefill", "eject", "return"):
        phases[tag]["conditions"].append("rapid_hydraulics_proven")
    for tag in ("eject", "return"):
        phases[tag]["commands"]["RT"] = "open"
    phases["eject"]["optional_lp"] = {
        "conditions": ["lp_bar >= 38"], "commands": {"XGLR": "open", "LR": "open"},
        "routes": [[f"ALP.A", f"CYR{i}.A", ["SAL", "LR", "LRC"]] for i in (1, 2)],
    }
    phases["return"].pop("optional_lp")
    for tag, port in (("gate_open", "B"), ("gate_close", "A")):
        phases[tag]["optional_lp"] = {
            "conditions": ["lp_bar >= 38"], "commands": {"LG": "open", "XGLG": "open"},
            "routes": [["ALP.A", f"CYG.{port}", ["SAL", "LG", "LGC", "VG"]]],
        }
    phases["pilot_reserve"] = {
        "reference_pattern": "pilot_reserve", "common_conditions": service,
        "conditions": ["ram_mm <= 1", "shoe_mm <= 1", "gate_closed", *CLEAR],
        "commands": {}, "on_loss": "stop",
        "routes": [["PXA.S", "SAX.A", ["PXA", "XCA", "FX", "SAX"]]],
    }
    patterns = {"pre_down": r"pre_down \d+", "prefill": r"prefill \d+",
                "closed_ports": "regen port compression", "press": r"press \d+",
                "gate_open": r"gate_open \d+", "eject": r"eject \d+"}
    for tag, pattern in patterns.items():
        phases[tag]["reference_pattern"] = pattern
    common = logic["defaults"]["common_routes"]
    common[:] = [path for path in common if all(not end.startswith(("E1.", "E2.")) for end in path[:2])]
    common += [["PC.S", "T0.R", ["PC", "WCP", "GL", "WCF", "FT", "CD"]],
               ["AX.A", "P1.Z", ["SAX", "XZD"]]]
    branches = logic["operating_branches"]
    branches["cool_water"] = {
        "entry_conditions": ["oil_C >= 45"], "continuation_conditions": ["water_flow_ok"],
        "exit_conditions": ["oil_C <= 42"], "commands": {"WV": "open"},
        "routes": [["WBR.IN", "WBR.OUT", ["WF", "WV", "WFT", "GL"]]],
        "on_missing_flow_after_proven_valve_response": "inhibit_cycle_and_stop",
    }
    branches["cool_air"] = {
        "conditions": ["cooler_1_flow_ok", "cooler_2_flow_ok", "cool_flow_ok"],
        "commands": {"WCP": "closed", "WCF": "closed", "ACP": "open", "ACF": "open", "CAPA": "open", "CAPB": "open"},
        "routes": [["PC.S", "T0.R", ["PC", "ACP", "CAPA", f"E{i}", f"FT{i}", "CAPB", "ACF", "FT", "CD"]]
                   for i in (1, 2)],
        "forbidden_routes": [["PC.S", "GL.A"]],
    }
    branches["cool_bypass"] = {"commands": {"CB": "relief"},
                               "routes": [["PC.S", "T0.R", ["PC", "CB", "CD"]]]}
    branches["relief_pre_A"]["conditions"] = ["pre_a_bar >= 132"]
    branches["relief_dfe_Z"] = {"actuation": "mechanical", "commands": {"RVZ": "relief"},
                               "routes": [["P1.Z", "T0.EZ", ["RVZ"]]]}
    branches["relief_gate_inlet"] = {"actuation": "mechanical", "commands": {"RVGH": "relief"},
                                    "routes": [["VG.P", "T0.T", ["RVGH", "F2"]]]}
    logic["cooling_changeover"] = {
        "conditions": ["m1_off_confirmed"], "mode": "manual",
        "sequence": "Остановить PC, отключить и сбросить давление. Для воды закрыть ACP/ACF, закрыть заглушками, открыть WCP/WCF. Для воздуха подключить модуль, закрыть WCP/WCF, открыть ACP/ACF и разъёмы. Проверить выбранный режим и поток перед циклом.",
    }
    logic["cooling_run_proof"] = {
        "water": {"oil_guards": ["cool_flow_ok", "oil_C <= 55"],
                  "on_demand_water_guards": ["water_flow_ok"]},
        "air": {"oil_guards": ["cool_flow_ok", "cooler_1_flow_ok", "cooler_2_flow_ok", "oil_C <= 55"]},
        "common": "Режим подтверждают при включении PC по фиксации отсечек и запертому ключу переключения.",
        "invalid_signal": "inhibit_cycle_and_stop",
    }
    logic["commissioning_conditions"] = {
        "rapid_hydraulics_proven": "До разрешения быстрого хода подтвердить p(A), минимальное p(CYM.A), Q(t), границы уровня/подпора TF при штатном и аварийном остановах; C-SAFE-01.",
        "nose": "На месте установить две раздельные мишени, диагностировать расхождение и переходы обоих каналов на каждом цикле. Уточнить испытанием 12 мм и остаточную нагрузку на нос.",
        "cap_pressure": "Ввести обе оценки верхней границы действительного давления с учётом погрешности. На режимах с открытием MF/MBT и началом pre_up проверить время подтверждения на гидросборке.",
    }
    return logic


if __name__ == "__main__":
    from revision import write_scheme

    write_scheme()
