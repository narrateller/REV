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


TOOL_VERSION = "1.1.0"
DEFAULT_FREECADCMD = "E:/Tools/FreeCAD-1.1/bin/freecadcmd.exe"
DEFAULT_DENSITY_KG_M3 = 7850
CONTACT_TOL_MM = 0.01
GEOMETRY_TOL_MM = 1e-7
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


def consumed_objects(objects):
    """Find components whose geometry is already represented by a result."""
    consumed = set()
    for obj in objects:
        if obj.isDerivedFrom("PartDesign::Body"):
            consumed.update(child.Name for child in obj.Group)
        elif obj.TypeId == "App::Link":
            source = obj.LinkedObject
            if source and source.Document == obj.Document and not source.Visibility:
                consumed.add(source.Name)
                if is_group(source):
                    consumed.update(
                        child.Name for child in objects if source in parent_groups(child)
                    )
        elif obj.isDerivedFrom("Part::Feature") and not obj.Shape.isNull():
            # OutList includes inputs to booleans, transforms and generated solids.
            # Attachment and pairing links are references to independent geometry.
            references = set()
            for key in ("Support", "AttachmentSupport", "PlacementRelTo", "RevPair"):
                value = getattr(obj, key, None)
                if isinstance(value, (list, tuple)):
                    value = value[0] if value else None
                if hasattr(value, "Name"):
                    references.add(value.Name)
            consumed.update(child.Name for child in obj.OutList
                            if hasattr(child, "Shape") and child.Name not in references)
    return consumed


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
    consumed = consumed_objects(doc.Objects)
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
    return bodies, non_solids


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


def contact_area(path, liner):
    # A solid-solid common omits coincident faces when the common volume is zero.
    box = path.BoundBox
    return math.fsum(
        number(face.common(path).Area, "contact_area_mm2")
        for face in liner.Faces if box.intersect(face.BoundBox)
    )


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


def feed(bodies, machine, nominal, threshold):
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
                candidate = {"body": other.name, "distance_mm": gap_mm,
                             "touches": gap_mm <= tolerance_mm}
                if role == "chamber_liner":
                    candidate["contact_area_mm2"] = contact_area(path, shape)
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


def side_gap(part, punch_shape, liner_shape, axis, section_mm):
    punch_wires = punch_shape.slice(axis, section_mm)
    liner_wires = liner_shape.slice(axis, section_mm)
    if not punch_wires or not liner_wires:
        return None
    punch_profile = part.makeCompound(punch_wires)
    faces = [(wire, part.Face(wire)) for wire in liner_wires if wire.isClosed()]
    bore_wires = [
        (wire, face) for wire, face in faces
        if any(outer.Area > face.Area and outer.isInside(wire.Vertexes[0].Point, GEOMETRY_TOL_MM, False)
               for _, outer in faces)
    ]
    if bore_wires:
        # Keep only bores containing the entire section of the punch.
        profiles = [part.Face(wire) for wire in punch_wires if wire.isClosed()]
        liner_wires = [
            wire for wire, bore in bore_wires
            if profiles and all(face.cut(bore).Area <= GEOMETRY_TOL_MM ** 2 for face in profiles)
        ]
        if not liner_wires:
            return None
    gap_mm = distance(punch_profile, part.makeCompound(liner_wires))
    return 0 if gap_mm <= GEOMETRY_TOL_MM else gap_mm


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
        # Sample just inside the entry side, or at mid-depth if fully inserted.
        before_mm = liner_min_mm - punch_min_mm
        after_mm = punch_max_mm - liner_max_mm
        if max(before_mm, after_mm) <= GEOMETRY_TOL_MM:
            section_mm = (start_mm + end_mm) / 2
        else:
            inset_mm = min(0.01, overlap_mm / 2)
            section_mm = start_mm + inset_mm if before_mm >= after_mm else end_mm - inset_mm
        gap_mm = side_gap(part, punch_shape, liner_shape, axis, section_mm)
        result.update(section_mm=section_mm, clearance_mm=gap_mm)
        if gap_mm is None:
            result["reason"] = "пуансон не в камере в номинальной позе"
        elif gap_mm <= max_mm:
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
        bodies, non_solids = read_bodies(doc, role_map)
        machine = [body for body in bodies if "machine" in body.roles]
        poses = placed_shapes(app, bodies, configured_poses)
        nominal = poses["nominal"]
        checks = {
            "G-ENV": lambda limit: envelope(app, machine, poses, limit),
            "G-MASS": lambda limit: mass(machine, limit),
            "G-COLL": lambda limit: collision(machine, poses, limit),
            "G-FEED": lambda limit: feed(bodies, machine, nominal, limit),
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
