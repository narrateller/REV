"""Supplementary exact-inequality audit, separate from frozen event solver.

Author self-check, not an independent R5 review. Units: exact input metres.
"""
import collections, gzip, itertools, json, sys
from fractions import Fraction as F
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'cad/layout_correction'))
from assess import NativeWitness, checked, TARGETS
from layout_common import load, bounds, digest


def strict_interval(a,b):
    # Six strict affine inequalities on normalized [0,1]. At a singleton,
    # evaluate all inequalities so a touching endpoint is never penetration.
    if a.get('motion')!='linear' or b.get('motion')!='linear' or a.get('delta') is None or b.get('delta') is None:
        return {'status':'INDETERMINATE','reason':'unsupported/unknown linear displacement'}
    checked.engine.body(a);checked.engine.body(b)
    lo,hi=F(0),F(1)
    for i in range(3):
        for c,v in ((F(a['hi'][i])-F(b['lo'][i]),F(a['delta'][i])-F(b['delta'][i])),(F(b['hi'][i])-F(a['lo'][i]),F(b['delta'][i])-F(a['delta'][i]))):
            if not v:
                if c<=0:return {'status':'NO_POSITIVE_VOLUME_ON_INTERVAL'}
            elif v>0:lo=max(lo,-c/v)
            else:hi=min(hi,-c/v)
    positive=lo<hi or lo==hi and all(F(a['hi'][i])+lo*F(a['delta'][i])>F(b['lo'][i])+lo*F(b['delta'][i]) and F(b['hi'][i])+lo*F(b['delta'][i])>F(a['lo'][i])+lo*F(a['delta'][i]) for i in range(3))
    return {'status':'POSITIVE_BOUND_OVERLAP','normalized_boundary_values':[str(lo),str(hi)],'boundary_inclusion':'test strict inequalities; roots themselves not automatically included'} if positive else {'status':'NO_POSITIVE_VOLUME_ON_INTERVAL'}


def main():
    out=ROOT/'cad/build/frame_mount';data=load(ROOT/'cad/frame_mount/inputs.assumed.json');old=load(ROOT/'cad/layout_correction/inputs.assumed.json')
    scenes=json.loads(gzip.decompress((out/'raw_checked_tool/all_pairs.json.gz').read_bytes()))+json.loads(gzip.decompress((out/'service_scenes.json.gz').read_bytes()))
    previous=json.loads(gzip.decompress((ROOT/'cad/build/layout_correction/raw_checked_tool/all_pairs.json.gz').read_bytes()))
    changed=set(json.loads((out/'interval_evidence.json').read_text())['changed_body_IDs']);target={tuple(sorted(p)) for p in TARGETS}
    after_native=NativeWitness(out);before_native=NativeWitness(ROOT/'cad/build/layout_correction');results=[];targets=[];coverage=[];total=0;service=[];native_regression=[]
    try:
        for s in scenes:
            for st in s['stages']:
                expected=list(itertools.combinations(sorted(st['state']),2));actual=[tuple(r['pair']) for r in st['pairs']];total+=len(actual)
                if actual!=expected:coverage.append([s['variant'],s['case'],st['phase']])
                for a,b in expected:
                    selected=bool(changed.intersection((a,b)));regression=(a,b) in target
                    cylinder_service=s['case'] in ('service_cylinder_barrel','service_rod','service_cylinder_module') and bool({'cylinder_barrel','rod'}.intersection((a,b)))
                    if not (selected or regression or cylinder_service):continue
                    proof=strict_interval(st['state'][a],st['state'][b]);r={'variant':s['variant'],'case':s['case'],'phase':st['phase'],'pair':[a,b],**proof,'bounds_exact_boxes':all(st['state'][n]['exact_box'] for n in (a,b))}
                    if selected:results.append(r)
                    if regression:targets.append(r)
                    if cylinder_service:service.append(r)
        assert not coverage,coverage
        assert all(r['status']!='POSITIVE_BOUND_OVERLAP' for r in results+targets+service),'positive overlap in selected group'
        # Compare every old positive native frame/mount pair, not merely one example.
        pairs=[('crossbar'+str(i),rail) for i in range(3) for rail in ('side_rail_L','side_rail_R')]
        pairs += [('crossbar0','cylinder_mount_rear'),('crossbar2','output_support'),('cylinder_barrel','cylinder_mount_front')]
        comparisons=[]
        for v in 'AB':
            initial_before=checked.bodies(old,v);initial_after=checked.bodies(data,v)
            for pair in pairs:
                before=before_native.at(v,pair,initial_before,'0',['0','1']);after=after_native.at(v,pair,initial_after,'0',['0','1'])
                assert before['common_volume_mm3']>1e-5 and after['common_volume_mm3']<=1e-5,(v,pair,before,after)
                comparisons.append({'variant':v,'pair':pair,'before':before,'after':after})
        # Reproduce R5's exact former gate/lock/stop dynamic witness poses.
        historic=json.loads((ROOT/'verification/r5_layout_output_review/evidence/dynamic_probe.json').read_text())
        for row in historic:
            if tuple(sorted(row['pair'])) not in target:continue
            s=next(s for s in scenes if s['variant']==row['variant'] and s['case']=='sufficient');st=next(st for st in s['stages'] if st['phase']==row['phase'])
            w=after_native.at(row['variant'],row['pair'],st['state'],row['sample_time'],st['time']);assert w.get('common_volume_mm3',0)<=1e-5
            native_regression.append({'original_R5':row,'current_native':w})
        # Independent affine continuity and actual restored positions, no lifecycle deletions.
        continuity=[]
        for s in scenes:
            if not s['case'].startswith('service_'):continue
            for left,right in zip(s['stages'],s['stages'][1:]):
                assert F(left['time'][1])==F(right['time'][0]) and set(left['state'])==set(right['state'])
                for n in left['state']:
                    for field in ('lo','hi'):
                        assert all(F(x)+F(d)==F(y) for x,d,y in zip(left['state'][n][field],left['state'][n]['delta'],right['state'][n][field])),(s['case'],n,'gap')
            first,last=s['stages'][0]['state'],s['stages'][-1]['state']
            assert set(first)==set(last) and all(first[n]['lo']==last[n]['lo'] and first[n]['hi']==last[n]['hi'] and last[n]['delta']==['0','0','0'] for n in first)
            continuity.append({'variant':s['variant'],'case':s['case'],'continuity':'CONTINUOUS','return':'RESTORED_GEOMETRY','physical_access_and_safety':'UNKNOWN'})
        # Real bodies/inputs untouched outside this group; config/work motion invariant.
        old_by_id={c['id']:c for c in old['components']};new_by_id={c['id']:c for c in data['components']}
        unchanged=[n for n in old_by_id if n not in changed];assert all(old_by_id[n]==new_by_id[n] and bounds(old,old_by_id[n])==bounds(data,new_by_id[n]) for n in unchanged)
        assert old['config']==data['config'] and all(old['parameters'][r]==data['parameters'][r] for r in old['config'].values())
        summary={'scope':'author supplementary audit of fixed research geometry and specified trajectories; not independent acceptance','method':'exact strict affine inequalities over closed normalized [0,1], unsupported inputs INDETERMINATE','coverage_rows':total,'coverage_errors':coverage,'changed_group_rows':len(results),'changed_group_counts':dict(collections.Counter(r['status'] for r in results)),'previous_target_rows':len(targets),'previous_target_counts':dict(collections.Counter(r['status'] for r in targets)),'cylinder_service_rows':len(service),'cylinder_service_counts':dict(collections.Counter(r['status'] for r in service)),'before_after_native':comparisons,'former_R5_dynamic_witnesses':native_regression,'service_sequences':continuity,'unchanged_old_body_IDs':sorted(unchanged),'all_original_IDs_retained':set(old_by_id)<=set(new_by_id),'working_motion_config_unchanged':True,'physical_real_parameters':'UNKNOWN','whole_press_READY':'INDETERMINATE','G1':'OPEN','sources':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'cad/frame_mount/inputs.assumed.json']}}
        (out/'geometry_evidence.json').write_text(json.dumps(summary,indent=2)+'\n')
        with gzip.GzipFile(filename=str(out/'inequality_rows.json.gz'),mode='wb',mtime=0) as stream:stream.write(json.dumps({'changed_group':results,'previous_targets':targets,'cylinder_services':service},sort_keys=True,separators=(',',':')).encode())
        print(json.dumps({k:summary[k] for k in ('coverage_rows','changed_group_rows','changed_group_counts','previous_target_rows','cylinder_service_rows')}))
    finally:after_native.close();before_native.close()


if __name__=='__main__':main()
