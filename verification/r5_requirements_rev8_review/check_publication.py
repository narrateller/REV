"""Read-only remote/CI receipt for the published R5 C/H, no merge or renewal.

Run after publishing and completing CI:
python3 verification/r5_requirements_rev8_review/check_publication.py \
  --review-C FULL_C --handoff-H FULL_H --branch FULL_BRANCH --output /tmp/r5-publication.json
The receipt necessarily postdates H; it is not a self-attestation embedded in H.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
TARGET='8d1b45afa84eca078a8de0a9822d6925dd87745b'
REQUEST='87f2f5889f9ba74e8eef3a3a040d936d13e0a011'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review-C',required=True);ap.add_argument('--handoff-H',required=True);ap.add_argument('--branch',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    commands=[];checks=[]
    def run(args):
        p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
        commands.append(dict(command=args,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if p.returncode:raise RuntimeError(str(args)+': '+p.stderr)
        return p.stdout
    def check(key,ok,observed):checks.append(dict(id=key,result='PASS' if ok else 'FAIL',observed=observed))
    ref='refs/heads/'+a.branch
    remote=run(['git','ls-remote','origin',ref]).split()
    check('remote-branch-exact-H',remote==[a.handoff_H,ref],remote)
    run(['git','fetch','origin',ref])
    fetched=run(['git','rev-parse','FETCH_HEAD']).strip()
    check('fetched-exact-H',fetched==a.handoff_H,fetched)
    parent=run(['git','rev-parse',fetched+'^']).strip()
    check('remote-H-parent-exact-C',parent==a.review_C,parent)
    grandparent=run(['git','rev-parse',parent+'^']).strip()
    check('review-C-parent-request-H',grandparent==REQUEST,grandparent)
    capsule=f'handoffs/T-r5-requirements-rev8-output-review-01/6afb0a73-b16c-8191-a539-9a6685e89034.md'
    text=run(['git','show',f'{fetched}:{capsule}'])
    check('H-capsule-pins-C-and-target',a.review_C in text and TARGET in text and REQUEST in text,'Full exact references in fetched capsule')
    pr=json.loads(run(['gh','api','repos/narrateller/REV/pulls/54']))
    check('PR54-open-unmerged',pr['state']=='open' and not pr['merged'] and pr['head']['sha']==REQUEST,dict(state=pr['state'],merged=pr['merged'],head=pr['head']['sha']))
    ci=[]
    for label,sha in [('review_C',a.review_C),('handoff_H',a.handoff_H)]:
        data=json.loads(run(['gh','api',f'repos/narrateller/REV/actions/runs?head_sha={sha}&per_page=30']))
        runs=[r for r in data['workflow_runs'] if r['head_sha']==sha and r['name']=='Registry & Traceability Gate' and r['event']=='push']
        runrow=max(runs,key=lambda r:r['id']) if runs else None
        check(label+':CI',runrow is not None and runrow['status']=='completed' and runrow['conclusion']=='success',None if not runrow else dict(id=runrow['id'],sha=runrow['head_sha'],status=runrow['status'],conclusion=runrow['conclusion'],url=runrow['html_url']))
        if runrow:
            jobs=json.loads(run(['gh','api',f'repos/narrateller/REV/actions/runs/{runrow["id"]}/jobs']))
            steps=[s for j in jobs['jobs'] for s in j.get('steps',[]) if s['name'] in ['Check committed evidence without regeneration','Test validator and initializer in isolated temporary copies']]
            check(label+':registry-and-tests',len(steps)==2 and all(s['conclusion']=='success' for s in steps),steps)
            ci.append(dict(label=label,sha=sha,id=runrow['id'],url=runrow['html_url'],conclusion=runrow['conclusion'],jobs=jobs))
    main_head=run(['git','ls-remote','origin','refs/heads/main']).strip()
    dirty=run(['git','status','--porcelain'])
    check('worktree-clean',dirty=='',dirty)
    result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),reviewed_target_C=TARGET,request_H=REQUEST,review_C=a.review_C,handoff_H=a.handoff_H,branch=a.branch,remote_main=main_head,CI=ci,checks=checks,commands=commands,counts={s:sum(x['result']==s for x in checks) for s in ['PASS','FAIL']},G1='OPEN',W02='NO_GO',physical_READY='NO_GO',physical_sections={'4':'NOT_RUN','5':'NOT_RUN','6':'NOT_RUN'})
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(counts=result['counts'],C=a.review_C,H=a.handoff_H,CI=[{k:x[k] for k in ['label','id','conclusion','url']} for x in ci])))
    return any(x['result']=='FAIL' for x in checks)

if __name__=='__main__':raise SystemExit(main())
