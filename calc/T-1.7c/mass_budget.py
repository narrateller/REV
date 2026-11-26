"""Machine mass changes from T-1.7. Alternatives retain the round-one record."""
from math import fsum,pi


def steel_kg(volume_mm3):
    return volume_mm3*7.85e-6


def rounded_area_mm2(width_mm,height_mm,radius_mm):
    return width_mm*height_mm-(4-pi)*radius_mm**2


def budget(frame, frame_results, geometry, blade):
    mass = frame_results['variants']['cast']['mass']
    machine_rows = mass['machine_rows']
    frame_rows = mass['frame_rows']
    base_kg = mass['machine_kg']
    station_kg = next(r['mass_kg'] for r in machine_rows if r['node']=='Гидростанция в сборе')
    est_kg = fsum(r['mass_kg'] for r in machine_rows if r['node'] in ('Подача и бункер','Ограждения','Электрика'))
    supports_kg = next(r['mass_kg'] for r in frame_rows if r['node'].startswith('Боковой упор'))
    old_insert_kg = next(r['mass_kg'] for r in frame_rows if r['node'].startswith('Распределительная вставка'))
    cols = frame['columns']
    shortening_kg = steel_kg(cols['quantity']*pi/4*cols['smooth_span_diameter_mm']**2*geometry['column_shortening_mm'])
    guide_area_mm2 = rounded_area_mm2(*geometry['passage_inlet_mm'],geometry['bored_gate_and_insert_R_mm'])
    bare_area_mm2 = rounded_area_mm2(*geometry['cast_channel_mm_R'])
    insert_w_mm,insert_h_mm,insert_r_mm = blade['seat_outline_mm_R']
    insert_kg = steel_kg((rounded_area_mm2(insert_w_mm,insert_h_mm,insert_r_mm)-guide_area_mm2)*geometry['insert_recess_depth_mm'])
    cast_removed_kg = steel_kg((rounded_area_mm2(insert_w_mm+.2,insert_h_mm+.2,insert_r_mm)-bare_area_mm2)*geometry['insert_recess_depth_mm'])
    shuttle_kg = steel_kg((rounded_area_mm2(*blade['blade_outline_mm_R'])-guide_area_mm2)*geometry['closed_gate_thickness_mm'])
    base_owned_components = [r for r in machine_rows if 'шибер' in r['node'].lower()]
    old_shuttle_kg = next(r['mass_kg'] for r in machine_rows if r['node']=='Плита шибера')
    # Complete liner envelope (solid difference) is a mass estimate from above.
    liner_kg = steel_kg((bare_area_mm2-guide_area_mm2)*(geometry['channel_length_mm']-geometry['insert_recess_depth_mm']))

    def line(item,delta_kg,lower_kg,upper_kg,source):
        return dict(item=item,delta_kg=delta_kg,lower_delta_kg=lower_kg,upper_delta_kg=upper_kg,source=source)

    changes = [
        line('Упоры зоны падения',-supports_kg,0.,0.,'T-1.7 variants.cast.mass.frame_rows'),
        line('Четыре колонны Ø70',-shortening_kg,0.,5.,'frame.t17.yaml, сокращение на 245 мм'),
        line('Прежняя вставка',-old_insert_kg,0.,0.,'T-1.7 variants.cast.mass.frame_rows'),
        line('Отливка, карман',-cast_removed_kg,0.,8.,'По расточке 340,2 × 180,2 R12 в координатах модели'),
        line('Новая вставка',insert_kg,-1.,2.,'Контактная геометрия fea/contact.py'),
        line('Оконный шибер, дельта',shuttle_kg-old_shuttle_kg,-1.,3.,'По геометрии с вычетом плиты 260×260×38 из базы'),
        line('Вставные направляющие R20',liner_kg,-liner_kg/2,1.,'Верхняя оценка полного заполнения зазора сталью'),
        line('Сервисный выход, крепёж, датчики',10.,-5.,15.,'Эскизный бюджет, подтвердить ведомостью КД'),
    ]
    uncertainty = [
        line('Гидростанция',0.,-.05*station_kg,.05*station_kg,'T-1.7 GK_review M3, ±5 %'),
        line('Припуски литья',0.,0.,40.,'T-1.7 GK_review M3'),
        line('Подача, ограждения, электрика',0.,-.1*est_kg,.1*est_kg,'Как в круге 1, чувствительность ±10 %'),
    ]
    nominal_kg = base_kg+fsum(r['delta_kg'] for r in changes)
    lower_kg = nominal_kg+fsum(r['lower_delta_kg'] for r in changes+uncertainty)
    upper_kg = nominal_kg+fsum(r['upper_delta_kg'] for r in changes+uncertainty)
    return dict(baseline_kg=base_kg,baseline_rows=machine_rows,baseline_gate_source_rows=base_owned_components,
                delta_rows=changes,uncertainty_rows=uncertainty,nominal_kg=nominal_kg,lower_kg=lower_kg,upper_kg=upper_kg,
                target_kg=4850.,limit_kg=5000.,margin_to_target_kg=4850.-nominal_kg,
                margin_to_limit_kg=5000.-nominal_kg,upper_margin_to_limit_kg=5000.-upper_kg,
                shuttle_mass_kg=shuttle_kg)

