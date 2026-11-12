"""Before/after nominal sections; full native models and pair evidence are separate."""
import html,json,sys
from pathlib import Path
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'cad/layout'))
from layout_common import load,selected,bounds,config


def write_figures(out):
    old=load(ROOT/'cad/layout/conditional_inputs.assumed.json');new=load(ROOT/'cad/layout_correction/inputs.assumed.json');out=Path(out)
    def figure(filename,title,axes,limits,parts,motion=False):
        w,h=1500,900;svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/><text x="35" y="40" font-size="23">{html.escape(title)}</text><text x="35" y="70" font-size="16">ASSUMED / nominal sections; NOT REV design or safety validation; units m</text>']
        for panel,(label,data) in enumerate([('BEFORE / de377f0',old),('AFTER / research rev4',new)]):
            x0=55+panel*735;y0=140;ww=640;hh=620;(u0,u1),(v0,v1)=limits
            def x(v):return x0+(float(v)-u0)/(u1-u0)*ww
            def y(v):return y0+hh-(float(v)-v0)/(v1-v0)*hh
            svg.append(f'<text x="{x0}" y="115" font-size="20">{label}</text><rect x="{x0}" y="{y0}" width="{ww}" height="{hh}" fill="#f4f7f8" stroke="#78858c"/>')
            svg.append(f'<defs><clipPath id="panel{panel}"><rect x="{x0}" y="{y0}" width="{ww}" height="{hh}"/></clipPath></defs><g clip-path="url(#panel{panel})">')
            byid={c['id']:c for c in selected(data,'B')}
            for name,color in parts:
                if name not in byid:continue
                lo,hi=bounds(data,byid[name]);poses=[(lo,hi,False)]
                if motion and name in ('lock','end_stop'):
                    d=config(data,'open_lock_y' if name=='lock' else 'open_stop_y');a=list(lo);b=list(hi);a[1]+=d;b[1]+=d;poses.append((a,b,True))
                elif name=='inlet_gate':
                    d=config(data,'gate_isolate_y')/2;poses=[([lo[0],lo[1]+d,lo[2]],[hi[0],hi[1]+d,hi[2]],False)]
                for a,b,ghost in poses:
                    u,v=axes;xx,yy=x(a[u]),y(b[v]);rw,rh=x(b[u])-xx,y(a[v])-yy
                    svg.append(f'<rect x="{xx:.2f}" y="{yy:.2f}" width="{rw:.2f}" height="{rh:.2f}" fill="{color}" fill-opacity="{0.2 if ghost else 0.65}" stroke="{color}" stroke-width="2"'+(' stroke-dasharray="8 4"' if ghost else '')+'/>')
                    if not ghost:svg.append(f'<text x="{max(x0+3,min(x0+ww-115,xx+3)):.2f}" y="{max(y0+14,min(y0+hh-2,yy+14)):.2f}" font-size="11">{name}</text>')
            svg.append('</g>')
            svg.append(f'<text x="{x0}" y="{y0+hh+30}" font-size="15">{("XYZ"[axes[0]])} = {u0} .. {u1}; {("XYZ"[axes[1]])} = {v0} .. {v1}</text>')
        svg.append('<text x="35" y="835" font-size="16">Solid rectangles: fixed/closed; dashed: fully open B. Gate shown at half ISOLATE stroke.</text><text x="35" y="865" font-size="16">Only listed section bodies shown; full geometry/continuous checks in FCStd and JSON matrices.</text></svg>');(out/filename).write_text('\n'.join(svg))
    figure('gate_before_after.svg','Inlet gate: explicit slot, lower wall and enclosed retract bay',(1,2),[(-.3,.95),(.18,.72)],[('pocket_R','#346c94'),('pocket_R_lower','#346c94'),('gate_support','#73808e'),('gate_house_top','#299d99'),('gate_service_cap','#299d99'),('inlet_gate','#db673c')])
    figure('stop_before_after.svg','B output: reaction portal, widened lock and relocated guard',(0,1),[(1.0,1.7),(-.4,2.0)],[('stop_support','#408d91'),('stop_support_L','#408d91'),('guard_right','#78818d'),('end_stop','#d99536'),('lock','#d15d46')],True)


if __name__=='__main__':write_figures(sys.argv[1])
