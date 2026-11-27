"""Run REV geometry checks on a saved FreeCAD document."""

import hashlib
import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass
from itertools import combinations, product
from pathlib import Path


TOOL_VERSION = "1.2.0"
DEFAULT_FREECADCMD = "E:/Tools/FreeCAD-1.1/bin/freecadcmd.exe"
DEFAULT_DENSITY_KG_M3 = 7850
CONTACT_TOL_MM = 0.01
GEOMETRY_TOL_MM = 1e-7
# Ignore face-intersection slivers smaller than a square micrometre.
CONTACT_AREA_TOL_MM2 = 1e-6
WALL_SAMPLES_MIN = 8
ARC_STEP_DEG = 5
# Only these FreeCAD properties supply geometry to the result.
# App::Link.LinkedObject is handled separately because source visibility matters.
GEOMETRY_OPERANDS = {
    "PartDesign::Body": ("Group",),
    "Part::Cut": ("Base", "Tool"),
    "Part::Fuse": ("Base", "Tool"),
    "Part::Common": ("Base", "Tool"),
    "Part::MultiFuse": ("Shapes",),
    "Part::MultiCommon": ("Shapes",),
    "Part::Extrusion": ("Base",),
    "Part::Revolution": ("Source",),
    "Part::Mirroring": ("Source",),
    "Part::Scale": ("Base",),
    "Part::Offset": ("Source",),
    "Part::Offset2D": ("Source",),
    "Part::Thickness": ("Faces",),  # LinkSub: Faces[0] is the source object.
    "Part::Fillet": ("Base",),
    "Part::Chamfer": ("Base",),
    "Part::Compound": ("Links",),
    "Part::Loft": ("Sections",),
    "Part::Sweep": ("Sections", "Spine"),
}
REFERENCE_PROPERTIES = ("Support", "AttachmentSupport", "PlacementRelTo", "RevPair")
ROLES = {"machine", "moving", "punch", "chamber_liner", "feed_path", "hopper"}
GATE_SPECS = {
    "G-ENV": ("C-ENV-01", "mm"),
    "G-MASS": ("C-MASS-01", "kg"),
    "G-COLL": ("C-COLL-01", "mm3"),
    "G-FEED": ("C-FEEDPATH-01", "mm2"),
    "G-CLEAR": ("C-CLR-01", "mm"),
}


@dataclass
class Body:
    name: str
    label: str
    shape: object
    roles: frozenset
    groups: frozenset
    material: str | None
    density_kg_m3: float
    feed_absence_note: str | None
    pair: str | None
    stroke_axis: object | None


def freecadcmd_path():
    return os.environ.get("REV_FREECADCMD", DEFAULT_FREECADCMD)


def mapping(value, field):
    if not isinstance(value, dict):
        raise ValueError(f"{field}: expected a mapping")
    return value


def number(value, field):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{field}: expected a finite number")
    return value


def triplet(value, field):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{field}: expected three coordinates in mm")
    return tuple(number(item, field) for item in value)


def read_yaml(data, field):
    import yaml

    return mapping(yaml.safe_load(data), field)


def is_group(obj):
    return obj.isDerivedFrom("App::Part") or obj.isDerivedFrom("App::DocumentObjectGroup")


def parent_groups(obj):
    for parent in obj.InList:
        if is_group(parent) and obj in parent.Group:
            yield parent
            yield from parent_groups(parent)


def linked_objects(value):
    """Read a Link, LinkList, LinkSub (object, subnames), or LinkSubList."""
    if hasattr(value, "Name"):
        yield value
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from linked_objects(item)


def consumed_objects(objects):
    """Find geometric operands and unclassified references in the document."""
    consumed = set()
    unclassified = {}
    for obj in objects:
        if obj.TypeId == "App::Link" or obj.isDerivedFrom("App::Link"):
            source = obj.LinkedObject
            if source and source.Document == obj.Document and not source.Visibility:
                consumed.add(source.Name)
                if is_group(source):
                    consumed.update(
                        child.Name for child in objects if source in parent_groups(child)
                    )
            continue
        properties = GEOMETRY_OPERANDS.get(obj.TypeId)
        if properties is None:
            properties = next((keys for type_id, keys in GEOMETRY_OPERANDS.items()
                               if obj.isDerivedFrom(type_id)), None)
        if properties is not None:
            if obj.isDerivedFrom("PartDesign::Body") or not obj.Shape.isNull():
                consumed.update(source.Name for key in properties
                                for source in linked_objects(getattr(obj, key, None))
                                if source.Document == obj.Document)
            continue
        dependencies = obj.OutList
        if dependencies:
            properties = REFERENCE_PROPERTIES + (("Group",) if is_group(obj) else ())
            if obj.TypeId.startswith("TechDraw::") and obj.isDerivedFrom("TechDraw::DrawViewPart"):
                # FreeCAD documents Source as the "3D Shape to view".
                properties += ("Source",)
            references = {source.Name for key in properties
                          for source in linked_objects(getattr(obj, key, None))}
            unclassified[obj.Name] = {
                child.Name for child in dependencies
                if child.Document == obj.Document and child.Name not in references
            }
    return consumed, unclassified


def body_metadata(obj, role_map):
    entry = mapping(role_map.get(obj.Label, {}), f"roles[{obj.Label!r}]")
    roles = getattr(obj, "RevRole", None) or entry.get("role", "machine")
    if isinstance(roles, str):
        roles = [roles]
    if not isinstance(roles, list) or not roles or any(
        not isinstance(role, str) or role not in ROLES for role in roles
    ):
        raise ValueError(f"{obj.Name}: invalid RevRole or YAML role: {roles!r}")
    roles = frozenset(roles)
    if "feed_path" in roles:
        if roles != {"feed_path"}:
            raise ValueError(f"{obj.Name}: feed_path must be the sole role")
    else:
        roles |= {"machine"}
    material = getattr(obj, "RevMaterial", None) or entry.get("material")
    if material is not None and not isinstance(material, str):
        raise ValueError(f"{obj.Name}: expected a material name")
    density = getattr(obj, "RevDensity_kg_m3", None)
    if density is None:
        density = entry.get("density_kg_m3", DEFAULT_DENSITY_KG_M3)
    density_kg_m3 = number(density, f"{obj.Name}.density_kg_m3")
    if density_kg_m3 <= 0:
        raise ValueError(f"{obj.Name}: density_kg_m3 must be positive")
    note = entry.get("feed_absence_note")
    if note is not None and (not isinstance(note, str) or not note.strip()):
        raise ValueError(f"{obj.Name}: expected a feed_absence_note string")
    return roles, material, density_kg_m3, note


def read_bodies(doc, role_map):
    consumed, unclassified = consumed_objects(doc.Objects)
    bodies = []
    non_solids = []
    for obj in doc.Objects:
        if obj.Name in consumed or not (
            obj.isDerivedFrom("Part::Feature") or obj.TypeId == "App::Link"
        ):
            continue
        shape = obj.Shape
        if shape.isNull() or not shape.Solids:
            non_solids.append({"name": obj.Name, "label": obj.Label})
            continue
        if not shape.isValid() or number(shape.Volume, f"{obj.Name}.volume_mm3") <= 0:
            raise ValueError(f"{obj.Name}: invalid solid")
        groups = list(parent_groups(obj))
        shape = shape.copy()
        if obj.TypeId == "App::Link":
            # A link's Shape already includes its own placement.
            parent = next((group for group in groups if group.isDerivedFrom("App::Part")), None)
            if parent is not None:
                shape.Placement = parent.getGlobalPlacement().multiply(shape.Placement)
        else:
            # Shape includes object placement. Apply its enclosing part's transform.
            parent_placement = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
            shape.Placement = parent_placement.multiply(shape.Placement)
        group_names = frozenset(key for group in groups for key in (group.Name, group.Label))
        roles, material, density_kg_m3, note = body_metadata(obj, role_map)
        pair = getattr(obj, "RevPair", None)
        if hasattr(pair, "Name"):
            pair = pair.Name
        if pair is not None and not isinstance(pair, str):
            raise ValueError(f"{obj.Name}: RevPair must be a string or a link")
        bodies.append(Body(
            obj.Name, obj.Label, shape, roles, group_names, material, density_kg_m3, note,
            (pair.strip() or None) if pair else None, getattr(obj, "RevStrokeAxis", None),
        ))
    machine_names = {body.name for body in bodies if "machine" in body.roles}
    unknown_dependencies = [
        {"object": obj.Name, "type": obj.TypeId, "links": sorted(links)}
        for obj in doc.Objects
        if (links := unclassified.get(obj.Name, set()) & machine_names)
    ]
    return bodies, non_solids, unknown_dependencies


def placed_shapes(app, bodies, configured_poses):
    known_groups = set().union(*(body.roles | body.groups for body in bodies))
    poses = {"nominal": {}, **configured_poses}
    placed = {}
    for pose, raw_offsets in poses.items():
        if not isinstance(pose, str) or not pose:
            raise ValueError("Pose names must be nonempty strings")
        offsets = {}
        for group, offset in mapping(raw_offsets, f"poses[{pose!r}]").items():
            if group not in known_groups:
                raise ValueError(f"{pose}: no bodies in group {group!r}")
            offsets[group] = triplet(offset, f"{pose}.{group}")
        shapes = {}
        for body in bodies:
            shifts = {offsets[key] for key in body.roles | body.groups if key in offsets}
            if len(shifts) > 1:
                raise ValueError(f"{pose}: conflicting translations for {body.name}")
            shift_mm = next(iter(shifts), (0, 0, 0))
            shape = body.shape
            if any(shift_mm):
                shape = shape.copy()
                shape.translate(app.Vector(*shift_mm))
            shapes[body.name] = shape
        placed[pose] = shapes
    return placed


def envelope(app, machine, poses, max_mm):
    total_box = app.BoundBox()
    per_pose = {}
    for pose, shapes in poses.items():
        box = app.BoundBox()
        for body in machine:
            box.add(shapes[body.name].BoundBox)
        per_pose[pose] = [box.XLength, box.YLength, box.ZLength]
        total_box.add(box)
    size_mm = [total_box.XLength, total_box.YLength, total_box.ZLength]
    status = "FAIL" if any(size > limit for size, limit in zip(size_mm, max_mm)) else "PASS"
    return status, size_mm, {"per_pose_mm": per_pose, "body_count": len(machine)}


def mass(machine, limits):
    parts = []
    for body in machine:
        volume_mm3 = body.shape.Volume
        parts.append({
            "name": body.name, "label": body.label, "roles": sorted(body.roles),
            "material": body.material, "density_kg_m3": body.density_kg_m3,
            "volume_mm3": volume_mm3, "mass_kg": body.density_kg_m3 * (volume_mm3 * 1e-9),
        })
    total_kg = math.fsum(part["mass_kg"] for part in parts)
    moving_kg = math.fsum(part["mass_kg"] for part in parts if "moving" in part["roles"])
    status = "PASS"
    if total_kg > limits["max_kg"]:
        status = "FAIL"
    elif total_kg > limits["target_kg"]:
        status = "WARN"
    return status, total_kg, {"moving_mass_kg": moving_kg, "bodies": parts}


def overlapping_pairs(pose, shapes, pairs, limit_mm3):
    boxes = {name: shape.BoundBox for name, shape in shapes.items()}
    overlaps = []
    for first, second in pairs:
        a, b = first.name, second.name
        if not boxes[a].intersect(boxes[b]):
            continue
        try:
            volume_mm3 = number(shapes[a].common(shapes[b]).Volume, "common_volume_mm3")
        except Exception as error:
            raise RuntimeError(f"{pose}: {a} / {b}: {error}") from error
        if volume_mm3 > limit_mm3:
            overlaps.append({"pose": pose, "bodies": [a, b], "common_volume_mm3": volume_mm3})
    return overlaps


def collision(machine, poses, limit_mm3):
    overlaps = []
    for pose, shapes in poses.items():
        overlaps.extend(overlapping_pairs(pose, shapes, combinations(machine, 2), limit_mm3))
    volume_mm3 = max((pair["common_volume_mm3"] for pair in overlaps), default=0)
    return ("FAIL" if overlaps else "PASS"), volume_mm3, {"poses": list(poses), "pairs": overlaps}


def common_volume(first, second):
    if not first.BoundBox.intersect(second.BoundBox):
        return 0
    return number(first.common(second).Volume, "common_volume_mm3")


def distance(first, second):
    return number(first.distToShape(second)[0], "distance_mm")


def contact_area(part, path, body, tolerance_mm):
    # Sum the union of contact patches on each body face. Two path faces
    # projected onto the same patch contribute its area only once.
    path_faces = [(face, face.BoundBox, isinstance(face.Surface, part.Plane))
                  for face in path.Faces]
    areas_mm2 = []
    for face in body.Faces:
        box = face.BoundBox
        box.enlarge(tolerance_mm)
        planar = isinstance(face.Surface, part.Plane)
        if planar:
            normal = face.normalAt(0, 0)
        patches = []
        for path_face, path_box, path_planar in path_faces:
            if not box.intersect(path_box):
                continue
            aligned = path_face
            if planar and path_planar:
                if not math.isclose(abs(normal.dot(path_face.normalAt(0, 0))), 1,
                                    rel_tol=0, abs_tol=1e-12):
                    continue
                offset_mm = normal.dot(path_face.CenterOfMass - face.CenterOfMass)
                if abs(offset_mm) > tolerance_mm:
                    continue
                if offset_mm:
                    aligned = path_face.copy()
                    aligned.translate(normal * -offset_mm)
            patch = face.common(aligned)
            if patch.Area > 0:
                patches.append(patch)
        if patches:
            union = patches[0].fuse(patches[1:]) if len(patches) > 1 else patches[0]
            areas_mm2.append(number(union.Area, "contact_area_mm2"))
    area_mm2 = math.fsum(areas_mm2)
    return area_mm2 if area_mm2 >= CONTACT_AREA_TOL_MM2 else 0


def feed_path_is_connected(path, tolerance_mm):
    solids = path.Solids
    unreached = set(range(1, len(solids)))
    queue = [0]
    while queue and unreached:
        current = queue.pop()
        reached = {index for index in unreached if distance(solids[current], solids[index]) <= tolerance_mm}
        unreached.difference_update(reached)
        queue.extend(reached)
    return not unreached


def feed(part, bodies, machine, nominal, threshold):
    paths = [body for body in bodies if "feed_path" in body.roles]
    if not paths:
        notes = {body.name: body.feed_absence_note for body in machine
                 if "chamber_liner" in body.roles and body.feed_absence_note}
        reason = "; ".join(["нет тела feed_path", *dict.fromkeys(notes.values())])
        details = {"reason": reason}
        if notes:
            details["liner_notes_from_roles"] = notes
        return "FAIL", None, details
    overlaps = overlapping_pairs(
        "nominal", nominal, product(paths, machine), threshold["max_common_volume_mm3"]
    )
    details = {"pose": "nominal", "paths": [body.name for body in paths], "pairs": overlaps}
    connections = {}
    tolerance_mm = threshold["max_contact_distance_mm"]
    for body in paths:
        path = nominal[body.name]
        connection = {"connected": feed_path_is_connected(path, tolerance_mm)}
        for role in ("chamber_liner", "hopper"):
            candidates = []
            for other in machine:
                if role not in other.roles:
                    continue
                shape = nominal[other.name]
                gap_mm = distance(path, shape)
                area_mm2 = contact_area(part, path, shape, tolerance_mm) if gap_mm <= tolerance_mm else 0
                candidate = {"body": other.name, "distance_mm": gap_mm,
                             "touches": area_mm2 > 0, "contact_area_mm2": area_mm2}
                candidates.append(candidate)
            connection[role] = candidates
        connection["window_area_mm2"] = math.fsum(
            item["contact_area_mm2"] for item in connection["chamber_liner"]
        )
        missing = [
            role for role in ("chamber_liner", "hopper")
            if (role == "chamber_liner" or connection[role])
            and not any(item["touches"] for item in connection[role])
        ]
        if missing:
            connection["missing_contact"] = missing
        connections[body.name] = connection
    details["connections"] = connections
    window_area_mm2 = min(item["window_area_mm2"] for item in connections.values())
    minimum_mm2 = threshold["min_window_area_mm2"]
    reasons = []
    if overlaps:
        reasons.append("объёмное пересечение пути подачи с физическим телом")
    if any("missing_contact" in item for item in connections.values()):
        reasons.append("путь подачи не связан с вкладышем или бункером")
    if any(not item["connected"] for item in connections.values()):
        reasons.append("путь подачи состоит из несвязанных объёмов")
    if minimum_mm2 is not None and window_area_mm2 < minimum_mm2:
        reasons.append("площадь окна меньше порога")
    if reasons:
        details["reasons"] = reasons
        return "FAIL", window_area_mm2, details
    if minimum_mm2 is None:
        details["reason"] = "порог окна не задан"
        return "WARN", window_area_mm2, details
    return "PASS", window_area_mm2, details


def matching_liner(punch, liners, nominal):
    if punch.pair:
        matches = [liner for liner in liners if punch.pair == liner.name]
        if not matches:
            matches = [liner for liner in liners if punch.pair in (liner.label, liner.pair)]
    else:
        matches = [liner for liner in liners if liner.pair in (punch.name, punch.label)]
        if not matches and liners:
            return min(liners, key=lambda liner: distance(nominal[punch.name], nominal[liner.name])), None
    if len(matches) == 1:
        return matches[0], None
    return None, ("RevPair соответствует нескольким вкладышам" if matches
                  else "вкладыш для пуансона не найден")


def infer_stroke_axis(app, part, punch, liner, shape):
    axis = punch.stroke_axis if punch.stroke_axis is not None else liner.stroke_axis
    if axis is not None:
        if isinstance(axis, str) and axis.upper() in ("X", "Y", "Z"):
            axis = app.Vector(*(int(component == axis.upper()) for component in "XYZ"))
        if not isinstance(axis, app.Vector) or not math.isfinite(axis.Length) or axis.Length == 0:
            raise ValueError(f"{punch.name} / {liner.name}: invalid RevStrokeAxis")
        return axis / axis.Length

    # The largest opening on a planar liner face identifies the bore, including
    # short liners and liners mounted in a rotated assembly.
    openings = [
        (part.Face(wire).Area, face.normalAt(0, 0))
        for face in shape.Faces if isinstance(face.Surface, part.Plane)
        for wire in face.Wires if not wire.isSame(face.OuterWire)
    ]
    if openings:
        return max(openings, key=lambda opening: opening[0])[1]
    box = shape.BoundBox
    axis_index = max(range(3), key=(box.XLength, box.YLength, box.ZLength).__getitem__)
    return app.Vector(*(int(index == axis_index) for index in range(3)))


def axial_interval(app, shape, axis):
    aligned = shape.copy()
    rotation = app.Placement(app.Vector(), app.Rotation(axis, app.Vector(1, 0, 0)))
    aligned.Placement = rotation.multiply(aligned.Placement)
    box = aligned.BoundBox
    return box.XMin, box.XMax


def wall_sample_parameters(part, edge):
    start, end = edge.FirstParameter, edge.LastParameter
    if isinstance(edge.Curve, (part.Circle, part.Ellipse)):
        count = max(WALL_SAMPLES_MIN, math.ceil(math.degrees(end - start) / ARC_STEP_DEG))
        # Use the centre of each angular interval, including on periodic edges.
        return [start + (end - start) * (i + 0.5) / count for i in range(count)]
    return [start + (end - start) * i / (WALL_SAMPLES_MIN + 1)
            for i in range(1, WALL_SAMPLES_MIN + 1)]


def ray_clearance(part, bore, punch_profile, axis, edge, parameter, point, reach_mm):
    # OCCT may omit an intersection at the origin of a ray when the
    # profiles touch. Test the wall point itself before tracing the ray.
    if distance(part.Vertex(point), punch_profile) <= GEOMETRY_TOL_MM:
        return 0
    normal = axis.cross(edge.tangentAt(parameter))
    normal.normalize()
    line = part.makeLine(point - normal * reach_mm, point + normal * reach_mm)
    # Find the interval of the normal inside the opening and incident to this
    # wall point. In concave bores an outward ray could otherwise hit a remote lobe.
    inner_end = next((
        opposite.Point
        for segment in bore.common(line).Edges
        for wall_end, opposite in (segment.Vertexes, list(reversed(segment.Vertexes)))
        if (wall_end.Point - point).Length <= GEOMETRY_TOL_MM
    ), None)
    if inner_end is None:
        return None
    inward = inner_end - point
    inward.normalize()
    ray = part.makeLine(point, inner_end)
    intersections = punch_profile.section(ray)
    hits_mm = [(vertex.Point - point).dot(inward) for vertex in intersections.Vertexes]
    nearest_mm = min((hit for hit in hits_mm if hit >= -GEOMETRY_TOL_MM), default=None)
    if nearest_mm is None:
        return None
    return 0 if nearest_mm <= GEOMETRY_TOL_MM else nearest_mm


def side_gap(part, punch_shape, liner_shape, axis, section_mm):
    punch_wires = punch_shape.slice(axis, section_mm)
    liner_wires = liner_shape.slice(axis, section_mm)
    section = {"section_mm": section_mm, "wall_edges": []}
    if not punch_wires or not liner_wires:
        return dict(section, reason="профиль пуансона или вкладыша отсутствует в сечении")
    punch_profile = part.makeCompound(punch_wires)
    faces = [(wire, part.Face(wire)) for wire in liner_wires if wire.isClosed()]
    bore_wires = [
        (wire, face) for wire, face in faces
        if any(outer.Area > face.Area and outer.isInside(wire.Vertexes[0].Point, GEOMETRY_TOL_MM, False)
               for _, outer in faces)
    ]
    if not bore_wires:
        return dict(section, reason="замкнутый контур отверстия не найден в сечении")
    profiles = [part.Face(wire) for wire in punch_wires if wire.isClosed()]
    # Measure the inner contours that contain the entire punch section.
    bores = [(wire, bore) for wire, bore in bore_wires
             if profiles and all(face.cut(bore).Area <= GEOMETRY_TOL_MM ** 2 for face in profiles)]
    if not bores:
        return dict(section, reason="пуансон не в камере в номинальной позе")
    walls = section["wall_edges"]
    for wire, bore in bores:
        reach_mm = wire.BoundBox.DiagonalLength
        for edge in wire.Edges:
            ends = [edge.valueAt(edge.FirstParameter), edge.valueAt(edge.LastParameter)]
            hits = []
            missed_point_mm = None
            count = 0
            for parameter in wall_sample_parameters(part, edge):
                point = edge.valueAt(parameter)
                if any((point - end).Length <= GEOMETRY_TOL_MM for end in ends):
                    continue
                count += 1
                point_mm = [point.x, point.y, point.z]
                gap_mm = ray_clearance(part, bore, punch_profile, axis, edge, parameter, point, reach_mm)
                if gap_mm is None:
                    if missed_point_mm is None:
                        missed_point_mm = point_mm
                else:
                    hits.append((gap_mm, point_mm))
            largest_mm, max_point_mm = max(hits, key=lambda hit: hit[0], default=(None, None))
            wall = {"sample_count": count, "clearance_mm": largest_mm, "max_point_mm": max_point_mm,
                    "min_side_mm": min((hit[0] for hit in hits), default=None)}
            if missed_point_mm is not None:
                wall["missed_point_mm"] = missed_point_mm
            if count < WALL_SAMPLES_MIN:
                wall["insufficient_samples"] = True
            walls.append(wall)
    return section


def measure_clearance(app, part, punch, liner, nominal, max_mm):
    punch_shape, liner_shape = nominal[punch.name], nominal[liner.name]
    axis = infer_stroke_axis(app, part, punch, liner, liner_shape)
    punch_min_mm, punch_max_mm = axial_interval(app, punch_shape, axis)
    liner_min_mm, liner_max_mm = axial_interval(app, liner_shape, axis)
    start_mm, end_mm = max(punch_min_mm, liner_min_mm), min(punch_max_mm, liner_max_mm)
    overlap_mm = end_mm - start_mm
    volume_mm3 = common_volume(punch_shape, liner_shape)
    result = {
        "bodies": [punch.name, liner.name], "stroke_axis": [axis.x, axis.y, axis.z],
        "axial_overlap_mm": max(overlap_mm, 0), "common_volume_mm3": volume_mm3,
        "clearance_mm": None, "status": "FAIL",
    }
    if volume_mm3 > 0:
        result.update(clearance_mm=0, reason="пуансон пересекает материал вкладыша", related_gate="G-COLL")
    elif overlap_mm <= GEOMETRY_TOL_MM:
        result["reason"] = "пуансон не в камере в номинальной позе"
    else:
        # Stay inside the intersecting axial intervals so coplanar end faces
        # do not enter the sections. The middle plane also covers full insertion.
        inset_mm = min(0.01, overlap_mm / 4)
        positions_mm = (start_mm + inset_mm, (start_mm + end_mm) / 2, end_mm - inset_mm)
        sections = [side_gap(part, punch_shape, liner_shape, axis, section_mm)
                    for section_mm in positions_mm]
        walls = [(section["section_mm"], wall) for section in sections for wall in section["wall_edges"]]
        result.update(sections=sections, section_count=len(sections),
                      sample_count=sum(wall["sample_count"] for _, wall in walls))
        measured = [(section_mm, wall) for section_mm, wall in walls if wall["clearance_mm"] is not None]
        result["min_side_mm"] = min((wall["min_side_mm"] for _, wall in measured), default=None)
        missed = next(((section_mm, wall["missed_point_mm"]) for section_mm, wall in walls
                       if "missed_point_mm" in wall), None)
        section_error = next((section["reason"] for section in sections if "reason" in section), None)
        if missed is not None:
            result.update(missed_ray={"section_mm": missed[0], "point_mm": missed[1]},
                          reason="нормаль к стенке не пересекает профиль пуансона")
        elif section_error is not None:
            result["reason"] = section_error
        elif any("insufficient_samples" in wall for _, wall in walls):
            result["reason"] = "недостаточно точек для измерения зазора на ребре отверстия"
        else:
            section_mm, worst = max(measured, key=lambda item: item[1]["clearance_mm"])
            gap_mm = worst["clearance_mm"]
            result.update(section_mm=section_mm, clearance_mm=gap_mm, max_point_mm=worst["max_point_mm"])
            if gap_mm <= max_mm:
                result["status"] = "PASS"
            else:
                result["reason"] = "боковой зазор больше допустимого"
    return result


def clearance(app, part, machine, nominal, max_mm):
    punches = [body for body in machine if "punch" in body.roles]
    liners = [body for body in machine if "chamber_liner" in body.roles]
    details = {"pose": "nominal", "punches": [body.name for body in punches],
               "chamber_liners": [body.name for body in liners], "pairs": []}
    if not punches or not liners:
        details["reason"] = "нет обязательной роли punch или chamber_liner"
        return "FAIL", None, details
    pairs = details["pairs"]
    for punch in punches:
        liner, reason = matching_liner(punch, [body for body in liners if body.name != punch.name], nominal)
        if liner is None:
            pairs.append({"bodies": [punch.name, None], "status": "FAIL",
                          "clearance_mm": None, "reason": reason, "rev_pair": punch.pair})
        else:
            pairs.append(measure_clearance(app, part, punch, liner, nominal, max_mm))
    measured = [pair for pair in pairs if pair["clearance_mm"] is not None]
    worst = max(measured, key=lambda pair: pair["clearance_mm"], default=None)
    if worst is not None:
        details["bodies"] = worst["bodies"]
    failures = [pair for pair in pairs if pair["status"] == "FAIL"]
    if failures:
        if len(failures) == 1:
            details["reason"] = failures[0]["reason"]
        if any("related_gate" in pair for pair in failures):
            details["related_gate"] = "G-COLL"
    return ("FAIL" if failures else "PASS"), worst["clearance_mm"] if worst else None, details


def gate_template(gate_id, criteria):
    criterion_id, unit = GATE_SPECS[gate_id]
    criterion = mapping(criteria[criterion_id], criterion_id)
    if gate_id == "G-ENV":
        threshold = triplet(criterion["max_mm"], criterion_id)
    elif gate_id == "G-MASS":
        threshold = {key: number(criterion[key], key) for key in ("target_kg", "max_kg")}
        if not 0 < threshold["target_kg"] <= threshold["max_kg"]:
            raise ValueError(f"{criterion_id}: invalid mass thresholds")
    elif gate_id == "G-COLL":
        threshold = number(criterion["max_common_volume_mm3"], criterion_id)
    elif gate_id == "G-FEED":
        rule = criterion["rule"]
        if not isinstance(rule, str) or not rule.strip():
            raise ValueError(f"{criterion_id}: expected a feed-path rule")
        minimum = criterion.get("min_window_area_mm2")
        if minimum is not None and number(minimum, criterion_id) <= 0:
            raise ValueError(f"{criterion_id}: min_window_area_mm2 must be positive")
        threshold = {
            "max_common_volume_mm3": 0, "max_contact_distance_mm": CONTACT_TOL_MM,
            "min_window_area_mm2": minimum, "rule": rule,
        }
    else:
        threshold = number(criterion["max_mm"], criterion_id)
    return {
        "id": gate_id, "status": "ERROR", "value": None, "threshold": threshold,
        "unit": unit, "criteria_ids": [criterion_id], "details": {},
    }


def run_gates(app, part, model, role_map, configured_poses, gates):
    doc = app.openDocument(str(model.resolve()))
    try:
        bodies, non_solids, unknown_dependencies = read_bodies(doc, role_map)
        machine = [body for body in bodies if "machine" in body.roles]
        poses = placed_shapes(app, bodies, configured_poses)
        nominal = poses["nominal"]
        checks = {
            "G-ENV": lambda limit: envelope(app, machine, poses, limit),
            "G-MASS": lambda limit: mass(machine, limit),
            "G-COLL": lambda limit: collision(machine, poses, limit),
            "G-FEED": lambda limit: feed(part, bodies, machine, nominal, limit),
            "G-CLEAR": lambda limit: clearance(app, part, machine, nominal, limit),
        }
        for gate in gates:
            gate_id = gate["id"]
            try:
                if not machine and gate_id in {"G-ENV", "G-MASS", "G-COLL"}:
                    if not non_solids:
                        raise ValueError("No machine solids in the model")
                    status, value, details = "WARN", None, {"reason": "нет физических тел с Solids"}
                else:
                    status, value, details = checks[gate_id](gate["threshold"])
                gate.update(status=status, value=value, details=details)
            except Exception as error:
                gate["details"] = {"reason": str(error)}
            if non_solids:
                gate["details"]["bodies_without_solids"] = non_solids
                if gate["status"] == "PASS":
                    gate["status"] = "WARN"
            if gate_id in {"G-MASS", "G-COLL"}:
                gate["details"]["unknown_dependencies"] = unknown_dependencies
                if unknown_dependencies and gate["status"] == "PASS":
                    gate["status"] = "WARN"
    finally:
        app.closeDocument(doc.Name)


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    output = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    )
    temporary = Path(output.name)
    try:
        with output:
            json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write("\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_args(args):
    args = mapping(args, "REV_GATE_ARGS")
    for key in ("model", "roles", "criteria", "out", "poses"):
        if key == "poses" and key not in args:
            continue
        if key == "roles" and key in args and args[key] is None:
            continue
        if key == "poses" and args[key] is None:
            continue
        value = args.get(key)
        if not isinstance(value, str) or not value.strip() or "\0" in value:
            raise ValueError(f"REV_GATE_ARGS.{key}: expected a path")
    ids = args.get("gates", list(GATE_SPECS))
    if not isinstance(ids, list) or not ids or any(
        not isinstance(gate, str) or gate not in GATE_SPECS for gate in ids
    ) or len(ids) != len(set(ids)):
        raise ValueError("REV_GATE_ARGS.gates: expected a nonempty list of distinct geometry gate IDs")
    return args, ids


def output_path(args):
    if not isinstance(args, dict):
        return None
    value = args.get("out")
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        return None
    output = Path(value)
    for key in ("model", "roles", "criteria", "poses"):
        source = args.get(key)
        if isinstance(source, str) and "\0" not in source and output.resolve() == Path(source).resolve():
            raise ValueError("The report path must differ from the input paths")
    return output


def overall_result(gates):
    statuses = {gate["status"] for gate in gates}
    if "ERROR" in statuses:
        return "FAIL", 2
    if "FAIL" in statuses:
        return "FAIL", 1
    if statuses & {"WARN", "NOT_AVAILABLE"}:
        return "WARN", 0
    return "PASS", 0


def main():
    output = None
    report = {
        "schema": "rev.gate_report/1", "tool": "geom_gates", "tool_version": TOOL_VERSION,
        "input": None, "criteria_version": None, "criteria_sha256": None, "overall": "ERROR",
        "gates": [], "freecad_version": None,
    }
    try:
        import FreeCAD as app
        import Part  # Registers Part shapes in the embedded interpreter.

        report["freecad_version"] = ".".join(app.Version()[:3])
        raw_args = os.environ.get("REV_GATE_ARGS")
        if raw_args is None:
            raise ValueError("REV_GATE_ARGS is missing")
        args = json.loads(raw_args)
        output = output_path(args)
        if isinstance(args, dict) and isinstance(args.get("model"), str):
            report["input"] = args["model"]
        args, ids = read_args(args)
        paths = {key: Path(args[key]) for key in ("model", "criteria", "roles", "poses")
                 if args.get(key) is not None}
        criteria_data = paths["criteria"].read_bytes()
        report["criteria_sha256"] = hashlib.sha256(criteria_data).hexdigest()
        criteria_file = read_yaml(criteria_data, "criteria file")
        version = criteria_file["version"]
        if type(version) is not int:
            raise ValueError("criteria.version: expected an integer")
        report["criteria_version"] = version
        criteria = mapping(criteria_file["criteria"], "criteria")
        gates = [gate_template(gate_id, criteria) for gate_id in ids]
        report["gates"] = gates
        try:
            model = paths["model"]
            if model.suffix.lower() != ".fcstd" or not model.is_file():
                raise ValueError(f"Expected an existing .FCStd file: {model}")
            roles = read_yaml(paths["roles"].read_bytes(), "roles file") if "roles" in paths else {}
            poses = read_yaml(paths["poses"].read_bytes(), "poses file") if "poses" in paths else {}
            run_gates(app, Part, model, roles, poses, gates)
        except Exception as error:
            for gate in gates:
                gate.update(status="ERROR", value=None, details={"reason": str(error)})
        report["overall"], exit_code = overall_result(gates)
    except Exception as error:
        exit_code = 2
        report["error"] = str(error)
    if output is not None:
        try:
            write_report(output, report)
        except Exception as error:
            print(f"geom_gates: {error}", file=sys.stderr)
            return 2
    else:
        print(f"geom_gates: {report['error']}", file=sys.stderr)
        return 2
    return exit_code


if __name__ == "__main__" or any(
    Path(arg).name == "geom_gates.py" and Path(arg).resolve() == Path(__file__).resolve()
    for arg in sys.argv[1:]
):
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    # FreeCAD imports positional .py files and can catch SystemExit.
    os._exit(code)
