"""Contact and hydraulic screening inputs shared by the study and design outputs."""
from math import pi

from mass_budget import rounded_area_mm2, steel_kg


def support(geometry, baseline_mass):
    seat_volume_mm3 = (rounded_area_mm2(340., 180., 12.) -
                       rounded_area_mm2(158., 65., 3.))*55.
    based = next(x['delta_kg'] for x in baseline_mass['delta_rows'] if x['item']=='Новая вставка')
    current = steel_kg(seat_volume_mm3)
    return dict(
        body='Цельная сменная кассета с опорными полосами по контуру окна. Полосы шлифуются в одной установке.',
        dimensions_mm_R=[340.,180.,55.,12.], bore_mm_R=[158.,65.,3.],
        pocket_mm_R=[340.2,180.2,55.,12.], 
        lower_land_width_mm=geometry['gate_working_travel_mm']-65.,
        material='34CrNiMo6+QT, плита и кассета, Rp0,2 ≥ 800 МПа / Rm ≥ 1000 МПа в определяющем сечении ≤ 60 мм.',
        material_acceptance='Поковку квалифицировать по фактическому определяющему сечению перед ТО и сертификату свойств сердцевины. При превышении 60 мм требуется отдельно гарантировать свойства 800/1000 МПа.',
        cast_bearing_quality='Rz ≤6,3 мкм на дне кармана и в R20; УЗК и МПК по требованиям T-1.7.',
        induction_on='Опорные полосы кассеты и ответные дорожки тыльной плоскости плиты. Отпуск и окончательное шлифование после упрочнения.',
        surface_HRC=[52,57], SHD_min_mm=6., roughness_Rz_max_um=6.3,
        hardening_depth_method='ISO 18203, SHD по микротвёрдости на поперечных шлифах, в том числе на сбеге и на концах дорожки.',
        residual_stress='Контроль остаточных напряжений у конца дорожки и перехода слоя. В FKM заложены свойства +QT без прироста от упрочнения.',
        fixing='Дно кармана передаёт осевую силу в торец. Сопряжённые боковые упорные грани или сменные ключи воспринимают сдвиг по двум осям. Прижимы снаружи проекции плиты удерживают кассету при обслуживании.',
        service='Подпереть шибер при разгруженной и изолированной гидравлике, снять плиту и прижимы со стороны камеры, извлечь кассету в сторону камеры, восстановить базу и проверить ход.',
        wear='Сменные пылесъёмники на входе в направляющие, лабиринт и удаление пыли из кармана; дозированная подача совместимой смазки к дорожкам вне канала и отвод излишка наружу. Проверка задира при 8–12% влажности сырья по T-1.7c, загрязнение представительными частицами.',
        calculated_blank_mass_kg=current, baseline_insert_mass_kg=based, retention_mass_allowance_kg=1.,
        contact_allowance_requires_pair_test=True,
    )


def hydraulics(setup, options, cycle, candidate):
    moving_kg=setup['moving_mass_kg']
    bore=setup['gate_bore_mm']
    opening=setup['opening'][bore]
    v=options['gate_speed_m_s']
    a=options['gate_accel_m_s2']
    p_open=opening['required_N']/(opening['annulus_mm2']*.92*.1)
    p_open+=5.*opening['cap_mm2']/opening['annulus_mm2']
    energy_J=.5*moving_kg*v*v
    ramp_mm=1000.*v*v/(2.*a)
    q_L_min={key:opening[key+'_mm2']*v*.06 for key in ('cap','annulus')}
    volumes_L={key:opening[key+'_mm2']*setup['geometry']['gate_working_travel_mm']*1e-6
               for key in ('cap','annulus')}
    bore_passage={'cap':32.,'annulus':28.}
    inlet_max_bar=175.
    kinetic_peak_factor=2.
    close_bar=(inlet_max_bar*opening['cap_mm2']/opening['annulus_mm2']+
               kinetic_peak_factor*energy_J*10000/(opening['annulus_mm2']*ramp_mm)+
               moving_kg*9.81/(opening['annulus_mm2']*.1))
    open_bar=(inlet_max_bar*opening['annulus_mm2']/opening['cap_mm2']+
              kinetic_peak_factor*energy_J*10000/(opening['cap_mm2']*ramp_mm))
    acc=candidate['drive']['accumulator']
    return dict(
        speed_command_m_s=v, acceleration_command_m_s2=a, ramp_distance_at_command_mm=ramp_mm,
        moving_mass_kg=moving_kg, peak_acceleration_force_N=moving_kg*a,
        opening_support_required_N=opening['required_N'], moving_open_pressure_screen_bar=p_open,
        full_speed_port_flow_L_min=q_L_min, stroke_oil_L=volumes_L, minimum_work_passage_ID_mm=bore_passage,
        flow_velocity_m_s={k: q/60000./(pi*(bore_passage[k]/1000)**2/4) for k,q in q_L_min.items()},
        WRLE_fully_open_loss_per_edge_bar={k: 5.*(q/400.)**2 for k,q in q_L_min.items()},
        cushion=dict(kinetic_energy_J=energy_J, initial_cushion_length_mm=ramp_mm, inlet_pressure_limit_bar=inlet_max_bar,
                     assumed_peak_to_mean_inertial_pressure=kinetic_peak_factor,
                     ideal_peak_screen_bar={'opening':open_bar,'closing':close_bar},
                     local_relief_limit_at_full_flow_bar=315., 
                     validation='Профиль торможения проверяется датчиками обеих полостей при крайних температурах. До зоны торможения снизить давление подпора привода. Нужны гидравлическое демпфирование на двух концах, защита от кавитации и независимое локальное ограничение давления.'),
        LP=dict(effective_gas_volume_L=18.4, precharge_operating_bar=28., minimum_gas_bar=38., maximum_gas_bar=52.,
                min_delivery_bar=acc['min_delivery_pressure_bar'], max_delivery_L_min=acc['max_flow_L_min'],
                working_volume_L=acc['usable_oil_L'], open_admission='Только если давление потребителя + потери покрыты, при расчётном усилии открытия подача от PV180.',
                close_admission='От ГА в A через отдельную отсечку, редуцирование, обратный клапан. Допуск от PLC после подтверждения возврата.',
                charge_and_delivery_drop_bar=3., periodic_draw_L={p:cycle[p]['boost_L'] for p in ('realistic','pessimistic')},
                maximum_deficit_between_recharges_L={p:cycle[p]['peak_lp_deficit_L'] for p in ('realistic','pessimistic')},
                minimum_simulated_gas_bar={p:cycle[p]['min_lp_gas_bar'] for p in ('realistic','pessimistic')}),
        overlaps=dict(press_hold_unload_feed='Вне групп движения', priority='выдача, возврат, закрытие шибера, подъём башмака',
                      close_punch_x_max_mm=205.-options.get('gate_close_punch_inset_mm',10.),
                      return_installed_limit_x_mm=setup['geometry']['main_installed_stroke_mm'],
                      upper_dose_eject_end_x_mm=setup['geometry']['punch_face_maximum_eject_end_x_mm'],
                      confirmation='Начало возврата после завершения выдачи. Закрытие только при свободном хвосте и достоверной координате пуансона.'),
    )
