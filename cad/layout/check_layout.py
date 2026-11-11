#!/usr/bin/env python3
"""Continuous research-box checks and explicit limitations of the CAD adapter."""
import argparse,copy,gzip,hashlib,importlib.util,itertools,json,sys,math
from pathlib import Path
from fractions import Fraction as F
from layout_common import load,value,selected,config,bounds,digest,ROOT
from layout_lifecycle import q,apply_boundary_events
from cad_validation import check_cad_adapter,CadValidationError
spec=importlib.util.spec_from_file_location('verified_scene_engine',ROOT/'models/rev_linked_scene/engine.py');engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)

def bodies(data,variant):
    result={}
    for c in selected(data,variant):
        lo,hi=bounds(data,c);result[c['id']]={'lo':[str(x) for x in lo],'hi':[str(x) for x in hi],'delta':['0','0','0'],'motion':'linear','exact_box':c['kind']=='box','group':c['group'],'rigid_group':c['rigid_group']}
    return result

def evaluate_pair(a,b,left,right,time,variant):
    contact=None
    if {left,right}=={'punch','product_'+variant}:
        if left!='punch':a,b=b,a
        contact={'allowed_time':time,'patch_yz':[[a['lo'][1],a['hi'][1]],[a['lo'][2],a['hi'][2]]],'direction':'either'}
    evidence=engine.pair(a,b,time,contact,time if contact else None, bool(contact))
    statuses=[row['collision_status'] for row in evidence['segments']]
    if 'INVALID_INPUT' in statuses or evidence['input_status']=='INVALID_INPUT': status='INVALID_INPUT'
    elif a['exact_box'] and b['exact_box'] and 'COLLISION' in statuses:status='COLLISION'
    elif any(row in ('INDETERMINATE',) for row in statuses):status='INDETERMINATE'
    elif not a['exact_box'] or not b['exact_box']:
        status='CLEAR' if statuses and all(x=='CLEAR' for x in statuses) else 'INDETERMINATE'
    else:status='COLLISION' if 'COLLISION' in statuses else 'ALLOWED_CONTACT' if 'ALLOWED_CONTACT' in statuses else 'CLEAR'
    return {'pair':[left,right],'status':status,'basis':'exact axis-aligned synthetic solids' if a['exact_box'] and b['exact_box'] else 'conservative bounding boxes: clear proves separation, overlap is not a solid collision proof','evidence':evidence}

def matrix(current,time,variant):
    return [evaluate_pair(current[a],current[b],a,b,time,variant) for a,b in itertools.combinations(sorted(current),2)]

def summarize(rows):return {status:sum(r['status']==status for r in rows) for status in ('CLEAR','ALLOWED_CONTACT','COLLISION','INDETERMINATE','INVALID_INPUT')}


def advance(current):
    result=copy.deepcopy(current)
    for name,b in result.items():
        if b['delta'] is None:continue
        b['lo']=[str(q(x)+q(d)) for x,d in zip(b['lo'],b['delta'])];b['hi']=[str(q(x)+q(d)) for x,d in zip(b['hi'],b['delta'])];b['delta']=['0','0','0']
    return result

def assess_continuity(stages, events, removal_conditions=None):
    checks=[];assigned=set()
    for left,right in zip(stages,stages[1:]):
        bad=[];unknown=[];boundary_events=[];time_valid=True
        try:
            ls,le=map(q,left['time']);rs,re=map(q,right['time'])
            time_valid=ls<le and rs<re and le==rs
            expected=advance(left['state'])
            for index,event in enumerate(events):
                try:
                    if isinstance(event,dict) and q(event.get('time'))==le:
                        boundary_events.append(event);assigned.add(index)
                except (TypeError,ValueError,ZeroDivisionError):pass
            _,audit=apply_boundary_events(expected,right['state'],str(le),boundary_events,removal_conditions)
            for name in sorted(set(expected)&set(right['state'])):
                if left['state'][name]['delta'] is None or right['state'][name]['delta'] is None:unknown.append(name)
                elif any(q(a)!=q(b) for key in ('lo','hi') for a,b in zip(expected[name][key],right['state'][name][key])):bad.append(name)
            checks.append({'from':left['phase'],'to':right['phase'],'time_contiguous':time_valid,'mismatches':bad,'unknown':unknown,'lifecycle_valid':audit['status']=='VALID','lifecycle_status':audit['status'],'lifecycle_audit':audit,'removed':sorted(set(expected)-set(right['state'])),'created':sorted(set(right['state'])-set(expected))})
        except (KeyError,TypeError,ValueError,ZeroDivisionError) as exc:
            checks.append({'from':left.get('phase'),'to':right.get('phase'),'time_contiguous':False,'mismatches':bad,'unknown':unknown,'lifecycle_valid':False,'lifecycle_status':'INVALID_INPUT','reason':str(exc)})
    for index,event in enumerate(events):
        if index not in assigned:
            checks.append({'from':None,'to':None,'time_contiguous':True,'mismatches':[],'unknown':[],'lifecycle_valid':False,'lifecycle_status':'INVALID_INPUT','event_index':index,'event':event,'reason':'event has no validated consecutive-stage boundary (invalid/extraneous time or event)'})
    return checks


def continuity_status(checks):
    if any(c['mismatches'] or not c['time_contiguous'] or c.get('lifecycle_status') in ('INVALID_INPUT','BLOCKED') or (not c['lifecycle_valid'] and c.get('lifecycle_status')!='INDETERMINATE') for c in checks):return 'BLOCKED'
    if any(c['unknown'] or c.get('lifecycle_status')=='INDETERMINATE' for c in checks):return 'INDETERMINATE'
    return 'CONTINUOUS'


def scenario(data,variant,case):
    product='product_'+variant;current=bodies(data,variant);start=copy.deepcopy(current);t=F(0);stages=[];event=[]
    travel=config(data,('short_' if case=='short' else 'travel_')+variant);exit_x=config(data,'exit_'+variant)
    if case=='collision':
        x=config(data,'obstacle_'+variant);th=config(data,'obstacle_thickness');pbox=current[product];current['research_obstacle']={'lo':[str(x),pbox['lo'][1],pbox['lo'][2]],'hi':[str(x+th),pbox['hi'][1],pbox['hi'][2]],'delta':['0','0','0'],'motion':'linear','exact_box':True,'group':'obstacle','rigid_group':'obstacle'}
    def stage(name,moves=None,unknown=False):
        nonlocal current,t
        state=copy.deepcopy(current)
        for key,d in (moves or {}).items():state[key]['delta']=[str(x) for x in d]
        if unknown:state[product]['delta']=None
        interval=[str(t),str(t+config(data,'phase_duration'))];rows=matrix(state,interval,variant)
        stages.append({'phase':name,'time':interval,'state':state,'pairs':rows,'counts':summarize(rows)})
        current=advance(state);t+=config(data,'phase_duration')
    zero=F(0);doser=config(data,'doser_fill_y');gate=config(data,'gate_isolate_y')
    stage(variant+'-READY');stage(variant+'-FILL',{'doser_slide':(zero,doser,zero)})
    stage(variant+'-ISOLATE',{'doser_slide':(zero,-doser,zero),'inlet_gate':(zero,gate,zero)})
    if variant=='B':
        stage('B-PRESS',{}) # geometric hold only; no compaction physics
        stage('B-UNLOAD',{})
        stage('B-OPEN-LOCK',{'lock':(zero,config(data,'open_lock_y'),zero)})
        stage('B-OPEN-STOP',{'end_stop':(zero,config(data,'open_stop_y'),zero)})
    stage('A-PRESS-OUT' if variant=='A' else 'B-EJECT',{'punch':(travel,zero,zero),'rod':(travel,zero,zero),product:(travel,zero,zero)},case=='unknown')
    active=stages[-1];path_names={'punch',product,'research_obstacle'}|{name for name in current if name.startswith('chamber_') or name.startswith('channel_') or name in ('end_stop','lock')}
    # This explicitly limited result does not claim clearance of frames or mounts.
    path=[r for r in active['pairs'] if set(r['pair']).issubset(path_names) and set(r['pair']).intersection({'punch',product})]
    path_collision=any(r['status']=='COLLISION' for r in path)
    required=next(r for r in active['pairs'] if set(r['pair'])=={'punch',product})['evidence']['link']
    rear=None if case=='unknown' else F(current[product]['lo'][0]);geo='INDETERMINATE' if rear is None else 'GEOMETRY_SUFFICIENT' if rear>=exit_x else 'SHORT_STROKE'
    path_status='COLLISION' if path_collision else 'INDETERMINATE' if any(r['status'] in ('INDETERMINATE','INVALID_INPUT') for r in path) else 'NO_COLLISION'
    removal_conditions={product:{'exit_boundary':str(exit_x),'receiving_yz':[[start[product]['lo'][i],start[product]['hi'][i]] for i in (1,2)],'required_link':required,'path_collision':path_status}}
    if geo=='GEOMETRY_SUFFICIENT' and path_status=='NO_COLLISION' and required=='LINK_CONFIRMED':
        event.append({'type':'REMOVE','id':product,'time':str(t),'final_rear':str(rear),'exit_boundary':str(exit_x),'basis':'conditional path subset only; whole assembly not validated'})
        proposed=copy.deepcopy(current);del proposed[product]
        current,removal_audit=apply_boundary_events(current,proposed,str(t),event,removal_conditions)
        if removal_audit['status']!='VALID':raise ValueError('generated REMOVE failed independent lifecycle validation')
        stage(variant+'-RETURN',{'punch':(-travel,zero,zero),'rod':(-travel,zero,zero)})
        if variant=='B':
            stage('B-RESET-STOP',{'end_stop':(zero,-config(data,'open_stop_y'),zero)});stage('B-RESET-LOCK',{'lock':(zero,-config(data,'open_lock_y'),zero)})
        stage(variant+'-RESET-INLET',{'inlet_gate':(zero,-gate,zero)})
        stage(variant+'-READY-RETURNED')
    transition='BLOCKED' if path_status=='COLLISION' or geo=='SHORT_STROKE' or required=='LINK_ABSENT' else 'INDETERMINATE' if path_status=='INDETERMINATE' or required=='LINK_INDETERMINATE' else 'ALLOWED_FOR_PATH_SUBSET'
    continuity=assess_continuity(stages,event,removal_conditions);continuity_result=continuity_status(continuity)
    if continuity_result=='BLOCKED':transition='BLOCKED'
    elif continuity_result=='INDETERMINATE' and transition!='BLOCKED':transition='INDETERMINATE'
    restored=all(all(F(a)==F(b) for key in ('lo','hi') for a,b in zip(current[name][key],start[name][key])) for name in current if name in start and name!=product)
    global_counts={status:sum(st['counts'][status] for st in stages) for status in active['counts']}
    return {'variant':variant,'case':case,'stages':stages,'ejection_phase':active['phase'],'path_subset':sorted(path_names),'path_collision':path_status,'required_link':required,'geometry':geo,'final_product_rear':str(rear),'exit_boundary':str(exit_x),'path_transition':transition,'path_ready':'RESTORED_FOR_PATH_SUBSET' if event and restored and continuity_result=='CONTINUOUS' else 'NOT_CONFIRMED','whole_assembly_transition':'BLOCKED_ASSUMED_INTERFERENCES' if global_counts['COLLISION'] else 'INDETERMINATE','whole_assembly_ready':'INDETERMINATE','counts':global_counts,'lifecycle':event,'lifecycle_conditions':removal_conditions,'continuity':continuity,'continuity_status':continuity_result,'physical':{'unloading':'UNKNOWN','holding':'UNKNOWN','forces':'UNKNOWN','safety':'UNKNOWN'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--models',required=True);p.add_argument('--out',required=True);args=p.parse_args();data=load(args.inputs);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    try:adapter=check_cad_adapter(data,args.models,args.inputs)
    except CadValidationError as exc:
        failure={'status':'FAILED','classification':'ASSUMED_RESEARCH_ONLY_NOT_REV','cad_adapter':exc.report,'scenarios':'NOT_RUN','previous_pair_files':'STALE/NOT_USED'}
        (out/'report.json').write_text(json.dumps(failure,indent=2)+'\n')
        print(json.dumps(failure),file=sys.stderr);return 1
    scenarios=[scenario(data,v,c) for v in 'AB' for c in ('sufficient','short','collision','unknown')]
    # Stream full pair evidence compressed to retain inspectable results without a huge text diff.
    with gzip.GzipFile(filename=str(out/'all_pairs.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(scenarios,sort_keys=True,separators=(',',':')).encode())
    summaries=[{k:v for k,v in r.items() if k!='stages'}|{'phase_count':len(r['stages']),'pair_rows':sum(len(st['pairs']) for st in r['stages'])} for r in scenarios]
    services=[]
    for variant in 'AB':
        base=bodies(data,variant)
        for name in ['cylinder_barrel','rod','doser_slide']+(['clamp_L'] if variant=='A' else ['end_stop','lock']):
            scene=copy.deepcopy(base);scene[name]['delta']=['0','0',str(config(data,'service_lift'))];rows=[r for r in matrix(scene,['0',str(config(data,'phase_duration'))],variant) if name in r['pair']]
            services.append({'variant':variant,'operation':'conditional vertical extraction '+name,'counts':summarize(rows),'pairs':rows,'real_service_safety':'UNKNOWN'})
    with gzip.GzipFile(filename=str(out/'service_pairs.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(services,sort_keys=True,separators=(',',':')).encode())
    # Phase diagrams are schematics of moving envelopes, not CAD clearance evidence.
    for v in 'AB':
        r=next(r for r in scenarios if r['variant']==v and r['case']=='sufficient');height=100+80*len(r['stages']);svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1300" height="{height}"><rect width="100%" height="100%" fill="white"/><text x="30" y="35" font-size="22">ASSUMED phase envelopes — not physical validation</text>']
        for i,st in enumerate(r['stages']):
            y=85+i*80;svg.append(f'<text x="30" y="{y}" font-size="16">{st["phase"]} t={st["time"]}</text>')
            for name,color in [('punch','#e56e41'),('product_'+v,'#b78a53')]:
                b=st['state'].get(name)
                if b:
                    x=420+float(F(b['lo'][0]))*200;w=float(F(b['hi'][0])-F(b['lo'][0]))*200;svg.append(f'<rect x="{x}" y="{y-20}" width="{w}" height="28" fill="{color}"/>')
        svg.append('</svg>');(Path(args.models)/v/'phase_views.svg').write_text('\n'.join(svg))
    source=[Path(__file__).resolve(),Path(__file__).with_name('build_model.py'),Path(__file__).with_name('layout_common.py'),Path(__file__).with_name('layout_lifecycle.py'),Path(__file__).with_name('cad_validation.py'),ROOT/'models/rev_linked_scene/engine.py',Path(args.inputs).resolve(),ROOT/'params/registry.yaml',ROOT/'cad/layout/model_build_task.md']
    unsupported=[{'operation':name,'status':'INDETERMINATE','reason':reason} for name,reason in [
        ('insert extraction and clamp_R removal','separate insert geometry and removal sequence not defined'),
        ('guard opening and operator approach','rotation, hinges, opening envelopes and approach dimensions UNKNOWN'),
        ('lifting and installation','lifting points, mass, rigging, centre of gravity and installation path UNKNOWN'),
        ('hose loops and connections','routing envelope is a solid placeholder, flexibility and ports UNKNOWN'),
        ('operating zone and downstream receiving capacity','extent, capacity and site interface UNKNOWN; output half-space criterion only')]]
    report={'status':'COMPLETED_WITH_KNOWN_INTERFERENCES','classification':'ASSUMED_RESEARCH_ONLY_NOT_REV','source_commit_inputs':'0d587fa226fee78abc7c86752adee825febb164d','input_sha256':digest(args.inputs),'sha256':{str(p.relative_to(ROOT)):digest(p) for p in source},'adapter_scope':'exact boxes and linear translations only; cylinders use conservative bounding separation; overlap for curved shapes INDETERMINATE','cad_adapter':adapter,'known_native_penetrations':{'review_commit':'e939b41d0139b0a3a08a5950eeeec6e92324cf9b','source':'verification/r5_layout_output_review/evidence/cad_probe.json and dynamic_probe.json','status':'preserved; tool fix does not fix geometry','whole_assembly_ready':'INDETERMINATE'},'tool_blockers':'R5-CAD-TOOL-B01/B02 OPEN pending independent RECHECK','scenarios':summaries,'services':[{k:v for k,v in s.items() if k!='pairs'} for s in services],'unsupported_service_and_zones':unsupported,'unresolved':['real mounting holes/contacts, guide surfaces and load paths','full rod/barrel geometry during stroke','rotating doser, rotating stop, flexible hoses','real tolerances and force/material model','safe access, guard rotation and lifting procedure','whole-press READY not demonstrated; static proxy interferences retained'],'files':{'all_pairs.json.gz':digest(out/'all_pairs.json.gz'),'service_pairs.json.gz':digest(out/'service_pairs.json.gz')}}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in summaries:print(r['variant'],r['case'],r['geometry'],r['path_collision'],r['path_transition'],r['counts'])
if __name__=='__main__':sys.exit(main())
