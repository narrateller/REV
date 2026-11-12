"""Native FCStd profiles before/after; presentation only, no collision oracle."""
import html, json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'cad/layout_correction'))
from assess import NativeWitness
from layout_common import load,config,digest


def figures():
    out=ROOT/'cad/build/frame_mount';before=NativeWitness(ROOT/'cad/build/layout_correction');after=NativeWitness(out)
    data=load(ROOT/'cad/frame_mount/inputs.assumed.json');colors={'frame':'#7896a8','mounts':'#d25b45','cylinder':'#3977b9','output':'#7d9c5a'}
    files=[]
    def figure(name,title,axes,limits,names,circles=(),service=False):
        svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1030" viewBox="0 0 1600 1030">','<rect width="100%" height="100%" fill="#fafaf7"/>',f'<text x="35" y="38" font-family="sans-serif" font-size="25">{html.escape(title)}</text>','<text x="35" y="70" font-family="sans-serif" font-size="18">ASSUMED research / native FCStd profiles, metres / no REV hardware, strength or safety validation</text>']
        native_records=[]
        for panel,(label,native) in enumerate([('BEFORE / 66924ae',before),('AFTER / rev7',after)]):
            left=55+panel*790;top=145;width=680;height=580;lo,hi=limits;scale=min(width/(hi[0]-lo[0]),height/(hi[1]-lo[1]));xoff=left+(width-(hi[0]-lo[0])*scale)/2;yoff=top+(height-(hi[1]-lo[1])*scale)/2
            def point(x,y):return xoff+(x-lo[0])*scale,yoff+(hi[1]-y)*scale
            svg += [f'<text x="{left}" y="115" font-family="sans-serif" font-size="22">{label}</text>',f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="white" stroke="#ccd1d5"/>']
            for name in names:
                obj=native.objects['A'].get(name)
                if obj is None:continue
                bb=obj.Shape.optimalBoundingBox(False,False);a=(bb.XMin/1000,bb.YMin/1000,bb.ZMin/1000);b=(bb.XMax/1000,bb.YMax/1000,bb.ZMax/1000);i,j=axes
                native_records.append({'panel':label,'id':name,'native_bounds_m':[a,b]})
                color=('#3977b9' if name=='cylinder_barrel' else '#df943b') if name in circles else colors.get(obj.Family,'#dfaf49');xx,yy=point(a[i],b[j]);ww=(b[i]-a[i])*scale;hh=(b[j]-a[j])*scale
                if name not in circles:
                    # QtSvg Tiny does not consistently implement SVG clipPath;
                    # crop presentation rectangles explicitly, never native CAD.
                    x0,y0=max(xx,left),max(yy,top);x1,y1=min(xx+ww,left+width),min(yy+hh,top+height)
                    if x1>x0 and y1>y0:
                        svg.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="{color}" fill-opacity="0.45" stroke="{color}" stroke-width="2"/>')
                else:
                    cx,cy=point((a[i]+b[i])/2,(a[j]+b[j])/2);radius=float(obj.Radius.Value)/1000*scale
                    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{color}" fill-opacity="0.14" stroke="{color}" stroke-width="3"/>')
                    if service:
                        lift=float(config(data,'service_lift'));tx,ty=point((a[i]+b[i])/2,(a[j]+b[j])/2+lift)
                        svg.append(f'<circle cx="{tx}" cy="{ty}" r="{radius}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="7,5"/><line x1="{cx}" y1="{cy}" x2="{tx}" y2="{ty}" stroke="{color}" stroke-width="2" stroke-dasharray="4,5"/>')
            for k,name in enumerate(names):
                svg.append(f'<text x="{left+(k//6)*340}" y="{760+(k%6)*24}" font-family="monospace" font-size="14">{html.escape(name)}</text>')
            svg.append(f'<text x="{left}" y="925" font-family="sans-serif" font-size="16">Axes: {"XYZ"[axes[0]]} / {"XYZ"[axes[1]]}; limits {lo} .. {hi} m</text>')
        svg += ['<text x="35" y="970" font-family="sans-serif" font-size="17">Projected profiles may overlap at butt faces: use 3D interval evidence. Fasteners, radial location and loads UNKNOWN.</text>','<text x="35" y="1000" font-family="sans-serif" font-size="17">All intervals and remaining conflicts are reported separately. Whole press READY INDETERMINATE; G1 OPEN.</text>','</svg>']
        return '\n'.join(svg),native_records
    specs=[('frame_before_after','Frame / transverse members and cylinder supports, before and after',(0,2),((-3.35,-1.22),(-.55,.45)),['base_L','side_rail_L','crossbar0','crossbar1','cylinder_mount_rear','cylinder_mount_front','cylinder_seat_bridge','upper_post_L0','upper_post_L1','cylinder_barrel','rod'],(),False),('seat_before_after','Open-top front U seat / actual axial native profiles',(1,2),((-.42,-.42),(.42,.42)),['cylinder_mount_front','cylinder_seat_L','cylinder_seat_R','cylinder_barrel','rod'],('cylinder_barrel','rod'),False),('crossbar_before_after','Transverse members / rail joints / output interface',(0,1),((-3.4,-.9),(2.65,.9)),['side_rail_L','side_rail_R','crossbar0','crossbar1','crossbar2','cylinder_seat_bridge','output_support'],(),False),('service_before_after','Rod and barrel vertical extraction / outbound and return share the corridor',(1,2),((-.45,-.45),(.45,1.7)),['cylinder_mount_front','cylinder_seat_L','cylinder_seat_R','cylinder_barrel','rod'],('cylinder_barrel','rod'),True)]
    records=[]
    try:
        for filename,title,axes,limits,names,circles,service in specs:
            content,items=figure(filename,title,axes,limits,names,circles,service);p=out/(filename+'.svg');p.write_text(content);files.append(p);records.append({'file':p.name,'native_records':items,'projection_not_section':True})
        renderer='''from PySide2 import QtSvg,QtGui,QtCore
from pathlib import Path
import sys
app=QtGui.QGuiApplication([])
for filename in sys.argv[1:]:
 r=QtSvg.QSvgRenderer(filename);assert r.isValid(),filename
 i=QtGui.QImage(1600,1030,QtGui.QImage.Format_ARGB32);i.fill(QtCore.Qt.white)
 p=QtGui.QPainter(i);r.render(p);p.end();assert i.save(str(Path(filename).with_suffix('.png')))
'''
        subprocess.run(['/usr/bin/python3','-c',renderer,*map(str,files)],env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},check=True)
        files += [p.with_suffix('.png') for p in list(files)]
        manifest={'sources':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),ROOT/'cad/frame_mount/inputs.assumed.json']},'figures':records,'sha256':{p.name:digest(p) for p in files},'scope':'native primitive projections from FCStd, no inference of full-interval clearance; detail geometry common to A/B'}
        (out/'figure_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('4 before/after native-profile SVG figures generated; general A/B PNG/SVG/PDF from frozen native builder')
    finally:before.close();after.close()


if __name__=='__main__':figures()
