"""Read-only output checks, including both new design counterexamples.

This is new R4 self-check code, not an independent review or a patched core.
"""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'cad/build/layout_correction'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    run=json.loads((OUT/'run.json').read_text());assessment=json.loads((OUT/'assessment.json').read_text())
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
    result={'status':'PASS','maturity':'R4_SELF_CHECK_REQUIRES_INDEPENDENT_REVIEW','command':'/usr/bin/python3 cad/layout_correction/verify_output.py','classification_rows':total,'trial_counterexample_controls':[{'pair':list(p),'full_stroke_rows':count,'result':'CLEAR or declared exact zero-volume face touch'} for p,count in controls.items()],'new_body_penetration_or_envelope_rows':len(introduced),'checked_tool_files_unchanged':len(run['checked_tool']['sha256']),'input_sha256':run['input_sha256'],'sha256':{str(p.relative_to(ROOT)):digest(p) for p in (Path(__file__),OUT/'run.json',OUT/'classifications.jsonl.gz',OUT/'assessment.json')}}
    (ROOT/'verification/r4_layout_correction/final_checks.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS: hashes, unchanged tool, original/new target counterexamples, added-body checks and restored services')

if __name__=='__main__':main()
