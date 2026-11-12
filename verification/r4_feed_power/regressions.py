"""Actual saved-package readonly/fault regressions in an isolated checkout."""
import gzip,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DEST=Path(__file__).parent/'regressions';DEST.mkdir(exist_ok=True)


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def snapshot(root):return {p.relative_to(root).as_posix():(sha(p),p.stat().st_mtime_ns,p.stat().st_size) for folder in ('cad','verification','models','params','drives') for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}


def main():
    commands=[];cases=[];result={'status':'RUNNING','scope':'R4 self-check, independent review NOT_RUN'}
    def run(root,label):
        before=snapshot(root);p=subprocess.run(['/usr/bin/python3','-B','cad/feed_power/verify_output.py'],cwd=root,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});after=snapshot(root)
        commands.append({'label':label,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr});(DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert before==after,(label,'verifier wrote files');return p
    try:
        with tempfile.TemporaryDirectory(prefix='rev-fp-readonly-') as temp:
            root=Path(temp)/'REV'
            subprocess.run(['git','clone','--shared','--no-checkout',str(ROOT),str(root)],check=True,capture_output=True)
            subprocess.run(['git','checkout','HEAD'],cwd=root,env={**os.environ,'GIT_LFS_SKIP_SMUDGE':'1'},check=True,capture_output=True);subprocess.run(['git','lfs','install','--local'],cwd=root,check=True,capture_output=True)
            for name in subprocess.check_output(['git','lfs','ls-files','-n'],cwd=ROOT,text=True).splitlines():
                if (ROOT/name).is_file():shutil.copy2(ROOT/name,root/name)
            for folder in ('cad/feed_power','cad/build/feed_power','verification/r4_feed_power'):shutil.copytree(ROOT/folder,root/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','regressions'))
            a=run(root,'saved-1');b=run(root,'saved-2');assert a.returncode==b.returncode==0,(a.stdout,b.stdout);assert (a.stdout,a.stderr)==(b.stdout,b.stderr)
            cases.append({'case':'two saved-package verifiers','exits':[0,0],'identical_results':True,'all_files_unchanged':True})
            faults=[]
            for action in ('missing','corrupt'):
                for name in ('A/layout_A.FCStd','B/layout_B.step','A/isometric.png','interval_rows.json.gz','before_after_native.json','publication_manifest.json'):
                    faults.append((action+'-'+name,{'cad/build/feed_power/'+name:None if action=='missing' else b'corrupt fixture\x00'}))
            stale=subprocess.check_output(['git','show','a5d5bad6dd8928045512bca16836fd1d2544b7ca:cad/frame_mount/inputs.assumed.json'],cwd=ROOT)
            faults.append(('stale-input',{'cad/feed_power/inputs.assumed.json':stale}))
            invpath='cad/build/feed_power/inventory/inventory.json';inv=json.loads((root/invpath).read_text());drop=next(r for r in inv['rows'] if r['classification']=='NATIVE_PENETRATION');inv['rows'].remove(drop);inv['summary']['NATIVE_PENETRATION']-=1
            faults.append(('hide-one-native-pair-with-updated-hash',{invpath:(json.dumps(inv,indent=2)+'\n').encode()}))
            path='cad/build/feed_power/before_after_native.json';native=json.loads((root/path).read_text());native.pop();faults.append(('drop-before-after-with-updated-hash',{path:(json.dumps(native,indent=2)+'\n').encode()}))
            path='cad/build/feed_power/interval_rows.json.gz';rows=json.loads(gzip.decompress((root/path).read_bytes()));i=next(i for i,r in enumerate(rows) if r['status']=='POSITIVE_BOUND_OVERLAP');rows.pop(i);proofpath='cad/build/feed_power/interval_evidence.json';proof=json.loads((root/proofpath).read_text());proof['audited_critical_rows']-=1
            faults.append(('drop-legacy-interval-with-updated-hash',{path:gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0),proofpath:(json.dumps(proof,indent=2)+'\n').encode()}))
            del rows,inv,native
            for label,changes in faults:
                manifest=root/'cad/build/feed_power/publication_manifest.json';restore={}
                def remember(p):restore[p]=(p.read_bytes(),p.stat())
                for name,payload in changes.items():
                    p=root/name;remember(p)
                    if payload is None:p.unlink()
                    else:p.write_bytes(payload)
                if 'updated-hash' in label:
                    remember(manifest);m=json.loads(manifest.read_text())
                    for name in changes:m['sha256'][name]=sha(root/name)
                    manifest.write_text(json.dumps(m,indent=2)+'\n')
                p=run(root,label);assert p.returncode==1,(label,p.stdout);diagnostic=json.loads(p.stdout);assert diagnostic['status']=='FAIL'
                cases.append({'case':label,'exit_code':1,'no_auto_repair':True,'diagnostic':diagnostic['reason']})
                for path,(content,stat) in restore.items():path.write_bytes(content);os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
            a=run(root,'restored-1');b=run(root,'restored-2');assert a.returncode==b.returncode==0 and a.stdout==b.stdout
            cases.append({'case':'explicit fixture restoration','exits':[0,0],'all_files_unchanged':True})
            result.update({'status':'PASS','cases':cases,'commands':len(commands),'negative_cases':len(faults),'verifier_writes':0,'G1':'OPEN'})
    except Exception as e:result.update({'status':'FAIL','cases':cases,'reason':str(e) or repr(e)})
    result['source_sha256']=sha(__file__);(DEST/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cases'}));return 0 if result['status']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
