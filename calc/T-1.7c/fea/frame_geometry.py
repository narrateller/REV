"""OCC construction for the six traverses, in the local press-axis coordinates (z)."""
from math import acos, atan2, cos, hypot, pi, sin, sqrt, tan

from frame_analytic import (
    CORNERS, COLUMN_HOLE_mm, COLUMN_INNER_SEAT_BORE_mm,
    COLUMN_OUTER_BLEND_mm, HALF_PITCH_mm,
    OUTLET_HEIGHT_mm, OUTLET_RADIUS_mm, OUTLET_WIDTH_mm,
    REAR_INNER_RADIUS_mm, STUDS, STUD_HOLE_RADIUS_mm,
    outline_radius_mm,
)


def rotate(point, angle_rad):
    x, y = point
    c, s = cos(angle_rad), sin(angle_rad)
    return (x*c - y*s, x*s + y*c)


def unit(point):
    norm = hypot(*point)
    return tuple(value / norm for value in point)


def subtract(a, b):
    return (a[0] - b[0], a[1] - b[1])


def add(a, b, scale=1.):
    return (a[0] + scale*b[0], a[1] + scale*b[1])


class Geo:
    def __init__(self):
        self.lines = ['SetFactory("OpenCASCADE");']
        self.counter = 100
        self.points = {}

    def new(self):
        self.counter += 1
        return self.counter

    def emit(self, command):
        self.lines.append(command)

    def point(self, point, z_mm):
        key = tuple(round(q, 8) for q in (*point, z_mm))
        if key not in self.points:
            self.points[key] = self.new()
            self.emit(f"Point({self.points[key]}) = {{{key[0]}, {key[1]}, {key[2]}}};")
        return self.points[key]

    def line(self, a, b, z_mm):
        tag = self.new()
        self.emit(f"Line({tag}) = {{{self.point(a, z_mm)}, {self.point(b, z_mm)}}};")
        return tag

    def arc(self, a, center, b, z_mm):
        tag = self.new()
        # Gmsh OCC circles use the shortest arc for three distinct points.
        points = [self.point(p, z_mm) for p in (a, center, b)]
        self.emit(f"Circle({tag}) = {{{points[0]}, {points[1]}, {points[2]}}};")
        return tag

    def extrude(self, edges, z_len_mm, name):
        loop, face = self.new(), self.new()
        self.emit(f"Curve Loop({loop}) = {{{','.join(map(str, edges))}}};")
        self.emit(f"Plane Surface({face}) = {{{loop}}};")
        self.emit(f"{name}Ex[] = Extrude {{0,0,{z_len_mm}}} {{ Surface{{{face}}}; }};")
        self.emit(f"{name} = {name}Ex[1];")
        self.counter += 1000

    def cylinder(self, x, y, z, h, r):
        tag = self.new()
        self.emit(f"Cylinder({tag}) = {{{x},{y},{z},0,0,{h},{r}}};")
        return tag

    def cut(self, body, tools, result):
        self.emit(f"{result}[] = BooleanDifference{{ Volume{{{body}}}; Delete; }}"
                  f"{{ Volume{{{','.join(map(str, tools))}}}; Delete; }};")


def polygon(geo, vertices, radius_mm, z_mm):
    corners = []
    for i, p in enumerate(vertices):
        incoming = unit(subtract(vertices[i - 1], p))
        outgoing = unit(subtract(vertices[(i + 1) % len(vertices)], p))
        half_angle = acos(sum(a*b for a, b in zip(incoming, outgoing))) / 2
        tangent_mm = radius_mm / tan(half_angle)
        center = add(p, unit(add(incoming, outgoing)), radius_mm / sin(half_angle))
        corners.append((add(p, incoming, tangent_mm), center, add(p, outgoing, tangent_mm)))
    edges = []
    for i, (a, c, b) in enumerate(corners):
        edges.extend((geo.arc(a, c, b, z_mm), geo.line(b, corners[(i + 1) % len(corners)][0], z_mm)))
    return edges, corners


def profiled_outline(geo, v, end):
    waist = outline_radius_mm(v, end)
    quarter = [(waist, -73), (waist, 73), (370, 160), (370, 330), (330, 370), (160, 370)]
    points = [rotate(p, i*pi/2) for i in range(4) for p in quarter]
    edges, corners = polygon(geo, points, v.radius_mm, 0)
    return edges, [center for i, (_, center, _) in enumerate(corners) if i % 6 in (0, 1)]


def cast_outline(geo, v):
    """Ring, tangent straight ribs, and bosses with concave circular R36 blends."""
    r, b, boss, fillet = v.ring_radius_mm, v.rib_half_width_mm, 100., v.radius_mm
    pitch = hypot(HALF_PITCH_mm, HALF_PITCH_mm)
    root_u = sqrt((r+fillet)**2 - (b+fillet)**2)
    boss_u = pitch - sqrt((boss+fillet)**2 - (b+fillet)**2)
    assert boss_u > root_u
    root_center = (root_u, -b-fillet)
    cap_center = (boss_u, -b-fillet)
    hub_point = (r*root_center[0]/(r+fillet), r*root_center[1]/(r+fillet))
    cap_point = add((pitch, 0), subtract(cap_center, (pitch, 0)), boss/(boss+fillet))
    local_points = [hub_point, root_center, (root_u, -b), (boss_u, -b),
                    cap_center, cap_point, (pitch, 0), (pitch+boss, 0)]
    edges, roots = [], []
    for i in range(4):
        angle = pi/4 + i*pi/2
        lower = [rotate(p, angle) for p in local_points]
        upper = [rotate((x, -y), angle) for x, y in local_points]
        edges.extend([
            geo.arc(lower[0], lower[1], lower[2], 0),
            geo.line(lower[2], lower[3], 0),
            geo.arc(lower[3], lower[4], lower[5], 0),
            geo.arc(lower[5], lower[6], lower[7], 0),
            geo.arc(upper[7], upper[6], upper[5], 0),
            geo.arc(upper[5], upper[4], upper[3], 0),
            geo.line(upper[3], upper[2], 0),
            geo.arc(upper[2], upper[1], upper[0], 0),
            geo.arc(upper[0], (0., 0.), rotate(hub_point, angle+pi/2), 0),
        ])
        roots.extend([lower[1], upper[1], lower[4], upper[4]])
    return edges, roots


def rounded_box(geo, cx, cy, half_w, half_l, radius, z, h, angle, name):
    vertices = [add((cx, cy), rotate(p, angle))
                for p in ((-half_w,-half_l),(half_w,-half_l),(half_w,half_l),(-half_w,half_l))]
    edges, _ = polygon(geo, vertices, radius, z)
    geo.extrude(edges, h, name)
    return name


def model(v, end, level):
    geo = Geo()
    depth_mm = v.depth_mm
    outline, roots = cast_outline(geo, v) if v.name == "cast" else profiled_outline(geo, v, end)
    cavities = []
    geo.extrude(outline, depth_mm, "outer")
    for i, (x, y) in enumerate(CORNERS):
        geo.emit(f"padMark{i} = {i};")
    tools = [geo.cylinder(x, y, -1, depth_mm+2, COLUMN_HOLE_mm/2) for x,y in CORNERS]
    for x,y in CORNERS:
        cone = geo.new()
        r0 = COLUMN_INNER_SEAT_BORE_mm/2
        r1 = COLUMN_HOLE_mm/2
        r_start = r0+(r0-r1)/COLUMN_OUTER_BLEND_mm
        height_mm = COLUMN_OUTER_BLEND_mm+1.
        geo.emit(f"Cone({cone}) = {{{x},{y},-1,0,0,{height_mm},{r_start},{r1}}};")
        tools.append(cone)
    if end == "cylinder":
        tools.append(geo.cylinder(0, 0, -1, depth_mm+2, REAR_INNER_RADIUS_mm))
        tools.extend(geo.cylinder(x,y,-1,depth_mm+2,STUD_HOLE_RADIUS_mm) for x,y in STUDS)
    else:
        rounded_box(geo, 0, 0, OUTLET_WIDTH_mm/2, OUTLET_HEIGHT_mm/2,
                    OUTLET_RADIUS_mm, -1., depth_mm+2., 0, "outlet")
        tools.append("outlet")
    if v.flange_mm:
        for i in range(4):
            a = i*pi/2
            x,y = rotate((282.,0.),a)
            name = f"pocket{i}"
            rounded_box(geo, x,y,26.,104.,16.,v.flange_mm,
                        depth_mm-2*v.flange_mm,a,name)
            tools.append(name)
            cavities.append((x, y, a))
    geo.cut("outer", tools, "bodies")
    geo.emit("For i In {0:#bodies[]-1}")
    geo.emit('  Printf("VOL %g %.15g", bodies[i], Mass Volume{bodies[i]});')
    geo.emit("EndFor")
    clip = geo.new()
    geo.emit(f"Box({clip}) = {{0,0,-100,500,500,400}};")
    geo.emit(f"sector[] = BooleanIntersection{{ Volume{{bodies[]}}; Delete; }}{{ Volume{{{clip}}}; Delete; }};")
    base_mm, near_mm, pad_mm = [(48., 9., 6.), (43., 6.3, 4.4), (38., 4.5, 3.1),
                                (33., 3.6, 2.5), (29., 2.8, 2.), (29., 2.55, 1.9),
                                (29., 2.3, 1.7)][level]
    geo.emit(f"Mesh.MeshSizeMax = {base_mm};")
    curvature = 10
    geo.emit(f"Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = {curvature}; Mesh.SecondOrderLinear = 1;")
    geo.emit("Mesh.MeshSizeExtendFromBoundary = 0; Mesh.RandomSeed = 42; Mesh.MaxNumThreads3D = 1;")
    fields = []
    targets = [(x,y,v.radius_mm,near_mm,False) for x,y in roots if x >= 0 and y >= 0]
    if end == "cylinder":
        targets += [(x,y,STUD_HOLE_RADIUS_mm,pad_mm,True) for x,y in STUDS if x > -1e-6 and y > -1e-6]
        targets.append((0.,0.,REAR_INNER_RADIUS_mm,near_mm,True))
    else:
        targets.append((OUTLET_WIDTH_mm/2-OUTLET_RADIUS_mm,
                        OUTLET_HEIGHT_mm/2-OUTLET_RADIUS_mm,OUTLET_RADIUS_mm,pad_mm,False))
    for x,y,r,near,faces_only in targets:
        tag = geo.new()
        distance = f"Abs(Sqrt((x-({x}))^2+(y-({y}))^2)-{r})"
        if faces_only:
            depth_from_face = f"Min(Abs(z),Abs(z-{depth_mm}))"
            distance = f"Max({distance},({depth_from_face}-11)*.65)"
        geo.emit(f"Field[{tag}] = MathEval;")
        geo.emit(f'Field[{tag}].F = "{near}+({base_mm}-{near})*Min(1,Max(0,({distance}-1)/13))";')
        fields.append(tag)
    tag = geo.new()
    a = HALF_PITCH_mm
    radial = f"Sqrt((x-{a})^2+(y-{a})^2)"
    seat_distance = (f"Max(Abs({radial}-{COLUMN_INNER_SEAT_BORE_mm/2}),"
                     f"Max(0,z-{COLUMN_OUTER_BLEND_mm}))")
    geo.emit(f'Field[{tag}] = MathEval; Field[{tag}].F = "{near_mm}+({base_mm}-{near_mm})*Min(1,{seat_distance}/24)";')
    fields.append(tag)
    if v.flange_mm:
        face_mm = (15.,12.,9.,7.,5.5,5.,4.5)[level]
        for x,y,_ in cavities:
            if x < -1e-6 or y < -1e-6:
                continue
            half_x,half_y = (30.,108.) if abs(x)>abs(y) else (108.,30.)
            for z in (v.flange_mm, depth_mm-v.flange_mm):
                tag = geo.new()
                geo.emit(f"Field[{tag}] = Box; Field[{tag}].XMin = {x-half_x}; Field[{tag}].XMax = {x+half_x};")
                geo.emit(f"Field[{tag}].YMin = {y-half_y}; Field[{tag}].YMax = {y+half_y};")
                geo.emit(f"Field[{tag}].ZMin = {z-6}; Field[{tag}].ZMax = {z+6};")
                geo.emit(f"Field[{tag}].Thickness = 12; Field[{tag}].VIn = {face_mm}; Field[{tag}].VOut = {base_mm};")
                fields.append(tag)
    if fields:
        tag = geo.new()
        geo.emit(f"Field[{tag}] = Min; Field[{tag}].FieldsList = {{{','.join(map(str, fields))}}};")
        geo.emit(f"Background Field = {tag};")
    return "\n".join(geo.lines) + "\n", roots, cavities, (base_mm, near_mm, pad_mm)
