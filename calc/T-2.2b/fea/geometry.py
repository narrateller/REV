"""Generate OCC study geometry in .geo. This is the calculation idealization."""
from math import pi, sqrt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mass import PORTAL_X_MM, POST_X_MM, PORTAL_HEIGHT_MM, TIE_Y_MM, b_housing_boxes, B_POST_Z_MM, LOCK_PLAN_RIGHT_MM
from hand import HOUSING_Y_MM

HERE = Path(__file__).resolve().parent
GAP_MM = .025
SHOE_R_MM = 15.
LOCK_EDGE_MM = 5.
CROWN_MM = .10
TIE_AREA_MM2 = 976.
TIE_R_MM = sqrt(TIE_AREA_MM2/pi)
YOKE_BOTTOM_MM = B_POST_Z_MM[1]
YOKE_TOP_MM = YOKE_BOTTOM_MM+PORTAL_HEIGHT_MM
TIE_X_MM = tuple(sum(p)/2 for p in PORTAL_X_MM)
TIE_CENTERS_MM = tuple((x,y) for x in TIE_X_MM for y in (-TIE_Y_MM,TIE_Y_MM))
BODY_IDS = dict(HOUSING=1, SHOE=2, LEFT=3, RIGHT=4, BACK_YOKE=5, FRONT_YOKE=6,
                ST1=7, ST2=8, ST3=9, ST4=10)


class Geometry:
    def __init__(self):
        self.lines = ['SetFactory("OpenCASCADE");', 'Geometry.Tolerance = 1.e-7;',
                      'Mesh.MshFileVersion = 2.2;', 'Mesh.MaxNumThreads3D = 1;',
                      'Mesh.Algorithm3D = 1;', 'Mesh.ElementOrder = 2;',
                      'Mesh.SecondOrderLinear = 1;', 'Mesh.MeshSizeExtendFromBoundary = 0;', 'Mesh.Optimize = 1;']

    def add(self, line):
        self.lines.append(line)

    def box(self, name, x0, x1, y0, y1, z0, z1):
        self.add(f'{name} = newv; Box({name}) = {{{x0}, {y0}, {z0}, {x1-x0}, {y1-y0}, {z1-z0}}};')
        return name

    def cylinder(self, name, x, y, base, height, radius):
        self.add(f'{name} = newv; Cylinder({name}) = {{{x},{y},{base},0,0,{height},{radius}}};')
        return name

    def union(self, name, parts):
        a, *b = parts
        self.add(f'{name}[] = BooleanUnion{{Volume{{{a}}}; Delete;}}{{Volume{{{",".join(b)}}}; Delete;}};')
        return name+"[]"

    def subtract(self, name, base, tools):
        self.add(f'{name}[] = BooleanDifference{{Volume{{{base}}}; Delete;}}{{Volume{{{",".join(tools)}}}; Delete;}};')
        return name+"[]"

    def extrude(self, name, points, vector):
        pts = []
        for index, point in enumerate(points):
            tag = f'{name}p{index}'
            self.add(f'{tag} = newp; Point({tag}) = {{{",".join(map(str, point))}}};')
            pts.append(tag)
        curves = []
        for index, (a,b) in enumerate(zip(pts,pts[1:]+pts[:1])):
            tag = f'{name}l{index}'
            self.add(f'{tag} = newl; Line({tag}) = {{{a},{b}}};')
            curves.append(tag)
        self.add(f'{name}loop = newll; Curve Loop({name}loop) = {{{",".join(curves)}}};')
        self.add(f'{name}face = news; Plane Surface({name}face) = {{{name}loop}};')
        self.add(f'{name}v[] = Extrude {{{",".join(map(str,vector))}}} {{ Surface{{{name}face}}; }};')
        return f'{name}v[1]'

    def fillet(self, name, volume, bounds, radius):
        self.add(f'{name}edges[] = {{}};')
        for index,bounds6 in enumerate(bounds):
            tag = f'{name}edges{index}'
            self.add(f'{tag}[] = Curve In BoundingBox{{{",".join(map(str,bounds6))}}};')
            self.add(f'{name}edges[] += {tag}[];')
        self.add(f'{name}[] = Fillet{{{volume}}}{{{name}edges[]}}{{{radius}}};')
        return name+"[]"

    def physical(self, name, volume):
        self.add(f'Physical Volume("{name}",{BODY_IDS[name]}) = {{{volume}}};')


def build_geo(path):
    g = Geometry()
    housing = [g.box(f'h{i}',*box) for i,box in enumerate(b_housing_boxes())]
    # Blend each vertical column into its lower side rail, beside the lock
    # envelope. Cylinders remove the material outside an R15 tangent blend.
    for i,(xa,xb) in enumerate(POST_X_MM):
        x = xb if i==0 else xa
        x_far = x+(15. if i==0 else -15.)
        for j,y in enumerate((-216.,162.)):
            tag=f'root{i}{j}'
            blank=g.box(tag+'b',min(x,x_far),max(x,x_far),y,y+54,-18.,-3.)
            g.add(f'{tag}c = newv; Cylinder({tag}c) = {{{x_far},{y-1},-3.,0,56.,0,15.}};')
            housing.append(g.subtract(tag,blank,[tag+'c']))
    body=g.union('housingblank',housing)
    bores=[g.cylinder(f'hb{i}',x,y,-88.,370.,21.) for i,(x,y) in enumerate(TIE_CENTERS_MM)]
    g.physical('HOUSING',g.subtract('housing',body,bores))

    # Shoulder ring integral with the shoe. Above y=75 it begins at z=15;
    # subtract a quadrant cylinder to blend into the 150 mm product face.
    core=g.box('shcore',5.,205.,-75.,75.,0.,160.)
    lobes=[]
    for i,sign in enumerate((-1,1)):
        y0,y1=sorted((sign*75.,sign*111.))
        lobe=g.box(f'shl{i}',5.,205.,y0,y1,15.,160.)
        g.add(f'shcut{i} = newv; Cylinder(shcut{i}) = {{4.,{sign*90.},0.,202.,0,0,15.}};')
        lobes.append(g.subtract(f'shside{i}',lobe,[f'shcut{i}']))
        fy0,fy1=sorted((sign*75.,sign*90.))
        blank=g.box(f'shf{i}',5.,205.,fy0,fy1,0.,15.)
        g.add(f'shh{i} = newv; Cylinder(shh{i}) = {{4.,{sign*90.},0.,202.,0,0,15.}};')
        lobes.append(g.subtract(f'shfill{i}',blank,[f'shh{i}']))
    shoe=g.union('shoeblank',[core,*lobes])
    shoe=g.fillet('shoe',shoe,[(4.999,-111.001,159.999,205.001,111.001,160.001)],5.)
    g.physical('SHOE',shoe)

    for name,sign in (('RIGHT',1),('LEFT',-1)):
        low=160.+GAP_MM
        high=280.+GAP_MM
        lock=g.extrude(name.lower(),[(x,sign*y,low) for x,y in LOCK_PLAN_RIGHT_MM],(0.,0.,120.))
        bounds=[(-51.001,-145.001,z-.001,257.001,145.001,z+.001) for z in (low,high)]
        lock=g.fillet(name.lower()+'round',lock,bounds,LOCK_EDGE_MM)
        g.physical(name,lock)

    for i,((xa,xb),(pa,pb),name) in enumerate(zip(PORTAL_X_MM,POST_X_MM,('BACK_YOKE','FRONT_YOKE'))):
        z0,z1=YOKE_BOTTOM_MM,YOKE_TOP_MM
        main=g.box(f'yoke{i}',xa,xb,-216.,216.,z0,z1)
        corners=[g.box(f'yokeb{i}{j}',pa,pb,y,y+54,z0,z1) for j,y in enumerate((-216.,162.))]
        body=g.union(f'yokem{i}',[main,*corners])
        # Contact edge radius on central bearing band. Side clamp seats stay flat.
        hole=[g.cylinder(f'yb{i}{j}',TIE_X_MM[i],y,z0-1.,PORTAL_HEIGHT_MM+2,21.) for j,y in enumerate((-189.,189.))]
        g.physical(name,g.subtract(f'yoked{i}',body,hole))

    for i,(x,y) in enumerate(TIE_CENTERS_MM,1):
        flange_z=YOKE_TOP_MM
        shank=g.cylinder(f'st{i}pin',x,y,-87.,flange_z+10.+87.,TIE_R_MM)
        nut=g.cylinder(f'st{i}nut',x,y,flange_z,35.,33.)
        recess=g.cylinder(f'st{i}relief',x,y,flange_z-1.,4.,21.02)
        pad=g.subtract(f'st{i}pad',nut,[recess])
        g.physical(f'ST{i}',g.union(f'st{i}body',[shank,pad]))
    path.write_text('\n'.join(g.lines)+'\n',encoding='ascii',newline='\n')


if __name__ == '__main__':
    build_geo(HERE/'portal.geo')

