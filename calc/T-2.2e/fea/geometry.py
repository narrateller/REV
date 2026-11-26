"""Generate only the local analysis solids of one bayonet station, in mm."""

from math import cos, radians, sin


class Geometry:
    def __init__(self):
        self.lines = ['SetFactory("OpenCASCADE");', 'Geometry.Tolerance = 1e-7;']
        self.count = 0

    def add(self, expression):
        self.lines.append(expression)

    def tag(self, kind, values):
        self.count += 1
        tag = 1000 * self.count
        self.add(f"{kind}({tag}) = {{{','.join(map(str, values))}}};")
        return tag

    def point(self, r_mm, angle_deg, z_mm):
        angle = radians(angle_deg)
        return self.tag("Point", (r_mm * cos(angle), r_mm * sin(angle), z_mm))

    def cylinder(self, radius_mm, z_mm, depth_mm):
        return self.tag("Cylinder", (0, 0, z_mm, 0, 0, depth_mm, radius_mm))

    def annulus(self, inner_mm, outer_mm, z_mm, depth_mm):
        outer = self.cylinder(outer_mm, z_mm, depth_mm)
        inner = self.cylinder(inner_mm, z_mm, depth_mm)
        name = f"ann{self.count}"
        self.add(f"{name}[] = BooleanDifference{{Volume{{{outer}}}; Delete;}}"
                 f"{{Volume{{{inner}}}; Delete;}};")
        return f"{name}[0]"

    def extrude(self, surface, z_mm):
        name = f"ex{self.count}"
        self.add(f"{name}[] = Extrude{{0, 0, {z_mm}}}{{Surface{{{surface}}};}};")
        return f"{name}[1]"

    def section(self, inner_mm, outer_mm, angle_deg, half_deg, z_mm):
        c = self.point(0, 0, z_mm)
        low, high = angle_deg - half_deg, angle_deg + half_deg
        il = self.point(inner_mm, low, z_mm)
        ol = self.point(outer_mm, low, z_mm)
        oh = self.point(outer_mm, high, z_mm)
        ih = self.point(inner_mm, high, z_mm)
        edges = (self.tag("Line", (il, ol)), self.tag("Circle", (ol, c, oh)),
                 self.tag("Line", (oh, ih)), self.tag("Circle", (ih, c, il)))
        loop = self.tag("Curve Loop", edges)
        return self.tag("Plane Surface", (loop,))

    def root_sector(self, radius_mm, angle_deg, width_deg, z_mm, root_mm):
        """Quarter-circle shoulder, revolved through one tooth or one heel sector."""
        a = self.point(radius_mm, angle_deg, z_mm - root_mm)
        b = self.point(radius_mm, angle_deg, z_mm)
        c = self.point(radius_mm + root_mm, angle_deg, z_mm)
        center = self.point(radius_mm + root_mm, angle_deg, z_mm - root_mm)
        edges = (self.tag("Line", (a, b)), self.tag("Line", (b, c)),
                 self.tag("Circle", (c, center, a)))
        loop = self.tag("Curve Loop", edges)
        surface = self.tag("Plane Surface", (loop,))
        name = f"rev{self.count}"
        self.add(f"{name}[] = Extrude{{{{0,0,1}},{{0,0,0}},{radians(width_deg)}}}"
                 f"{{Surface{{{surface}}};}};")
        return f"{name}[1]"

    def union(self, name, solids):
        first, *rest = map(str, solids)
        self.add(f"{name}[] = BooleanUnion{{Volume{{{first}}}; Delete;}}"
                 f"{{Volume{{{','.join(rest)}}}; Delete;}};")

    def write(self, path, mesh_mm, curvature_segments=0, bearing_z_mm=-155.):
        self.add("Mesh.MshFileVersion = 2.2;")
        self.add("Mesh.SaveAll = 0;")
        self.add("Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 1;")
        self.add(f"Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeFromCurvature = {curvature_segments};")
        self.add("Mesh.MeshSizeExtendFromBoundary = 0;")
        self.add(f"Mesh.MeshSizeMin = {mesh_mm}; Mesh.MeshSizeMax = 38.;")
        for field, z_mm in enumerate((0, bearing_z_mm), 1):
            self.add(f"Field[{field}] = Box; Field[{field}].VIn = {mesh_mm};")
            self.add(f"Field[{field}].VOut = 38.;")
            self.add(f"Field[{field}].XMin = -95; Field[{field}].XMax = 95;")
            self.add(f"Field[{field}].YMin = -95; Field[{field}].YMax = 95;")
            self.add(f"Field[{field}].ZMin = {z_mm - 7}; Field[{field}].ZMax = {z_mm + 9};")
            self.add(f"Field[{field}].Thickness = 16;")
        self.add("Field[3] = Min; Field[3].FieldsList = {1,2}; Background Field = 3;")
        path.write_text("\n".join(self.lines) + "\n", encoding="ascii", newline="\n")


SECTOR_DEG = 55.
THREE_TEETH_DEG = (0., 120., 240.)
ROOT_MM = 15.
BEARING_TOP_MM = -155.
CAST_CUT_MM = -116.
EDGE_RADIUS_MM = 5.
CROWN_MM = .1
# The projecting pad is an analytical geometry trial. The parent tooth root
# starts 8 mm above the bearing plane and the pad merges into that tooth.
PAD_PROJECTION_MM = 8.
PAD_INNER_RELIEF_MM = 4.
RADIAL_INSERTION_MM = 1.
LAND_CLEARANCE_MM = .001
SEAT_CROWN_MM = .1


def axial_planes(station):
    bearing_z_mm = station.get("foot_bearing_z_mm", -65.) - station.get("working_tooth_z_mm", 90.)
    elevated = station.get("sleeve_shoulder_z_mm", 20.) > 20.
    return bearing_z_mm, bearing_z_mm + (23. if elevated else 39.), -20. if elevated else -station["tooth_height_mm"]


def make_geometry(path, station, mesh_mm, half=False, curvature_segments=0):
    g = Geometry()
    bearing_z_mm, cast_z_mm, drive_z_mm = axial_planes(station)
    shank = station["shank_r_mm"]
    head = station["head_r_mm"]
    collar = station["collar_r_mm"]
    foot = station["foot_r_mm"]
    height = station["tooth_height_mm"]
    # All bodies are disconnected in the mesh. There is no TIE in this model.
    fixed = [g.cylinder(shank, bearing_z_mm - 28., height - bearing_z_mm + 28.),
             g.cylinder(foot, bearing_z_mm - 28., 28.)]
    for angle in THREE_TEETH_DEG:
        fixed.append(g.root_sector(shank, angle - SECTOR_DEG / 2, SECTOR_DEG, PAD_PROJECTION_MM, ROOT_MM))
        fixed.append(g.extrude(g.section(shank + PAD_INNER_RELIEF_MM, head, angle,
                                         SECTOR_DEG / 2, 0), height))
        fixed.append(g.extrude(g.section(shank, head, angle, SECTOR_DEG / 2, PAD_PROJECTION_MM),
                               height - PAD_PROJECTION_MM))
    root_blank = g.cylinder(shank + ROOT_MM, bearing_z_mm - .1, ROOT_MM + .1)
    root_tool = g.tag("Torus", (0, 0, bearing_z_mm + ROOT_MM, shank + ROOT_MM, ROOT_MM))
    g.add(f"footroot[] = BooleanDifference{{Volume{{{root_blank}}}; Delete;}}"
          f"{{Volume{{{root_tool}}}; Delete;}};")
    fixed.append("footroot[0]")
    g.union("fixed", fixed)

    # Radial overlap of one mm with the external ring guarantees a single solid.
    sleeve = [g.annulus(head + RADIAL_INSERTION_MM, collar, drive_z_mm, -drive_z_mm)]
    if drive_z_mm > -height:
        sleeve.append(g.annulus(head + RADIAL_INSERTION_MM, head + 2.85, -height, height))
    for angle in THREE_TEETH_DEG:
        sleeve.append(g.extrude(g.section(shank + 5., head + 2. * RADIAL_INSERTION_MM,
                                           angle, SECTOR_DEG / 2, -height), height))
    g.union("sleeve", sleeve)
    cast = g.annulus(shank + ROOT_MM + RADIAL_INSERTION_MM, foot + 12., bearing_z_mm,
                     cast_z_mm - bearing_z_mm)
    bodies = {"POST": "fixed[]", "SLEEVE": "sleeve[]", "CAST": str(cast)}
    for index, (name, volume) in enumerate(bodies.items(), 1):
        if half:
            tool = g.tag("Box", (-100., 0., -230., 200., 100., 340.))
            g.add(f"half_{index}[] = BooleanIntersection{{Volume{{{volume}}}; Delete;}}"
                  f"{{Volume{{{tool}}}; Delete;}};")
            volume = f"half_{index}[]"
        g.add(f'Physical Volume("{name}",{index}) = {{{volume}}};')
    g.write(path, mesh_mm, curvature_segments, bearing_z_mm)





