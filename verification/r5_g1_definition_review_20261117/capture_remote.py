"""Read-only fresh main/PR60/source CI evidence; no remote mutation."""
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess
import hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def run(*args):return subprocess.check_output(args,cwd=ROOT,text=True)
def api(path):return json.loads(run('gh','api',path))
def main():
    run('git','fetch','origin','main');now=datetime.now(timezone.utc).isoformat();main=run('git','rev-parse','origin/main').strip()
    pr=api('repos/narrateller/REV/pulls/60')
    claim='coordination/claims/T-r5-g1-supplement-output-review-01.json';amend='coordination/scope_amendments/T-r5-g1-supplement-output-review-01/G1-DEFINITION-REGISTER-01.json'
    claims=run('git','ls-tree','-r','--name-only',main,'coordination/claims').splitlines()
    data=dict(checked_at_utc=now,remote_main=main,main_parents=run('git','show','-s','--format=%P',main).split(),PR60={k:pr[k] for k in ['number','state','draft','merged','merged_at','html_url']},PR60_head=pr['head']['sha'],PR60_base=pr['base']['sha'],PR60_branch=pr['head']['ref'],source_remote_ref=run('git','ls-remote','origin','refs/heads/'+pr['head']['ref']).strip(),claim=json.loads(run('git','show',main+':'+claim)),claim_sha256=hashlib.sha256(run('git','show',main+':'+claim).encode()).hexdigest(),scope_amendment=json.loads(run('git','show',main+':'+amend)),accepted_claims=[json.loads(run('git','show',main+':'+p)) for p in claims],PR60_merge_authorized=False)
    (OUT/'remote_context.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    ci=[]
    for label,sha in [('target_C','7e2d5ecff42fe1d09b461e05375924cb644c27c9'),('request_H','7e4ce7aad8396493da6e2284d29441b46b4abb80'),('accepted_main',main)]:
        runs=api('repos/narrateller/REV/actions/runs?head_sha='+sha+'&per_page=30')['workflow_runs'];selected=[]
        for r in runs:
            row={k:r[k] for k in ['id','name','event','head_sha','status','conclusion','html_url']}
            row['jobs']=api('repos/narrateller/REV/actions/runs/'+str(r['id'])+'/jobs')
            selected.append(row)
        ci.append(dict(label=label,exact_sha=sha,runs=selected,absence_is_not_failure_or_success=not bool(selected)))
    (OUT/'target_CI.json').write_text(json.dumps(dict(checked_at_utc=now,CI=ci,source_CI_is_not_independent_review=True),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(main=main,head=pr['head']['sha'],PR60=dict(state=pr['state'],draft=pr['draft'],merged=pr['merged']),CI=[dict(label=r['label'],runs=[dict(id=x['id'],status=x['status'],conclusion=x['conclusion']) for x in r['runs']]) for r in ci])))
if __name__=='__main__':main()
