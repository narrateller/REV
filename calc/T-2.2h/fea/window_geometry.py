"""Gmsh analysis geometry of the open window, locking cheeks and shoe."""

from math import acos, ceil, pi, sin, tan

import numpy as np

from layout import (FLOOR_SKIN_DEPTH_MM, FLOOR_TAPER_X_MM, LOCK_LOWER_Y_MM, LOCK_UPPER_Y_MM,
                    LOWER_RETURN_START_Y_MM, REAR_FLOOR_DEPTH_MM, SHOE_ABS_Y_MAX_MM,
                    STATIONS, WEAR_LAND_DEPTH_MM, WINDOW_FLOOR_ABS_Y_MM, WINDOW_REAR_X_MM,
                    WINDOW_SIDEWALL_ABS_Y_MM)


class Model:
    def __init__(self, mesh_mm):
        self.lines = ['SetFactory("OpenCASCADE");']
        self.id = 100
        self.mesh_mm = mesh_mm

    def tag(self, command, values):
        self.id += 1
        self.lines.append(f"{command}({self.id}) = {{{','.join(f'{i:.12g}' for i in values)}}};")
        return self.id

    def section(self, vertices, radii_mm, axes, fixed_mm):
        """Planar OCC loop. Corner rounds also cover reentrant vertices."""
        arcs = []
        for i, point in enumerate(np.asarray(vertices, dtype=float)):
            incoming = np.array(vertices[i-1]) - point
            outgoing = np.array(vertices[(i+1) % len(vertices)]) - point
            incoming /= np.linalg.norm(incoming)
            outgoing /= np.linalg.norm(outgoing)
            radius_mm = radii_mm[i]
            if not radius_mm:
                tag = self.point(point,axes,fixed_mm)
                arcs.append((tag,tag,None))
                continue
            angle = acos(float(np.clip(incoming @ outgoing,-1.,1.))) / 2
            tangent_mm = radius_mm / tan(angle)
            start = self.point(point+tangent_mm*incoming,axes,fixed_mm)
            end = self.point(point+tangent_mm*outgoing,axes,fixed_mm)
            cos_dir = (incoming+outgoing) / np.linalg.norm(incoming+outgoing)
            centre = self.point(point+radius_mm*cos_dir/sin(angle),axes,fixed_mm)
            tag = self.tag("Circle",(start,centre,end))
            segments = max(3,ceil(radius_mm*(pi-2*angle)/(self.mesh_mm*.6)))
            self.lines.append(f"Transfinite Curve {{{tag}}} = {segments+1};")
            arcs.append((start,end,tag))
        lines = []
        for i,(start,end,arc) in enumerate(arcs):
            lines.append(self.tag("Line",(arcs[i-1][1],start)))
            if arc:
                lines.append(arc)
        return self.tag("Curve Loop",lines)

    def point(self, values, axes, fixed_mm):
        xyz = np.full(3,fixed_mm)
        xyz[list(axes)] = values
        return self.tag("Point",(*xyz,self.mesh_mm))

    def prism(self, vertices, radii_mm, axes, fixed_mm, length_mm, holes=()):
        outer = self.section(vertices,radii_mm,axes,fixed_mm)
        inner = [self.section(corners,radii,axes,fixed_mm) for corners,radii in holes]
        face = self.tag("Plane Surface",[outer,*inner])
        d = [0.,0.,0.]
        d[({0,1,2}-set(axes)).pop()] = length_mm
        self.lines.append(f"tube{face}[] = Extrude {{{','.join(map(str,d))}}} {{ Surface{{{face}}}; }};")
        self.id += 1000
        return f"tube{face}[1]"

    def box(self,x0,x1,y0,y1,z0,z1):
        return str(self.tag("Box",(x0,y0,z0,x1-x0,y1-y0,z1-z0)))

    def combine(self, bodies):
        parts = ",".join(bodies[1:])
        self.lines.append(f"joined[] = BooleanUnion {{ Volume{{{bodies[0]}}}; Delete; }}"
                          f" {{ Volume{{{parts}}}; Delete; }};")
        self.lines.append("Coherence;")

    def geo(self):
        self.lines.extend((f"Mesh.MeshSizeMin={self.mesh_mm*.5}; Mesh.MeshSizeMax={self.mesh_mm};",
                           "Mesh.MeshSizeFromCurvature=0; Mesh.SecondOrderLinear=1;",
                           "Mesh.HighOrderOptimize=0; Mesh.RandomSeed=1;"))
        return "\n".join(self.lines) + "\n"


def rect(x_min_mm,x_max_mm,z_min_mm,z_max_mm):
    return [(x_min_mm,z_min_mm),(x_max_mm,z_min_mm),(x_max_mm,z_max_mm),(x_min_mm,z_max_mm)]


def cast(layout, size_mm, reinforcement=False):
    m = Model(size_mm)
    xa,xb = FLOOR_TAPER_X_MM
    wa_mm = WINDOW_REAR_X_MM
    floor_plan = [(wa_mm,-30.-REAR_FLOOR_DEPTH_MM),(xa,-30.-REAR_FLOOR_DEPTH_MM),
                  (xb,-30.-FLOOR_SKIN_DEPTH_MM),(205.,-30.-FLOOR_SKIN_DEPTH_MM),
                  (205.,-30.),(wa_mm,-30.)]
    floor_mm = WINDOW_FLOOR_ABS_Y_MM
    body = [m.prism(floor_plan,(0.,15.,15.,0.,0.,0.),(0,2),-floor_mm,2*floor_mm)]
    z_seat_mm = 30. + layout.shoe_depth_mm
    for side in (-1,1):
        def y_span(y0,y1):
            return tuple(sorted((side*y0,side*y1)))

        body.append(m.box(wa_mm,205.,*y_span(75.,WINDOW_SIDEWALL_ABS_Y_MM),-31.,30.))
        for name,station in STATIONS.items():
            x = station["x_mm"]
            w = station["key_width_mm"]/2 + .8
            leg_mm = station["leg_width_mm"]
            bottom_mm = REAR_FLOOR_DEPTH_MM if name == "rear" else FLOOR_SKIN_DEPTH_MM
            depth_mm = station["key_depth_mm"]
            cap_mm = z_seat_mm + depth_mm + WEAR_LAND_DEPTH_MM
            heel_mm = z_seat_mm - WEAR_LAND_DEPTH_MM
            top_mm = cap_mm + station["cap_depth_mm"]
            returned_mm = station["return_depth_mm"]
            y0,y1 = y_span(*LOCK_UPPER_Y_MM)
            slot = rect(x-w,x+w,heel_mm,cap_mm)
            light = rect(x-w,x+w,-17.,heel_mm-returned_mm)
            outer = rect(x-w-leg_mm,x+w+leg_mm,-38.,top_mm)
            body.append(m.prism(outer,(0.,0.,5.,5.),(0,2),y0,y1-y0,
                                holes=((slot,(15.,)*4),(light,(15.,)*4))))
            body.append(m.box(x-w-leg_mm,x+w+leg_mm,*y_span(floor_mm-1.,LOCK_UPPER_Y_MM[1]),
                              -30.-bottom_mm,-30.+1.))
            body.append(m.box(x-w-leg_mm,x+w+leg_mm,*y_span(LOWER_RETURN_START_Y_MM,LOCK_LOWER_Y_MM[1]),
                              heel_mm-returned_mm,heel_mm))
            if name == "rear":
                body.append(m.box(x-w-leg_mm,x+w+leg_mm,*y_span(104.,LOCK_UPPER_Y_MM[0]+1.),
                                  -34.,29.98))
    if reinforcement:
        front = STATIONS["front"]
        outer_leg_begin_mm = front["x_mm"] + front["key_width_mm"]/2 + .8
        for side in (-1,1):
            y0,y1 = sorted((side*110.,side*155.))
            profile = [(y0,-115.),(y1,-115.),(y1,60.),(y0,-49.)] if side>0 else [
                (y0,-115.),(y1,-115.),(y1,-49.),(y0,60.)]
            body.append(m.prism(profile,(5.,5.,15.,15.),(1,2),outer_leg_begin_mm,
                                205.-outer_leg_begin_mm))
    m.combine(body)
    return m.geo()


def shoe(layout, size_mm):
    m = Model(size_mm)
    rear = STATIONS["rear"]
    front = STATIONS["front"]
    left,rear_right = rear["x_mm"]-rear["key_width_mm"]/2,rear["x_mm"]+rear["key_width_mm"]/2
    front_left = front["x_mm"]-front["key_width_mm"]/2
    start_x, end_x, main_y, wing_y = 5.2,204.8,74.8,SHOE_ABS_Y_MAX_MM
    top = [(start_x,main_y),(left,main_y),(left,wing_y),(rear_right,wing_y),
           (rear_right,main_y),(front_left,main_y),(front_left,wing_y),(end_x,wing_y)]
    vertices = top + [(x,-y) for x,y in reversed(top)]
    radii_one_side = (1.,15.,5.,5.,15.,15.,5.,5.)
    m.prism(vertices,radii_one_side+radii_one_side[::-1],(0,1),30.,layout.shoe_depth_mm)
    return m.geo()

