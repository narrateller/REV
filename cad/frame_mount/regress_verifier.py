"""Full materialized-checkout regressions for R5-FRAME-NEW-B01.

Generate twice over an existing published package; verify twice after each.
Faults are injected and restored ONLY by this explicit test harness, never
by the verifier. Evidence is stored outside the verified publication catalog.
"""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(root):
    # Includes historical source/evidence and native CAD, beyond manifest scope.
    return {p.relative_to(root).as_posix():{'sha256':sha(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for folder in ('cad','verification','params','models','drives') for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,default=ROOT/'verification/r4_frame_fix/regressions');args=parser.parse_args();dest=args.evidence.resolve();dest.mkdir(parents=True,exist_ok=True)
    records=[];cases=[];report={'status':'RUNNING','scope':'author regression, independent R5 NOT_RUN','baseline':'5198e0184b35978701ed1ce762d9e4fcd44997b3'}
    def run(root,command,label):
        p=subprocess.run(command,cwd=root,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        records.append({'label':label,'command':command,'cwd':str(root),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        (dest/'commands.json').write_text(json.dumps(records,indent=2)+'\n');return p
    def verify_pair(root,label):
        before=snapshot(root);first=run(root,['/usr/bin/python3','-B','cad/frame_mount/verify_output.py'],label+'-verify-1');middle=snapshot(root);second=run(root,['/usr/bin/python3','-B','cad/frame_mount/verify_output.py'],label+'-verify-2');after=snapshot(root)
        assert first.returncode==second.returncode==0,(label,first.stdout,second.stdout)
        assert first.stdout==second.stdout and first.stderr==second.stderr,(label,'result differs')
        assert before==middle==after,(label,'verifier changed saved files or mtime')
        (dest/(label+'-snapshot.json')).write_text(json.dumps(before,indent=2)+'\n')
        cases.append({'case':label,'verifier_exits':[first.returncode,second.returncode],'identical_results':True,'checked_files_unchanged':True,'snapshot_files':len(before)})
        return json.loads(first.stdout)
    def semantic(root):
        saved=json.loads((ROOT/'verification/r4_frame_fix/preservation.json').read_text())
        for path,h in saved['sha256'].items():assert sha(root/path)==h,('geometry/evidence changed',path)
        native={}
        for v in 'AB':
            m=json.loads((root/'cad/build/frame_mount'/v/'manifest.json').read_text());assert m['objects']==saved['manifest_objects'][v]
            native[v]={k:m[k] for k in ('objects','input_sha256','reopen_recompute','edit_probe','spreadsheet_parameters','query_volumes')}
        return {'geometry_evidence_sha256':{p:sha(root/p) for p in saved['sha256']},'native_manifest_semantics':native}
    try:
        with tempfile.TemporaryDirectory(prefix='rev-frame-readonly-') as temp:
            root=Path(temp)/'REV'
            p=subprocess.run(['git','clone','--shared','--no-checkout',str(ROOT),str(root)],capture_output=True,text=True);assert p.returncode==0,p.stderr
            p=subprocess.run(['git','checkout','HEAD'],cwd=root,capture_output=True,text=True,env={**os.environ,'GIT_LFS_SKIP_SMUDGE':'1'});assert p.returncode==0,p.stderr
            p=subprocess.run(['git','lfs','install','--local'],cwd=root,capture_output=True,text=True);assert p.returncode==0,p.stderr
            # Materialize LFS from existing local files, no downloads/remote side effects.
            listing=subprocess.check_output(['git','lfs','ls-files','-n'],cwd=ROOT,text=True).splitlines()
            for name in listing:
                path=ROOT/name
                if path.is_file():shutil.copy2(path,root/name)
            # Include the exact current source/package even before final C exists.
            for folder in ('cad/frame_mount','cad/build/frame_mount','verification/r4_frame_mount','verification/r4_frame_fix'):
                shutil.copytree(ROOT/folder,root/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','regressions'))
            generated=[]
            for i in (1,2):
                p=run(root,['/usr/bin/python3','-B','cad/frame_mount/generate.py'],'explicit-generation-'+str(i));assert p.returncode==0,p.stderr
                assert 'publication_manifest.json' not in json.loads((root/'cad/build/frame_mount/run.json').read_text())['artifacts'],'run still hashes publication layer'
                verify_pair(root,'generation-'+str(i));generated.append(semantic(root))
            assert generated[0]==generated[1],'explicit regeneration differs semantically'
            (dest/'semantic_repeat.json').write_text(json.dumps({'status':'PASS','explicit_generations':2,'identical_deterministic_geometry_and_proofs':True,'native_semantics':generated[0]['native_manifest_semantics'],'preserved_evidence_hashes':generated[0]['geometry_evidence_sha256'],'binary_FCStd_STEP':'semantic/native comparison; serialization metadata may differ'},indent=2)+'\n')
            faults=[('missing-manifest','cad/build/frame_mount/publication_manifest.json',None),('corrupt-manifest','cad/build/frame_mount/publication_manifest.json',b'not JSON'),('stale-manifest','cad/build/frame_mount/publication_manifest.json',b'{"schema_version":1,"sha256":{}}')]
            for kind in ('missing','corrupt'):
                for name in ('A/layout_A.FCStd','B/layout_B.step','A/isometric.png','geometry_evidence.json','inventory/inventory.json'):
                    faults.append((kind+'-'+name.replace('/','-'),'cad/build/frame_mount/'+name,None if kind=='missing' else b'broken artifact\x00'))
            stale=subprocess.check_output(['git','show','5198e0184b35978701ed1ce762d9e4fcd44997b3:cad/build/frame_mount/assessment.md'],cwd=ROOT)
            faults.append(('stale-valid-report','cad/build/frame_mount/assessment.md',stale))
            old_input=json.loads((root/'cad/frame_mount/inputs.assumed.json').read_text());old_input['input_revision']=6
            faults.append(('stale-valid-input','cad/frame_mount/inputs.assumed.json',(json.dumps(old_input,indent=2)+'\n').encode()))
            for label,name,payload in faults:
                path=root/name;original=path.read_bytes();metadata=path.stat()
                if payload is None:path.unlink()
                else:path.write_bytes(payload)
                before=snapshot(root);p=run(root,['/usr/bin/python3','-B','cad/frame_mount/verify_output.py'],label);after=snapshot(root)
                assert p.returncode!=0,(label,'fault accepted')
                assert before==after,(label,'automatic repair or evidence mutation')
                result=json.loads(p.stdout);assert result['status']=='FAIL' and result['reason']
                cases.append({'case':label,'exit_code':p.returncode,'checked_files_unchanged':True,'diagnostic':result['reason']})
                # Explicit fixture restoration, outside verifier. Preserve original metadata too.
                path.write_bytes(original);os.utime(path,ns=(metadata.st_atime_ns,metadata.st_mtime_ns))
            verify_pair(root,'restored-fixture')
            report.update({'status':'PASS','cases':cases,'generation_replay':'two explicit full builds over existing published outputs, each followed by two read-only checks','geometry_preservation':'all preservation.json hashes and native semantic objects identical','command_count':len(records),'verifier_writes':0,'remaining_native_pairs':20,'eliminated_native_pairs':18,'physical_trials':'NOT_RUN','G1':'OPEN'})
    except Exception as e:
        report.update({'status':'FAIL','cases':cases,'reason':str(e) or repr(e)});print(report['reason'],file=sys.stderr)
    report['source_hashes']={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'cad/frame_mount').glob('*.py')}
    (dest/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'cases':len(cases),'commands':len(records)}));return 0 if report['status']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
