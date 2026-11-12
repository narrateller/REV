"""Two explicit electrical-budget alternatives; frozen legacy arithmetic is not a planner."""
import argparse
import csv
import hashlib
import io
import json
import math
import platform
from pathlib import Path
import yaml
from repo_support import flatten, parameter_ref, sha256, engineering_sha
from rev_parametric import solve, INPUT_UNITS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'verification/r3_power_reconcile'
LEGACY=ROOT/'verification/r3_parametric_sizing'
PHASES=('approach','work','eject','return')
CODE=['scripts/rev_power_reconcile.py','scripts/rev_parametric.py','scripts/repo_support.py']


def number(x,name,positive=False):
    if type(x) not in (int,float) or not math.isfinite(x) or x<0 or (positive and x==0):
        raise ValueError('invalid '+name)
    return x


def assess_hold(pressure,eta_p,eta_m,*,mode=None,leakage=None,pump_flow=None,
                unload_pressure=None,standby=None,aux=None,budget=None):
    """Known numeric balances only, not proof of a real holding arrangement.

    pressure_regulated: supply flow includes leakage + any relief/bypass at pressure.
    isolated_unloaded: only supported with explicitly known zero leakage; otherwise
    pressure maintenance/storage/recharge is not established by an unloaded pump.
    Unknowns never default to zero. Accumulator energy/charge is outside this API.
    """
    number(pressure,'pressure',True)
    for name,x in [('eta_p',eta_p),('eta_m',eta_m)]:
        number(x,name,True)
        if x>1:raise ValueError('efficiency >1')
    for name,x in [('leakage',leakage),('pump_flow',pump_flow),('unload_pressure',unload_pressure),
                   ('standby',standby),('aux',aux),('budget',budget)]:
        if x is not None:number(x,name)
    result={'status':'UNKNOWN','electric_power':None,'budget_status':'INDETERMINATE',
            'leakage_electric_lower_bound':None if leakage is None else pressure*leakage/(eta_p*eta_m)}
    if mode not in (None,'pressure_regulated','isolated_unloaded','accumulator'):
        raise ValueError('unsupported hold mode')
    if mode in (None,'accumulator') or any(x is None for x in (leakage,pump_flow,standby,aux)):
        return result
    if mode=='pressure_regulated':
        if pump_flow<leakage:
            result['status']='INSUFFICIENT_REPLENISHMENT';return result
        hydraulic=pressure*pump_flow
    else:
        if leakage>0:
            result['status']='PRESSURE_MAINTENANCE_NOT_ESTABLISHED';return result
        if unload_pressure is None:return result
        hydraulic=unload_pressure*pump_flow
    power=hydraulic/(eta_p*eta_m)+standby+aux
    result.update(status='NUMERIC_MODEL_ONLY',electric_power=power,
                  budget_status='INDETERMINATE' if budget is None else ('EXCEEDS_BUDGET' if power>budget else 'WITHIN_BUDGET'))
    return result


def reconcile(p,variant,allocation,*,hold_power=None,motion_extra=None,pause_power=None):
    """Actual totals stay null unless every power component is provided explicitly.

    allocation is an ASSUMED upper envelope for total additional motion consumers,
    total hold input (pump+standby+aux), and total other-pause input. Its validity is
    unverified. Fixed-budget times apply only under this contract. Original times
    and budget are retained; no budget increase or target-time replacement occurs.
    """
    for k in ('motion_extra_cap','hold_total_cap','pause_total_cap'):number(allocation[k],k)
    for name,x in [('hold_power',hold_power),('motion_extra',motion_extra),('pause_power',pause_power)]:
        if x is not None:number(x,name)
    old,legacy_flags=solve(p,variant)
    efficiency=p['eta_pump']*p['eta_motor'];budget=p['electric_limit']
    reserve=allocation['motion_extra_cap'];available=budget-reserve
    pause_t=p['t_aux_a'] if variant=='A' else p['t_unload_b']+p['t_open_b']
    reason=[]
    if available<=0:reason.append('NO_MOTION_POWER_ALLOCATION')
    if allocation['hold_total_cap']>budget:reason.append('HOLD_ENVELOPE_EXCEEDS_BUDGET')
    if allocation['pause_total_cap']>budget:reason.append('PAUSE_ENVELOPE_EXCEEDS_BUDGET')
    for actual,cap,label in [(hold_power,allocation['hold_total_cap'],'HOLD'),
                             (motion_extra,reserve,'MOTION_EXTRA'),(pause_power,allocation['pause_total_cap'],'PAUSE')]:
        if actual is not None and actual>cap:reason.append(label+'_EXCEEDS_ALLOCATION')
    if hold_power is not None and hold_power>budget:reason.append('HOLD_POWER_EXCEEDS_BUDGET')
    if pause_power is not None and pause_power>budget:reason.append('PAUSE_POWER_EXCEEDS_BUDGET')
    o={};new_times=[];fixed_peaks=[];new_peaks=[];motion_energy=0.;original_motion_t=0.
    for name in PHASES:
        original_t=p['t_'+name];q0=old[name+'_flow_supply'];energy=old[name+'_supply_energy']/efficiency
        axis_power=old[name+'_supply_power']/efficiency
        supply=p['supply_return'] if name=='return' else p['supply_eject'] if name=='eject' else p['supply_work']
        # Explicit additional-consumer reservation applies to the common electrical input.
        qlimit=max(0.,available)*efficiency/supply
        q=min(q0,qlimit)
        stroke=old[name+'_speed']*original_t
        if q0==0:
            time=original_t;ratio=0.;speed=0.
        elif available<=0:
            time=None;ratio=0.;speed=0.
        else:
            time=max(original_t,energy/available);ratio=original_t/time;speed=stroke/time
        if time is not None:new_times.append(time)
        # Blocked mode does not publish a finite phase time or cycle as a schedule.
        fields={'time':time,'speed':None if time is None else speed,'qin_limit':qlimit,
                'qin':None if time is None else q,'qout':None if time is None else old[name+'_flow_return']*ratio,
                'power_axis':None if time is None else axis_power*ratio,
                'power_total_bound':None if time is None else axis_power*ratio+reserve,
                'fixed_times_power_bound':axis_power+reserve}
        for key,value in fields.items():o[name+'_'+key]=value
        fixed_peaks.append(axis_power+reserve)
        if time is not None:new_peaks.append(axis_power*ratio+reserve)
        motion_energy+=energy;original_motion_t+=original_t
    original_cycle=old['cycle_budget']
    motion_t=sum(new_times) if len(new_times)==len(PHASES) else None
    cycle=None if reason or motion_t is None else motion_t+p['t_hold']+pause_t
    bounded_energy=None if cycle is None else motion_energy+reserve*motion_t+allocation['hold_total_cap']*p['t_hold']+allocation['pause_total_cap']*pause_t
    fixed_energy_bound=motion_energy+reserve*original_motion_t+allocation['hold_total_cap']*p['t_hold']+allocation['pause_total_cap']*pause_t
    actuals_known=all(x is not None for x in (hold_power,motion_extra,pause_power))
    known_fixed_energy=None if not actuals_known else motion_energy+motion_extra*original_motion_t+hold_power*p['t_hold']+pause_power*pause_t
    actual_budget_energy=None if not actuals_known or cycle is None else motion_energy+motion_extra*motion_t+hold_power*p['t_hold']+pause_power*pause_t
    o.update(fixed_budget_cycle=cycle,fixed_budget_mass_rate=None if cycle is None else p['mass']/cycle,
             fixed_budget_peak_bound=None if cycle is None else max(*new_peaks,allocation['hold_total_cap'],allocation['pause_total_cap']),
             fixed_budget_energy_bound=bounded_energy,
             fixed_budget_average_bound=None if cycle is None else bounded_energy/cycle,
             fixed_times_cycle=original_cycle,fixed_times_mass_rate=p['mass']/original_cycle,
             fixed_times_required_peak_bound=max(*fixed_peaks,allocation['hold_total_cap'],allocation['pause_total_cap']),
             fixed_times_energy_bound=fixed_energy_bound,fixed_times_average_bound=fixed_energy_bound/original_cycle,
             known_motion_energy=motion_energy,known_motion_load_work=old['load_work_total'],
             known_motion_conversion_loss=motion_energy-old['load_work_total'],
             original_power_margin=budget-old['electric_power_peak'],
             fixed_times_average_lower_bound=motion_energy/original_cycle)
    flags={'original_scenario':'INCOMPATIBLE_WITH_ORIGINAL_BUDGET' if old['electric_power_peak']>budget else 'MOTION_WITHIN_BUDGET_HOLD_NOT_ESTABLISHED',
           'fixed_budget_status':'BLOCKED' if reason else 'CONDITIONAL_ON_UNVERIFIED_POWER_ENVELOPES',
           'blockers':reason,'fixed_times_status':'REQUIRES_SEPARATE_SUPPLY_RESOURCE_NOT_APPROVED' if o['fixed_times_required_peak_bound']>budget else 'CONDITIONAL_RESOURCE_BOUND_WITHIN_ORIGINAL_BUDGET',
           'actual_hold_power':hold_power,'actual_motion_extra_power':motion_extra,'actual_pause_power':pause_power,
           'actual_fixed_budget_energy':actual_budget_energy,
           'actual_fixed_budget_average':None if actual_budget_energy is None else actual_budget_energy/cycle,
           'actual_fixed_times_energy':known_fixed_energy,
           'actual_fixed_times_average':None if known_fixed_energy is None else known_fixed_energy/original_cycle,
           'hold_adequacy':'INDETERMINATE' if hold_power is None else 'INSUFFICIENT_POWER' if hold_power>budget else 'NUMERICALLY_WITHIN_BUDGET',
           'actual_whole_machine_feasibility':'INDETERMINATE',
           'B_open_permission':legacy_flags['B_open_permission'],
           'architecture_approved':False,'G1':'OPEN'}
    if any('EXCEEDS_ALLOCATION' in x for x in reason):
        for key in ('fixed_times_required_peak_bound','fixed_times_energy_bound','fixed_times_average_bound'):o[key]=None
        flags['fixed_times_status']='BLOCKED_ENVELOPE_MISMATCH'
    return o,flags


def unit(key):
    if key.endswith('time') or key.endswith('cycle'):return 's'
    if key.endswith('speed'):return 'm/s'
    if 'qin' in key or 'qout' in key:return 'm^3/s'
    if 'mass_rate' in key:return 'kg/s'
    if 'energy' in key or key in ('known_motion_load_work','known_motion_conversion_loss'):return 'J'
    return 'W'


def run(write=False):
    params=flatten(yaml.safe_load((ROOT/'params/registry.yaml').read_text()))
    identity=json.loads((OUT/'inputs/identity.json').read_text())
    for name,h in identity['frozen_files'].items():
        if sha256(ROOT/name)!=h:raise ValueError('frozen source changed '+name)
    for name,h in identity['original_engineering_hashes'].items():
        if engineering_sha(params[name])!=h:raise ValueError('original definition changed '+name)
    cases=json.loads((LEGACY/'cases.json').read_text())
    allocation_refs=json.loads((OUT/'allocation.json').read_text());allocation={}
    for name,k in allocation_refs.items():
        e=params[k]
        if e['unit']!='W' or e['lifecycle']!='ASSUMED' or e['validity']!='CURRENT':raise ValueError('allocation definition')
        allocation[name]=e['value']
    docs={};rows=[];files={}
    artifacts=[LEGACY/'cases.json',OUT/'allocation.json',OUT/'inputs/r5_review.txt',OUT/'inputs/identity.json']
    for case in cases:
        refs=case['parameters'];values={}
        for name,k in refs.items():
            e=params[k]
            if e['unit']!=INPUT_UNITS[name] or e['validity']!='CURRENT' or e['lifecycle']!='ASSUMED':raise ValueError('source input')
            values[name]=e['value']
        result,flags=reconcile(values,case['variant'],allocation)
        outputs=[]
        for name,value in result.items():
            key='R3P_'+case['id']+'_'+name.upper();e=params[key]
            if value is None or e['value']!=value or e['unit']!=unit(name):raise ValueError('registered result mismatch '+key)
            outputs.append(dict(parameter_ref(key,e),value=value,unit=e['unit']))
            rows.append(dict(scenario=case['id'],quantity=name,value_SI=format(value,'.17g'),unit=e['unit'],parameter_id=key,revision=e['revision']))
        deps=list(dict.fromkeys([*refs.values(),*allocation_refs.values()]))
        subset={'schema_version':'1.1','project_id':'REV','mode':'PROJECT','units_policy':'SI','domains':{name:{} for name in ('brochure_boundary','process_medium','kinematics_and_drive','aero_thermo_fluid','geometry_mass','strength_safety_factors')}}
        subset['domains']['kinematics_and_drive']={k:params[k] for k in deps+[x['id'] for x in outputs]}
        snap_bytes=yaml.safe_dump(subset,allow_unicode=True,sort_keys=False).encode();digest=hashlib.sha256(snap_bytes).hexdigest();snap='evidence/snapshots/'+digest+'.yaml'
        files[ROOT/snap]=snap_bytes
        docs[case['id']]={'schema_version':'1.1','scope':'REV_R3_POWER_RECONCILIATION_WHAT_IF_ONLY',
            'inputs':[dict(parameter_ref(k,params[k]),value=params[k]['value'],unit=params[k]['unit']) for k in deps],
            'outputs':outputs,'registry_snapshot':snap,'registry_sha256':digest,
            'script_sha256':sha256(Path(__file__)),'code_files':[dict(path=k,sha256=sha256(ROOT/k)) for k in CODE],
            'artifacts':[dict(path=str(k.relative_to(ROOT)),sha256=sha256(k)) for k in artifacts],
            'environment':dict(python=platform.python_version(),pyyaml=yaml.__version__),'conclusions':flags}
    text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    files[OUT/'scenarios.csv']=text.getvalue().encode()
    for name,doc in docs.items():files[OUT/'results'/f'{name}.json']=(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode()
    for path,content in files.items():
        if write:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        elif path.suffix=='.json':
            expected=json.loads(content);actual=json.loads(path.read_bytes());expected['environment']=actual['environment']
            if expected!=actual:raise ValueError('saved output differs '+str(path))
        elif path.read_bytes()!=content:raise ValueError('saved artifact differs '+str(path))
    print(f'{len(cases)} original incompatible cases, two explicit alternatives each, {len(rows)} registered scalar outputs; '+('saved' if write else 'verified without writes'))
    return docs


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true')
    run(parser.parse_args().write)
