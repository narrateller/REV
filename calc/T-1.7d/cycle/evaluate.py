from dataclasses import replace
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
from stack import from_reference
from drive import configuration, get_inputs, source_data
from make_params_t14b import gate_module, make_candidate
from x1_calc import periodic_run


def configure(layout, moving_mass_kg, residual_product_N=100000., profile='realistic',
              peak_kW=36., gate_bore_mm=80., rapid_mass_increment_kg=0.,
              gate_speed_m_s=None, gate_accel_m_s2=None, gate_lp=False,
              gate_close_oil_priority=False, gate_close_punch_inset_mm=10., lp_flow_L_min=None,
              gate_losses_bar=None):
    inputs = get_inputs()
    upstream, params, *_ = inputs
    params['main_cylinder']['stroke_mm'] = layout['main_installed_stroke_mm']
    params['main_cylinder']['working_range_mm'] = layout['punch_face_maximum_eject_end_x_mm']
    params['chamber']['ejection_overtravel_mm'] = layout['overtravel_nominal_mm']
    model, cylinder, settings, projection, charge = configuration(
        inputs, data=source_data(), profile=profile, limit_kW=peak_kW)
    if gate_speed_m_s is not None:
        cfg = source_data()['engineering_inputs']
        ratio = cfg['pessimistic_gate_speed_mm_s'] / cfg['slide_gate_speed_mm_s']
        model = replace(model, gate_speed_m_s=gate_speed_m_s*(ratio if profile=='pessimistic' else 1.))
    if gate_accel_m_s2 is not None:
        model = replace(model, gate_accel_m_s2=gate_accel_m_s2)
    if gate_lp:
        settings['boost_branches'] += ('gate_open', 'gate_close')
    if lp_flow_L_min is not None:
        settings['accumulator_kwargs']['delivery_L_min'] = lp_flow_L_min
        charge['max_flow_L_min'] = lp_flow_L_min
    lateral_travel_mm = layout['gate_working_travel_mm']
    if lateral_travel_mm != 75.:
        params['drive']['slide_gate_cylinder']['stroke_mm'] = lateral_travel_mm + 5.
    params['drive']['slide_gate_cylinder']['bore_mm'] = gate_bore_mm
    gate_cyl = replace(model.gate_cylinder, bore_mm=gate_bore_mm,
                       stroke_mm=params['drive']['slide_gate_cylinder']['stroke_mm'])
    model = replace(model, overtravel_m=layout['overtravel_nominal_mm']/1000,
                    gate_travel_m=lateral_travel_mm/1000, gate_cylinder=gate_cyl,
                    gate_mass_kg=moving_mass_kg, gate_open_weight_N=9.81*moving_mass_kg,
                    gate_close_oil_priority=gate_close_oil_priority, gate_losses_bar=gate_losses_bar,
                    gate_close_punch_inset_m=gate_close_punch_inset_mm/1000,
                    rapid_mass_kg=model.rapid_mass_kg+rapid_mass_increment_kg,
                    gate_open_residual_friction_N=.15*(residual_product_N+.5*cylinder.cap_m2*1e6))
    stack, _ = from_reference(upstream, layout, model, .50, 5000., 'base', 2., 'nominal')
    model = replace(model, stack_force_N=stack.force_N)
    return inputs, (model, cylinder, settings, projection, charge)


def assess(layout, moving_mass_kg, detailed=False, **config):
    inputs, cfg = configure(layout, moving_mass_kg, **config)
    candidate = make_candidate(inputs, cfg)
    candidate['description'] = ('T-1.7d, гидравлический эквивалент фаз T-1.4b для G-CYCLE. '
                                'Геометрия задана в design/frame.t17d.yaml. Уставка по D-GK-02 36 кВт.')
    gate = gate_module()
    criteria = gate.read_criteria((ROOT/'ops/criteria/design_criteria.yaml').read_bytes())['criteria']
    checked = gate.evaluate_cycle(candidate, criteria)
    summary = dict(gate_cycle_s=checked['value'], gate_status=checked['status'],
                   gate_rms_kW=checked['details']['rms_power_kW'],
                   gate_margin_s=6.-checked['value'])
    if detailed:
        for profile in ('realistic','pessimistic'):
            _, configs = configure(layout, moving_mass_kg, profile=profile, **config)
            model, cylinder, settings, _, _ = configs
            run = periodic_run(model, cylinder, 90., .64, settings, .000625)
            summary[profile] = ({k:run[k] for k in ('cycle_s','average_shaft_kW','rms_shaft_kW',
                                                   'peak_shaft_kW','motion_events','stage_events','feasible',
                                                   'boost_L_by_motion','boost_L','recharged_L','extra_recharge_s','net_lp_oil_balance_L',
                                                   'peak_lp_deficit_L','min_lp_gas_bar',
                                                   'peak_working_bar','switches','lp_charge_s_by_window') if k in run}
                                if run['feasible'] else run)
        if summary['realistic']['feasible']:
            comparison = summary['realistic']
            summary['difference_gate_reference_s'] = checked['value']-comparison['cycle_s']
            ejection = comparison['motion_events']['eject']
            projected_ejection = [row for row in checked['details']['phases'] if row['name'].startswith('eject ')]
            nominal_tail_begin_s = ejection['start_s']-cfg[2]['switch_s']
            projected_tail_begin_s = projected_ejection[0]['group_start_s']
            nominal_tail_end_s = comparison['stage_events']['feed'][0]
            projected_tail_end_s = next(row['group_start_s'] for row in checked['details']['phases'] if row['name']=='feed')
            summary['gate_minus_reference_by_block_s'] = {
                'through_opening': projected_tail_begin_s-nominal_tail_begin_s,
                'eject_return_close': (projected_tail_end_s-projected_tail_begin_s)-
                                      (nominal_tail_end_s-nominal_tail_begin_s),
                'feed': (checked['value']-projected_tail_end_s)-(comparison['cycle_s']-nominal_tail_end_s),
            }
            summary['reference_margin_s'] = 6.-summary['realistic']['cycle_s']
        if summary['pessimistic']['feasible']:
            summary['pessimistic_margin_s'] = 6.-summary['pessimistic']['cycle_s']
    return summary, candidate

