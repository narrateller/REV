#!/usr/bin/env python3
"""Build editable research-only FreeCAD variants, export and render without GUI."""
import argparse,json,sys,hashlib,math
from pathlib import Path
sys.path.append('/usr/lib/freecad-python3/lib')
import FreeCAD as App
import Part
from layout_common import load,value,selected,config,bounds,digest,ROOT

def render(document,objects,out,variant,deflection):
    from PIL import Image,ImageDraw,ImageFont
    from reportlab.pdfgen import canvas
    palettes={'frame':'#5d6c82','motion':'#df663d','chamber':'#54a0b0','channel':'#54a0b0','clamp':'#be8050','drive':'#406d9a','mounts':'#8290a3','guides':'#768491','infeed':'#d9b655','hopper':'#dfbd67','power':'#5e9d76','control':'#7a9b80','routes':'#a06c86','guard':'#bac2cd','output':'#828c9c','product':'#b38c68'}
    triangle_data=[]
    for obj in objects:
        if obj.Family=='guard':continue # exported CAD retains guards; drawing is an explicit cutaway
        vertices,faces=obj.Shape.tessellate(deflection)
        for face in faces:
            triangle_data.append(([tuple(vertices[i]) for i in face],palettes.get(obj.Family,'#999999')))
    views={'isometric':lambda p:(.82*p[0]-.55*p[1],.25*p[0]+.36*p[1]-.9*p[2],.4*p[0]+.6*p[1]+.4*p[2]),
           'side':lambda p:(p[0],-p[2],p[1]),'top':lambda p:(p[0],-p[1],p[2]),'front':lambda p:(p[1],-p[2],p[0])}
    for name,project in views.items():
        tris=[([project(p) for p in points],color) for points,color in triangle_data]
        allpts=[p for tri,_ in tris for p in tri];xmin=min(x[0] for x in allpts);xmax=max(x[0] for x in allpts);ymin=min(x[1] for x in allpts);ymax=max(x[1] for x in allpts)
        width,height=1500,950;scale=min(1380/(xmax-xmin),700/(ymax-ymin));ox=(width-(xmax-xmin)*scale)/2;oy=110+(700-(ymax-ymin)*scale)/2
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="#f5f5f2"/>']
        im=Image.new('RGB',(width,height),'#f5f5f2');draw=ImageDraw.Draw(im);pdf=canvas.Canvas(str(out/(name+'.pdf')),pagesize=(width,height))
        for points,color in sorted(tris,key=lambda t:sum(p[2] for p in t[0])/3):
            pts=[(ox+(p[0]-xmin)*scale,oy+(p[1]-ymin)*scale) for p in points]
            coords=' '.join(f'{x:.2f},{y:.2f}' for x,y in pts);svg.append(f'<polygon points="{coords}" fill="{color}" stroke="#39434c" stroke-width="0.45"/>')
            draw.polygon(pts,fill=color,outline='#39434c');pdf.setFillColor(color);pdf.setStrokeColor('#39434c');path=pdf.beginPath();path.moveTo(pts[0][0],height-pts[0][1])
            for x,y in pts[1:]:path.lineTo(x,height-y)
            path.close();pdf.drawPath(path,fill=1,stroke=1)
        title=f'REV / VARIANT {variant} / {name.upper()} / ASSUMED RESEARCH LAYOUT'
        subtitle='NOT REV DIMENSIONS  |  No strength or safety validation  |  Side guards hidden for visibility'
        svg+= [f'<text x="45" y="45" font-family="sans-serif" font-size="26" fill="#223344">{title}</text>',f'<text x="45" y="78" font-family="sans-serif" font-size="17">{subtitle}</text>','<text x="45" y="885" font-family="sans-serif" font-size="18">Ochre: intake / hopper / doser   Orange: moving tools   Teal: chamber / channel   Blue: cylinder</text>','<text x="45" y="920" font-family="sans-serif" font-size="17">Conceptual envelopes and interfaces only. Real strokes, loads and feedstock properties: UNKNOWN.</text>','</svg>']
        try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24);small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',17)
        except OSError:font=small=ImageFont.load_default()
        draw.text((45,26),title,fill='#223344',font=font);draw.text((45,67),subtitle,fill='#333333',font=small);draw.text((45,880),'Research geometry only. Real REV dimensions, strokes, loads and safety: UNKNOWN.',fill='#333333',font=small)
        pdf.setFillColor('#223344');pdf.setFont('Helvetica',22);pdf.drawString(45,height-45,title);pdf.setFont('Helvetica',15);pdf.drawString(45,height-78,subtitle);pdf.drawString(45,45,'Research geometry only; no physical press validation.');pdf.save()
        (out/(name+'.svg')).write_text('\n'.join(svg));im.save(out/(name+'.png'))
    # Actual section curves at y=0 from OpenCascade; no area/safety inference.
    plane=Part.Plane(App.Vector(0,0,0),App.Vector(0,1,0)).toShape()
    paths=[]
    for obj in objects:
        if obj.Family=='guard':continue
        for edge in obj.Shape.section(plane).Edges:
            points=edge.discretize(Deflection=deflection)
            paths.append([(p.x,p.z) for p in points])
    if paths:
        xs=[p[0] for line in paths for p in line];zs=[p[1] for line in paths for p in line];sx=1300/(max(xs)-min(xs));sz=650/(max(zs)-min(zs));s=min(sx,sz)
        lines=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="850"><rect width="100%" height="100%" fill="white"/><text x="40" y="40" font-size="24">ASSUMED section Y=0; actual FreeCAD section curves</text>']
        for line in paths:lines.append('<polyline points="'+' '.join(f'{60+(x-min(xs))*s:.2f},{100+(max(zs)-z)*s:.2f}' for x,z in line)+'" fill="none" stroke="#32485d" stroke-width="1.5"/>')
        lines.append('</svg>');(out/'section_y0.svg').write_text('\n'.join(lines))

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--variant',choices=['A','B'],required=True);p.add_argument('--out',required=True);args=p.parse_args()
    App.ParamGet('User parameter:BaseApp/Preferences/Document').SetInt('CountBackupFiles',0)
    data=load(args.inputs);out=Path(args.out);out.mkdir(parents=True,exist_ok=True);doc=App.newDocument('Research_'+args.variant);assembly=doc.addObject('App::Part','Assembly');sheet=doc.addObject('Spreadsheet::Sheet','Inputs');aliases={}
    for i,(key,item) in enumerate(data['parameters'].items(),1):
        alias='param_'+str(i);aliases[key]=alias;sheet.set('A'+str(i),key);sheet.set('B'+str(i),'='+item['value']+' '+item['unit']);sheet.setAlias('B'+str(i),alias)
    doc.recompute();objects=[];records=[]
    for c in selected(data,args.variant):
        obj=doc.addObject('Part::Box' if c['kind']=='box' else 'Part::Cylinder',c['id']);obj.Label=c['id']+' [ASSUMED]';assembly.addObject(obj)
        for property_name,text in [('Family',c['group']),('ResearchStatus','ASSUMED_NOT_REV'),('InputID',c['id']),('RigidGroup',c['rigid_group'])]:obj.addProperty('App::PropertyString',property_name);setattr(obj,property_name,text)
        for axis,ref in zip('xyz',c['position']):obj.setExpression('Placement.Base.'+axis,'Inputs.'+aliases[ref])
        if c['kind']=='box':
            for field,ref in zip(['Length','Width','Height'],c['size']):obj.setExpression(field,'Inputs.'+aliases[ref])
        else:
            obj.Placement.Rotation=App.Rotation(App.Vector(0,0,1),App.Vector(1,0,0));obj.setExpression('Radius','Inputs.'+aliases[c['radius']]);obj.setExpression('Height','Inputs.'+aliases[c['length']])
        objects.append(obj)
    zones=doc.addObject('App::Part','QueryVolumes')
    for zone_name,source_name in [('CylinderRemoval','cylinder_barrel'),('DoserRemoval','doser_slide')]:
        c=next(x for x in selected(data,args.variant) if x['id']==source_name);zone=doc.addObject('Part::Box',zone_name);zones.addObject(zone);zone.Label=zone_name+' [QUERY / ASSUMED]';zone.addProperty('App::PropertyString','Role');zone.Role='QUERY_NOT_SOLID'
        for axis,ref in zip('xyz',c['position']):zone.setExpression('Placement.Base.'+axis,'Inputs.'+aliases[ref])
        if c['kind']=='box':
            for prop,ref in zip(['Length','Width','Height'],c['size']):zone.setExpression(prop,'Inputs.'+aliases[ref]+(' + Inputs.'+aliases[data['config']['service_lift']] if prop=='Height' else ''))
        else:
            radius='Inputs.'+aliases[c['radius']];zone.setExpression('Placement.Base.y','Inputs.'+aliases[c['position'][1]]+' - '+radius);zone.setExpression('Placement.Base.z','Inputs.'+aliases[c['position'][2]]+' - '+radius);zone.setExpression('Length','Inputs.'+aliases[c['length']]);zone.setExpression('Width','2 * '+radius);zone.setExpression('Height','2 * '+radius+' + Inputs.'+aliases[data['config']['service_lift']])
    doc.recompute()
    for obj in objects:
        if obj.Shape.isNull(): print('NULL',obj.Name,obj.State,obj.getStatusString(),obj.ExpressionEngine)
    validity={obj.Name:not obj.Shape.isNull() and obj.Shape.isValid() for obj in objects}
    if not all(validity.values()):raise RuntimeError('invalid shape')
    cad_path=out/('layout_'+args.variant+'.FCStd');doc.saveAs(str(cad_path));Part.export(objects,str(out/('layout_'+args.variant+'.step')))
    render(doc,objects,out,args.variant,float(config(data,'tessellation'))*1000)
    for obj,c in zip(objects,selected(data,args.variant)):
        b=obj.Shape.optimalBoundingBox(False,False);lo,hi=bounds(data,c)
        records.append({'id':c['id'],'kind':c['kind'],'group':c['group'],'rigid_group':c['rigid_group'],'lo_m':[str(v) for v in lo],'hi_m':[str(v) for v in hi],'cad_bounds_mm':[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],'valid':validity[obj.Name],'volume_m3':obj.Shape.Volume/1e9,'expressions':len(obj.ExpressionEngine)})
    name=doc.Name;App.closeDocument(name);opened=App.openDocument(str(cad_path));opened.recompute()
    restored=[obj for obj in opened.Objects if hasattr(obj,'ResearchStatus')]
    if len(restored)!=len(objects) or not all(obj.Shape.isValid() for obj in restored):raise RuntimeError('reopen failed')
    probe=restored[0];before_x=probe.Placement.Base.x;original=data['parameters'][next(iter(data['parameters']))];opened.Inputs.set('B1','='+str(float(original['value'])+float(config(data,'obstacle_thickness')))+' m');opened.recompute();after_x=probe.Placement.Base.x
    editable=math.isclose(after_x-before_x,float(config(data,'obstacle_thickness'))*1000,rel_tol=1e-9,abs_tol=1e-9)
    if not editable:raise RuntimeError('spreadsheet edit failed to update geometry')
    opened.Inputs.set('B1','='+original['value']+' m');opened.recompute()
    chain=['cylinder_mount_rear','cylinder_barrel / rod','punch','material UNKNOWN']+(['channel / clamp','frame','cylinder_mount_rear'] if args.variant=='A' else ['end_stop','lock','frame','cylinder_mount_rear'])
    load_svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="240"><rect width="100%" height="100%" fill="white"/><text x="35" y="40" font-size="23">ASSUMED load-path topology; forces and contact capability UNKNOWN</text>']
    for i,label in enumerate(chain):
        x=35+i*175;load_svg.append(f'<rect x="{x}" y="85" width="165" height="55" fill="#e5edf2" stroke="#50657b"/><text x="{x+5}" y="115" font-size="12">{label}</text>')
        if i:load_svg.append(f'<path d="M {x-10} 112 L {x} 112" stroke="black"/>')
    load_svg.append('<text x="35" y="205" font-size="17">Gate-support branch, transverse clamp forces, joints, stability, unloading and strength remain UNKNOWN.</text></svg>');(out/'load_path.svg').write_text('\n'.join(load_svg))
    manifest={'classification':'ASSUMED_RESEARCH_NOT_REV','variant':args.variant,'input_sha256':digest(args.inputs),'source_hashes':{str(x.relative_to(ROOT)):digest(x) for x in [Path(__file__).resolve(),Path(__file__).with_name('layout_common.py')]},'cad_bounds_method':'optimalBoundingBox(useTriangulation=False, useShapeTolerance=False)','freecad_version':App.Version()[:3],'python':sys.version,'objects':records,'reopen_recompute':'PASS','edit_probe':{'parameter':'first spreadsheet coordinate','change_mm':after_x-before_x,'result':'PASS' if editable else 'FAIL'},'query_volumes':['CylinderRemoval','DoserRemoval'],'spreadsheet_parameters':len(aliases),'real_REV':data['real_REV'],'exports':{file.name:digest(file) for file in out.iterdir() if file.suffix in ('.FCStd','.step','.svg','.png','.pdf') and file.name!='phase_views.svg'}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');App.closeDocument(opened.Name);print(args.variant,len(records),'valid editable bodies; reopened and recomputed')
if __name__=='__main__':main()
