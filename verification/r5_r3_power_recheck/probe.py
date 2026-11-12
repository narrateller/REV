"""Independent Decimal oracle for the limited W01/W02 recheck.

Expected values are from force/volume/energy balances, not either author solver.
Synthetic overrides below are test fixtures, not new engineering parameters.
"""
from decimal import Decimal as D,getcontext
from pathlib import Path
import csv,hashlib,json,math,re,sys
import yaml
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts'))
from repo_support import flatten
getcontext().prec=50
PI=D('3.1415926535897932384626433832795028841971693993751')
PHASES=('approach','work','eject','return')
OUT=ROOT/'verification/r3_power_reconcile'
P=flatten(yaml.safe_load((ROOT/'params/registry.yaml').read_text()))
cases=json.loads((ROOT/'verification/r3_parametric_sizing/cases.json').read_text())
allocation={k:P[v]['value'] for k,v in json.loads((OUT/'allocation.json').read_text()).items()}

def oracle(raw,variant,alloc):
    p={k:D(str(v)) for k,v in raw.items()};a={k:D(str(v)) for k,v in alloc.items()}
    eta=p['eta_pump']*p['eta_motor'];face=p['width']*p['height'];r=1-p['kappa']**2
    slide=p['channel_slide'] if variant=='A' else D(0)
    peak=p['sigma_end']*face+slide+p['guide']
    eject=slide+p['guide'] if variant=='A' else p['eject_load_b']+p['guide']
    ret=p['return_load']+p['guide']
    cap=max((max(peak,p['guide'])+p['seal'])/(p['supply_work']-p['back_forward']*r),
            (eject+p['seal'])/(p['supply_eject']-p['back_forward']*r),
            (ret+p['seal'])/(p['supply_return']*r-p['back_return']))
    ann=cap*r;occupied=p['mass']/p['rho']/face
    strokes=[occupied/p['phi']-occupied,occupied-p['product_length'],p['eject_travel']]
    strokes.append(sum(strokes))
    forces=[p['guide'],(p['sigma_start']+p['sigma_end'])/2*face+slide+p['guide'],eject,ret]
    available=p['electric_limit']-a['motion_extra_cap']
    assert available>0
    o={};times=[];old_times=[];energies=[];old_powers=[];new_powers=[];work=D(0)
    for i,name in enumerate(PHASES):
        supply=p['supply_return'] if i==3 else p['supply_eject'] if i==2 else p['supply_work']
        ain,aout=(ann,cap) if i==3 else (cap,ann)
        volume=ain*strokes[i];e=supply*volume/eta;t0=p['t_'+name]
        # Derive constrained velocity directly from the power/area inequality.
        v0=strokes[i]/t0;vmax=available*eta/(supply*ain)
        v=min(v0,vmax);t=max(t0,strokes[i]/v) if strokes[i] else t0
        qin=ain*v;qout=aout*v;axis_power=supply*qin/eta;old_power=e/t0
        o.update({name+'_'+k:v for k,v in dict(time=t,speed=v,qin_limit=available*eta/supply,
                 qin=qin,qout=qout,power_axis=axis_power,power_total_bound=axis_power+a['motion_extra_cap'],
                 fixed_times_power_bound=old_power+a['motion_extra_cap']).items()})
        assert abs(qin*t-volume)<D('1e-40')
        assert abs(qout*t-aout*strokes[i])<D('1e-40')
        assert t>=t0 and v<=v0 and axis_power+a['motion_extra_cap']<=p['electric_limit']+D('1e-40')
        times.append(t);old_times.append(t0);energies.append(e);old_powers.append(old_power);new_powers.append(axis_power)
        work+=forces[i]*strokes[i]
    pause=p['t_aux_a'] if variant=='A' else p['t_unload_b']+p['t_open_b']
    cycle=sum(times)+p['t_hold']+pause;old_cycle=sum(old_times)+p['t_hold']+pause
    eaxis=sum(energies);eb=eaxis+a['motion_extra_cap']*sum(times)+a['hold_total_cap']*p['t_hold']+a['pause_total_cap']*pause
    et=eaxis+a['motion_extra_cap']*sum(old_times)+a['hold_total_cap']*p['t_hold']+a['pause_total_cap']*pause
    o.update(fixed_budget_cycle=cycle,fixed_budget_mass_rate=p['mass']/cycle,
             fixed_budget_peak_bound=max(max(new_powers)+a['motion_extra_cap'],a['hold_total_cap'],a['pause_total_cap']),
             fixed_budget_energy_bound=eb,fixed_budget_average_bound=eb/cycle,
             fixed_times_cycle=old_cycle,fixed_times_mass_rate=p['mass']/old_cycle,
             fixed_times_required_peak_bound=max(max(old_powers)+a['motion_extra_cap'],a['hold_total_cap'],a['pause_total_cap']),
             fixed_times_energy_bound=et,fixed_times_average_bound=et/old_cycle,
             known_motion_energy=eaxis,known_motion_load_work=work,known_motion_conversion_loss=eaxis-work,
             original_power_margin=p['electric_limit']-max(max(old_powers),p['supply_work']*p['leak_hold']/eta),
             fixed_times_average_lower_bound=eaxis/old_cycle)
    return {k:float(v) for k,v in o.items()}

def compare(expected,actual):
    assert set(expected)==set(actual),(set(expected)-set(actual),set(actual)-set(expected))
    for k,v in expected.items():assert math.isclose(v,actual[k],rel_tol=3e-13,abs_tol=1e-8),(k,v,actual[k])

records={};csvrows=list(csv.DictReader((OUT/'scenarios.csv').open()))
for c in cases:
    raw={k:P[v]['value'] for k,v in c['parameters'].items()};expected=oracle(raw,c['variant'],allocation)
    saved=json.loads((OUT/'results'/f"{c['id']}.json").read_text());prefix='R3P_'+c['id']+'_'
    actual={x['id'][len(prefix):].lower():x['value'] for x in saved['outputs']};compare(expected,actual)
    compare(expected,{row['quantity']:float(row['value_SI']) for row in csvrows if row['scenario']==c['id']})
    f=saved['conclusions']
    assert f['original_scenario']=='INCOMPATIBLE_WITH_ORIGINAL_BUDGET'
    assert f['fixed_budget_status']=='CONDITIONAL_ON_UNVERIFIED_POWER_ENVELOPES'
    assert f['actual_whole_machine_feasibility']=='INDETERMINATE'
    for key in ('actual_hold_power','actual_motion_extra_power','actual_pause_power','actual_fixed_budget_energy','actual_fixed_budget_average','actual_fixed_times_energy','actual_fixed_times_average'):assert f[key] is None
    if c['variant']=='B':assert f['B_open_permission']=='INDETERMINATE'
    records[c['id']]={'inputs':raw,'parameter_ids':c['parameters'],'independent':expected,'conclusions':f}

display=[]
factors={'W':.001,'J':.001,'s':1,'kg/s':3600,'m^3/s':60000,'m/s':1}
for value,key,rev in re.findall(r'(-?\d+(?:\.\d+)?)\s+\[([A-Z0-9_]+)@(\d+)\]',(OUT/'report.md').read_text()):
    entry=P[key];assert entry['revision']==int(rev)
    factor=factors[entry['unit']];digits=len(value.split('.')[1]) if '.' in value else 0
    expected=entry['value']*factor
    assert abs(float(value)-expected)<=.50001*10**(-digits),(key,value,expected)
    display.append({'id':key,'printed':value,'unit':entry['unit'],'SI_value':entry['value'],'display_factor':factor})

# Import implementation only AFTER constructing all eight independent gold results.
from rev_power_reconcile import reconcile,assess_hold
base=records['BASE_A']['inputs'];tests=[]
def capture(name,raw=None,variant='A',alloc=None,expected_status=None,**actual_components):
    p={**base,**(raw or {})};a={**allocation,**(alloc or {})}
    o,f=reconcile(p,variant,a,**actual_components)
    if expected_status:assert f['fixed_budget_status']==expected_status,(name,f)
    assert f['actual_whole_machine_feasibility']=='INDETERMINATE'
    if variant=='B':assert f['B_open_permission']=='INDETERMINATE'
    if f['fixed_budget_status']=='BLOCKED':
        for k in ('fixed_budget_cycle','fixed_budget_mass_rate','fixed_budget_energy_bound','fixed_budget_average_bound','fixed_budget_peak_bound'):assert o[k] is None,(name,k)
    else:compare(oracle(p,variant,a),o)
    tests.append({'name':name,'overrides':raw or {},'variant':variant,'allocation':a,'actual_components':actual_components,'outputs':o,'conclusions':f})
    return o,f

long={k:1000. for k in ('t_approach','t_work','t_eject','t_return')}
holdtests=[]
def hold(name,expected_status,expected_power=None,**kw):
    h=assess_hold(base['supply_work'],base['eta_pump'],base['eta_motor'],**kw)
    assert h['status']==expected_status,(name,h)
    if expected_power is None:assert h['electric_power'] is None
    else:assert math.isclose(h['electric_power'],expected_power,rel_tol=3e-13)
    holdtests.append({'name':name,'inputs':kw,'outputs':h})
    return h

full=dict(mode='pressure_regulated',leakage=.001,pump_flow=.001,standby=0.,aux=0.,budget=30000.)
h=hold('original_W01_hold_deficit','NUMERIC_MODEL_ONLY',30000/.765,**full)
o,f=capture('original_R5_W01_exact',{**long,'leak_hold':.001},hold_power=h['electric_power'],expected_status='BLOCKED')
assert f['hold_adequacy']=='INSUFFICIENT_POWER' and 'HOLD_POWER_EXCEEDS_BUDGET' in f['blockers']
capture('direct_nonzero_leak_without_model',{**long,'leak_hold':.001},expected_status='BLOCKED')
assert tests[-1]['conclusions']['fixed_times_status']=='BLOCKED_ENVELOPE_MISMATCH'
assert tests[-1]['outputs']['fixed_times_required_peak_bound'] is None
h=hold('zero_leak_running_pump','NUMERIC_MODEL_ONLY',30000/.765+1500.,**{**full,'leakage':0.,'standby':500.,'aux':1000.})
capture('zero_leak_running_pump_blocks_long_cycle',long,hold_power=h['electric_power'],expected_status='BLOCKED')
for missing in ('mode','leakage','pump_flow','standby','aux'):
    args={k:v for k,v in full.items() if k!=missing};h=hold('missing_'+missing,'UNKNOWN',**args)
    capture('missing_'+missing+'_with_nonzero_legacy_leak',{**long,'leak_hold':.001},hold_power=h['electric_power'],expected_status='BLOCKED')
h=hold('insufficient_replenishment','INSUFFICIENT_REPLENISHMENT',**{**full,'pump_flow':.0005})
capture('insufficient_replenishment_not_zero',{**long,'leak_hold':.001},hold_power=h['electric_power'],expected_status='BLOCKED')
h=hold('isolated_nonzero_leak','PRESSURE_MAINTENANCE_NOT_ESTABLISHED',**{**full,'mode':'isolated_unloaded','unload_pressure':1e6})
capture('isolated_nonzero_leak_not_permitted',{**long,'leak_hold':.001},hold_power=h['electric_power'],expected_status='BLOCKED')
hold('isolated_unloaded_explicit_zero_leak','NUMERIC_MODEL_ONLY',1000/.765+1500.,**{**full,'mode':'isolated_unloaded','unload_pressure':1e6,'leakage':0.,'standby':500.,'aux':1000.})
hold('unmodelled_accumulator','UNKNOWN',**{**full,'mode':'accumulator'})
capture('no_motion_power',alloc={'motion_extra_cap':30000.},expected_status='BLOCKED')
capture('hold_cap_exceeds_budget',alloc={'hold_total_cap':31000.},expected_status='BLOCKED')
capture('pause_cap_exceeds_budget',alloc={'pause_total_cap':31000.},expected_status='BLOCKED')
for label,args in [('motion_extra',{'motion_extra':4000.}),('hold',{'hold_power':6000.}),('pause',{'pause_power':4000.})]:
    o,f=capture(label+'_envelope_mismatch',expected_status='BLOCKED',**args)
    assert f['fixed_times_status']=='BLOCKED_ENVELOPE_MISMATCH'
    for k in ('fixed_times_required_peak_bound','fixed_times_energy_bound','fixed_times_average_bound'):assert o[k] is None
capture('compound_no_motion_hold_and_pause_mismatch',{'leak_hold':.001},alloc={'motion_extra_cap':30000.},hold_power=40000.,pause_power=4000.,expected_status='BLOCKED')
capture('mixed_limited_and_target_time_phases',{'t_work':1000.})
capture('zero_approach_preserves_target_interval',{'phi':1.})
capture('unity_efficiency_boundary',{'eta_pump':1.,'eta_motor':1.})
capture('ample_explicit_budget_preserves_target_Q_v_t',{'electric_limit':1e6},variant='B')
capture('explicit_zero_envelopes_are_not_actual_measurements',alloc={'motion_extra_cap':0.,'hold_total_cap':0.,'pause_total_cap':0.})
for key in ('hold_total_cap','pause_total_cap'):
    o,f=capture(key+'_dominates_fixed_times_peak',alloc={key:1e6},expected_status='BLOCKED')
    assert o['fixed_times_required_peak_bound']==1e6
    a={**allocation,key:1e6}
    e=o['known_motion_energy']+a['motion_extra_cap']*6+a['hold_total_cap']*base['t_hold']+a['pause_total_cap']*base['t_aux_a']
    assert math.isclose(o['fixed_times_energy_bound'],e,rel_tol=3e-13)
capture('hold_power_exactly_at_budget',alloc={'hold_total_cap':30000.},hold_power=30000.)
o,f=capture('all_numeric_components_close_energy',hold_power=4000.,motion_extra=2000.,pause_power=1000.)
motion=sum(o[n+'_time'] for n in PHASES)
assert math.isclose(f['actual_fixed_budget_energy'],o['known_motion_energy']+2000*motion+4000*base['t_hold']+1000*base['t_aux_a'],rel_tol=3e-13)
assert f['actual_fixed_budget_energy']<=o['fixed_budget_energy_bound']
assert math.isclose(f['actual_fixed_times_energy'],o['known_motion_energy']+2000*6+4000+1000,rel_tol=3e-13)

invalid=[]
for key in ('motion_extra_cap','hold_total_cap','pause_total_cap'):
    for value in (-1.,float('nan'),True,None):
        try: reconcile(base,'A',{**allocation,key:value})
        except ValueError:invalid.append({'field':key,'value':str(value),'result':'ValueError'})
        else:raise AssertionError((key,value))
print(json.dumps({'scope':'LIMITED_ARITHMETIC_RECHECK_NOT_PHYSICAL_VALIDATION','method':'50-digit Decimal balances; velocity from power inequality; p*dV energy; no author solver for expected values',
                  'registered_scalar_comparisons':sum(len(v['independent']) for v in records.values()),'csv_rows':len(csvrows),'printed_values_checked':len(display),
                  'allocation':allocation,'cases':records,'display_checks':display,'reconcile_probes':tests,'hold_probes':holdtests,'invalid_probes':invalid},ensure_ascii=False,indent=2,allow_nan=False))
