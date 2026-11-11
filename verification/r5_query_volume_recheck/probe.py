"""Independent native QueryVolume mutations; all expected outcomes are corrected."""
import sys,json,tempfile,shutil,hashlib,subprocess,math
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,sys.argv[1]+'/cad/layout');sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App,Part
from cad_validation import check_cad_adapter,CadValidationError
from layout_common import load
root=Path(sys.argv[1]);models=root/'cad/build/research_layout';ip=root/'cad/layout/conditional_inputs.assumed.json';data=load(ip);result={'baseline':[],'mutations':[]}
def val(k):return F(data['parameters'][k]['value'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# Derive expected boxes directly from input components and lift, not manifest or validator helper.
for v in 'AB':
 d=App.openDocument(str(models/v/f'layout_{v}.FCStd'));d.recompute();cs={c['id']:c for c in data['components'] if c['variant'] in ('both',v)}
 for name,source in [('CylinderRemoval','cylinder_barrel'),('DoserRemoval','doser_slide')]:
  c=cs[source];pos=[val(k) for k in c['position']]
  if source=='cylinder_barrel':
   r=val(c['radius']);lo=[pos[0],pos[1]-r,pos[2]-r];size=[val(c['length']),2*r,2*r+val(data['config']['service_lift'])]
  else:lo=pos;size=[val(k) for k in c['size']];size[2]+=val(data['config']['service_lift'])
  expected=Part.makeBox(*[float(x)*1000 for x in size],App.Vector(*[float(x)*1000 for x in lo]));actual=d.getObject(name);b=actual.Shape.optimalBoundingBox(False,False);eb=expected.optimalBoundingBox(False,False)
  err=max(abs(getattr(b,k)-getattr(eb,k)) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax'));intersection=actual.Shape.common(expected).Volume;ok=err<1e-8 and math.isclose(intersection,expected.Volume,rel_tol=1e-10) and actual.Role=='QUERY_NOT_SOLID';assert ok
  result['baseline'].append({'variant':v,'name':name,'source':source,'position_mm':[float(x)*1000 for x in lo],'size_mm':[float(x)*1000 for x in size],'max_bounds_error_mm':err,'passed':ok})
 App.closeDocument(d.Name)
modes=sys.argv[3:] or ['height','form','local','global','role','delete_forged_registry','empty','parent_local_compensation','size_and_forged_manifest']
for v in 'AB':
 for name in ('CylinderRemoval','DoserRemoval'):
  for mode in modes:
   with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)
    for w in 'AB':
     (p/w).mkdir()
     for n in ('manifest.json',f'layout_{w}.FCStd',f'layout_{w}.step'):shutil.copyfile(models/w/n,p/w/n)
    fc=p/v/f'layout_{v}.FCStd';mp=p/v/'manifest.json';m=json.loads(mp.read_text());d=App.openDocument(str(fc));z=d.getObject(name);before={'height_mm':z.Height.Value,'type':z.TypeId}
    if mode in ('height','size_and_forged_manifest','size_length','size_width'):
     prop={'size_length':'Length','size_width':'Width'}.get(mode,'Height');z.setExpression(prop,None);setattr(z,prop,99999);d.recompute()
     if mode=='size_and_forged_manifest':m['query_dimensions_forged']={name:{'Height':99999}}
    elif mode=='local_rotation':
     pl=z.Placement;pl.Rotation=App.Rotation(App.Vector(0,0,1),90);z.Placement=pl;d.recompute()
    elif mode=='parent_rotation_compensated':
     gp=d.QueryVolumes.Placement;gp.Rotation=App.Rotation(App.Vector(0,0,1),90);d.QueryVolumes.Placement=gp
     for obj in d.QueryVolumes.Group:
      for axis in 'xyz':obj.setExpression('Placement.Base.'+axis,None)
      obj.Placement=gp.inverse().multiply(obj.Placement)
     d.recompute()
    elif mode=='local':
     z.setExpression('Placement.Base.x',None);pl=z.Placement;pl.Base.x+=137;z.Placement=pl;d.recompute()
    elif mode in ('global','parent_local_compensation'):
     gp=d.QueryVolumes.Placement;gp.Base.y+=137;d.QueryVolumes.Placement=gp
     if mode=='parent_local_compensation':
      for a in 'xyz':z.setExpression('Placement.Base.'+a,None)
      pl=z.Placement;pl.Base.y-=137;z.Placement=pl
     d.recompute()
    elif mode=='role':z.Role='SOLID';d.recompute();m['query_roles_forged']={name:'SOLID'}
    elif mode=='delete_forged_registry':d.removeObject(name);d.recompute();m['query_volumes'].remove(name)
    elif mode=='empty':
     d.removeObject(name);z=d.addObject('Part::Feature',name);z.addProperty('App::PropertyString','Role');z.Role='QUERY_NOT_SOLID';z.Shape=Part.Shape();d.QueryVolumes.addObject(z);d.recompute()
    elif mode=='form_preserved_placement':
     d.recompute();saved=z.Placement;z.Shape=Part.makeCylinder(20,100);z.Placement=saved
    elif mode=='form':
     # Preserve Part::Box properties but replace persisted BRep after recompute.
     d.recompute();z.Shape=Part.makeCylinder(20,100,z.Placement.Base)
    d.save();App.closeDocument(d.Name);m['exports'][fc.name]=sha(fc);mp.write_text(json.dumps(m))
    try:obs=check_cad_adapter(data,p,ip);passed=False;evidence={'unexpected_status':{w:obs[w]['status'] for w in 'AB'}}
    except CadValidationError as exc:passed=True;evidence=exc.report
    row={'variant':v,'name':name,'mode':mode,'hash_refreshed':True,'before':before,'expected':'FAILED','passed':passed,'evidence':evidence}
    if v=='A' and name=='CylinderRemoval' and mode=='height':
     out=p/'out';out.mkdir();(out/'report.json').write_text('{"status":"PASS"}')
     cmd=['/usr/bin/python3',str(root/'cad/layout/check_layout.py'),'--inputs',str(ip),'--models',str(p),'--out',str(out)];proc=subprocess.run(cmd,capture_output=True,text=True);j=json.loads((out/'report.json').read_text());row['CLI']={'exit':proc.returncode,'status':j['status'],'scenarios':j.get('scenarios')};assert proc.returncode!=0 and j['status']=='FAILED' and j['scenarios']=='NOT_RUN'
    result['mutations'].append(row);print(v,name,mode,'PASS' if passed else 'FAIL',flush=True)
    assert passed,row
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
