"""Disposable native/CLI regressions. PASS here is test matching, never path fitness."""
import copy,json,sys,shutil,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'cad/calculated_layout'))
from bridge import *
from scenes import service_scene,pair_matrix
from pipeline import seal

def replaced(base,motions,evaluator):
    s=copy.deepcopy(base);current=copy.deepcopy(s['stages'][0]['state'])
    for i,st in enumerate(s['stages']):
        state=copy.deepcopy(current)
        for b in state.values():b['delta']=['0','0','0']
        if 0<i<len(s['stages'])-1:
            for n,delta in motions[i-1]:state[n]['delta']=list(map(str,delta))
        st['state']=state;st['pairs']=pair_matrix(evaluator,s['variant'],state,st['time']);st['counts']=checked.summarize(st['pairs']);current=checked.advance(state)
    s['continuity']=checked.assess_continuity(s['stages'],[]);s['continuity_status']=checked.continuity_status(s['continuity']);s['positions_restored']=all(current[n]['lo']==s['stages'][0]['state'][n]['lo'] and current[n]['hi']==s['stages'][0]['state'][n]['hi'] for n in current)
    return s

def main():
    records=[];mutants=[];evaluators={v:Evaluator(load(input_path(v)),OUT) for v in VARS}
    try:
        for v in VARS:
            d=load(input_path(v));ev=evaluators[v];spec=protocols(d,v);base=service_scene(d,v,'service_fp_doser_retract_lift',spec['service_fp_doser_retract_lift'],ev);lift=config(d,'service_lift');side=config(d,'doser_service_y')
            mutants.append((v+'_retract_omitted',replaced(base,[[('doser_slide',(0,0,0))],[('doser_slide',(0,0,lift))],[('doser_slide',(0,0,-lift))],[('doser_slide',(0,0,0))]],ev)))
            if v=='A':mutants.append(('A_lift_before_retract',replaced(base,[[('doser_slide',(0,0,lift))],[('doser_slide',(0,side,0))],[('doser_slide',(0,0,-lift))],[('doser_slide',(0,-side,0))]],ev)))
        d=load(input_path('A'));ev=evaluators['A'];spec=protocols(d,'A');base=service_scene(d,'A','service_fp_powerpack_module',spec['service_fp_powerpack_module'],ev);lift=config(d,'service_lift');names=['hydraulic_tank','pump_motor','motor_mount_rear']
        mutants.append(('A_stationary_front_plate',replaced(base,[[(n,(0,0,lift)) for n in names],[(n,(0,0,-lift)) for n in names]],ev)))
        s=service_scene(d,'A','service_fp_motor',spec['service_fp_motor'],ev);s['stages'][1]['state']['pump_motor']['motion']='rotation';st=s['stages'][1];st['pairs']=pair_matrix(ev,'A',st['state'],st['time']);st['counts']=checked.summarize(st['pairs']);mutants.append(('A_rotation',s))
        first_five=copy.deepcopy(mutants)
        s=copy.deepcopy(mutants[0][1]);s['stages'][2]['state']['pump_motor']['motion']='rotation';st=s['stages'][2];st['pairs']=pair_matrix(ev,'A',st['state'],st['time']);st['counts']=checked.summarize(st['pairs']);mutants.append(('collision_plus_rotation',s))
        s=copy.deepcopy(mutants[0][1]);s['stages'][1]['pairs']=[];s['stages'][1]['counts']=checked.summarize([]);mutants.append(('collision_plus_missing_pair_matrix',s))
        s=copy.deepcopy(mutants[0][1]);s['stages'][2]['time'][0]=str(F(s['stages'][2]['time'][0])+F(1,10));mutants.append(('collision_plus_time_gap',s))
        for label,s in mutants:
            ev=evaluators[s['variant']];result=evaluate_scene(s,load(input_path(s['variant'])),ev)
            assert not result['limited_geometry_success'] and not result['matches_test_expectation'],label
            if label=='A_rotation':assert result['unknown_mandatory_conditions'],label
            elif 'missing_pair' not in label and 'time_gap' not in label:assert result['proven_collisions'],label
            if label=='collision_plus_rotation':assert result['proven_collisions'] and result['unknown_mandatory_conditions'] and result['geometric_path_outcome']=='BLOCKED'
            records.append({'id':label,'actual':result,'test_expectation_match':True,'path_success':False})
        # Early REMOVE cannot delete the actual still-in-chamber product.
        state=checked.bodies(d,'A');proposed=copy.deepcopy(state);del proposed['product_A'];events=[{'type':'REMOVE','id':'product_A','time':'1','final_rear':'0','exit_boundary':'0'}]
        from layout_lifecycle import apply_boundary_events
        conditions={'product_A':{'exit_boundary':str(config(d,'exit_A')),'receiving_yz':[[state['product_A']['lo'][i],state['product_A']['hi'][i]] for i in (1,2)],'required_link':'LINK_ABSENT','path_collision':'COLLISION'}}
        updated,audit=apply_boundary_events(state,proposed,'1',events,conditions);assert 'product_A' in updated and audit['status']!='VALID';records.append({'id':'early_REMOVE','audit':audit,'product_retained':True,'test_expectation_match':True})
        # Updated hashes cannot authorize a changed saved path in the new CLI.
        cli=[]
        for label,s in first_five:
            with tempfile.TemporaryDirectory(prefix='rev-cl-negative-cli-') as temp:
                dest=Path(temp)/'package';shutil.copytree(OUT,dest);p=dest/s['variant']/'scenes.json.gz';scenes=read_packed(p);scenes=[s if x['case']==s['case'] else x for x in scenes];packed(p,scenes);seal(dest)
                cmd=['/usr/bin/python3','-B',str(R/'cad/calculated_layout/pipeline.py'),'verify','--out',str(dest)];run=subprocess.run(cmd,cwd=R,text=True,capture_output=True);assert run.returncode==1,(label,run.stdout,run.stderr)
                cli.append({'id':label,'argv':cmd,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'test_expectation_match':True})
    finally:
        for ev in evaluators.values():ev.close()
    return records,cli

if __name__=='__main__':
    # Native mutations use a separate interpreter to keep OpenCascade ownership isolated.
    r,c=main();save(AUDIT/'path_regressions.json',{'calculation_cases':r,'cli_cases':c,'test_result':'PASS','path_fitness':'NOT_CONFIRMED'})
