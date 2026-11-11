import sys,json,tempfile,shutil,hashlib,subprocess
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/cad/layout');sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App,Part
from cad_validation import check_cad_adapter,CadValidationError
from layout_common import load
root=Path(sys.argv[1]);models=root/'cad/build/research_layout';ip=root/'cad/layout/conditional_inputs.assumed.json';data=load(ip);rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=check_cad_adapter(data,models,ip);assert all(base[v]['status']=='PASS' for v in 'AB')
rows.append({'case':'pristine_actual_CAD','passed':True,'status':'PASS','counts':{v:base[v]['solid_count'] for v in 'AB'}})
for case in ('manifest_only','missing_step_and_bad_fcstd','bad_fcstd_old_hash','bad_fcstd_forged_hash','bad_step_forged_hash','variant_step_substitution_forged_hash','native_fcstd_shift_forged_hash_and_manifest','native_step_shift_forged_hash','query_volume_mutation'):
 with tempfile.TemporaryDirectory() as tmp:
  p=Path(tmp)
  for v in 'AB':
   (p/v).mkdir()
   for n in ('manifest.json',f'layout_{v}.FCStd',f'layout_{v}.step'):shutil.copyfile(models/v/n,p/v/n)
  mutation={};a=p/'A';m=json.loads((a/'manifest.json').read_text());fc=a/'layout_A.FCStd';st=a/'layout_A.step'
  if case=='manifest_only':
   for f in p.glob('*/layout_*'):f.unlink()
  elif case=='missing_step_and_bad_fcstd':st.unlink();fc.write_bytes(b'corrupt')
  elif case.startswith('bad_fcstd'):fc.write_bytes(b'not zip/FreeCAD')
  elif case=='bad_step_forged_hash':st.write_bytes(b'not STEP')
  elif case=='variant_step_substitution_forged_hash':shutil.copyfile(p/'B/layout_B.step',st)
  elif case in ('native_fcstd_shift_forged_hash_and_manifest','query_volume_mutation'):
   d=App.openDocument(str(fc))
   if case.startswith('native_fcstd'):
    old=d.Inputs.get('B1').Value;d.Inputs.set('B1','='+str(old+10)+' mm');d.recompute()
    # Forge the corresponding manifest geometry too. Persisted input stays fixed.
    for r in m['objects']:
     o=d.getObject(r['id']);b=o.Shape.optimalBoundingBox(False,False);r['cad_bounds_mm']=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax];r['volume_m3']=o.Shape.Volume/1e9
   else:
    z=d.QueryVolumes.Group[0];mutation={'object':z.Name,'before_height_mm':z.Height.Value,'before_expressions':str(z.ExpressionEngine)};z.setExpression('Height',None);z.Height=99999;d.recompute();mutation['after_height_mm']=z.Height.Value
   d.save();App.closeDocument(d.Name)
  elif case=='native_step_shift_forged_hash':
   shape=Part.read(str(st));shape.translate(App.Vector(10,0,0));d=App.newDocument('MutatedSTEP');o=d.addObject('Part::Feature','Body');o.Shape=shape;d.recompute();Part.export([o],str(st));App.closeDocument(d.Name)
  if case not in ('manifest_only','missing_step_and_bad_fcstd','bad_fcstd_old_hash'):
   m['exports'][fc.name]=sha(fc);m['exports'][st.name]=sha(st)
  (a/'manifest.json').write_text(json.dumps(m))
  try:
   r=check_cad_adapter(data,p,ip);observed='PASS';evidence={v:r[v]['status'] for v in 'AB'}
  except CadValidationError as exc:observed='FAILED';evidence=exc.report
  expected='FAILED';passed=observed==expected
  rows.append({'case':case,'expected':expected,'status':observed,'passed':passed,'evidence':evidence,'mutation':mutation});
  if case!='query_volume_mutation':assert passed,rows[-1]
  else:
   assert observed=='PASS', 'query counterexample no longer reproduces'
   out=p/'checks';cmd=['/usr/bin/python3',str(root/'cad/layout/check_layout.py'),'--inputs',str(ip),'--models',str(p),'--out',str(out)];cli=subprocess.run(cmd,capture_output=True,text=True);payload=json.loads((out/'report.json').read_text());rows[-1]['CLI']={'command_suffix':cmd[1:],'exit_code':cli.returncode,'status':payload['status'],'CAD_statuses':{v:payload['cad_adapter'][v]['status'] for v in 'AB'}};assert cli.returncode==0
open(sys.argv[2],'w').write(json.dumps(rows,indent=2)+'\n');print([(r['case'],r['status']) for r in rows])
