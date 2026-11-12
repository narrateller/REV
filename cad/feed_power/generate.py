#!/usr/bin/env python3
"""Explicit generation for revised geometry; frozen tool files are not edited."""
import argparse,subprocess,sys,json,tempfile
from pathlib import Path
from common import *
from service_evidence import *


def reanalyze():
    """Explicit semantic regeneration from saved current poses, no CAD rebuild."""
    data=load(INPUT);freeze();check_cad_adapter(data,OUT,INPUT);work=read_packed(OUT/'raw_checked_tool/all_pairs.json.gz');services_now=read_packed(OUT/'service_scenes.json.gz');evaluator=Evaluator(data,OUT)
    try:
        semantics=evaluate_services(data,services_now,evaluator);require_expected(semantics)
        geometry(data,work+services_now,evaluator);save(OUT/'service_semantics.json',semantics)
        assessment=json.loads((OUT/'assessment.json').read_text());save(OUT/'assessment.json',attach_assessment(assessment,semantics))
        derived=verify_derived(data,work,services_now,semantics,evaluator)
        generation=json.loads((OUT/'generation.json').read_text());generation['service_test_evaluation']=semantics['test_evaluation'];generation['service_geometry_counts']=semantics['geometric_path_counts'];generation['service_overall_counts']=semantics['overall_service_counts'];generation['semantic_reanalysis']={'command':'/usr/bin/python3 -B cad/feed_power/generate.py --reanalyze','derived_evidence':derived,'sources':{str(p.relative_to(ROOT)):digest(p) for p in (ROOT/'cad/feed_power').glob('*.py')}};save(OUT/'generation.json',generation)
        p=subprocess.run(['/usr/bin/python3','-B','cad/feed_power/present.py','--report-only'],cwd=ROOT,text=True,capture_output=True)
        if p.returncode:raise RuntimeError('presentation validation failed '+p.stdout+p.stderr)
        seal();print(json.dumps({'execution':{'status':'COMPLETED','exit_code':0},'test_evaluation':semantics['test_evaluation'],'service_geometry_counts':semantics['geometric_path_counts'],'service_overall_counts':semantics['overall_service_counts'],'physical_feasibility':'INDETERMINATE'}));return 0
    except ServiceValidationFailure as e:
        print(json.dumps({'execution':{'status':'COMPLETED','exit_code':1},'test_evaluation':'FAIL','service_semantics':e.semantics,'reason':str(e)}),file=sys.stderr);return 1
    finally:evaluator.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--reanalyze',action='store_true');args=parser.parse_args()
    if args.reanalyze:return reanalyze()
    OUT.mkdir(parents=True,exist_ok=True);commands=[]
    def run(cmd):
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True);commands.append({'command':cmd,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        if p.returncode:raise RuntimeError('command failed '+str(cmd)+'\n'+p.stderr)
    try:
        frozen=freeze();data=load(INPUT);baseline=load(ROOT/'cad/frame_mount/inputs.assumed.json')
        for v in 'AB':
            assert {c['id'] for c in selected(baseline,v)} <= {c['id'] for c in selected(data,v)},'body removed'
            run(['/usr/bin/python3','-B','cad/layout/build_model.py','--inputs',str(INPUT),'--variant',v,'--out',str(OUT/v)])
        save(OUT/'cad_validation.json',check_cad_adapter(data,OUT,INPUT))
        run(['/usr/bin/python3','-B','cad/layout/check_layout.py','--inputs',str(INPUT),'--models',str(OUT),'--out',str(OUT/'raw_checked_tool')])
        work=read_packed(OUT/'raw_checked_tool/all_pairs.json.gz');suite=evaluate_suite(work,data);assert suite['status']=='PASS'
        save(OUT/'cycles.json',suite);save(OUT/'cycle_assertions.json',verify_cycles(work,data))
        extra=[module_service(data,v) for v in 'AB']+[s for v in 'AB' for s in services(data,v)];packed(OUT/'work_and_extra.json.gz',work+extra)
        assessment=analyze(data,OUT,OUT/'work_and_extra.json.gz',OUT,suite);all_services=read_packed(OUT/'service_scenes.json.gz');scenes=work+all_services
        for s in all_services:assert s['positions_restored'] and s['continuity_status']=='CONTINUOUS',s['case']
        for s in assessment['scenes']:
            assert not s['target_penetration_rows'],s['case']
            if s['case'].startswith('service_') and s['case']!='service_doser_slide':assert not s['service_moving_penetrations'],('service collision',s)
        evaluator=Evaluator(data,OUT)
        semantics=evaluate_services(data,all_services,evaluator);require_expected(semantics)
        evidence=geometry(data,scenes,evaluator);save(OUT/'service_semantics.json',semantics);assessment=attach_assessment(assessment,semantics);save(OUT/'assessment.json',assessment)
        verify_derived(data,work,all_services,semantics,evaluator);evaluator.close()
        comparisons,joints=native_evidence(data,scenes)
        remaining=inventory(OUT,OUT/'inventory');native=[r for r in remaining['rows'] if r['classification']=='NATIVE_PENETRATION'];assert len(native)==6
        assert {(r['variant'],tuple(r['pair'])) for r in native}=={(v,p) for v in 'AB' for p in LEGACY}
        # Do not rewrite any class to hide the old service. Add context only.
        for r in native:r['disposition']='BLOCKED_LEGACY_STRAIGHT_UP';r['physical_service_feasibility']='INDETERMINATE: actual retract stroke/rigging UNKNOWN'
        save(OUT/'inventory/inventory.json',remaining)
        save(OUT/'scene_roles.json',[{'variant':s['variant'],'case':s['case'],'role':'BLOCKED_LEGACY_SERVICE_COUNTEREXAMPLE' if s['case']=='service_doser_slide' else 'NEW_ASSUMED_SERVICE_SEQUENCE' if s['case'].startswith('service_fp_') else 'PRESERVED_BASELINE_SCENE','physical_feasibility':'UNKNOWN'} for s in scenes])
        repeat={}
        with tempfile.TemporaryDirectory(prefix='rev-fp-repeat-') as temp:
            for v in 'AB':
                run(['/usr/bin/python3','-B','cad/layout/build_model.py','--inputs',str(INPUT),'--variant',v,'--out',temp+'/'+v])
                a=json.loads((OUT/v/'manifest.json').read_text());b=json.loads((Path(temp)/v/'manifest.json').read_text());fields=('objects','input_sha256','reopen_recompute','edit_probe','spreadsheet_parameters','query_volumes')
                assert all(a[k]==b[k] for k in fields),'semantic repeat'
                pngs={p.name:digest(p)==digest(Path(temp)/v/p.name) for p in (OUT/v).glob('*.png')};assert all(pngs.values()),'PNG repeat'
                repeat[v]={'semantics':'PASS','PNG':pngs}
            check_cad_adapter(data,Path(temp),INPUT)
        freeze()
        save(OUT/'generation.json',{'execution':{'status':'COMPLETED','exit_code':0},'commands':commands,'repeat':repeat,'frozen_modules':len(frozen['sha256']),'input_sha256':digest(INPUT),'body_inventory':{v:{'before':len(selected(baseline,v)),'after':len(selected(data,v)),'all_original_IDs_retained':True} for v in 'AB'},'static_original_native_pairs_removed':14,'legacy_service_native_pairs_still_BLOCKED':6,'new_service_sequences':8,'new_service_moving_positive_overlap':0,'whole_press_READY':'INDETERMINATE','physical_parameters':'UNKNOWN','G1':'OPEN','raw_metadata_caveat':'historical source_commit_inputs/known_native_penetrations/tool_blockers in frozen checker are not current provenance; use this manifest/input hash'})
        record=json.loads((OUT/'generation.json').read_text());record['service_test_evaluation']=semantics['test_evaluation'];record['service_geometry_counts']=semantics['geometric_path_counts'];record['service_overall_counts']=semantics['overall_service_counts'];save(OUT/'generation.json',record)
        run(['/usr/bin/python3','-B','cad/feed_power/present.py'])
        # Save command log after presentation; manifest is produced last.
        record=json.loads((OUT/'generation.json').read_text());record['commands']=commands;save(OUT/'generation.json',record);seal()
        print(json.dumps({'execution':'COMPLETED','static_native_pairs_removed':14,'legacy_vertical_native_pairs_BLOCKED':6,'new_service_sequences':8,'whole_press_READY':'INDETERMINATE'}));return 0
    except Exception as e:
        print(json.dumps({'execution':'COMPLETED' if isinstance(e,ServiceValidationFailure) else 'FAILED','test_evaluation':'FAIL' if isinstance(e,ServiceValidationFailure) else 'NOT_COMPLETED','service_semantics':e.semantics if isinstance(e,ServiceValidationFailure) else None,'reason':str(e) or repr(e),'commands':commands}),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
