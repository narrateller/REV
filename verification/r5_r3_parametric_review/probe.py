"""Independent R5 arithmetic oracle; stdlib Decimal, no author solver for expected values.

Run at repository root with .venv/bin/python -B <this file>.
Author solver is imported ONLY as the implementation under test for new boundary probes.
These are synthetic arithmetic cases, not registered design inputs or measured limits.
"""
from decimal import Decimal as D, getcontext
from pathlib import Path
import csv
import hashlib
import json
import math
import sys

getcontext().prec = 50
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from repo_support import flatten
import yaml

P = flatten(yaml.safe_load((ROOT / 'params/registry.yaml').read_text()))
OUT = ROOT / 'verification/r3_parametric_sizing'
CASES = json.loads((OUT / 'cases.json').read_text())
PI = D('3.1415926535897932384626433832795028841971693993751')


def independent(raw, variant):
    p = {k: D(str(v)) for k, v in raw.items()}
    face = p['width'] * p['height']
    occupied = p['mass'] / p['rho'] / face
    chamber = occupied / p['phi']
    strokes = [chamber - occupied, occupied - p['product_length'], p['eject_travel']]
    strokes.append(sum(strokes))
    slide = p['channel_slide'] if variant == 'A' else D(0)
    low = face * p['sigma_start'] + slide + p['guide']
    high = face * p['sigma_end'] + slide + p['guide']
    eject = slide + p['guide'] if variant == 'A' else p['eject_load_b'] + p['guide']
    ret = p['return_load'] + p['guide']
    # Independently solve cap-area inequalities, including approach and both directions.
    r = 1 - p['kappa'] ** 2
    candidates = [(f + p['seal']) / (ps - pb * r) for f, ps, pb in (
        (p['guide'], p['supply_work'], p['back_forward']),
        (high, p['supply_work'], p['back_forward']),
        (eject, p['supply_eject'], p['back_forward']))]
    candidates.append((ret + p['seal']) / (p['supply_return'] * r - p['back_return']))
    cap = max(candidates)
    ann = cap * r
    diameter = (4 * cap / PI).sqrt()
    o = dict(area=face, chamber_volume=chamber * face, chamber_length=chamber,
             occupied_length=occupied, approach_stroke=strokes[0], work_stroke=strokes[1],
             eject_stroke=strokes[2], return_stroke=strokes[3],
             product_density=p['mass'] / (face * p['product_length']),
             force_work_start=low, force_work_peak=high, force_eject=eject,
             force_return_required=ret, bore=diameter, rod=p['kappa'] * diameter,
             bore_area=cap, annulus_area=ann,
             force_extension_capacity=p['supply_work'] * cap - p['back_forward'] * ann - p['seal'],
             force_return_capacity=p['supply_return'] * ann - p['back_return'] * cap - p['seal'],
             mass_residual=p['rho'] * p['phi'] * chamber * face - p['mass'],
             eject_required_geometry=p['product_length'] + p['clearance'],
             eject_geometry_margin=strokes[2] - p['product_length'] - p['clearance'])
    if variant == 'A': o['A_hold_margin'] = p['channel_hold'] - p['rebound']
    else: o['B_stop_peak_reaction'] = face * p['sigma_end']
    energies = []; loads = []; seals = []; drains = []; valves = []; times = []; qs = []; powers = []
    eta = p['eta_pump'] * p['eta_motor']
    for i, name in enumerate(('approach', 'work', 'eject', 'return')):
        ain, aout = (ann, cap) if i == 3 else (cap, ann)
        ps = p['supply_return'] if i == 3 else p['supply_eject'] if i == 2 else p['supply_work']
        pb = p['back_return'] if i == 3 else p['back_forward']
        force = [p['guide'], (low + high) / 2, eject, ret][i]
        s = strokes[i]; t = p['t_' + name]
        # Integrate a ramp independently with 32 trapezoids; constant loads otherwise.
        if i == 1:
            f = [low + (high-low)*D(j)/32 for j in range(33)]
            load_work = sum((f[j]+f[j+1])*s/64 for j in range(32))
        else: load_work = force * s
        displaced_in, displaced_out = ain * s, aout * s
        supplied = ps * displaced_in
        sealing, draining = p['seal'] * s, pb * displaced_out
        valve = supplied - load_work - sealing - draining
        fields = dict(speed=s/t, flow_supply=displaced_in/t, flow_return=displaced_out/t,
                      mean_chamber_pressure=(force+p['seal']+pb*aout)/ain,
                      supply_power=supplied/t, supply_energy=supplied, load_work=load_work,
                      seal_loss=sealing, back_loss=draining, valve_loss=valve,
                      minimum_time_power=supplied/(eta*p['electric_limit']))
        o.update({name+'_'+k: v for k,v in fields.items()})
        energies.append(supplied); loads.append(load_work); seals.append(sealing)
        drains.append(draining); valves.append(valve); times.append(max(t, fields['minimum_time_power']))
        qs.append(displaced_in/t); powers.append(supplied/t)
    hold = p['supply_work'] * p['leak_hold'] * p['t_hold']
    eh = sum(energies) + hold; ee = eh/eta
    pump = eh/p['eta_pump'] - eh; motor = ee - eh/p['eta_pump']
    aux = p['t_aux_a'] if variant == 'A' else p['t_unload_b']+p['t_open_b']
    cycle = sum(p['t_'+n] for n in ('approach','work','eject','return'))+p['t_hold']+aux
    peak_h = max(powers+[p['supply_work']*p['leak_hold']])
    o.update(hold_loss=hold, hydraulic_energy=eh, load_work_total=sum(loads),
             seal_loss_total=sum(seals), back_loss_total=sum(drains), valve_loss_total=sum(valves),
             pump_loss=pump, motor_loss=motor, electric_energy=ee, modeled_heat=ee-sum(loads),
             hydraulic_energy_residual=eh-sum(loads)-sum(seals)-sum(drains)-sum(valves)-hold,
             electric_energy_residual=ee-sum(loads)-sum(seals)-sum(drains)-sum(valves)-hold-pump-motor,
             flow_peak=max(qs+[p['leak_hold']]), hydraulic_power_peak=peak_h,
             electric_power_peak=peak_h/eta, cycle_budget=cycle,
             cycle_budget_power_limited=sum(times)+p['t_hold']+aux,
             electric_power_margin=p['electric_limit']-peak_h/eta,
             conditional_mass_rate=p['mass']/cycle, electric_power_average=ee/cycle)
    return {k:float(v) for k,v in o.items()}


def compare(a,b):
    assert set(a)==set(b), (set(a)-set(b),set(b)-set(a))
    for k,v in a.items():
        # Numerical comparison tolerance, NOT a design tolerance or accuracy claim.
        assert math.isclose(v,b[k],rel_tol=3e-13,abs_tol=1e-8), (k,v,b[k])


data = {}; rows = list(csv.DictReader((OUT/'scenarios.csv').open()))
for case in CASES:
    raw = {name:P[k]['value'] for name,k in case['parameters'].items()}
    expected = independent(raw,case['variant'])
    saved = json.loads((OUT/'results'/f"{case['id']}.json").read_text())
    prefix = 'R3_'+case['id']+'_'
    actual = {x['id'][len(prefix):].lower():x['value'] for x in saved['outputs']}
    for special in ('A_hold_margin','B_stop_peak_reaction'):
        if special.lower() in actual: actual[special] = actual.pop(special.lower())
    compare(expected,actual)
    compare(expected,{x['quantity']:float(x['value_SI']) for x in rows if x['scenario']==case['id']})
    data[case['id']] = {'inputs':raw,'input_refs':case['parameters'],'independent':expected,'flags':saved['conclusions']}

# Verify the two displayed scenario tables and the phase table at their printed precision.
report = (OUT/'report.md').read_text().splitlines()
display_count = 0
for line in report:
    cells = [x.strip() for x in line.split('|')[1:-1]]
    if not cells or cells[0] not in data or len(cells) != 6: continue
    keys,scale = (['chamber_volume','work_stroke','force_work_peak','bore','rod'],[1000,1000,.001,1000,1000]) if 'CHAMBER_VOLUME@' in line else (['flow_peak','electric_power_peak','electric_energy','cycle_budget','cycle_budget_power_limited'],[60000,.001,.001,1,1])
    for cell,key,factor in zip(cells[1:],keys,scale):
        token=cell.split()[0]; digits=len(token.split('.')[1]) if '.' in token else 0
        assert abs(float(token)-data[cells[0]]['independent'][key]*factor) <= .50001*10**(-digits), (cells[0],key,cell)
        display_count += 1
phase_count = 0
for line in (OUT/'phases.md').read_text().splitlines():
    c=[x.strip() for x in line.split('|')[1:-1]]
    if not c or c[0] not in ('approach','work','eject','return'): continue
    for cell,key,factor in zip(c[1:],('speed','flow_supply','flow_return','mean_chamber_pressure','supply_energy','load_work'),(1,60000,60000,1e-6,.001,.001)):
        assert abs(float(cell.split()[0])-data['BASE_A']['independent'][c[0]+'_'+key]*factor) <= .00050001
        phase_count += 1

from rev_parametric import solve
base=data['BASE_A']['inputs']
probes=[]
def probe(name, variant='A', **changes):
    p={**base,**changes}; oracle=independent(p,variant); actual,flags=solve(p,variant)
    compare(oracle,actual)
    probes.append({'name':name,'variant':variant,'changes':changes,'outputs':actual,'flags':flags,'oracle_comparison':'PASS'})
    return actual,flags

probe('zero_work_and_approach',mass=.9,rho=1000.,width=.15,height=.06,product_length=.1,phi=1.)
probe('zero_forward_backpressure_ideal_bore','B',back_forward=0.,back_return=0.,guide=0.,seal=0.,eject_load_b=0.,return_load=0.)
probe('reverse_controls',return_load=3e6)
probe('ejection_controls','B',eject_load_b=3e6)
probe('constant_stress',sigma_start=base['sigma_end'])
probe('rod_ratio_near_one_reverse_controls',kappa=.95,back_return=0.,return_load=3e6)
probe('small_fill_fraction',phi=.05)
probe('unity_efficiencies',eta_pump=1.,eta_motor=1.)
probe('hold_leak_exceeds_budget',leak_hold=.001,t_approach=1000.,t_work=1000.,t_eject=1000.,t_return=1000.)
probe('hold_failure_short_ejection_compound',channel_hold=1.,rebound=10001.,eject_travel=.01)
probe('B_no_material_load_does_not_prove_unloaded','B',sigma_start=0.,sigma_end=1e-9,back_forward=0.,back_return=0.,seal=0.)
probe('B_long_ejection_high_return','B',eject_travel=.34,return_load=3e6)
assert probes[-2]['flags']['B_open_permission']=='INDETERMINATE'
assert probes[-2]['flags']['power_budget_arithmetic']=='WITHIN_ASSUMED_LIMIT'
assert probes[-3]['flags']['A_hold_arithmetic']=='INSUFFICIENT'
assert probes[-3]['flags']['ejection_geometry_arithmetic']=='SHORT_TRAVEL'
assert probes[0]['outputs']['approach_stroke']==0 and abs(probes[0]['outputs']['work_stroke'])<1e-15
assert probes[8]['outputs']['cycle_budget_power_limited']==4002
assert probes[8]['outputs']['electric_power_peak']>base['electric_limit']
invalid=[]
for name,changes in [('zero_density',{'rho':0}),('zero_time',{'t_work':0}),('overfill',{'phi':1.01}),('rod_equals_bore',{'kappa':1}),('no_reverse_pressure_head',{'back_return':7.68e6}),('no_forward_pressure_head',{'back_forward':46.875e6}),('expansion_instead_of_compaction',{'rho':10000}),('unknown_mass',{'mass':None}),('nonfinite_pressure',{'supply_work':float('nan')}),('boolean_efficiency',{'eta_motor':True})]:
    try: solve({**base,**changes},'A')
    except ValueError as exc: invalid.append({'name':name,'expected':'ValueError','actual':str(exc),'result':'PASS'})
    else: raise AssertionError('accepted invalid '+name)

print(json.dumps({'scope':'INDEPENDENT_ARITHMETIC_ONLY; synthetic probes are not design inputs',
 'method':'50-digit Decimal; independent cap-area inequalities; 32-segment load integral; p*dV energy',
 'scalar_comparisons':sum(len(x['independent']) for x in data.values()),'csv_rows':len(rows),
 'report_values_checked':display_count,'phase_values_checked':phase_count,
 'cases':data,'boundary_probes':probes,'invalid_probes':invalid},ensure_ascii=False,indent=2,allow_nan=False))
