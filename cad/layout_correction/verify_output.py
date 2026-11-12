"""Read-only output checks, including both new design counterexamples.

This is new R4 self-check code, not an independent review or a patched core.
"""
import argparse,gzip,hashlib,json,sys
from verify_cycles import verify_cycles
from layout_common import load
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'cad/build/layout_correction'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'cad/build/layout_correction');args=parser.parse_args(argv);OUT=args.out.resolve()
    report_path=ROOT/'verification/r4_layout_correction/final_checks.json' if OUT==(ROOT/'cad/build/layout_correction') else OUT/'verification.json'
    try:return verify(OUT,report_path)
    except Exception as exc:
        report_path.write_text(json.dumps({'execution':{'status':'COMPLETED','exit_code':1},'test_evaluation':{'status':'FAIL'},'reason':str(exc)},indent=2)+'\n');print('VERIFICATION FAILED: '+str(exc),file=sys.stderr);return 1


def verify(OUT,report_path):
    run=json.loads((OUT/'run.json').read_text());assessment=json.loads((OUT/'assessment.json').read_text())
    assert run['execution']=={'status':'COMPLETED','exit_code':0} and run['test_evaluation']['status']=='PASS','run execution or strict test evaluation failed'
    scenes=json.loads(gzip.decompress((OUT/'raw_checked_tool/all_pairs.json.gz').read_bytes()))
    actual_input=Path(next(k for k in run['source_hashes'] if k.endswith('inputs.assumed.json')))
    if not actual_input.is_absolute():actual_input=ROOT/actual_input
    cycles=verify_cycles(scenes,load(actual_input))
    assert len(run['limited_outcomes'])==8
    for row,cycle in zip(run['limited_outcomes'],cycles):
        assert row['variant']==cycle['variant'] and row['case']==cycle['case'] and row['matches_expectation'],row
        assert row['geometric_scene_outcome']==cycle['geometric_scene_outcome']
        assert row['limited_cycle_success']==(cycle['case']=='sufficient')
    for path,sha in run['source_hashes'].items():assert digest(ROOT/path)==sha,path
    for path,sha in run['artifacts'].items():assert digest(OUT/path)==sha,path
    for path,sha in run['checked_tool']['sha256'].items():assert digest(ROOT/path)==sha,path
    added=set(json.loads((ROOT/'cad/layout_correction/change_inputs.json').read_text())['added_bodies'])
    controls={tuple(sorted(p)):0 for p in [('guard_right','pump_motor'),('output_support','stop_support_bridge')]};introduced=[];total=0
    with gzip.open(OUT/'classifications.jsonl.gz','rt') as stream:
        for line in stream:
            row=json.loads(line);total+=1;pair=tuple(sorted(row['pair']))
            if pair in controls:
                controls[pair]+=1
                assert row['class'] in ('CLEAR','ALLOWED_SYNTHETIC_TOUCH'),row
            if set(pair)&added and row['class'] in ('PENETRATION','NATIVE_PENETRATION_WITNESS','ENVELOPE_INTERSECTION'):introduced.append(row)
    assert not introduced,introduced
    assert all(s['target_penetration_rows']==0 for s in assessment['scenes'])
    assert all(s['positions_restored'] and s['continuity_status']=='CONTINUOUS' for s in assessment['scenes'] if s['case'].startswith('service_'))
    baseline=json.loads((ROOT/'verification/r4_analysis_fix/geometry_baseline.json').read_text())
    for path,sha in baseline['unchanged_file_hashes'].items():assert digest(ROOT/path)==sha,('geometry/evidence changed',path)
    for v,objects in baseline['manifest_objects'].items():assert json.loads((OUT/v/'manifest.json').read_text())['objects']==objects,('native geometry changed',v)
    result={'status':'PASS','execution':{'status':'COMPLETED','exit_code':0},'test_evaluation':{'status':'PASS'},'scene_results':cycles,'geometry_preserved_from':'120a9582f4835e81cdf324605a14f632ce7db2cb','maturity':'R4_SELF_CHECK_REQUIRES_INDEPENDENT_REVIEW','command':'/usr/bin/python3 cad/layout_correction/verify_output.py','classification_rows':total,'trial_counterexample_controls':[{'pair':list(p),'full_stroke_rows':count,'result':'CLEAR or declared exact zero-volume face touch'} for p,count in controls.items()],'new_body_penetration_or_envelope_rows':len(introduced),'checked_tool_files_unchanged':len(run['checked_tool']['sha256']),'input_sha256':run['input_sha256'],'sha256':{str(p.relative_to(ROOT)):digest(p) for p in (Path(__file__),OUT/'run.json',OUT/'classifications.jsonl.gz',OUT/'assessment.json')}}
    report_path.write_text(json.dumps(result,indent=2)+'\n');print('EXECUTION COMPLETED; VERIFICATION PASS; strict limited cycles and preserved target geometry confirmed; whole press INDETERMINATE.');return 0

if __name__=='__main__':sys.exit(main())
