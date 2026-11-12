"""Recompute and cross-check saved matrix/interval/classification/aggregation."""
import collections
from service_semantics import *
from assess import function_witness,scene_geometric_status


class ServiceValidationFailure(ValueError):
    def __init__(self,semantics,reason):super().__init__(reason);self.semantics=semantics


def require_expected(semantics):
    if semantics['test_evaluation']!='PASS':raise ServiceValidationFailure(semantics,'current service path/method/plan/evidence differs from its required outcome')


def verify_derived(data,work,services,semantics,evaluator):
    """Hashes are insufficient: compare every saved result with current poses."""
    scenes=work+services;changed=changed_bodies(data);coverage=0;cursor=0;rows=read_packed(OUT/'interval_rows.json.gz');counts=collections.Counter();positive=[];target_count=0;targets={tuple(sorted(p)) for p in TARGETS}
    for scene in scenes:
        for stage in scene['stages']:
            pairs=list(itertools.combinations(sorted(stage['state']),2));coverage+=len(pairs)
            assert [tuple(r['pair']) for r in stage['pairs']]==pairs,'pair matrix IDs/coverage'
            for pair in pairs:
                if not mandatory_pair(scene,pair,changed):continue
                assert cursor<len(rows),'missing mandatory interval row';r=rows[cursor];cursor+=1
                key=(r['variant'],r['case'],r['phase'],tuple(r['pair']));assert key==(scene['variant'],scene['case'],stage['phase'],pair),'interval evidence identity/order'
                proof=evaluator.proof(*(stage['state'][n] for n in pair));assert {k:v for k,v in r.items() if k not in ('variant','case','phase','pair')}==proof,('stale interval result',key)
                counts[proof['status']]+=1
                if pair in targets:target_count+=1
                if proof['status']=='POSITIVE_BOUND_OVERLAP':positive.append(r)
            actual=[evaluator.raw(scene['variant'],p,stage['state'],stage['time']) for p in pairs]
            assert actual==stage['pairs'],'stale calculated pair matrix'
            assert checked.summarize(actual)==stage['counts'],'stale pair-count aggregation'
    assert cursor==len(rows),'extra interval evidence'
    evidence=json.loads((OUT/'interval_evidence.json').read_text());assert evidence['all_pair_rows']==coverage and evidence['audited_critical_rows']==cursor
    assert evidence['changed_body_IDs']==sorted(changed),'saved changed-set is not derived from current inputs'
    assert evidence['counts']==dict(counts) and evidence['previous_target_rows']==target_count and evidence['legacy_vertical_positive_rows']==positive,'stale interval aggregation'
    assert all(r['case']=='service_doser_slide' and tuple(r['pair']) in LEGACY for r in positive)
    # Follow the original analyzer's traversal/priming so native sample metadata
    # (including its historical first-pose cache timestamp) is comparable.
    if evaluator.native is None:evaluator.native=NativeWitness(OUT)
    fresh_functions=function_witness(data,scenes,evaluator.native)
    assessment=json.loads((OUT/'assessment.json').read_text());assert assessment['function_witnesses']==fresh_functions,'stale function witnesses'
    indexed={(s['variant'],s['case']):s for s in assessment['scenes']};acc={};class_total=0
    expected=((s,st,p) for s in scenes for st in s['stages'] for p in itertools.combinations(sorted(st['state']),2))
    with gzip.open(OUT/'classifications.jsonl.gz','rt') as stream:
        for line in stream:
            saved=json.loads(line)
            try:scene,stage,pair=next(expected)
            except StopIteration:raise AssertionError('extra classification row')
            fresh=evaluator.classification(scene,stage,pair);assert saved==fresh,('stale classification',scene['variant'],scene['case'],stage['phase'],pair)
            class_total+=1;key=(scene['variant'],scene['case']);item=acc.setdefault(key,{'counts':collections.Counter(),'target_rows':0,'target_penetration_rows':0,'service_moving_penetrations':[]})
            item['counts'][fresh['class']]+=1
            if pair in targets:
                item['target_rows']+=1;item['target_penetration_rows']+=fresh['class'] in ('PENETRATION','ENVELOPE_INTERSECTION','NATIVE_PENETRATION_WITNESS')
            if scene['case'].startswith('service_') and any(is_moving(stage['state'][n]) for n in pair) and fresh['class'] in ('PENETRATION','ENVELOPE_INTERSECTION','NATIVE_PENETRATION_WITNESS'):item['service_moving_penetrations'].append({'phase':stage['phase'],'pair':list(pair),'class':fresh['class']})
    assert next(expected,None) is None,'missing classification row'
    assert set(indexed)==set(acc),'assessment scene coverage'
    for key,item in acc.items():
        scene=indexed[key]
        for field in ('counts','target_rows','target_penetration_rows','service_moving_penetrations'):assert scene[field]==item[field],('stale assessment',key,field)
        assert scene['geometric_scene_outcome']==scene_geometric_status(item['counts']),('stale aggregate geometry',key)
    assert json.loads((OUT/'service_semantics.json').read_text())==semantics,'saved service semantics stale'
    assert assessment==attach_assessment(assessment,semantics),'assessment service semantic fields stale'
    assert assessment.get('service_semantics')==semantics,'missing current assessment semantics'
    # The redundant serialized service source is independently tied to the same
    # current scenes; it cannot silently retain a different path.
    extra=read_packed(OUT/'work_and_extra.json.gz');service_by={(s['variant'],s['case']):s for s in services}
    assert [s for s in extra if not s['case'].startswith('service_')]==work,'work/source mismatch'
    expected_extra={(v,'service_cylinder_module') for v in 'AB'}|{(v,'service_fp_'+n) for v in 'AB' for n in plans(data)}
    actual_extra=[s for s in extra if s['case'].startswith('service_')];assert len(actual_extra)==len(expected_extra) and {(s['variant'],s['case']) for s in actual_extra}==expected_extra
    assert all(s==service_by[(s['variant'],s['case'])] for s in actual_extra),'divergent service copies'
    return {'matrix_pair_rows_recomputed':coverage,'interval_rows_recomputed':cursor,'classification_rows_recomputed':class_total,'all_saved_aggregates_current':True}
