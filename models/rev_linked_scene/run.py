#!/usr/bin/env python3
import hashlib
import json
import platform
import shutil
from pathlib import Path
from scenes import run
from negative_cases import execute

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    config=json.loads((HERE/'fixtures.json').read_text())
    output=HERE/'results';output.mkdir(exist_ok=True)
    scenes=[run(v,c,config) for v in 'AB' for c in config['expected']]
    for scene in scenes:
        scene['expected']=config['expected'][scene['case']]
        scene['matches_expected']=all(scene[k]==value for k,value in scene['expected'].items())
        scene['pair_coverage_complete']=all(len(s['output']['pairs'])==s['output']['expected_pairs'] for s in scene['stages'])
    negatives=execute()
    registry=ROOT/'params/registry.yaml';shutil.copyfile(registry,output/'registry_snapshot.yaml')
    files=[HERE/name for name in ('engine.py','scenes.py','negative_cases.py','run.py','fixtures.json','test_engine.py','contract_snapshot.md','input_audit.md','r5_documentary_review.md')]+[registry]
    report={'classification':'SYNTHETIC ONLY; NOT REV', 'source_commit':'7b5192382b06d4f148a6c98ffecc8e4d50ec4e66','r5_review_commit':'d2ab72f24028f1cc5d8e9cb3a11d14744e46273f','r5_reviewed_commit':'bb31d82b4aacebd6ccff8b6b343837d4443f8150','w01_revision_review':'NOT_RUN', 'claim_merge':'76666e8eb1d11d51be144c59980587e4ffa6a1f1','python':platform.python_version(),'registry_snapshot':'registry_snapshot.yaml','sha256':{str(f.relative_to(ROOT)):sha(f) for f in files},'scenes':scenes,'negative_cases':negatives,'limitations':['synthetic AABB only; no physical force, holding, unloading, actual ejection or safety','W01 clarification and implementation await independent review','CREATE/SPLIT remain INDETERMINATE; no real equipment tested']}
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for s in scenes:print(s['variant'],s['case'],s['geometry'],s['collision'],s['link'],s['transition'],s['ready'],'PASS' if s['matches_expected'] and s['pair_coverage_complete'] else 'FAIL')
    print('negative_cases',sum(x['matches_expected'] for x in negatives),'/',len(negatives))
    return 0 if all(s['matches_expected'] and s['pair_coverage_complete'] for s in scenes) and all(x['matches_expected'] for x in negatives) else 1
if __name__=='__main__':raise SystemExit(main())
