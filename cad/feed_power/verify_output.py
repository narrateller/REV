"""Read-only revision verifier; no generation/manifest/report writes."""
import collections,subprocess,sys,os
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
from common import *


def functional(data,scenes):
    old=load(ROOT/'cad/frame_mount/inputs.assumed.json')
    for k,r in old['config'].items():assert data['config'][k]==r and data['parameters'][r]==old['parameters'][r],('working/service baseline config changed',k)
    oldby={c['id']:c for c in old['components']};newby={c['id']:c for c in data['components']}
    for n in ('doser_slide','punch','rod','cylinder_barrel','inlet_gate','lock','end_stop'):
        assert oldby[n]==newby[n] and bounds(old,oldby[n])==bounds(data,newby[n]),('moving body changed',n)
    def aperture(d,prefix):
        by={c['id']:bounds(d,c) for c in d['components']}
        if prefix=='pocket':a,b,c,e=('pocket_rear','pocket_front','pocket_L','pocket_R')
        else:a,b,c,e=(prefix+'_rear',prefix+'_front',prefix+'_left',prefix+'_right')
        return [[by[a][1][0],by[b][0][0]],[by[c][1][1],by[e][0][1]]]
    route={tag:aperture(data,tag) for tag in ('hopper_floor','doser_floor','pocket')}
    overlap_xy=[[max(a[i][0] for a in route.values()),min(a[i][1] for a in route.values())] for i in range(2)]
    assert all(lo<hi for lo,hi in overlap_xy),'material throat disconnected'
    support_min=None;guide_min=None;checked_rows=0
    for s in scenes:
        for st in s['stages']:
            body=st['state']['doser_slide']
            if body['delta'] is None or F(body['delta'][2]) or F(body['lo'][2])!=bounds(data,newby['doser_floor_right'])[1][2]:continue
            floors=[st['state'][n] for n in ('doser_floor_left','doser_floor_right','doser_tray_inner','doser_tray_outer')];guides=[st['state'][n] for n in ('doser_guide_L_inner','doser_guide_L_outer')]
            # Breakpoints where the moving Y edges cross any fixed support edge.
            events={F(0),F(1)};dy=F(body['delta'][1])
            if dy:
                for support in floors+guides:
                    for key in ('lo','hi'):
                        for edge in ('lo','hi'):
                            u=(F(support[key][1])-F(body[edge][1]))/dy
                            if 0<u<1:events.add(u)
            for u in events:
                lo=[F(x)+u*F(d) for x,d in zip(body['lo'],body['delta'])];hi=[F(x)+u*F(d) for x,d in zip(body['hi'],body['delta'])]
                floor_area=sum(max(F(0),min(hi[0],F(f['hi'][0]))-max(lo[0],F(f['lo'][0])))*max(F(0),min(hi[1],F(f['hi'][1]))-max(lo[1],F(f['lo'][1]))) for f in floors)
                guide_area=sum(max(F(0),min(hi[1],F(g['hi'][1]))-max(lo[1],F(g['lo'][1])))*max(F(0),min(hi[2],F(g['hi'][2]))-max(lo[2],F(g['lo'][2]))) for g in guides)
                assert floor_area>0 and guide_area>0,('support/guide coverage lost',s['case'],st['phase'],str(u))
                support_min=floor_area if support_min is None else min(support_min,floor_area);guide_min=guide_area if guide_min is None else min(guide_min,guide_area)
            checked_rows+=1
    return {'working_body_and_config_unchanged':True,'route_apertures_xy_m':{k:[[str(x) for x in a] for a in v] for k,v in route.items()},'common_positive_throat_xy_m':[[str(x) for x in a] for a in overlap_xy],'horizontal_stages_checked':checked_rows,'minimum_nominal_lower_support_area_m2':str(support_min),'minimum_nominal_one_side_guide_area_m2':str(guide_min),'scope':'nominal geometric continuity only; legacy float boundary differences retained explicitly, raw feed behavior and joint strength UNKNOWN'}


def main():
    try:
        n=verify_manifest();frozen=freeze();data=load(INPUT);generation=json.loads((OUT/'generation.json').read_text());assert generation['execution']=={'status':'COMPLETED','exit_code':0}
        assert generation['input_sha256']==digest(INPUT)
        for name,h in frozen['sha256'].items():assert subprocess.check_output(['git','show',frozen['reference']+':'+name],cwd=ROOT)==(ROOT/name).read_bytes(),name
        actual=check_cad_adapter(data,OUT,INPUT);assert actual==json.loads((OUT/'cad_validation.json').read_text())
        work=read_packed(OUT/'raw_checked_tool/all_pairs.json.gz');suite=evaluate_suite(work,data);assert suite['status']=='PASS' and suite==json.loads((OUT/'cycles.json').read_text())
        assert verify_cycles(work,data)==json.loads((OUT/'cycle_assertions.json').read_text())
        all_services=read_packed(OUT/'service_scenes.json.gz');assert len(all_services)==22
        for s in all_services:
            assert s['continuity_status']=='CONTINUOUS' and s['positions_restored']
            assert checked.continuity_status(checked.assess_continuity(s['stages'],[]))=='CONTINUOUS'
            initial=s['stages'][0]['state'];last=checked.advance(s['stages'][-1]['state']);assert set(initial)==set(last) and all(initial[k]['lo']==last[k]['lo'] and initial[k]['hi']==last[k]['hi'] for k in initial)
        scenes=work+all_services;coverage=0
        for s in scenes:
            for st in s['stages']:
                expected=list(itertools.combinations(sorted(st['state']),2));assert [tuple(r['pair']) for r in st['pairs']]==expected
                coverage+=len(expected)
        inv=json.loads((OUT/'inventory/inventory.json').read_text());nonclear=set();positive=set();counts=collections.Counter();bad_new=[]
        with gzip.open(OUT/'classifications.jsonl.gz','rt') as stream:
            for line in stream:
                r=json.loads(line);counts[r['class']]+=1
                if r['class']!='CLEAR':nonclear.add((r['variant'],tuple(r['pair'])))
                if r['class'] in ('PENETRATION','NATIVE_PENETRATION_WITNESS'):
                    # Synthetic injected obstacle collision cases are explicit controls.
                    if 'research_obstacle' in r['pair']:continue
                    assert r['case']=='service_doser_slide' and tuple(r['pair']) in LEGACY,('unexpected positive',r)
                    positive.add((r['variant'],tuple(r['pair'])))
        assert sum(counts.values())==coverage and nonclear=={(r['variant'],tuple(r['pair'])) for r in inv['rows']}
        assert positive=={(v,p) for v in 'AB' for p in LEGACY}
        remaining=[r for r in inv['rows'] if r['classification']=='NATIVE_PENETRATION'];assert len(remaining)==6
        assert all(r['disposition']=='BLOCKED_LEGACY_STRAIGHT_UP' for r in remaining)
        evidence=json.loads((OUT/'interval_evidence.json').read_text());assert evidence['all_pair_rows']==coverage
        rows=read_packed(OUT/'interval_rows.json.gz');assert len(rows)==evidence['audited_critical_rows']
        changed=set(evidence['changed_body_IDs']);cursor=0
        for s in scenes:
            for st in s['stages']:
                for pair in itertools.combinations(sorted(st['state']),2):
                    if not critical_pair(pair,changed):continue
                    assert cursor<len(rows),'missing critical row'
                    r=rows[cursor];cursor+=1
                    assert (r['variant'],r['case'],r['phase'],tuple(r['pair']))==(s['variant'],s['case'],st['phase'],pair),'critical interval coverage/order/duplicate'
        assert cursor==len(rows),'extra critical rows'
        legacy_positive=set()
        for r in rows:
            if r['status']=='POSITIVE_BOUND_OVERLAP':
                assert r['case']=='service_doser_slide' and tuple(r['pair']) in LEGACY
                legacy_positive.add((r['variant'],tuple(r['pair'])))
        assert legacy_positive=={(v,p) for v in 'AB' for p in LEGACY},'blocked UP evidence lost'
        compare=json.loads((OUT/'before_after_native.json').read_text());assert len(compare)==20
        assert sum(r['after']['common_volume_mm3']<=1e-5 for r in compare)==14
        interfaces=json.loads((OUT/'interfaces.json').read_text());assert len(interfaces)==2*len(joint_pairs()) and all(r['native_face_area_mm2']>0 and r['native']['common_volume_mm3']<=1e-5 for r in interfaces)
        assessment=json.loads((OUT/'assessment.json').read_text());assert assessment['whole_assembly_READY']=='INDETERMINATE'
        for s in assessment['scenes']:
            assert not s['target_penetration_rows']
            if s['case'].startswith('service_') and s['case']!='service_doser_slide':assert not s['service_moving_penetrations']
        functions=functional(data,scenes)
        print(json.dumps({'status':'PASS','scope':'new R4 adapter requires independent review; not whole press acceptance','publication_files':n,'frozen_modules_unchanged':len(frozen['sha256']),'native_CAD':{v:{'solids':x['solid_count'],'queries':x['query_count'],'status':x['status']} for v,x in actual.items()},'all_pair_rows':coverage,'static_pairs_removed':14,'remaining_native_pairs':6,'remaining_status':'BLOCKED legacy straight UP, no positive overlap on new ASSUMED service routes; actual service feasibility INDETERMINATE','service_sequences':22,'functions':functions,'whole_press_READY':'INDETERMINATE','physical_parameters':'UNKNOWN','physical_trials':'NOT_RUN','G1':'OPEN'},indent=2));return 0
    except Exception as e:
        print(json.dumps({'status':'FAIL','reason':str(e) or repr(e),'whole_press_READY':'INDETERMINATE','G1':'OPEN'},indent=2));return 1


if __name__=='__main__':sys.exit(main())
