"""Conditional reference arithmetic; not a BP500 reconstruction or REV design approval."""
import argparse
import json
import math
import platform
from pathlib import Path
import yaml
from repo_support import parameter_ref, sha256
ROOT = Path(__file__).resolve().parents[1]
# Universal conversion: standard gravity 9.80665 m/s². No measured material law.
FORMULAS = {
 'BP500_D_AREA': (['REF_BP500_WIDTH', 'REF_BP500_HEIGHT'], lambda w,h: w*h, 'reference width * height'),
 'BP500_D_VOL_MIN': (['BP500_D_AREA','REF_BP500_LENGTH_MIN'], lambda a,l:a*l, 'reference area * minimum product length'),
 'BP500_D_VOL_MAX': (['BP500_D_AREA','REF_BP500_LENGTH_MAX'], lambda a,l:a*l, 'reference area * maximum product length'),
 'BP500_D_MASS_RATE': (['REF_BP500_RATE','REF_BP500_MASS'], lambda n,m:n*m, 'stated product rate * stated product mass, same advertised condition assumed'),
 'BP500_D_INTERVAL': (['REF_BP500_RATE'], lambda n:1/n, 'inverse advertised product rate; NOT a cylinder cycle time'),
 'REV_D_FACE_AREA': (['REV_ASSUMED_WIDTH','REV_ASSUMED_HEIGHT'], lambda w,h:w*h, 'scenario rectangular projected face'),
 'REV_D_FACE_FORCE': (['REV_ASSUMED_SIGMA','REV_D_FACE_AREA'], lambda s,a:s*a, 'uniform scenario face stress * area; NOT measured force'),
 'REV_D_IDEAL_BORE': (['REV_D_FACE_FORCE','REV_ASSUMED_OIL_PRESSURE'], lambda f,p:math.sqrt(4*f/(math.pi*p)), 'ideal full bore, rod-side pressure zero, no friction/inertia/margin'),
 'BP500_D_IDEAL_FLOW': (['REF_BP500_MAIN_POWER','REF_BP500_OIL_MAX'], lambda w,p:w/p, 'ideal power/pressure at simultaneous conditions; NOT actual pump flow')
}
def read():
    d=yaml.safe_load((ROOT/'params/registry.yaml').read_text())
    return {k:v for domain in d['domains'].values() for k,v in domain.items()}
def recompute(p):
    values={k:v['value'] for k,v in p.items()}
    for key,(deps,fn,_) in FORMULAS.items():
        values[key]=fn(*(values[d] for d in deps))
    return values

def main(write):
    p=read()
    expected_units = {
        'REF_BP500_WIDTH':'m','REF_BP500_HEIGHT':'m',
        'REF_BP500_LENGTH_MIN':'m','REF_BP500_LENGTH_MAX':'m',
        'REF_BP500_RATE':'1/s','REF_BP500_MASS':'kg',
        'REF_BP500_MAIN_POWER':'W','REF_BP500_OIL_MAX':'Pa',
        'REV_ASSUMED_WIDTH':'m','REV_ASSUMED_HEIGHT':'m',
        'REV_ASSUMED_SIGMA':'Pa','REV_ASSUMED_OIL_PRESSURE':'Pa'}
    for key,unit in expected_units.items():
        e=p[key]
        if e['unit']!=unit or e['validity']!='CURRENT' or e['value'] is None or e['value']<=0:
            raise ValueError('Unavailable or incompatible input: '+key)
        if key.startswith('REV_ASSUMED_') and (e['lifecycle']!='ASSUMED' or e['scope']!='REV_RESEARCH_SCENARIO_ONLY'):
            raise ValueError('Unapproved change of scenario meaning: '+key)
    values=recompute(p)
    source=ROOT/'params/registry.yaml'; digest=sha256(source)
    snapshot=f'evidence/snapshots/{digest}.yaml'
    if write:
        path=ROOT/snapshot; path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and path.read_bytes()!=source.read_bytes():
            raise ValueError('Snapshot collision')
        path.write_bytes(source.read_bytes())
    for key,(deps,_,expression) in FORMULAS.items():
        assert math.isfinite(values[key]) and values[key]==p[key]['value'], key
        assert all(p[d]['value'] is not None and p[d]['validity']=='CURRENT' for d in deps)
        doc={'schema_version':'1.1','scope':p[key]['scope'], 'formula':expression,
             'inputs':[dict(parameter_ref(d,p[d]),value=p[d]['value'],unit=p[d]['unit']) for d in deps],
             'outputs':[dict(parameter_ref(key,p[key]),value=values[key],unit=p[key]['unit'])],
             'registry_snapshot':snapshot,'registry_sha256':digest,'script_sha256':sha256(Path(__file__)),
             'code_files':[{'path':f,'sha256':sha256(ROOT/f)} for f in p[key]['calculation']['code_files']],
             'artifacts':[{'path':'sources/raw/Target_object_BP500.pdf','sha256':sha256(ROOT/'sources/raw/Target_object_BP500.pdf')}],
             'environment':{'python':platform.python_version(),'pyyaml':yaml.__version__},
             'independent_review':False,'physical_validation':False}
        if write:
            (ROOT/p[key]['calculation']['output']).write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
        print(key,values[key],p[key]['unit'])
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--write',action='store_true')
    main(parser.parse_args().write)
