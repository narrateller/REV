"""Explicit native build and read-only per-scenario validation; old tool unchanged."""
import argparse,subprocess,zipfile
from bridge import *
sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App
import Part
from cad_validation import same_shape,shape_bounds,close_number,validate_queries

def aliases(data):return {r:'src_'+r for r in sorted(data['source_records'])}
def formulae(v):
    p='src_R3_BASE_'+v+'_'
    return {'width':'src_R3_IN_WIDTH','height':'src_R3_IN_HEIGHT','product':'src_R3_IN_PRODUCT_LENGTH','bore':p+'BORE','rod':p+'ROD','eject':p+'EJECT_STROKE','chamber':'src_R3_IN_MASS/(src_R3_IN_RHO*src_R3_IN_PHI*calc_width*calc_height)','occupied':'src_R3_IN_MASS/(src_R3_IN_RHO*calc_width*calc_height)','approach':'calc_chamber-calc_occupied','work':'calc_occupied-calc_product','return':'calc_approach+calc_work+calc_eject','wratio':'calc_width/(0.4 m)','hratio':'calc_height/(0.4 m)','xratio':'calc_chamber/(1.1 m)','top':'0.24 m*calc_hratio'}

def fill_sources(doc,data,v):
    sheet=doc.addObject('Spreadsheet::Sheet','Sources')
    for i,(pid,alias) in enumerate(aliases(data).items(),1):
        r=data['source_records'][pid];sheet.set('A'+str(i),pid);sheet.setAlias('B'+str(i),alias)
        sheet.set('B'+str(i),'='+str(r['value'])+(' '+r['unit'] if r['unit']!='1' else ''));sheet.set('C'+str(i),r['source']);sheet.set('D'+str(i),r['engineering_sha256'])
    for i,(key,formula) in enumerate(formulae(v).items(),len(aliases(data))+2):
        sheet.set('A'+str(i),'calc_'+key);sheet.set('B'+str(i),'='+formula);sheet.setAlias('B'+str(i),'calc_'+key)
    doc.recompute()
    cells={pid:'B'+str(i) for i,pid in enumerate(data['parameters'],1)}
    # A Fraction token followed by a unit must be parenthesized: a/b m can
    # parse as a/(b m). Preserve the registered SI rational, explicitly.
    for pid,item in data['parameters'].items():doc.Inputs.set(cells[pid],'='+repr(float(F(item['value'])))+' * 1 '+item['unit'])
    for c in data['parameter_changes']:
        if c['native_spreadsheet_formula']:doc.Inputs.set(cells[c['cad_parameter_id']],'='+c['native_spreadsheet_formula'])
    doc.recompute()
    doc.Assembly.addProperty('App::PropertyString','ResearchScenario');doc.Assembly.ResearchScenario='BASE_'+v
    doc.Assembly.addProperty('App::PropertyString','ExactSourceRecordsJSON');doc.Assembly.ExactSourceRecordsJSON=json.dumps(data['source_records'],sort_keys=True,separators=(',',':'))
    doc.Assembly.addProperty('App::PropertyString','Mode');doc.Assembly.Mode='fixed-budget'
    doc.Assembly.addProperty('App::PropertyString','PhysicalFeasibility');doc.Assembly.PhysicalFeasibility='INDETERMINATE'
    doc.Assembly.addProperty('App::PropertyString','BOpenPermission');doc.Assembly.BOpenPermission='INDETERMINATE' if v=='B' else 'NOT_APPLICABLE'
    refs=doc.addObject('App::Part','References')
    barrel=next(c for c in selected(data,v) if c['id']=='cylinder_barrel')
    bore=doc.addObject('Part::Cylinder','BoreMinimum');refs.addObject(bore);bore.Label='Minimum bore [CALCULATED FROM ASSUMED / NOT COTS]'
    bore.Placement=App.Placement(App.Vector(*[float(F(data['parameters'][k]['value']))*1000 for k in barrel['position']]),App.Rotation(App.Vector(0,0,1),App.Vector(1,0,0)))
    bore.Height=float(F(data['parameters'][barrel['length']]['value']))*1000;bore.setExpression('Radius','Sources.calc_bore/2')
    dose=doc.addObject('Part::Box','DoseEnvelope');refs.addObject(dose);dose.Label='Occupied raw-dose envelope [REFERENCE ONLY, NO COMPRESSION MODEL]'
    for prop,formula in [('Length','Sources.calc_occupied'),('Width','Sources.calc_width'),('Height','Sources.calc_height'),('Placement.Base.x','Sources.calc_approach'),('Placement.Base.y','-Sources.calc_width/2'),('Placement.Base.z','-Sources.calc_height/2')]:dose.setExpression(prop,formula)
    for obj in (bore,dose):obj.addProperty('App::PropertyString','Role');obj.Role='REFERENCE_NOT_SOLID'
    doc.recompute()
    return cells

def build(v,out):
    data=load(input_path(v));folder=Path(out)/v;folder.mkdir(parents=True,exist_ok=True)
    cmd=['/usr/bin/python3','-B',str(ROOT/'cad/layout/build_model.py'),'--inputs',str(input_path(v)),'--variant',v,'--out',str(folder)]
    run=subprocess.run(cmd,capture_output=True,text=True)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    path=folder/f'layout_{v}.FCStd';doc=App.openDocument(str(path));cells=fill_sources(doc,data,v)
    objects=[doc.getObject(c['id']) for c in selected(data,v)]
    assert all(not o.Shape.isNull() and o.Shape.isValid() for o in objects),'source expressions invalid geometry'
    from build_model import render
    render(doc,objects,folder,v+' / BASE_'+v+' / fixed-budget',float(config(data,'tessellation'))*1000)
    # Editing the actual source field must update CAD, then restore before save/export.
    cell='B'+str(list(aliases(data)).index('R3_IN_WIDTH')+1);original=doc.Sources.getContents(cell);before=doc.punch.Width.Value
    doc.Sources.set(cell,'='+str(data['source_records']['R3_IN_WIDTH']['value']*2)+' m');doc.recompute();after=doc.punch.Width.Value
    assert close_number(after,2*before),'source edit does not drive CAD';doc.Sources.set(cell,original);doc.recompute()
    doc.saveAs(str(path));Part.export(objects,str(folder/f'layout_{v}.step'))
    manifest=json.loads((folder/'manifest.json').read_text())
    manifest.update(source_linked_scenario='BASE_'+v,mode='fixed-budget',source_aliases=aliases(data),reference_objects=['BoreMinimum','DoseEnvelope'],source_edit_probe={'parameter':'R3_IN_WIDTH','before_mm':before,'temporary_double_mm':after,'restored':True},bridge_sha256=digest(SOURCE/'bridge.py'),native_adapter_sha256=digest(Path(__file__)))
    for r in manifest['objects']:
        obj=doc.getObject(r['id']);r['cad_bounds_mm']=shape_bounds(obj.Shape);r['volume_m3']=obj.Shape.Volume/1e9
    manifest['exports']={p.name:digest(p) for p in folder.iterdir() if p.suffix in ('.FCStd','.step','.svg','.png','.pdf')}
    save(folder/'manifest.json',manifest);App.closeDocument(doc.Name)
    return {'argv':cmd,'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr}

def validate(v,out):
    data=load(input_path(v));folder=Path(out)/v;manifest=json.loads((folder/'manifest.json').read_text());path=folder/f'layout_{v}.FCStd';step_path=folder/f'layout_{v}.step'
    assert manifest['input_sha256']==digest(input_path(v)),'stale native inputs'
    for file in (path,step_path):assert file.is_file() and digest(file)==manifest['exports'][file.name],'missing/corrupt/stale '+file.name
    with zipfile.ZipFile(path) as archive:assert archive.testzip() is None and 'Document.xml' in archive.namelist()
    doc=App.openDocument(str(path));scratch=App.newDocument('ExpressionSyntaxOnly');parser=scratch.addObject('Spreadsheet::Sheet','Syntax')
    def canonical(expression):
        parser.set('A1',expression);return parser.getContents('A1')
    try:
        evidence=[]
        for before_recompute in (True,False):
            if not before_recompute:doc.recompute()
            assert doc.Assembly.ResearchScenario=='BASE_'+v and doc.Assembly.Mode=='fixed-budget'
            assert doc.Assembly.ExactSourceRecordsJSON==json.dumps(data['source_records'],sort_keys=True,separators=(',',':')),'exact source records changed'
            assert doc.Assembly.PhysicalFeasibility=='INDETERMINATE'
            assert doc.Assembly.BOpenPermission==('INDETERMINATE' if v=='B' else 'NOT_APPLICABLE')
            for i,(pid,alias) in enumerate(aliases(data).items(),1):
                r=data['source_records'][pid];want='='+str(r['value'])+(' '+r['unit'] if r['unit']!='1' else '')
                quantity=doc.Sources.get(alias);wanted=App.Units.Quantity(str(r['value'])+(' '+r['unit'] if r['unit']!='1' else ''))
                if isinstance(quantity,(int,float)):quantity=App.Units.Quantity(quantity)
                assert quantity.Unit==wanted.Unit,'source unit changed '+pid
                assert abs(quantity.Value-wanted.Value)<=32*math.ulp(wanted.Value),'source cell changed '+pid
                assert doc.Sources.getAlias('B'+str(i))==alias
            for i,(key,formula) in enumerate(formulae(v).items(),len(aliases(data))+2):
                assert doc.Sources.getAlias('B'+str(i))=='calc_'+key
                assert doc.Sources.getContents('B'+str(i))==canonical('='+formula),'source derivation changed '+key
            cells={pid:'B'+str(i) for i,pid in enumerate(data['parameters'],1)}
            changed={r['cad_parameter_id']:r['native_spreadsheet_formula'] for r in data['parameter_changes']}
            for pid,item in data['parameters'].items():
                expected='='+changed[pid] if changed.get(pid) else '='+repr(float(F(item['value'])))+' * 1 '+item['unit']
                assert doc.Inputs.getContents(cells[pid])==canonical(expected),'registered input cell changed '+pid
            for r in data['parameter_changes']:
                if r['native_spreadsheet_formula']:assert doc.Inputs.getContents(cells[r['cad_parameter_id']])==canonical('='+r['native_spreadsheet_formula']),'bridge expression changed'
            query_names,qe=validate_queries(doc,data,v,manifest,App,Part)
            objects={o.Name:o for o in doc.Objects if hasattr(o,'ResearchStatus')};expected_ids={c['id'] for c in selected(data,v)}
            assert set(objects)==expected_ids and {o.Name for o in doc.Assembly.Group}==expected_ids,'native registry differs'
            assert {o.Name for o in doc.References.Group}=={'BoreMinimum','DoseEnvelope'}
            assert {o.Name for o in doc.Objects if getattr(o,'Role',None)=='REFERENCE_NOT_SOLID'}=={'BoreMinimum','DoseEnvelope'}
            reference={}
            barrel=next(c for c in selected(data,v) if c['id']=='cylinder_barrel');p=data['source_records'];g={k:F(x) for k,x in data['exact_geometry'].items()}
            reference['BoreMinimum']=Part.makeCylinder(float(p['R3_BASE_'+v+'_BORE']['value'])*500,float(F(data['parameters'][barrel['length']]['value']))*1000,App.Vector(*[float(F(data['parameters'][k]['value']))*1000 for k in barrel['position']]),App.Vector(1,0,0))
            w=float(p['R3_IN_WIDTH']['value'])*1000;h=float(p['R3_IN_HEIGHT']['value'])*1000
            reference['DoseEnvelope']=Part.makeBox(float(g['OCCUPIED_LENGTH'])*1000,w,h,App.Vector(float(g['APPROACH_STROKE'])*1000,-w/2,-h/2))
            for n,shape in reference.items():assert same_shape(doc.getObject(n).Shape,shape),'reference shape mismatch '+n
            all_solids={o.Name for o in doc.Objects if hasattr(o,'Shape') and not o.Shape.isNull() and o.TypeId!='App::Part' and o.Shape.Solids}
            assert all_solids==expected_ids|query_names|set(reference),'extra/missing native material/query/reference'
            records={r['id']:r for r in manifest['objects']};assert set(records)==expected_ids
            step=Part.read(str(step_path));assert not step.isNull() and step.isValid() and len(step.Solids)==len(expected_ids),'STEP invalid/count'
            unmatched=list(step.Solids)
            for c in selected(data,v):
                n=c['id'];obj=objects[n];pos=App.Vector(*[float(F(data['parameters'][k]['value']))*1000 for k in c['position']])
                expected=Part.makeBox(*[float(F(data['parameters'][k]['value']))*1000 for k in c['size']],pos) if c['kind']=='box' else Part.makeCylinder(float(F(data['parameters'][c['radius']]['value']))*1000,float(F(data['parameters'][c['length']]['value']))*1000,pos,App.Vector(1,0,0))
                assert same_shape(obj.Shape,expected),'native BRep mismatch '+n
                assert all(close_number(a,b) for a,b in zip(records[n]['cad_bounds_mm'],shape_bounds(obj.Shape))),'native manifest mismatch '+n
                match=next((i for i,s in enumerate(unmatched) if same_shape(s,expected)),None);assert match is not None,'STEP BRep mismatch '+n;unmatched.pop(match)
            evidence.append({'before_recompute':before_recompute,'bodies':len(expected_ids),'all_queries':qe,'references':{n:shape_bounds(doc.getObject(n).Shape) for n in reference},'FCStd_STEP_native_correspondence':'PASS'})
        return {'status':'PASS','variant':v,'evidence':evidence,'source_edit_probe':manifest['source_edit_probe'],'sha256':{p.name:digest(p) for p in (path,step_path)},'scope':'persisted research bodies, all query volumes, bore/dose references and editable source expressions; no construction/physics acceptance'}
    finally:App.closeDocument(scratch.Name);App.closeDocument(doc.Name)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--build',action='store_true');parser.add_argument('--variant',choices=VARS,required=True);parser.add_argument('--out',type=Path,default=OUT);args=parser.parse_args()
    try:
        result=build(args.variant,args.out) if args.build else validate(args.variant,args.out);print('RESULT_JSON:'+json.dumps(result));return 0
    except Exception as exc:print('RESULT_JSON:'+json.dumps({'status':'FAILED','reason':str(exc),'type':type(exc).__name__}));return 1
if __name__=='__main__':sys.exit(main())
