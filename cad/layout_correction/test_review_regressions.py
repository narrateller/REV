"""Corrected expectations for independent R5 counterexamples and compounds."""
import copy,gzip,itertools,json,unittest,os,hashlib
from pathlib import Path
from assess import checked,classify,scene_geometric_status,box_at,ROOT
from outcomes import assess_scene,evaluate_suite
from verify_cycles import verify_cycles
from layout_common import load


def box(x,motion='linear'):
    return {'lo':[str(x),'0','0'],'hi':[str(x+1),'1','1'],'delta':['0','0','0'],'motion':motion,'exact_box':True,'group':'test'}


def classifier_cases():
    cases=[]
    for mode in ('rotation','spline',None):
        for x in (0,4):
            state={'moving':box(0,mode),'wall':box(x)};row=checked.evaluate_pair(*state.values(),'moving','wall',['0','1'],'A')
            result=classify(row,state,['0','1'],'A');cases.append({'id':'motion_'+str(mode)+'_wall_'+str(x),'actual':result,'expected':'INDETERMINATE','matches':result['class']=='INDETERMINATE' and bool(result.get('reason')) and result.get('exact_box_sign_coverage')!='complete checked event partition'})
    base={'moving':box(0),'wall':box(4)};raw=checked.evaluate_pair(*base.values(),'moving','wall',['0','1'],'A')
    for kind in ('delta_unknown','bad_extent','forged_clear_rotation','empty_evidence','gapped_evidence','raw_unknown','unknown_region','missing_body'):
        state=copy.deepcopy(base);row=copy.deepcopy(raw)
        if kind=='delta_unknown':state['moving']['delta']=None
        if kind=='bad_extent':state['moving']['hi'][0]='-1'
        if kind=='forged_clear_rotation':state['moving']['motion']='rotation';row['status']='CLEAR'
        if kind=='empty_evidence':row['evidence']['segments']=[]
        if kind=='gapped_evidence':row['evidence']['segments'][1]['from']='1/2'
        if kind=='raw_unknown':row['evidence']['input_status']='INDETERMINATE'
        if kind=='unknown_region':row['evidence']['segments'][1]['collision_status']='INDETERMINATE'
        if kind=='missing_body':del state['wall']
        result=classify(row,state,['0','1'],'A');cases.append({'id':kind,'actual':result,'expected':'INDETERMINATE','matches':result['class']=='INDETERMINATE' and bool(result.get('reason'))})
    state={'a':box(0),'b':box(0),'rotating':box(4,'rotation')};rows=[];counts={}
    for a,b in itertools.combinations(state,2):
        raw=checked.evaluate_pair(state[a],state[b],a,b,['0','1'],'A');row=classify(raw,state,['0','1'],'A');rows.append(row);counts[row['class']]=counts.get(row['class'],0)+1
    cases.append({'id':'confirmed_penetration_plus_unsupported_motion','actual':{'status':scene_geometric_status(counts),'counts':counts,'pairs':rows},'expected':'BLOCKED with unknown preserved','matches':scene_geometric_status(counts)=='BLOCKED' and counts.get('PENETRATION',0)>0 and counts.get('INDETERMINATE',0)>0})
    return cases


def scene_cases():
    data=load(ROOT/'cad/layout_correction/inputs.assumed.json');scenes=json.loads(gzip.decompress((ROOT/'cad/build/layout_correction/raw_checked_tool/all_pairs.json.gz').read_bytes()));rows=[]
    for v in 'AB':
        original=copy.deepcopy(next(s for s in scenes if s['variant']==v and s['case']=='sufficient'))
        for field in ('required_link','path_transition','continuity_status','path_ready'):
            values={'required_link':('LINK_ABSENT','LINK_INDETERMINATE',None),'path_transition':('BLOCKED','INDETERMINATE',None),'continuity_status':('BLOCKED','INDETERMINATE',None),'path_ready':('NOT_CONFIRMED',None)}[field]
            for value in values:
                scene=copy.deepcopy(original);scene[field]=value;result=assess_scene(scene,data)
                rows.append({'id':v+'_reported_'+field+'_'+str(value),'actual':result,'expected':'not successful sufficient','matches':not result['matches_expectation'] and not result['limited_cycle_success']})
        for mode in ('missing_READY','missing_remove','ghost_CREATE','time_gap','return_discontinuity','summary_forged_after_missing_return'):
            scene=copy.deepcopy(original)
            if mode=='missing_READY':scene['stages'].pop()
            if mode=='missing_remove':scene['lifecycle']=[]
            if mode=='ghost_CREATE':scene['lifecycle'].append({'type':'CREATE','id':'ghost','time':'0'})
            if mode=='time_gap':scene['stages'][1]['time'][0]='3/2'
            if mode=='return_discontinuity':scene['stages'][-1]['state']['punch']['lo'][0]='9'
            if mode=='summary_forged_after_missing_return':scene['stages']=scene['stages'][:4 if v=='A' else 8]
            result=assess_scene(scene,data);rejected=False
            payload=list(scenes);payload[next(i for i,s in enumerate(payload) if s['variant']==v and s['case']=='sufficient')]=scene
            try:verify_cycles(payload,data)
            except (AssertionError,KeyError,TypeError,ValueError):rejected=True
            rows.append({'id':v+'_'+mode,'actual':result,'independent_verifier_rejects':rejected,'expected':'reject altered cycle','matches':not result['matches_expectation'] and not result['limited_cycle_success'] and rejected})
        shifted=copy.deepcopy(data);ref=next(c for c in shifted['components'] if c['id']=='product_'+v)['position'][0];shifted['parameters'][ref]['value']='0.16'
        scene=checked.scenario(shifted,v,'sufficient');result=assess_scene(scene,shifted)
        rows.append({'id':'R5_actual_unlinked_'+v,'actual':result,'expected':'BLOCKED / LINK_ABSENT, not successful sufficient','matches':result['geometric_scene_outcome']=='BLOCKED' and result['recomputed']['required_link']=='LINK_ABSENT' and not result['matches_expectation'] and not result['limited_cycle_success']})
        compound=copy.deepcopy(scene);compound['continuity_status']='INDETERMINATE';result=assess_scene(compound,shifted)
        rows.append({'id':'unlinked_plus_unknown_continuity_'+v,'actual':result,'expected':'BLOCKED with unknown not hiding lost link','matches':result['geometric_scene_outcome']=='BLOCKED' and result['recomputed']['required_link']=='LINK_ABSENT' and not result['limited_cycle_success']})
        compound=copy.deepcopy(next(s for s in scenes if s['variant']==v and s['case']=='collision'));compound['required_link']='LINK_INDETERMINATE';result=assess_scene(compound,data)
        rows.append({'id':'collision_plus_unknown_link_'+v,'actual':result,'expected':'BLOCKED with collision preserved','matches':result['geometric_scene_outcome']=='BLOCKED' and result['recomputed']['path_collision']=='COLLISION' and not result['limited_cycle_success']})
    return rows


def save_observations(name,rows):
    directory=os.environ.get('REV_ANALYSIS_EVIDENCE_DIR')
    if directory:
        target=Path(directory);target.mkdir(parents=True,exist_ok=True)
        data=ROOT/'cad/layout_correction/inputs.assumed.json'
        (target/(name+'.json')).write_text(json.dumps({'scope':'corrected independent R5 regression fixtures, separate from run input scene outcomes','fixture_input_sha256':hashlib.sha256(data.read_bytes()).hexdigest(),'case_count':len(rows),'status':'PASS' if all(r['matches'] for r in rows) else 'FAIL','cases':rows},indent=2)+'\n')


class ReviewRegressions(unittest.TestCase):
    def test_method_and_evidence_counterexamples(self):
        rows=classifier_cases();save_observations('classifier_regressions',rows)
        for r in rows:
            with self.subTest(case=r['id']):self.assertTrue(r['matches'],r)
    def test_scene_contract_and_compounds(self):
        rows=scene_cases();save_observations('cycle_regressions',rows)
        for r in rows:
            with self.subTest(case=r['id']):self.assertTrue(r['matches'],r)
    def test_all_eight_expectations_and_outcomes_are_distinct(self):
        data=load(ROOT/'cad/layout_correction/inputs.assumed.json');scenes=json.loads(gzip.decompress((ROOT/'cad/build/layout_correction/raw_checked_tool/all_pairs.json.gz').read_bytes()));r=evaluate_suite(scenes,data)
        self.assertEqual(r['status'],'PASS');self.assertEqual(sum(s['limited_cycle_success'] for s in r['scene_results']),2)
        self.assertTrue(all(s['geometric_scene_outcome']!='LIMITED_READY_CONFIRMED' for s in r['scene_results'] if s['case']!='sufficient'))
        self.assertEqual(len(verify_cycles(scenes,data)),8)
    def test_box_at_never_extrapolates_rotation(self):
        self.assertIsNone(box_at(box(0,'rotation'),'1/2',['0','1']))


if __name__=='__main__':unittest.main()
