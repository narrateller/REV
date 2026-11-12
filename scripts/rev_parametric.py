"""Conditional REV arithmetic; no component selection or physical validation.

Default: recompute and verify committed outputs, without writing.
--write: explicitly save reproducible scenario tables/evidence (not CAD).
"""
import argparse
import hashlib
import csv
import io
import json
import math
import platform
from pathlib import Path
import yaml
from repo_support import flatten, parameter_ref, sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/r3_parametric_sizing'
CODE = ['scripts/rev_parametric.py', 'scripts/repo_support.py']
INPUT_UNITS = {
 'width':'m','height':'m','product_length':'m','mass':'kg','rho':'kg/m^3','phi':'1',
 'sigma_start':'Pa','sigma_end':'Pa','kappa':'1','supply_work':'Pa','supply_eject':'Pa',
 'supply_return':'Pa','back_forward':'Pa','back_return':'Pa','channel_slide':'N',
 'channel_hold':'N','rebound':'N','guide':'N','seal':'N','return_load':'N','eject_load_b':'N',
 'eject_travel':'m','clearance':'m','eta_pump':'1','eta_motor':'1','electric_limit':'W',
 'leak_hold':'m^3/s','t_approach':'s','t_work':'s','t_eject':'s','t_return':'s',
 't_hold':'s','t_aux_a':'s','t_unload_b':'s','t_open_b':'s'}


def solve(p, variant):
    """SI, direct drive, one dose/product, quasi-static linear stress law.

    p contains only scalar values; actual unknowns are not assigned by this API.
    Return scalar engineering outputs and discrete conditional conclusions.
    """
    positive = ['width','height','product_length','mass','rho','phi','sigma_end',
                'kappa','supply_work','supply_eject','supply_return','t_approach',
                't_work','t_eject','t_return','eta_pump','eta_motor','eject_travel','electric_limit']
    nonnegative = ['sigma_start','channel_slide','channel_hold','rebound','guide',
                   'seal','return_load','eject_load_b','back_forward','back_return',
                   'clearance','t_hold','t_aux_a','t_unload_b','t_open_b','leak_hold']
    for k in positive + nonnegative:
        if type(p.get(k)) not in (int,float) or not math.isfinite(p[k]):
            raise ValueError('nonfinite/missing/invalid '+k)
        if p[k] < 0 or (k in positive and p[k] == 0):
            raise ValueError('invalid sign '+k)
    if variant not in ('A','B'): raise ValueError('variant')
    if not 0 < p['kappa'] < 1 or not 0 < p['phi'] <= 1:
        raise ValueError('invalid area/fill ratio')
    if not 0 < p['eta_pump'] <= 1 or not 0 < p['eta_motor'] <= 1:
        raise ValueError('invalid efficiency')
    if p['sigma_start'] > p['sigma_end']: raise ValueError('stress must not decrease in this ramp')
    a = p['width']*p['height']
    volume = p['mass']/(p['rho']*p['phi'])
    chamber = volume/a
    occupied = p['phi']*chamber
    work = occupied-p['product_length']
    if work < 0: raise ValueError('loaded material shorter than specified final product')
    approach = chamber-occupied
    channel = p['channel_slide'] if variant == 'A' else 0.
    f0 = p['sigma_start']*a+channel+p['guide']
    f1 = p['sigma_end']*a+channel+p['guide']
    fe = channel+p['guide'] if variant == 'A' else p['eject_load_b']+p['guide']
    fr = p['return_load']+p['guide']
    ratio = 1-p['kappa']**2
    effective = [p['supply_work']-p['back_forward']*ratio,
                 p['supply_eject']-p['back_forward']*ratio,
                 p['supply_return']*ratio-p['back_return']]
    if min(effective) <= 0: raise ValueError('nonpositive effective pressure')
    # Size to the worst of approach/work, ejection and reverse load, including seal.
    ab = max((max(f1,p['guide'])+p['seal'])/effective[0],
             (fe+p['seal'])/effective[1],(fr+p['seal'])/effective[2])
    aa = ratio*ab
    bore=math.sqrt(4*ab/math.pi); rod=p['kappa']*bore
    travel=approach+work+p['eject_travel']
    o = {'area':a,'chamber_volume':volume,'chamber_length':chamber,
         'occupied_length':occupied,'approach_stroke':approach,'work_stroke':work,
         'return_stroke':travel,'eject_stroke':p['eject_travel'],
         'product_density':p['mass']/(a*p['product_length']),
         'force_work_start':f0,'force_work_peak':f1,'force_eject':fe,
         'force_return_required':fr,'bore':bore,'rod':rod,'bore_area':ab,'annulus_area':aa,
         'force_extension_capacity':p['supply_work']*ab-p['back_forward']*aa-p['seal'],
         'force_return_capacity':p['supply_return']*aa-p['back_return']*ab-p['seal'],
         'mass_residual':p['rho']*p['phi']*volume-p['mass'],
         'A_hold_margin':p['channel_hold']-p['rebound'] if variant=='A' else 0.,
         'B_stop_peak_reaction':p['sigma_end']*a if variant=='B' else 0.,
         'eject_required_geometry':p['product_length']+p['clearance'],
         'eject_geometry_margin':p['eject_travel']-p['product_length']-p['clearance']}
    energy=useful=seal=backloss=valveloss=0.; maxq=maxp=0.; bounded_time=0.
    phase_specs=[('approach',approach,p['t_approach'],p['guide'],p['supply_work'],False),
                 ('work',work,p['t_work'],(f0+f1)/2,p['supply_work'],False),
                 ('eject',p['eject_travel'],p['t_eject'],fe,p['supply_eject'],False),
                 ('return',travel,p['t_return'],fr,p['supply_return'],True)]
    for name,s,t,load,ps,reverse in phase_specs:
        inlet,outlet=(aa,ab) if reverse else (ab,aa)
        pb=p['back_return'] if reverse else p['back_forward']
        speed=s/t; qi=inlet*speed; qo=outlet*speed
        pc=(load+p['seal']+pb*outlet)/inlet
        ein=ps*qi*t; euse=load*s; eseal=p['seal']*s
        eback=pb*qo*t; evalve=(ps-pc)*qi*t
        if evalve < -1e-7: raise ValueError('phase demands more than available supply')
        for key,value in {'speed':speed,'flow_supply':qi,'flow_return':qo,
                          'mean_chamber_pressure':pc,'supply_power':ps*qi,
                          'supply_energy':ein,'load_work':euse,
                          'seal_loss':eseal,'back_loss':eback,'valve_loss':evalve}.items():
            o[name+'_'+key]=value
        tmin=ein/(p['electric_limit']*p['eta_pump']*p['eta_motor'])
        o[name+'_minimum_time_power']=tmin
        bounded_time+=max(t,tmin)
        energy+=ein;useful+=euse;seal+=eseal;backloss+=eback;valveloss+=evalve
        maxq=max(maxq,qi);maxp=max(maxp,ps*qi)
    hold_e=p['supply_work']*p['leak_hold']*p['t_hold']
    energy+=hold_e
    pump_loss=energy*(1/p['eta_pump']-1)
    motor_loss=energy/p['eta_pump']*(1/p['eta_motor']-1)
    elec=energy+pump_loss+motor_loss
    aux=p['t_aux_a'] if variant=='A' else p['t_unload_b']+p['t_open_b']
    cycle=sum(t for _,_,t,_,_,_ in phase_specs)+p['t_hold']+aux
    o.update({'hold_loss':hold_e,'hydraulic_energy':energy,'load_work_total':useful,
              'seal_loss_total':seal,'back_loss_total':backloss,'valve_loss_total':valveloss,
              'pump_loss':pump_loss,'motor_loss':motor_loss,'electric_energy':elec,
              'modeled_heat':elec-useful,'hydraulic_energy_residual':energy-useful-seal-backloss-valveloss-hold_e,
              'electric_energy_residual':elec-useful-seal-backloss-valveloss-hold_e-pump_loss-motor_loss,
              'flow_peak':max(maxq,p['leak_hold']),'hydraulic_power_peak':max(maxp,p['supply_work']*p['leak_hold']),
              'electric_power_peak':max(maxp,p['supply_work']*p['leak_hold'])/p['eta_pump']/p['eta_motor'],
              'cycle_budget':cycle,'cycle_budget_power_limited':bounded_time+p['t_hold']+aux,
              'electric_power_margin':p['electric_limit']-max(maxp,p['supply_work']*p['leak_hold'])/p['eta_pump']/p['eta_motor'],'conditional_mass_rate':p['mass']/cycle,
              'electric_power_average':elec/cycle})
    # NaN/inf must never be published as engineering results.
    if not all(math.isfinite(x) for x in o.values()): raise ValueError('nonfinite result')
    flags={'scenario_only':True,'physical_validation':False,'component_selection':False,
           'A_hold_arithmetic': ('NONNEGATIVE_MARGIN' if o['A_hold_margin']>=0 else 'INSUFFICIENT') if variant=='A' else 'NOT_APPLICABLE',
           'B_open_permission':'INDETERMINATE' if variant=='B' else 'NOT_APPLICABLE',
           'B_residual_stop_force':None,'B_allowed_open_reaction':None,
           'ejection_geometry_arithmetic':'ENOUGH_AXIAL_TRAVEL' if o['eject_geometry_margin']>=0 else 'SHORT_TRAVEL',
           'power_budget_arithmetic':'EXCEEDS_ASSUMED_LIMIT' if o['electric_power_margin']<0 else 'WITHIN_ASSUMED_LIMIT',
           'whole_cycle_feasibility':'INDETERMINATE'}
    if variant=='A':o.pop('B_stop_peak_reaction')
    else:o.pop('A_hold_margin')
    return o,flags


def unit(key):
    if key=='mass_residual':return 'kg'
    if key in ('bore','rod') or 'stroke' in key or 'length' in key or key.startswith('eject_required') or key=='eject_geometry_margin':return 'm'
    if key in ('area','bore_area','annulus_area'):return 'm^2'
    if key=='chamber_volume':return 'm^3'
    if key=='product_density':return 'kg/m^3'
    if key=='conditional_mass_rate':return 'kg/s'
    if key.startswith('cycle_budget') or key.endswith('minimum_time_power'):return 's'
    if 'flow' in key:return 'm^3/s'
    if 'speed' in key:return 'm/s'
    if 'pressure' in key:return 'Pa'
    if 'power' in key:return 'W'
    if 'force' in key or 'reaction' in key or key=='A_hold_margin':return 'N'
    return 'J'


def run(write=False):
    registry=ROOT/'params/registry.yaml'; params=flatten(yaml.safe_load(registry.read_text()))
    cases=json.loads((OUT/'cases.json').read_text())
    inputs=[{'path':str(p.relative_to(ROOT)),'sha256':sha256(p)} for p in sorted((OUT/'inputs').iterdir())]
    tables=[];docs={}
    snapshots={}
    for case in cases:
        refs=case['parameters']; values={}
        for name,k in refs.items():
            e=params[k]
            if e['lifecycle']!='ASSUMED' or e['validity']!='CURRENT' or e['scope']!='REV_R3_WHAT_IF_ONLY':
                raise ValueError('invalid input scope/status '+k)
            if e['unit']!=INPUT_UNITS[name]:raise ValueError('incompatible input unit '+k)
            values[name]=e['value']
        results,flags=solve(values,case['variant'])
        outputs=[]
        for key,v in results.items():
            k='R3_'+case['id']+'_'+key.upper();e=params[k]
            if e['unit']!=unit(key) or e['value']!=v:raise ValueError('registry differs '+k)
            outputs.append(dict(parameter_ref(k,e),value=v,unit=e['unit']))
            tables.append({'scenario':case['id'],'variant':case['variant'],'quantity':key,'value_SI':format(v,'.17g'),'unit':e['unit'],'parameter_id':k,'revision':e['revision']})
        subset={'schema_version':'1.1','project_id':'REV','domains':{'kinematics_and_drive':{k:params[k] for k in list(dict.fromkeys(refs.values()))+[x['id'] for x in outputs]}}}
        snapshot_bytes=yaml.safe_dump(subset,allow_unicode=True,sort_keys=False).encode()
        snapshot_hash=hashlib.sha256(snapshot_bytes).hexdigest()
        snapshot='evidence/snapshots/'+snapshot_hash+'.yaml';snapshots[snapshot]=snapshot_bytes
        docs[case['id']]={'schema_version':'1.1','scope':'REV_R3_CONDITIONAL_ARITHMETIC_ONLY',
            'inputs':[dict(parameter_ref(k,params[k]),value=params[k]['value'],unit=params[k]['unit']) for k in dict.fromkeys(refs.values())],
            'outputs':outputs,'registry_snapshot':snapshot,'registry_sha256':snapshot_hash,
            'script_sha256':sha256(Path(__file__)),'code_files':[{'path':p,'sha256':sha256(ROOT/p)} for p in CODE],
            'artifacts':inputs+[{'path':str((OUT/'cases.json').relative_to(ROOT)),'sha256':sha256(OUT/'cases.json')}],
            'environment':{'python':platform.python_version(),'pyyaml':yaml.__version__},'conclusions':flags}
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(tables[0]),lineterminator='\n');writer.writeheader();writer.writerows(tables)
    files={OUT/'scenarios.csv':stream.getvalue()}
    for name,doc in docs.items():files[OUT/'results'/f'{name}.json']=json.dumps(doc,ensure_ascii=False,indent=2)+'\n'
    if write:
        for name,content in snapshots.items():
            (ROOT/name).parent.mkdir(parents=True,exist_ok=True);(ROOT/name).write_bytes(content)
        for path,content in files.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
    else:
        for name,content in snapshots.items():
            if (ROOT/name).read_bytes()!=content:raise ValueError('snapshot differs')
        for path,content in files.items():
            stored=path.read_text()
            # Environment metadata is retained from generation, not a demand for identical host versions.
            if path.suffix=='.json':
                old=json.loads(stored);new=json.loads(content);new['environment']=old['environment']
                if old!=new:raise ValueError('saved output differs '+str(path))
            elif stored!=content:raise ValueError('saved table differs')
    print(f'{len(cases)} conditional cases, {len(tables)} registered scalar outputs; '+('saved' if write else 'recomputed and verified without writes'))
    return docs


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true')
    run(parser.parse_args().write)
