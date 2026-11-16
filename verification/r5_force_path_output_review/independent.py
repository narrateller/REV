"""R5 oracle: Decimal arithmetic and rational statics, independent of compare.py.

Run from any directory with the repository .venv interpreter. Fixtures below
are mathematical tests, never proposed REV dimensions or engineering tolerances.
"""
from pathlib import Path
from decimal import Decimal as D, getcontext
from fractions import Fraction as Q
import hashlib
import importlib.util
import json
import subprocess
import sys
import copy

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
C = '93b4aead4983f88919d8e8b4165e29d7f3246600'
H = 'aadc08a70fbaee16b7ba4c16463bab97275926bb'
SESSION = 'r5-force-path-output-20261116'
BASE = '1dce280bf4c6a790ef0ace10a757fe0a72148b5f'
getcontext().prec = 60
PI = D('3.14159265358979323846264338327950288419716939937510582097494459')
def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])
def blob(commit, path):
    return git('show', commit + ':' + path)
def js(path):
    return json.loads(blob(C, path))
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def flat(data):
    return {k:v for domain in data['domains'].values() for k,v in domain.items()}
def eng(p):
    # Match the documented engineering definition, not the author's calculator.
    fields = ('revision','value','unit','tolerance','uncertainty','scope','meaning',
              'provenance','depends_on','calculation')
    return sha(json.dumps({k:p.get(k) for k in fields}, sort_keys=True,
                         ensure_ascii=False, separators=(',',':'), allow_nan=False).encode())

def run():
    checks = []
    def check(name, condition, evidence):
        checks.append(dict(id=name, result='PASS' if condition else 'FAIL', evidence=evidence))
        assert condition, name
    git('merge-base','--is-ancestor', C, H)
    changed = git('diff','--name-only', C,H).decode().splitlines()
    check('H_scope', set(changed)=={'STATE.md','NEXT_MODEL.md',
          'handoffs/T-r3-force-path-01/r3-force-path-20261114.md'}, changed)
    pre = js('verification/r3_force_path/analysis/preflight.json')
    inputs=[]
    for item in pre['inputs']:
        p=item['path']; hashes=[sha(blob(x,p)) for x in (item['commit'],BASE,C,H)]
        check('pinned:'+p, all(x==item['sha256'] for x in hashes)
              and sha((ROOT/p).read_bytes())==item['sha256'], hashes)
        inputs.append(p)
    trees={}
    for p,expected in pre['protected_trees'].items():
        ids=[git('rev-parse',x+':'+p).decode().strip() for x in (BASE,C,H)]
        check('tree:'+p, all(x==expected for x in ids),ids)
        trees[p]=ids
    authored=git('ls-tree','-r','--name-only',C,'verification/r3_force_path/analysis').decode().splitlines()
    check('author_worktree_unchanged',all((ROOT/p).read_bytes()==blob(C,p) for p in authored),len(authored))
    path='verification/r4_cycle_interfaces/proposal/baseline_bindings.json'
    bindings=js(path)
    check('44_full_bindings', len(bindings['rows'])==44 and bindings==js(
          'verification/r3_force_path/analysis/baseline_snapshot.json'), 'full objects, ordered rows')
    import yaml
    original=flat(yaml.safe_load(blob(C,'params/registry.yaml')))
    case=flat(yaml.safe_load(blob(C,'verification/r3_force_path/analysis/params/registry.yaml')))
    check('case_originals', all(case[k]==v for k,v in original.items()), len(original))
    new={k:v for k,v in case.items() if k not in original}
    calc={k:v for k,v in new.items() if v['lifecycle']=='CALCULATED'}
    gaps={k:v for k,v in new.items() if v['lifecycle']=='RAW'}
    check('26_calculated_84_unknown',len(calc)==26 and len(gaps)==84 and
          all(v['value'] is None and v['unknown_reason'] and v['verifier'] is None for v in gaps.values()),
          {'calculated':len(calc),'unknown':len(gaps)})
    check('independence',all(SESSION not in v['author_sessions'] for v in new.values()),SESSION)
    values=[]
    for letter in 'AB':
        rows=[r for r in bindings['rows'] if r['scenario']=='BASE_'+letter]
        check('22_bindings_'+letter,len(rows)==22,'full fixed-budget source definitions')
        v={r['proposed_cad_field']:D(str(r['value'])) for r in rows}
        for r in rows:
            p=original[r['parameter_id']]
            check('binding:'+letter+':'+r['proposed_cad_field'],
                  all(p[k]==r[k] for k in ('revision','value','unit','lifecycle','validity'))
                  and r['mode']=='fixed-budget' and eng(p)==r['engineering_sha256'],r)
            source=js(r['source']); refs=source['inputs']+source['outputs']
            ref=next(x for x in refs if x['id']==r['parameter_id'])
            check('source:'+letter+':'+r['proposed_cad_field'],
                  all(ref[k]==r[k] for k in ('revision','value','unit','engineering_sha256')),r['source'])
        radius=v['cylinder.rod_diameter']/2
        area=PI*radius**2
        work=v['load.work_peak']; back=v['load.return_required']
        expected={
          'ROD_AREA':(area,'m2'),
          'ROD_WORK_STRESS':(-work/area,'Pa'),
          'ROD_RETURN_STRESS':(back/area,'Pa'),
          'PUNCH_MEAN_WORK_PRESSURE':(work/v['chamber.width']/v['chamber.height'],'Pa'),
          'IDEAL_WORK_N':(-work,'N'),'IDEAL_RETURN_N':(back,'N'),
          'WORK_MZ_PER_E':(-work,'N'),'RETURN_MZ_PER_E':(back,'N'),
          'WORK_R0_PER_E_OVER_A':(-work,'N'),'WORK_R1_PER_E_OVER_A':(work,'N'),
          'RETURN_R0_PER_E_OVER_A':(back,'N'),'RETURN_R1_PER_E_OVER_A':(-back,'N'),
          'EULER_BOUNDARY_COEFF':(work/PI**2,'N')}
        result=js('verification/r3_force_path/analysis/results_'+letter+'.json')
        check('snapshot_hash_'+letter,sha(blob(C,result['registry_snapshot']))==result['registry_sha256'],result['registry_sha256'])
        for f in result['code_files']+result['artifacts']:
            check('hash:'+letter+':'+f['path'],sha(blob(C,f['path']))==f['sha256'],f['sha256'])
        for row in result['outputs']:
            key=row['id']; name=key[len('R3F_'+letter+'_'):]; number,unit=expected[name]
            actual=D(str(row['value'])); relative=abs(actual-number)/max(abs(number),D(1))
            check(key,relative<D('3e-15') and row['unit']==unit and calc[key]['value']==row['value']
                  and calc[key]['unit']==unit and eng(calc[key])==row['engineering_sha256'],{'expected':str(number),'observed':str(actual),'unit':unit,'relative_error':str(relative)})
            values.append(checks[-1])
        check('actual_unknown_'+letter,not result['architecture_selected'] and
              result['physical_feasibility']=='INDETERMINATE' and all(
              x is None or x=='UNKNOWN' for x in result['actual_results'].values()),result['actual_results'])
    states=js('verification/r3_force_path/analysis/state_matrix.json')
    check('42_states',len(states)==42 and {r['variant'] for r in states}=={'A-V1','A-V2','B-V1','B-V2'} and all(
          r['actual_force_N'] is None and r['actual_moment_Nm'] is None and
          r['actual_joint_support_loads'] is None and r['reaction_available']=='UNKNOWN' and r['result']=='UNKNOWN'
          for r in states),'10 A states and 11 B states per topology')
    # Independent rational statics: solve the two equilibrium equations rather
    # than invoke the author's coefficients. r=(0,e_y,e_z), F=(F_x,0,0).
    spec=importlib.util.spec_from_file_location('reviewed_compare',ROOT/'verification/r3_force_path/analysis/compare.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    for force in (Q(17),Q(-7),Q(0)):
        for ey in (Q(2,7),Q(-2,7),Q(0)):
            a=Q(5,3); ez=Q(3,11)
            mz=-ey*force; my=ez*force
            r1=-mz/a; r0=-r1
            check('rational_balance:'+str((force,ey)),r0+r1==0 and a*r1+mz==0 and
                  -force+force==0 and ey*force-a*r1==0,
                  {'My':str(my),'Mz':str(mz),'R0':str(r0),'R1':str(r1),'frame_moment_residual':'0'})
            got=mod.eccentric_transfer(float(force),float(ey),float(a))
            check('implementation_balance:'+str((force,ey)),all(abs(got[k]-float(x))<1e-12 for k,x in
                  zip(('applied_Mz_Nm','guide_R0_N','guide_R1_N'),(mz,r0,r1))),got)
    check('unknown_offset',all(v is None for v in mod.eccentric_transfer(17,None,2).values()),'UNKNOWN != e=0')
    check('unknown_span',mod.eccentric_transfer(17,0,None)['guide_R0_N'] is None,'known zero moment does not define physical support')
    for i in range(4):
        args=[3,5,2,7];args[i]=None
        check('unknown_euler:'+str(i),mod.euler_capacity(*args) is None,'missing argument -> null')
    # Euler benchmark derives P from the pinned-pinned first sine eigenmode.
    capacity=float(PI**2*D(3)*D(5)/D(14)**2)
    check('euler_eigenmode',abs(mod.euler_capacity(3,5,2,7)-capacity)<1e-14 and
          abs(mod.euler_capacity(3,5,2,14)-capacity/4)<1e-14,'P=EI*(pi/L_eff)^2; fixture only')
    for bad in (True,'1',float('nan'),float('inf'),0,-1):
        try: mod.euler_capacity(bad,1,1,1)
        except ValueError: rejected=True
        else: rejected=False
        check('invalid_E:'+repr(bad),rejected,'must reject')
    params=original
    for label,mutate in (
        ('missing',lambda r:r.pop()),
        ('mode',lambda r:r[0].update(mode='fixed-times')),
        ('dimension',lambda r:r[0].update(unit='kg')),
        ('value',lambda r:r[0].update(value=None)),
        ('hash',lambda r:r[0].update(engineering_sha256='0'*64)),
        ('duplicate',lambda r:r.__setitem__(0,copy.deepcopy(r[1])))):
        rows=copy.deepcopy(bindings['rows']);mutate(rows)
        try:mod.validate_bindings(rows,params)
        except (ValueError,TypeError):rejected=True
        else:rejected=False
        check('mutation:'+label,rejected,'independent in-memory mutation; no source writes')
    output=dict(reviewed_C=C,reviewed_H=H,reviewer_session=SESSION,method='Decimal 60 digits; rational equilibrium; immutable Git inputs',
                comparison_tolerance='3e-15 relative to max(abs(expected),1), numerical comparison only, not engineering acceptance',
                checks=checks,quantities=values,passed=len(checks),failed=0)
    (HERE/'independent_results.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print('PASS',len(checks),'checks;',len(values),'independently recalculated quantities')
if __name__=='__main__':run()
