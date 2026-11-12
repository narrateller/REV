"""Read-only verification of document chains and exact immutable source inputs.

--capture saves only this task's new CAD extract; never invokes CAD or solver builds.
"""
import argparse,hashlib,json,gzip,subprocess,sys
from fractions import Fraction as F
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from repo_support import flatten,engineering_sha
CAD='3591a5f92f78b1edea07d3fc5354fd0a99090798'
CALC='c115f75fd900525d9ddc89d85e097ac5a0f00bc1'
NAMES=('doser_slide','inlet_gate','punch','rod','lock','end_stop','product_A','product_B','clamp_L','clamp_R','channel_left','channel_right','chamber_bottom','chamber_left','chamber_right')

def blob(path):return subprocess.check_output(['git','show',CAD+':'+path],cwd=ROOT)
def digest(x):return hashlib.sha256(x).hexdigest()

def collect():
    files={};variants={}
    def load(name,compressed=False):
        raw=blob(name);files[name]=digest(raw);return json.loads(gzip.decompress(raw) if compressed else raw)
    for variant in 'AB':
        directory='cad/build/calculated_layout/'+variant
        scenes=load(directory+'/scenes.json.gz',True);scene=next(s for s in scenes if s['case']=='sufficient')
        result=load(directory+'/results.json');nominal=next(s for s in result['scene_results'] if s['case']=='sufficient')
        inp=load('cad/calculated_layout/inputs.BASE_'+variant+'.json')
        manifest=load(directory+'/manifest.json')
        phases={}
        for stage in scene['stages']:
            poses={name:{k:b.get(k) for k in ('lo','hi','delta','motion','exact_box')} for name,b in stage['state'].items() if name in NAMES}
            phases[stage['phase']]={'time':stage['time'],'permission':stage['permission'],'bodies':poses,
               'moving_bodies':[name for name,b in stage['state'].items() if b.get('delta') and any(F(x)!=0 for x in b['delta'])]}
        config={name:{'id':key,**inp['parameters'][key]} for name,key in inp['config'].items() if name in ('phase_duration','doser_fill_y','gate_isolate_y','open_lock_y','open_stop_y','exit_'+variant)}
        source_summary={k:scene[k] for k in ('product_rear_after_eject','r3_nominal_exit','actual_CAD_exit','fixed_budget_interval','fixed_budget_duration','registered_fixed_budget_cycle','full_diagnostic_duration','nominal_return','READY','product_removed','B_open_permission','scope')}
        rear=F(scene['product_rear_after_eject']);exit_=F(scene['actual_CAD_exit'])
        assert rear<F(exit_) and nominal['actual_output_geometry']=='SHORT_STROKE'
        assert rear>=F(scene['r3_nominal_exit'])
        assert all(p['permission']=='CONDITIONAL_DIAGNOSTIC_ONLY_NOT_PHYSICAL_AUTHORIZATION' for p in phases.values())
        bools={'rear_short_of_preserved_CAD_exit':rear<exit_,'rear_passes_simplified_R3_plane':rear>=F(scene['r3_nominal_exit']),
               'full_diagnostic_duration_exceeds_main_axis_budget':F(scene['full_diagnostic_duration'])>F(scene['registered_fixed_budget_cycle']),
               'material_state_is_preformed_product':('product_'+variant in scene['stages'][0]['state']),
               'no_product_remove_event':not scene['product_removed'] and not scene['lifecycle']}
        if variant=='B':
            assert not phases['B-UNLOAD']['moving_bodies']
            stage=phases['B-RESET-LOCK'];product=stage['bodies']['product_B'];stop=stage['bodies']['end_stop']
            bools['retained_product_intersects_closed_stop_bounds']=all(max(F(product['lo'][i]),F(stop['lo'][i]))<min(F(product['hi'][i]),F(stop['hi'][i])) for i in range(3))
            assert bools['retained_product_intersects_closed_stop_bounds']
        variants[variant]={'source_paths':{'scenes':directory+'/scenes.json.gz','results':directory+'/results.json','inputs':'cad/calculated_layout/inputs.BASE_'+variant+'.json','manifest':directory+'/manifest.json'},
            'summary':source_summary,'config':config,'exact_geometry':inp['exact_geometry'],'phases':phases,
            'author_reported_positive_pairs':nominal['proven_positive_pairs'],
            'author_reported_geometry':nominal['geometric_scene_outcome'],'checks_on_recorded_coordinates':bools,
            'native_rerun':'NOT_RUN; preserved author witnesses only, not independent BRep validation'}
    interfaces=load('verification/r4_calculated_layout/functional_interfaces.json')
    return {'CAD_C':CAD,'calculation_C':CALC,'input_blob_sha256':files,'variants':variants,'functional_interfaces':interfaces,
            'scope':'documentary consistency and exact recorded coordinates; no CAD rebuild/native replay/physical test'}

def verify():
    data=collect();assert data==json.loads((HERE/'cad_evidence.json').read_text()),'saved CAD extract mismatch'
    preflight=json.loads((HERE/'preflight.json').read_text())
    for item in preflight['input_blobs']:
        raw=subprocess.check_output(['git','show',item['commit']+':'+item['path']],cwd=ROOT)
        assert len(raw)==item['size_bytes'] and digest(raw)==item['sha256'],item['path']
    assert subprocess.check_output(['git','rev-parse',CAD+':cad/build/calculated_layout'],cwd=ROOT,text=True).strip()==preflight['CAD_tree']
    ledger=json.loads((HERE/'sources.json').read_text());assert len(ledger['sources'])==4
    for item in ledger['sources'].values():
        raw=(ROOT/item['path']).read_bytes();assert digest(raw)==item['sha256']
    claims=ledger['claims']
    for claim in claims.values():
        src=ledger['sources'][claim['source']]
        assert claim['locator'] and claim['applicability'] and claim['not_proven_for_REV']
        assert all(1<=page<=src['PDF_pages'] and page in src['substantive_read_pages'] for page in claim['pages'])
    rows=json.loads((HERE/'cycle_table.json').read_text());backlog=json.loads((HERE/'r4_backlog.json').read_text())
    params=flatten(yaml.safe_load((ROOT/'params/registry.yaml').read_text()))
    old=flatten(yaml.safe_load(subprocess.check_output(['git','show',CALC+':params/registry.yaml'],cwd=ROOT)))
    ids={x['id'] for x in backlog};assert len(ids)==len(backlog)
    assert len({row['id'] for row in rows})==len(rows),'duplicate row'
    graph={x['id']:x['depends_on'] for x in backlog}
    def visit(key,trail):
        assert key not in trail,'cyclic backlog dependency'
        for dep in graph[key]:visit(dep,trail+[key])
    for key in graph:visit(key,[])
    coverage={(v,s):False for v in 'AB' for s in ('load','isolate','press','hold_unload','eject','return','ready')}
    for row in rows:
        assert row['sources'] and row['conditions'] and row['variant'] and row['rev_hypothesis'] and row['parameters'] and row['cad'] and row['transition_required'] and row['evidence'] and row['gap']
        for source in row['sources']:assert source in claims and claims[source]['pages']
        for ref in row['parameters']:
            key=ref['id'];assert params[key]['revision']==ref['revision'] and engineering_sha(params[key])==ref['engineering_sha256']==engineering_sha(old[key])
            assert ref['value']==params[key]['value'] and ref['unit']==params[key]['unit'],key
        variant=row['variant']
        assert variant in 'AB'
        for phase in row['cad']['phases']:assert phase in data['variants'][variant]['phases'],phase
        for body in row['cad']['bodies']:assert any(body in st['bodies'] for st in data['variants'][variant]['phases'].values()),body
        for issue in row['backlog']:assert issue in ids
        if (variant,row['stage']) in coverage:coverage[(variant,row['stage'])]=True
        assert row['status'] in ('UNKNOWN','BLOCKED_IN_DECLARED_CAD_MODEL','ASSUMED_FUNCTIONAL_HYPOTHESIS_WITH_GAPS')
    assert all(coverage.values()),coverage
    for issue in backlog:
        assert issue['cause'] and issue['required_change'] and issue['acceptance'] and issue['sources']
        for source in issue['sources']:assert source in claims,source
        for dependency in issue['depends_on']:assert dependency in ids
        for row in issue['rows']:assert any(r['id']==row for r in rows),row
    # The complete current calculation definition and all original files are frozen.
    package=json.loads((ROOT/'verification/pr39_integration/preservation.json').read_text())
    preservation=package['protected_files']
    for name,record in preservation.items():assert digest((ROOT/name).read_bytes())==record['sha256'],name
    retained=json.loads((HERE/'result_preservation.json').read_text())['preserved_R5_files']
    assert len(retained)==45
    for name,record in retained.items():
        current=(ROOT/name).read_bytes()
        original=subprocess.check_output(['git','show',record['commit']+':'+name],cwd=ROOT)
        assert current==original and digest(current)==record['sha256'],name
    print(f'{len(rows)} cycle chains, 14 mandatory stage/variant cells, {len(claims)} source claims, {len(backlog)} R4 issues verified; {len(preservation)} calculation and {len(retained)} R5 files unchanged')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',action='store_true');args=p.parse_args()
    if args.capture:
        (HERE/'cad_evidence.json').write_text(json.dumps(collect(),ensure_ascii=False,indent=2)+'\n')
        print('Saved document-only CAD extract from exact Git blobs; original files untouched')
    else:verify()
