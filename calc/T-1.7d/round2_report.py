"""Write the short T-1.7d report from the machine-readable evidence."""
from study import FEA, ROOT, read_json
from mass_budget import plate_kg


def fmt(value, places=3):
    if value is None:
        return '—'
    return f'{round(value,places)+0.:.{places}f}'.replace('.', ',')


def row(data, name):
    return next(r for r in data['comparison'] if r.get('fea_file','').endswith(name+'_slice_0.json'))


def design_levers(data):
    t=data['working_trial']['geometric_FEA_inputs']
    w=t['wing_mm']
    rib_kg=plate_kg(t['thickness_mm'],t['travel_mm'],w)-plate_kg(t['thickness_mm'],t['travel_mm'])
    def compare(label, first, last, risk):
        a,b=(row(data, ident) for ident in (first,last))
        v=lambda key: b['FKM'][key]-a['FKM'][key]
        return (f"| {label} | {fmt(v('static_factor'))} / {fmt(v('fatigue_factor'))} | "
                f"{b['delta_main_mm']-a['delta_main_mm']:+d} | {fmt(b['no_ribs_mass_kg']-a['no_ribs_mass_kg'],2)} | "
                f"{fmt(b['gate_cycle_screen_s']-a['gate_cycle_screen_s'])} | {risk} |")
    rows=[
        compare('а · 42 → 50 мм, ход 104','r2_42_104_14_15','r2_50_104_14_15','Пик 564 → 508 МПа и рост хода ГЦ'),
        compare('б · ход 100 → 105 мм, плита 44','r2_44_100_14_15','r2_44_105_14_15','Пик 545 → 541 МПа. Выигрыш ширины насыщается'),
        f'| в · боковые рёбра {fmt(w,0)} мм | Переход проверен в 3D | 0 | {fmt(rib_kg,2)} | <0,001 | Карманы по всему ходу. Отдельный вклад в глобальный запас открыт |',
        compare('г · сбег 14×0,15 → 9×0,07','r2_44_105_14_15','r2_44_105_9_7','Пик 541 → 512 МПа. Упрочнение требует проверки пары'),
        '| д · 42CrMo4 вместо 34CrNiMo6 | ×0,813 статика, ×0,908 амплитуда FKM | 0 | ≈0 | ≈0 | Меньше гарантированные Rp0,2 и Rm |',
    ]
    return '\n'.join(rows)


def cycle_table(data):
    names=(
        ('reference_speed_0p6','0,6 м/с, без подпитки шибера'),
        ('speed_to_1','Скорость до 1,0 м/с'),
        ('acceleration_to_40','Разгон и торможение 40 м/с²'),
        ('lp_close_220','Подпитка закрытия, предел ГА 220 л/мин'),
        ('lp_close_180','Подпитка закрытия, предел ГА 180 л/мин'),
        ('gate_pump_priority','Закрытие с первым приоритетом насоса'),
        ('earlier_close_screen','Команда при x ≤ 200 мм'),
        ('gate_loss_sensitivity','Потери в подаче и сливе шибера по 5 бар'),
        ('max_residual_product','Остаточное усилие 201 кН'),
    )
    rows=[]
    for key,label in names:
        v=data['cycle_levers'][key]
        rows.append(f"| {label} | {fmt(v['gate_cycle_s'])} | {fmt(v.get('delta_gate_from_baseline_s',0.))} | "
                    f"{fmt(v['gate_rms_kW'])} | {fmt(v['pessimistic']['cycle_s'])} |")
    return '\n'.join(rows)


def fea_table(data):
    run=data['fea']['r2_aligned_node54']
    labels={0:7.5,1:5.8,2:4.6,3:3.6,4:3.0,5:2.6}
    rows=[]
    for level,h in labels.items():
        name=f'r2_aligned_node54_{level}.json'
        if name not in run['files']:
            rows.append(f'| {fmt(h,1)} | — | — | — | — | — | — |')
            continue
        r=read_json(FEA/name)
        R,S,C=r['regions'],r['loads']['static'],r['clearance']
        rows.append(f"| {fmt(h,1)} | {fmt(R['blade']['static_factor'])} | {fmt(R['blade']['fatigue_factor'])} | "
                    f"{fmt(S['blade_seat']['peak_MPa'],1)} / {fmt(S['seat_cast']['peak_MPa'],1)} | "
                    f"{fmt(R['blade_step']['fatigue_factor'])} | {fmt(R['cast_R20']['fatigue_factor'])} | {fmt(C['combined_screen_mm'])} |")
    return '\n'.join(rows)


def write_report(data):
    w=data['working_trial']
    g,m,cy,h,proof=(w['geometry'],w['mass'],w['cycle'],w['hydraulic'],data['structural'])
    vol=data['fea']['r2_aligned_node54']
    finest=vol['finest']
    blade=finest['regions']['blade']
    ring=finest['regions']['cast_R20']
    end=finest['regions']['cast']
    hotspot_cross_mm,hotspot_height_mm,hotspot_axial_mm=blade['fatigue_xyz_mm']
    depth=w['geometric_FEA_inputs']['thickness_mm']-hotspot_axial_mm
    hotspot_location='под нижней полосой' if hotspot_height_mm<=-30.5 else 'на перемычке в проекции окна'
    lower=finest['regions']['blade_lower_depth']
    layer=min(lower,key=lambda d:d['fatigue_factor'])
    transition=next(d for d in lower if d['depth_mm']==[6,9])
    deeper=min((d for d in lower if d['depth_mm'][0]>=9),key=lambda d:d['fatigue_factor'])
    surface=finest['regions']['seat_upper_depth'][0]
    delta=vol['convergence_max']
    representative=[7.5,5.8,4.6,3.6,3.0,2.6]
    sizes='/'.join(fmt(representative[i],1) for i in vol.get('convergence_levels',[]))
    if delta is None:
        convergence='Для проверки сходимости нужны три завершённых сетки.'
    else:
        convergence=f'На трёх сетках {sizes} мм максимальное относительное изменение {fmt(delta*100,1)} % при требовании <5 %.'
        metric=max(vol['convergence_by_metric'],key=vol['convergence_by_metric'].get)
        _, location, quantity, *_=metric.split('.')
        if metric.startswith('loads'):
            load='при 1,70 МН' if location=='fatigue' else 'при 1,94 МН'
            joint='кассета–торец' if quantity=='seat_cast' else 'плита–кассета'
            convergence+=f' Наибольший разброс у пика давления в паре {joint} {load}.'
        elif metric.startswith('regions'):
            zone={'blade':'плиты','blade_land':'контактной зоны плиты','blade_step':'перехода ребра',
                  'cast':'литого торца','cast_R20':'R20','insert_land':'опорной зоны кассеты',
                  'seat':'кассеты'}[location]
            criterion='усталостного' if quantity=='fatigue_factor' else 'статического'
            convergence+=f' Наибольший разброс у {criterion} запаса {zone}.'

    shaft=w['cylinder_sizing'][0]['stability']
    cyl=next(r for r in w['cylinder_delta_rows'] if r['id']=='CY-MAIN')
    f=w['opening'][w['gate_bore_mm']]
    force_err=finest['loads']['static']['axial_balance_relative']*100.
    mass_values=', '.join(f"{r['item']} {fmt(r['delta_kg'],1)}" for r in m['delta_rows'])
    low_residual,high_residual=data['residual_bracket']
    pressure_limit='Подтверждённый предел плоской пары при 10⁷ циклах открыт.'
    rigid_files=data['fea']['r2_rigid']['files']
    rigid_fkm='/'.join(fmt(read_json(FEA/name)['regions']['blade']['fatigue_factor'])
                       for name in rigid_files if not name.endswith('_failure.json'))
    text=f"""# T‑1.7d · Торцевой шибер, круг 2

**Статус HOLD.** Рабочее исполнение — плита 54 мм с боковыми рёбрами 6 мм, ход шибера 100 мм, нижняя полоса 35 мм и сменная кассета. G‑CYCLE **{fmt(cy['gate_cycle_s'])} с**, пессимистичный эталон **{fmt(cy['pessimistic']['cycle_s'])} с** при сценарии остатка 100 кН. {pressure_limit} Сходимость, критерии и статус каждого расчёта приведены в [сводке](calc/T-1.7d/results.json).

## Сравнение конструктивных рычагов

Δ запасов — по центральному C3D8I сечению при жёстком тыле и одинаковом шаге 5 мм. Для рёбер приведена объёмная проверка перехода. Δ массы и времени — расчётные.

| Изменение | Δ статики / FKM | Δ перебега и хода ГЦ, мм | Δ массы, кг | Δ G‑CYCLE, с | Ограничение |
|---|---:|---:|---:|---:|---|
{design_levers(data)}

Проход 158 × 65 R3 задаёт минимальный просвет опор. Границы сбега 11 мм дают 180 мм по ширине и 87 мм по высоте между плоскими участками. Ход 105 → 120 мм при плите 38 мм и сбеге 14 × 0,15 мм почти не изменил FKM 0,531. Эскиз 50/104 с жёстким тылом дал FKM {rigid_fkm}. Плиты 51–53 мм на проверенных компоновках дали FKM 0,876–0,947 в сечении. Запас FKM ≥1 в сечении у 55/96 и 57/110 требует объёмного подтверждения. У 57/110 исходная настройка 1 м/с и ГА 200 л/мин даёт 6,020 с в пессимистичном сценарии. Минимум остаётся открытым до подтверждения силового пути и ресурса пары.

## Контакт и объёмная проверка

34CrNiMo6+QT, Rp0,2 ≥800 и Rm ≥1000 МПа для сечения до 60 мм. Кассета 340 × 180 × 55 мм опирается на дно кармана. Боковые упоры или сменные ключи передают сдвиг, прижимы удерживают кассету при разгрузке. Снятие со стороны камеры после демонтажа плиты. На полосах и ответной дорожке 52–57 HRC, целевая SHD ≥6 мм по ISO 18203. Предусмотреть пылесъёмники, лабиринт и дозированную смазку дорожек вне канала с отводом избытка. Проверить глубину, остаточное растяжение и твёрдость в переходе. [ISO 18203](https://www.iso.org/standard/89021.html) · [Плоская пара 34CrNiMo6](https://researchportal.tuni.fi/files/10868394/Juoksukangas_1472.pdf)

Расчёт сравнивает контакт с исходными статическими экранами 480/390 МПа. Публикации о зубьях дают данные для зубчатого зацепления, а опыт по плоскому фреттингу исследует другие давления, скольжение и число циклов. Для утверждения давления при 10⁷ циклах нужны данные по смазанной паре со сбегом и древесной пылью. [ISO 6336‑5](https://www.iso.org/standard/55353.html) · [ASTM G204](https://store.astm.org/g0204-21.html) · [Источники](calc/T-1.7d/sources.yaml)

C3D10, податливый торец с полями T‑1.7, две пары μ=0,15, эксцентриситет +10/−10 мм. Осевой небаланс на срезе {fmt(force_err,3)} %. Контактное давление — узловой CPRESS. Интеграл сглаженного CPRESS служит диагностикой распределения. Силовой баланс берётся из реакций среза.

| Шаг в зоне стыка, мм | Статика плиты | FKM плиты | p плита–кассета / кассета–торец, МПа | FKM ребра | FKM R20 | C‑CLR, мм |
|---:|---:|---:|---:|---:|---:|---:|
{fea_table(data)}

{convergence} На последней рассчитанной сетке FKM плиты {fmt(blade['fatigue_factor'])}, точка {hotspot_location}, поперечная/вертикальная координаты {fmt(hotspot_cross_mm,1)}/{fmt(hotspot_height_mm,1)} мм, глубина от тыла {fmt(depth,1)} мм, амплитуда Мизеса {fmt(blade['amplitude_MPa'],1)} МПа, среднее по доминирующему направлению {fmt(blade['signed_mean_normal_MPa'],1)} МПа. Под нижней полосой {fmt(layer['static_mises_MPa'],1)} МПа для управляющего по FKM слоя {layer['depth_mm'][0]}–{layer['depth_mm'][1]} мм. Для этого интервала требуется Rp0,2 ≥{fmt(proof['lower_land_Rp02_required_MPa'],0)} МПа при статическом запасе 1,5. Оценочный остаток по дополнительному среднему растяжению {fmt(proof['lower_land_tensile_mean_headroom_MPa'],0)} МПа при прежней амплитуде. В переходе 6–9 мм σeq {fmt(transition['static_mises_MPa'],0)} МПа и FKM {fmt(transition['fatigue_factor'])}, глубже 9 мм FKM ≥{fmt(deeper['fatigue_factor'])}. nσ рассчитан из градиента на поверхности. Во внутренней точке без поверхностной опоры nσ=1. Для смешанного тензора средних сохранена положительная поправка T‑1.7. У поверхности верхней полосы кассеты K_AK={fmt(surface['K_AK'])}, nσ={fmt(surface['n_sigma'])}. R20/торец дают запас {fmt(ring['static_factor'])}/{fmt(end['static_factor'])} по статике и {fmt(ring['fatigue_factor'])}/{fmt(end['fatigue_factor'])} по FKM. C‑CLR по базам камеры и плечу 77 мм при 1,70 МН составляет {fmt(proof['guide_deformation_mm'])} мм. [Метод FKM](https://doi.org/10.1016/j.ijfatigue.2024.108165)

## Цикл и требования к T‑1.6

| Рычаг или сценарий | G‑CYCLE, с | Δ к 0,6 м/с, с | RMS, кВт | Эталон песс., с |
|---|---:|---:|---:|---:|
{cycle_table(data)}

G‑PFACE {fmt(data['gates']['G-PFACE']['value'],2)} МПа и G‑DOSE {fmt(data['gates']['G-DOSE']['value'],0)} мм проходят. Запас G‑CYCLE до 6,0 с **{fmt(6.-cy['gate_cycle_s'])} с**, до 5,95 с **{fmt(5.95-cy['gate_cycle_s'])} с**. Реалистичный эталон {fmt(cy['realistic']['cycle_s'])} с. Разница гейта и эталона {fmt(cy['difference_gate_reference_s'])} с, из неё {fmt(cy['gate_minus_reference_by_block_s']['through_opening'])} с до выдачи и {fmt(cy['gate_minus_reference_by_block_s']['eject_return_close'])} с в хвосте. Гейт закладывает 100 мс на переключения и полосы по максимуму давления, эталон 70 мс и непрерывную характеристику PV180. ГЦ шибера Ø{w['gate_bore_mm']}/45 даёт {fmt(f['safety_factor'])} при 201 кН, μ=0,15 и разгоне 40 м/с².

- Пиковые скорости эталона {fmt(cy['realistic']['motion_events']['gate_open']['peak_speed_m_s'],2)}/{fmt(cy['realistic']['motion_events']['gate_close']['peak_speed_m_s'],2)} м/с. Пропорциональная рампа 12,5 мм и двустороннее демпфирование. Энергия {fmt(h['cushion']['kinetic_energy_J'],1)} Дж, экран пика при закрытии {fmt(h['cushion']['ideal_peak_screen_bar']['closing'],0)} бар при ограничении питания 175 бар в зоне торможения. Настройку до 315 бар подтвердить на обеих полостях.
- Проходы A/B ≥32/28 мм, расход {fmt(f['extend_flow_L_min'],0)}/{fmt(f['retract_flow_L_min'],0)} л/мин. Выделить линию ГА НД к A с обратным клапаном, отсечкой и редуцированием. SB330 имеет {fmt(h['LP']['working_volume_L'],2)} л рабочего объёма при 52 → 38 бар, максимальный дефицит {fmt(h['LP']['maximum_deficit_between_recharges_L']['realistic'],2)} л. Подтвердить потери, заряд и давление при фактическом расходе.
- Сохранить раздельные прессование, выдержку, сброс и подачу. Перед открытием два канала ≤3 бар плюс подтверждение обоих засовов. Выдача по подтверждённому открытому положению, прессование по фактическому закрытию. Закрывать на возврате при x≤195 мм и подтверждённом свободном хвосте. Обновить пределы координаты выдачи и возврата до {g['punch_face_maximum_eject_end_x_mm']}/{g['main_installed_stroke_mm']} мм. Приоритет насоса — возврат перед шибером. Пессимистичный эталон пересекает 6 с между 110 кН ({fmt(low_residual['pessimistic_cycle_s'])} с) и 130 кН ({fmt(high_residual['pessimistic_cycle_s'])} с). На стенде нужно измерить остаток на закрытом шибере. [Parker, торможение](https://www.parker.com/content/dam/Parker-com/Literature/Atlas-Cylinder/PDF/HY08-AC1151_HMI.pdf) · [HYDAC, SB330](https://www.hydac.com/download/accumulator-technology-product-catalogue-1000443492-en.pdf)

## Компоновка, масса и проект D‑GK‑01

В проект редакции для ГК входят главный ход **{fmt(g['punch_face_nominal_eject_end_x_mm'],0)}/{g['main_installed_stroke_mm']} мм**, верхняя рабочая точка {g['punch_face_maximum_eject_end_x_mm']} мм, перебег **{g['overtravel_nominal_mm']}/{g['overtravel_maximum_mm']} мм**, шибер 54 мм с рёбрами до 60 мм. Номинальный минимум по хвосту {fmt(g['minimum_relaxed_tail_clearance_mm'])} мм и {fmt(g['minimum_relaxed_tail_clearance_after_allowance_mm'])} мм с бюджетом 1 мм. Лицевая, тыльная и выходная плоскости на x={fmt(g['gate_face_x_mm'],0)}/{fmt(g['gate_back_x_mm'],0)}/{fmt(g['channel_exit_x_mm'],0)} мм. Свободный канал 205 мм, гладкая часть колонн {fmt(g['column_smooth_span_mm'],0)} мм, рама {fmt(g['frame_axial_length_mm'],0)} мм. ГЦ Ø280/200, масса с маслом {fmt(cyl['filled_mass_each_kg'],1)} кг, длина корпуса {fmt(cyl['body_length_mm'],0)} мм, втянут/выдвинут {fmt(cyl['rod_tip_retracted_length_mm'],0)}/{fmt(cyl['rod_tip_extended_length_mm'],0)} мм. Запас штока {fmt(shaft['safety_factor'],2)} при вылете {fmt(cyl['column_effective_length_max_mm'],0)} мм.

Масса **{fmt(m['nominal_kg'],0)} [{fmt(m['lower_kg'],0)}–{fmt(m['upper_kg'],0)}] кг**, +{fmt(-m['margin_to_4850_kg'],0)} к 4850 и запас {fmt(m['margin_to_5000_kg'],0)} до 5000 по номиналу. Дельты к T‑1.7c в кг — {mass_values}. Верх вилки требует закрытия по ведомости. Проект изменения остаётся на проверке ГК. Открыты подтверждение слоя и пары, устойчивый цикл при большом остатке и размерная цепь хвоста. [Проверки](self_check.json) · [Гейты](gates.t17d.json)
"""
    (ROOT/'report.md').write_text(text,encoding='utf-8',newline='\n')
