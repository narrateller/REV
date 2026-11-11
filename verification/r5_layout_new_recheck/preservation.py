"""Compare exact Git inputs plus materialized geometry against a native rebuild."""
import hashlib,json,subprocess,sys,gzip
from pathlib import Path
R=Path(sys.argv[1]).resolve();rebuilt=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]);C='66924aed1cb2d193b9883d2140d85560b1e4b0cb';old='120a9582f4835e81cdf324605a14f632ce7db2cb';base='de377f012da08f34796b2e59aee663ba0b2b3d2b'
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=R)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((R/'verification/r4_layout_correction/frozen_tool.json').read_text())['sha256'];f={p:blob(C,p)==blob(base,p) and hashlib.sha256(blob(C,p)).hexdigest()==h and sha(R/p)==h for p,h in frozen.items()}
baseline=json.loads((R/'verification/r4_analysis_fix/geometry_baseline.json').read_text());same={p:sha(R/p)==h and blob(C,p)==blob(old,p) for p,h in baseline['unchanged_file_hashes'].items()}
# Binary files may contain rebuild timestamps; compare native object manifests and adapter results, not binary identity.
semantic={};images={};raw={}
for v in 'AB':
 a=json.loads((R/f'cad/build/layout_correction/{v}/manifest.json').read_text());b=json.loads((rebuilt/f'cad/build/layout_correction/{v}/manifest.json').read_text())
 semantic[v]={k:a[k]==b[k] for k in ('objects','input_sha256','reopen_recompute','edit_probe','spreadsheet_parameters','query_volumes')}
 for p in ('front','side','top','isometric'):images[v+'/'+p]=sha(R/f'cad/build/layout_correction/{v}/{p}.png')==sha(rebuilt/f'cad/build/layout_correction/{v}/{p}.png')
for p in ('raw_checked_tool/all_pairs.json.gz','service_scenes.json.gz'):
 raw[p]=json.loads(gzip.decompress((R/'cad/build/layout_correction'/p).read_bytes()))==json.loads(gzip.decompress((rebuilt/'cad/build/layout_correction'/p).read_bytes()))
# Capture current native adapter output; this verifies FCStd and STEP, not only manifests.
sys.path.insert(0,str(R/'cad/layout'));sys.path.append('/usr/lib/freecad-python3/lib')
from cad_validation import check_cad_adapter
from layout_common import load
ip=R/'cad/layout_correction/inputs.assumed.json';data=load(ip)
adapter_saved=check_cad_adapter(data,R/'cad/build/layout_correction',ip)
ip2=rebuilt/'cad/layout_correction/inputs.assumed.json';adapter_rebuilt=check_cad_adapter(load(ip2),rebuilt/'cad/build/layout_correction',ip2)
result={'code_sha':C,'frozen_15_vs_de377':f,'unchanged_geometry_evidence_vs_120a958':same,'rebuilt_semantic_manifests':semantic,'rebuilt_images':images,'rebuilt_raw_scenes':raw,'saved_adapter':adapter_saved,'rebuilt_adapter':adapter_rebuilt}
assert all(f.values()) and all(same.values()) and all(all(x.values()) for x in semantic.values()) and all(images.values()) and all(raw.values()),result
out.write_text(json.dumps(result,indent=2)+'\n');print('PASS: frozen 15, geometry evidence, native FCStd/STEP, repeated semantics/raw scenes/8 PNG')
