"""Separate read-only assertions; does not call the run_revision test oracle."""
import itertools
from assess import checked,box_at
from layout_common import config


def verify_cycles(scenes,data):
    assert len(scenes)==8 and {(s['variant'],s['case']) for s in scenes}=={(v,c) for v in 'AB' for c in ('sufficient','short','collision','unknown')}
    outputs=[]
    for s in scenes:
        v=s['variant'];case=s['case'];product='product_'+v
        want={
         'sufficient':('GEOMETRY_SUFFICIENT','NO_COLLISION','LINK_CONFIRMED','ALLOWED_FOR_PATH_SUBSET','CONTINUOUS','RESTORED_FOR_PATH_SUBSET'),
         'short':('SHORT_STROKE','NO_COLLISION','LINK_CONFIRMED','BLOCKED','CONTINUOUS','NOT_CONFIRMED'),
         'collision':('GEOMETRY_SUFFICIENT','COLLISION','LINK_CONFIRMED','BLOCKED','CONTINUOUS','NOT_CONFIRMED'),
         'unknown':('INDETERMINATE','INDETERMINATE','LINK_INDETERMINATE','INDETERMINATE','INDETERMINATE','NOT_CONFIRMED')}[case]
        observed=tuple(s.get(k) for k in ('geometry','path_collision','required_link','path_transition','continuity_status','path_ready'))
        assert observed==want,(v,case,'mandatory outcome',observed,want)
        stages=s['stages'];phases=[st['phase'] for st in stages];prefix=[v+'-'+name for name in ('READY','FILL','ISOLATE')]
        if v=='B':prefix+=['B-'+name for name in ('PRESS','UNLOAD','OPEN-LOCK','OPEN-STOP')]
        eject='A-PRESS-OUT' if v=='A' else 'B-EJECT';prefix+=[eject]
        expected=prefix+([v+'-RETURN']+(['B-RESET-STOP','B-RESET-LOCK'] if v=='B' else [])+[v+'-RESET-INLET',v+'-READY-RETURNED'] if case=='sufficient' else [])
        assert phases==expected,(v,case,'phase sequence')
        active=stages[len(prefix)-1];bodies=active['state'];time=active['time']
        proof=checked.evaluate_pair(bodies['punch'],bodies[product],'punch',product,time,v)
        assert proof['evidence']['link']==want[2],(v,case,'actual required link')
        pos=box_at(bodies[product],time[1],time)
        actual_geo='INDETERMINATE' if pos is None else 'GEOMETRY_SUFFICIENT' if pos[0][0]>=config(data,'exit_'+v) else 'SHORT_STROKE'
        assert actual_geo==want[0],(v,case,'actual exit')
        for stage in stages:
            names=sorted(stage['state']);pairs=[tuple(sorted(p['pair'])) for p in stage['pairs']]
            assert len(pairs)==len(set(pairs)) and set(pairs)==set(itertools.combinations(names,2)),(v,case,'complete pair matrix')
            assert checked.engine.q(stage['time'][0])<checked.engine.q(stage['time'][1])
            for name,body in stage['state'].items():
                if case=='unknown' and name==product and stage['phase']==eject:
                    assert body['motion']=='linear' and body['delta'] is None
                else:checked.engine.body(body)
        for left,right in zip(stages,stages[1:]):
            assert checked.engine.q(left['time'][1])==checked.engine.q(right['time'][0]),'time gap'
            before=left['state'];after=right['state'];removed=set(before)-set(after)
            assert not set(after)-set(before),'unexplained creation'
            assert removed==({product} if case=='sufficient' and left['phase']==eject else set()),'unexpected lifecycle'
            for name in set(before)&set(after):
                if before[name]['delta'] is None:
                    assert case=='unknown' and name==product
                    continue
                for key in ('lo','hi'):
                    assert all(checked.engine.q(x)+checked.engine.q(d)==checked.engine.q(y) for x,d,y in zip(before[name][key],before[name]['delta'],after[name][key])),(v,case,name,'discontinuity')
        if case=='sufficient':
            events=s['lifecycle'];assert len(events)==1 and events[0]['type']=='REMOVE' and events[0]['id']==product
            assert checked.engine.q(events[0]['time'])==checked.engine.q(time[1])
            assert checked.engine.q(events[0]['final_rear'])==pos[0][0]>=config(data,'exit_'+v)
            initial=stages[0]['state'];final=stages[-1]['state'];assert set(final)==set(initial)-{product}
            for name,b in final.items():assert b['lo']==initial[name]['lo'] and b['hi']==initial[name]['hi'] and b['delta']==['0','0','0'],(name,'not READY restored')
            contexts={product:{'exit_boundary':str(config(data,'exit_'+v)),'receiving_yz':[[initial[product]['lo'][i],initial[product]['hi'][i]] for i in (1,2)],'required_link':'LINK_CONFIRMED','path_collision':'NO_COLLISION'}}
            checked_continuity=checked.assess_continuity(stages,events,contexts)
            assert checked.continuity_status(checked_continuity)=='CONTINUOUS' and all(c['lifecycle_valid'] for c in checked_continuity),'unvalidated return/removal'
        else:assert s['lifecycle']==[],(v,case,'negative case removed a body')
        outputs.append({'variant':v,'case':case,'assertions':'PASS','geometric_scene_outcome':'LIMITED_READY_CONFIRMED' if case=='sufficient' else 'INDETERMINATE' if case=='unknown' else 'BLOCKED','whole_press_READY':'INDETERMINATE'})
    return outputs
