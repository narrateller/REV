"""Analysis solids for the four-post bayonet with integral load diaphragms."""
from dataclasses import dataclass, replace
from math import hypot

from geometry import Geometry
from hand import prior, support_checks


@dataclass(frozen=True)
class Layout:
    name: str
    front_x_mm: float = 184.
    rear_x_mm: float = 42.
    front_shank_mm: float = 35.
    rear_shank_mm: float = 21.
    top_depth_mm: float = 195.
    base_depth_mm: float = 230.
    top_skin_mm: float = 13.
    base_skin_mm: float = 14.
    top_front_webs_mm: tuple = (22., 27.)
    base_front_webs_mm: tuple = (24., 29.)
    rear_web_mm: float = 12.
    longitudinal_mm: float = 9.
    front_ring_web_mm: float = 22.
    rear_ring_web_mm: float = 12.
    close_seats: bool = False
    pressure_rib_mm: float = 0.
    front_skin_add_mm: float = 0.
    focused_wing: bool = False
    through_ring: bool = False
    seat_haunch_mm: float = 0.
    closed_flanks: bool = False


CASES = (
    Layout("integral_baseline", 194., 38., 35., 23., 185., 225.,
           top_front_webs_mm=(20., 24.), base_front_webs_mm=(22., 26.)),
    Layout("move_stations"),
    Layout("short_front_span", 175., 32.),
    Layout("deep_light", top_depth_mm=240., base_depth_mm=270., top_skin_mm=11., base_skin_mm=12.,
           top_front_webs_mm=(19., 23.), base_front_webs_mm=(21., 25.), rear_web_mm=10.),
    Layout("front_stiff", 186., 38., 37., 21., 215., 248.,
           top_front_webs_mm=(23., 30.), base_front_webs_mm=(25., 32.), front_ring_web_mm=26.),
    Layout("deep_front_stiff", 186., 38., 37., 21., 240., 275.,
           top_front_webs_mm=(25., 33.), base_front_webs_mm=(26., 35.), front_ring_web_mm=29.),
    Layout("heavy_boundary", 188., 35., 38., 21., 270., 300., 16., 17., (29., 39.), (31., 42.),
           front_ring_web_mm=35.),
)
CLOSE_CASES = (
    Layout("near_plane_rings", 187., 37., 35., 21., 196., 230., close_seats=True, focused_wing=True),
    Layout("supported_pressure_strip", 187., 37., 35., 21., 205., 242.,
           close_seats=True, pressure_rib_mm=18., front_skin_add_mm=9., focused_wing=True),
    Layout("deep_redistributed", 181., 34., 36., 21., 249., 285., 11., 11., (22., 28.), (23., 29.),
           rear_web_mm=9., longitudinal_mm=8., close_seats=True, pressure_rib_mm=13., front_skin_add_mm=6.,
           focused_wing=True),
    Layout("aligned_heavy", 187., 37., 38., 21., 260., 290., 16., 16., (34., 39.), (35., 42.),
           close_seats=True, pressure_rib_mm=20., front_skin_add_mm=14., focused_wing=True),
    Layout("aligned_deep_boundary", 187., 37., 39., 21., 315., 330., 19., 21., (42., 48.), (44., 48.),
           close_seats=True, pressure_rib_mm=23., front_skin_add_mm=19., focused_wing=True),
)
THROUGH_CASES = (
    Layout("through_ring_light", 187., 37., 35., 21., 200., 230., 12., 12., (20., 25.), (22., 26.),
           rear_web_mm=9., longitudinal_mm=8., close_seats=True, pressure_rib_mm=12., front_skin_add_mm=6.,
           focused_wing=True, through_ring=True, seat_haunch_mm=9.),
    Layout("through_ring_front_stiff", 187., 37., 36., 21., 215., 250., 14., 14., (23., 29.), (24., 30.),
           rear_web_mm=9., longitudinal_mm=8., close_seats=True, pressure_rib_mm=14., front_skin_add_mm=12.,
           focused_wing=True, through_ring=True, seat_haunch_mm=13.),
    Layout("through_ring_deeper", 187., 37., 36., 21., 255., 285., 13., 14., (28., 34.), (29., 38.),
           rear_web_mm=9., longitudinal_mm=8., close_seats=True, pressure_rib_mm=17., front_skin_add_mm=15.,
           focused_wing=True, through_ring=True, seat_haunch_mm=17.),
    Layout("through_ring_overweight", 187., 37., 39., 21., 288., 310., 17., 18., (35., 42.), (36., 44.),
           rear_web_mm=10., longitudinal_mm=9., close_seats=True, pressure_rib_mm=20., front_skin_add_mm=19.,
           focused_wing=True, through_ring=True, seat_haunch_mm=25.),
    Layout("through_ring_upper_boundary", 187., 37., 39., 22., 335., 380., 23., 24., (44., 52.), (46., 54.),
           rear_web_mm=12., longitudinal_mm=13., close_seats=True, pressure_rib_mm=24., front_skin_add_mm=25.,
           focused_wing=True, through_ring=True, seat_haunch_mm=30.),
)
FLANK_CASES = (
    replace(THROUGH_CASES[0], name="closed_flanks_light", closed_flanks=True),
    replace(THROUGH_CASES[0], name="closed_flanks_shoe_priority", closed_flanks=True, top_depth_mm=255.,
            top_skin_mm=14., top_front_webs_mm=(23., 30.), base_depth_mm=215., base_front_webs_mm=(20., 22.)),
    replace(THROUGH_CASES[1], name="closed_flanks_front", closed_flanks=True, top_depth_mm=258.,
            top_front_webs_mm=(27., 31.), base_depth_mm=230., base_front_webs_mm=(25., 29.)),
    replace(THROUGH_CASES[3], name="closed_flanks_stiff", closed_flanks=True, top_depth_mm=308.,
            top_front_webs_mm=(35., 45.), base_depth_mm=280., base_front_webs_mm=(31., 40.)),
    replace(THROUGH_CASES[4], name="closed_flanks_upper_boundary", closed_flanks=True),
)
CASES += CLOSE_CASES + THROUGH_CASES + FLANK_CASES

SHOE_Z_MM = 60.
SHOULDER_Z_MM = 20.
HEEL_Z_MM = -65.


def seat_levels(layout):
    return (70., -23.) if layout.close_seats else (SHOULDER_Z_MM, HEEL_Z_MM)


def station_data(layout, gate, peak):
    offset = layout.front_shank_mm - 35.
    front = prior.station_geometry(layout.front_x_mm, 0., gate, layout.front_shank_mm,
                                  67. + offset, 86. + offset, 70.)
    rear_head, rear_collar = (47., 62.) if layout.close_seats else (49., 67.)
    rear = prior.station_geometry(layout.rear_x_mm, 130., gate, layout.rear_shank_mm, rear_head, rear_collar, 50.)
    front["foot_r_mm"] = 70. + offset
    rear["foot_r_mm"] = 56. + layout.rear_shank_mm - 23.
    stations = {"front": front, "rear": rear}
    shoulder_mm, heel_mm = seat_levels(layout)
    for station in stations.values():
        station.update(foot_bearing_z_mm=heel_mm, post_length_mm=90. - heel_mm,
                       sleeve_shoulder_z_mm=shoulder_mm)
    pitch_mm = hypot(front["x_mm"] - rear["x_mm"], front["y_mm"] - rear["y_mm"])
    clearance_mm = pitch_mm - front["outer_envelope_r_mm"] - rear["outer_envelope_r_mm"]
    front_share = (peak["centroid_x_mm"] - rear["x_mm"]) / (front["x_mm"] - rear["x_mm"])
    baseline = prior.station_geometry(194., 0., gate, 35., 67., 86., 70.)
    baseline_share = (peak["centroid_x_mm"] - 38.) / (194. - 38.)
    # Hold the transverse load centroid fixed at its round-one value.
    y_c_mm = (2 * prior.SIDE_SHARE - 1) * (130. + baseline_share * (baseline["y_mm"] - 130.))
    checks = {name: support_checks(prior.rotor(peak["shoe_force_N"] * prior.SIDE_SHARE * weight,
                                              station, prior.TOOTH_SHARE), station, name)
              for (name, station), weight in zip(stations.items(), (front_share, 1 - front_share))}
    return stations, checks, y_c_mm, clearance_mm


class Volumes(Geometry):
    def box(self, x0, x1, y0, y1, z0, z1):
        return self.tag("Box", (x0, y0, z0, x1 - x0, y1 - y0, z1 - z0))

    def polygon(self, xy, z0, z1):
        nodes = [self.tag("Point", (*point, z0)) for point in xy]
        edges = [self.tag("Line", (a, b)) for a, b in zip(nodes, nodes[1:] + nodes[:1])]
        loop = self.tag("Curve Loop", edges)
        return self.extrude(self.tag("Plane Surface", (loop,)), z1 - z0)

    def cylinder_at(self, x, y, z0, z1, radius):
        return self.tag("Cylinder", (x, y, z0, 0, 0, z1 - z0, radius))

    def cut(self, name, starting_volumes, tools):
        tool_str = ",".join(map(str, tools))
        self.add(f"{name}[] = BooleanDifference{{Volume{{{starting_volumes}}}; Delete;}}"
                 f"{{Volume{{{tool_str}}}; Delete;}};")


def strip(path_xy, thickness_mm):
    y = [point[1] for point in path_xy]
    if not (all(a < b for a,b in zip(y,y[1:])) or all(a > b for a,b in zip(y,y[1:]))):
        raise ValueError(f"Strip path must be monotone in y: {path_xy}")
    return ([(x - thickness_mm / 2, y) for x, y in path_xy]
            + [(x + thickness_mm / 2, y) for x, y in reversed(path_xy)])


def body(g, name, layout, stations):
    top = name == "SHOE"
    h = layout.top_depth_mm if top else layout.base_depth_mm
    skin = layout.top_skin_mm if top else layout.base_skin_mm
    z0, z1 = (SHOE_Z_MM, SHOE_Z_MM + h) if top else (-h, 0.)
    x0, x1 = (5., 205.) if top else (-35., 214.)
    inner0, inner1 = z0 + skin - .25, z1 - skin + .25
    skins = ((z0, z0 + skin), (z1 - skin, z1))
    parts = [g.box(x0, x1, -108., 108., a, b) for a, b in skins]
    t = layout.longitudinal_mm
    if not layout.closed_flanks:
        parts.extend(g.box(x0, x1, y - t / 2, y + t / 2, inner0, inner1) for y in (-97., 97.))
    else:
        rear, front = (stations[k] for k in ("rear", "front"))
        x_rear, x_front = rear["x_mm"], front["x_mm"]
        y_rear, y_front = rear["y_mm"], front["y_mm"]
        for sign in (-1, 1):
            flank = [(x0, 101.), (x1, 101.), (x1, y_front),
                     (x_front, y_front), (x_rear, y_rear), (x0, y_rear)]
            parts.extend(g.polygon([(x, y*sign) for x, y in flank], a, b) for a, b in skins)
            flank_web = [(x0, y_rear - t - .6), (x_rear, y_rear - t - .6),
                         (x_front, y_front - t - .6), (x1, y_front - t-.6),
                         (x1, y_front-.6), (x_front, y_front-.6),
                         (x_rear, y_rear-.6), (x0, y_rear-.6)]
            parts.append(g.polygon([(x,y*sign) for x,y in flank_web], inner0, inner1))
    shoulder_mm, heel_mm = seat_levels(layout)
    if layout.pressure_rib_mm:
        t = layout.pressure_rib_mm
        parts.extend(g.box(119., 204., y-t/2, y+t/2, inner0, inner1) for y in (-71., 71.))
    if top:
        parts.append(g.box(5., 205., -75., 75., 60., 95.))
        if layout.front_skin_add_mm:
            parts.append(g.box(126., 205., -86., 86., 60., 95. + layout.front_skin_add_mm))
    else:
        parts.append(g.box(115., 220., -75., 75., -26., 0.))
        if layout.front_skin_add_mm:
            parts.append(g.box(126., 214., -86., 86., -26. - layout.front_skin_add_mm, 0.))
        parts.append(g.box(205., 220., -75.25, 75.25, 60., 175.))
        for sign in (-1, 1):
            yl, yh = sorted((74.75 * sign, 113. * sign))
            parts.append(g.box(205., 214., yl, yh, -.25, 175.))
    cuts = []
    for label, station in stations.items():
        front = label == "front"
        x, y = station["x_mm"], station["y_mm"]
        outer = station["outer_envelope_r_mm"] if top else station["foot_r_mm"] + 12.
        widths = (layout.top_front_webs_mm if top else layout.base_front_webs_mm) if front else (layout.rear_web_mm,) * 2
        mids = ((147., 192.) if layout.focused_wing else (144., 187.)) if front else (x - 21., x + 23.)
        ring_web_mm = layout.front_ring_web_mm if front else layout.rear_ring_web_mm
        end_y = y + .47 * outer
        rim_fraction = .80 if layout.focused_wing else .64
        offsets = [x - rim_fraction * outer, x + rim_fraction * outer]
        for xc, at_ring, width in zip(mids, offsets, widths):
            bend_y = 117. if layout.focused_wing and front else 85.
            path = [(at_ring, -end_y), (at_ring, -y), (xc, -bend_y), (xc, bend_y), (at_ring, y), (at_ring, end_y)]
            parts.append(g.polygon(strip(path, width), inner0, inner1))
        for sign in (-1, 1):
            ys = sign * y
            if top:
                ring_hi = z1 if layout.through_ring else max(99., shoulder_mm + 28.)
                parts.append(g.cylinder_at(x, ys, shoulder_mm - 22., ring_hi, outer))
                insertion_r = station["head_r_mm"] + (3. if layout.close_seats else 1.)
                cuts.extend([g.cylinder_at(x, ys, shoulder_mm - 23., z1 + 1., insertion_r),
                             g.cylinder_at(x, ys, shoulder_mm, z1 + 1., station["collar_r_mm"] + .5)])
                if not layout.close_seats:
                    for xc, at_ring in zip(mids, offsets):
                        local = [(xc, sign * 97.), (at_ring, ys), (at_ring, sign * end_y)]
                        parts.append(g.polygon(strip(local, ring_web_mm), 8., inner0 + .5))
                else:
                    # Upper collar throat is co-planar with the lower
                    # flange. The front and rear cover the seat directly.
                    parts.append(g.box(min(offsets), max(offsets), ys - .55 * outer,
                                       ys + .55 * outer, shoulder_mm - 22., inner0 + 7.))
            else:
                ring_lo = z0 if layout.through_ring else heel_mm
                parts.append(g.cylinder_at(x, ys, ring_lo, 0., outer))
                cuts.extend([g.cylinder_at(x, ys, z0 - 1., heel_mm, station["foot_r_mm"] + .5),
                             g.cylinder_at(x, ys, heel_mm, 1., station["shank_r_mm"] + 16.)])
            root_y = 71. if layout.focused_wing and front else 98.
            wing = [(mids[0] - widths[0] / 2, root_y), (mids[1] + widths[1] / 2, root_y),
                    (x + .81 * outer, y), (x + .54 * outer, y + .52 * outer),
                    (x - .54 * outer, y + .52 * outer), (x - .81 * outer, y)]
            parts.extend(g.polygon([(a, b * sign) for a, b in wing], lo, hi) for lo, hi in skins)
            if layout.close_seats:
                near = (z0, z0 + skin + (12. if front else 5.)) if top else (z1 - skin - (12. if front else 5.), z1)
                parts.append(g.polygon([(a, b * sign) for a, b in wing], *near))
            if layout.through_ring:
                # Full circular collar walls connect the two skins directly.
                # Widen the two flange webs under the forward ring at both
                # load levels, while preserving the bored assembly paths.
                extra = layout.seat_haunch_mm if front else layout.seat_haunch_mm / 2
                for xc, ring_x in zip(mids, offsets):
                    root = [(xc, sign * 91.), (xc, sign * min(131., y - 9.)), (ring_x, ys), (ring_x, sign * end_y)]
                    for lo, hi in ((z0, z0 + skin + extra), (z1 - skin - extra, z1)):
                        parts.append(g.polygon(strip(root, (widths[0]+widths[1])/2 + 9.), lo, hi))
    raw = name + "Raw"
    g.union(raw, parts)
    if top:
        cuts.extend([g.box(211., 500., -133., 133., -4., 193.),
                     g.box(205., 500., -113., 113., SHOE_Z_MM - .25, 175.)])
    else:
        cuts.extend([g.box(220., 500., -133., 133., -149., 200.),
                     g.box(214., 220., 79., 133., -149., 200.),
                     g.box(214., 220., -133., -79., -149., 200.)])
    g.cut(name + "Body", raw + "[]", cuts)


def make_geo(path, layout, stations, mesh_mm):
    g = Volumes()
    for number, name in enumerate(("SHOE", "FLOOR"), 1):
        body(g, name, layout, stations)
        g.add(f'If (#{name}Body[] != 1) Error("Disconnected {name}"); EndIf')
        g.add(f'Physical Volume("{name}",{number}) = {{{name}Body[]}};')
        g.add(f'v{name} = Mass Volume{{{name}Body[0]}}; Printf("{name} volume_mm3 %.12g", v{name});')
    g.add("Mesh.MshFileVersion = 2.2; Mesh.SaveAll = 0;")
    g.add("Mesh.ElementOrder = 2; Mesh.SecondOrderLinear = 1;")
    g.add("Mesh.MeshSizeFromPoints = 0; Mesh.MeshSizeExtendFromBoundary = 0;")
    g.add("Mesh.MeshSizeFromCurvature = 24; Mesh.Algorithm3D = 10;")
    g.add(f"Mesh.MeshSizeMin = {mesh_mm * .50}; Mesh.MeshSizeMax = {mesh_mm};")
    path.write_text("\n".join(g.lines) + "\n", encoding="ascii")

