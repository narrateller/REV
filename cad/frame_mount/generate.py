#!/usr/bin/env python3
"""Explicitly rebuild and seal the research package. Never invoked by verifier."""
import json,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
from publication import write_manifest
ROOT=Path(__file__).resolve().parents[2]


def main():
    records=[]
    for script in ('run','geometry_evidence','figures','report'):
        command=['/usr/bin/python3','-B',str(ROOT/'cad/frame_mount'/f'{script}.py')]
        p=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        records.append({'command':command,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        if p.returncode:
            print(json.dumps({'execution':{'status':'FAILED','exit_code':1},'commands':records,'manifest_updated':False}),file=sys.stderr);return 1
    out=ROOT/'cad/build/frame_mount'
    (out/'generation.json').write_text(json.dumps({'execution':{'status':'COMPLETED','exit_code':0},'commands':records,'verification':'NOT_RUN; use verify_output.py separately','whole_press_READY':'INDETERMINATE','G1':'OPEN'},indent=2)+'\n')
    manifest=write_manifest(ROOT)
    print(json.dumps({'execution':{'status':'COMPLETED','exit_code':0},'manifest_files':len(manifest['sha256']),'verification':'NOT_RUN; explicit verifier required'}));return 0


if __name__=='__main__':sys.exit(main())
