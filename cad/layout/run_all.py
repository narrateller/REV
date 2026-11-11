#!/usr/bin/env python3
"""One reproducible entrypoint; retain failures and semantic reproducibility checks."""
import json,subprocess,sys,tempfile,shutil
from pathlib import Path
from layout_common import ROOT,digest

def main():
    directory=ROOT/'cad/build/research_layout';directory.mkdir(parents=True,exist_ok=True)
    commands=[];assumed='cad/layout/conditional_inputs.assumed.json'
    def execute(args):
        p=subprocess.run(args,cwd=ROOT,text=True,capture_output=True);commands.append({'command':args,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        if p.returncode: raise RuntimeError('command failed: '+' '.join(args)+'\n'+p.stderr)
    try:
        execute(['/usr/bin/python3','-m','unittest','discover','-s','cad/layout','-p','test_*.py'])
        execute(['/usr/bin/python3','-m','unittest','discover','-s','models/rev_linked_scene','-p','test_*.py'])
        execute(['/usr/bin/python3','-m','unittest','discover','-s','models/kinematic_press','-p','test_*.py'])
        for variant in 'AB':execute(['/usr/bin/python3','cad/layout/build_model.py','--inputs',assumed,'--variant',variant,'--out',f'cad/build/research_layout/{variant}'])
        execute(['/usr/bin/python3','cad/layout/check_layout.py','--inputs',assumed,'--models','cad/build/research_layout','--out','cad/build/research_layout/checks'])
        repeat={}
        with tempfile.TemporaryDirectory(prefix='rev-layout-repeat-') as temp:
            for variant in 'AB':
                execute(['/usr/bin/python3','cad/layout/build_model.py','--inputs',assumed,'--variant',variant,'--out',temp+'/'+variant])
                first=json.loads((directory/variant/'manifest.json').read_text());second=json.loads((Path(temp)/variant/'manifest.json').read_text())
                match=all(first[k]==second[k] for k in ('objects','input_sha256','reopen_recompute','edit_probe','spreadsheet_parameters','query_volumes'))
                repeat[variant]='PASS' if match else 'FAIL'
                if not match:raise RuntimeError('semantic repeat failed '+variant)
        import sys
        sys.path.append('/usr/lib/freecad-python3/lib');import FreeCAD,Part
        step={}
        for v in 'AB':
            shape=Part.read(str(directory/v/f'layout_{v}.step'));m=json.loads((directory/v/'manifest.json').read_text())
            step[v]={'solid_count':len(shape.Solids),'valid':shape.isValid(),'matches_manifest_count':len(shape.Solids)==len(m['objects'])}
            if not step[v]['valid'] or not step[v]['matches_manifest_count']:raise RuntimeError('STEP read failed')
        checks=json.loads((directory/'checks/report.json').read_text())
        expected={'sufficient':('GEOMETRY_SUFFICIENT','NO_COLLISION'),'short':('SHORT_STROKE','NO_COLLISION'),'collision':('GEOMETRY_SUFFICIENT','COLLISION'),'unknown':('INDETERMINATE','INDETERMINATE')}
        outcomes=[]
        for case in checks['scenarios']:
            okay=(case['geometry'],case['path_collision'])==expected[case['case']]
            want_continuity='INDETERMINATE' if case['case']=='unknown' else 'CONTINUOUS'
            continuity_ok=case['continuity_status']==want_continuity and all(not c['mismatches'] and c['lifecycle_valid'] and c['time_contiguous'] for c in case['continuity'])
            ready_ok=case['path_ready']==('RESTORED_FOR_PATH_SUBSET' if case['case']=='sufficient' else 'NOT_CONFIRMED')
            outcomes.append({'variant':case['variant'],'case':case['case'],'expected_path_only':expected[case['case']],'observed_path_only':[case['geometry'],case['path_collision']],'matches':okay,'continuity':case['continuity_status'],'continuity_matches':continuity_ok,'return_matches':ready_ok})
            if not okay:raise RuntimeError('unexpected ejection path result '+case['variant']+' '+case['case'])
            if not continuity_ok or not ready_ok:raise RuntimeError('unexpected continuity or return '+case['variant']+' '+case['case'])
        if any(checks['cad_adapter'][v]['status']!='PASS' for v in 'AB'):raise RuntimeError('actual CAD not verified')
        if any(c['whole_assembly_ready']!='INDETERMINATE' for c in checks['scenarios']):raise RuntimeError('whole assembly readiness expanded')
        execute(['/usr/bin/python3','cad/layout/tool_regressions.py','--inputs',assumed,'--models',str(directory),'--out',str(directory/'checks/tool_regressions.json')])
        execute(['/usr/bin/python3','verification/r5_layout_output_review/cad_probe.py',str(ROOT),str(directory/'checks/native_static_recheck.json')])
        execute(['/usr/bin/python3','verification/r5_layout_output_review/dynamic_probe.py',str(ROOT),str(directory/'checks/native_dynamic_recheck.json')])
        execute(['/usr/bin/python3','cad/layout/geometry_preservation.py','--models',str(directory),'--out',str(directory/'checks/geometry_preservation.json')])
        shutil.copyfile(ROOT/assumed,directory/'conditional_inputs.snapshot.json')
        shutil.copyfile(ROOT/'params/registry.yaml',directory/'registry_snapshot.yaml')
        artifacts={str(f.relative_to(directory)):digest(f) for f in directory.rglob('*') if f.is_file() and f.name not in ('validation.json','validation_failed.json','assessment.md') and f.suffix not in ('.FCStd1','.fcstd1','.FCBak')}
        sources=[ROOT/'cad/layout'/name for name in ('run_all.py','build_model.py','check_layout.py','layout_common.py','layout_lifecycle.py','cad_validation.py','geometry_preservation.py','tool_regressions.py','test_layout.py','test_lifecycle.py','test_cad_artifacts.py')]+[ROOT/assumed,ROOT/'params/registry.yaml']
        report={'classification':'ASSUMED_RESEARCH_NOT_REV','commands':commands,'artifacts':artifacts,'reproduce_semantic':repeat,'step_roundtrip':step,'ejection_subset_tests':outcomes,'tool_blockers':'R5-CAD-TOOL-B01/B02 OPEN pending independent RECHECK','whole_assembly':'not accepted; assumed interferences and unknown conditions remain','source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in sources}}
        (directory/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS: both CAD documents, STEP reread, semantic repeat, eight limited ejection cases. Whole assembly still unresolved.')
    except Exception as e:
        (directory/'validation_failed.json').write_text(json.dumps({'error':str(e),'commands':commands},indent=2)+'\n');raise
if __name__=='__main__':main()
