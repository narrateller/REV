"""Export W02 iteration 04 nominal geometry at 1:1 using FreeCAD's bundled Python."""
import argparse
from collections import defaultdict
from hashlib import sha256
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from xml.etree import ElementTree

import ezdxf

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import FreeCAD as App
import Part
import TechDraw
from PySide import QtCore, QtGui, QtSvg, QtWidgets
from pypdf import PdfReader, PdfWriter
from pypdf.generic import FloatObject, NameObject, RectangleObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from redesign_1p5mn.prepare import add_view, dimension

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cad/source/force_geometry/redesign_1p5mn_04"
CATALOG = ROOT / "drives/cots_catalog.yaml"
VERDICT = ROOT / "cae/cases/T-R3-FORCE-CALC-05/engineering_verdict.json"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
AUDITED_INPUTS = (
    CATALOG, VERDICT, SOURCE/"manifest.json", SOURCE/"screening.json",
    ROOT/"cad/force_geometry/redesign_1p5mn_04/interfaces.json",
    ROOT/"params/r4_w02_iteration_04.json",
    ROOT/"cae/cases/T-R3-FORCE-CALC-05/output_manifest.json",
    ROOT/"coordination/tasks/T-R4-FINAL-DRAWINGS-02/task.json",
)
COTS = {
    "W02-105": "linear_guides",
    "W02-201": "hydraulic_cylinder",
    "W02-302": "guide_pads",
    "W02-303": "punch_plate",
    "W02-401": "chamber_liner",
}
B_NAMES = {
    "W02-501": "Упор камеры прессования B",
    "W02-502": "Седло упора камеры прессования B",
    "W02-503": "Направляющая упора камеры прессования B",
    "W02-504": "Ключ механизма фиксации упора B",
    "W02-505": "Опора ключа механизма фиксации упора B",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def size(objects):
    box = App.BoundBox()
    for obj in objects:
        box.add(obj.Shape.BoundBox)
    return box.XLength, box.YLength, box.ZLength


def geometry_key(obj):
    """Group translated copies with the same oriented geometry and component role."""
    shape = obj.Shape.copy()
    shape.translate(-shape.BoundBox.Center)
    return (obj.BOMItem, obj.Name.rstrip("0123456789").split("_")[0],
            tuple(round(v, 6) for v in size([obj])),
            round(shape.Volume, 4),
            tuple(sorted(tuple(round(k, 5) for k in v.Point) for v in shape.Vertexes)),
            tuple(sorted((type(e.Curve).__name__, round(e.Length, 6),
                          tuple(round(k, 5) for k in e.CenterOfMass)) for e in shape.Edges)))


def text(x, y, label, height=4):
    return f'<text x="{x:g}" y="{y:g}" font-size="{height}">{escape(label)}</text>'


def line(x1, y1, x2, y2):
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" stroke="black" stroke-width="0.25"/>'


def svg_dimension(x, y, span, vertical=False):
    half = span / 2
    if vertical:
        return (line(x, y-half, x, y+half) + line(x-9, y-half, x+3, y-half)
                + line(x-9, y+half, x+3, y+half)
                + line(x-1, y-half+3, x, y-half) + line(x+1, y-half+3, x, y-half)
                + line(x-1, y+half-3, x, y+half) + line(x+1, y+half-3, x, y+half)
                + text(x+3, y, f"{span:g}"))
    return (line(x-half, y, x+half, y) + line(x-half, y-10, x-half, y+3)
            + line(x+half, y-10, x+half, y+3)
            + line(x-half+3, y-1, x-half, y) + line(x-half+3, y+1, x-half, y)
            + line(x+half-3, y-1, x+half, y) + line(x+half-3, y+1, x+half, y)
            + text(x-5, y-3, f"{span:g}"))


def identify_svg(content, sheet_name):
    """Assign sheet-wide IDs after assembling the independent TechDraw views."""
    root = ElementTree.fromstring(content)
    for index, element in enumerate(root.iter(), 1):
        tag = element.tag.rsplit("}", 1)[-1]
        if element.get("id") == "section-AA":
            tag = "section-AA"
        element.set("id", f"{sheet_name}_{tag}_{index:04d}")
    ElementTree.register_namespace("", SVG_NAMESPACE)
    return root


def sheet(doc, name, objects, bom, output, temporary, svg_only):
    x, y, z = size(objects)
    die = name.endswith("-402-33")
    width = max(x+y+120, 450)
    top = 65 + z/2
    bottom = z+120+y/2
    footer = z+y+155
    if die:
        section_top = footer + 20
        footer += y + 130
    height = footer + 8*len(bom)+38
    views = [
        ("XZ", (0,-1,0), (1,0,0), 38+x/2, top, x,z),
        ("XY", (0,0,1), (1,0,0), 38+x/2, bottom, x,y),
        ("YZ", (1,0,0), (0,1,0), x+80+y/2, top, y,z),
    ]
    header = [text(15, 16, name + "  |  W02  |  REV 04  |  1:1  |  mm", 6),
              text(15, 26, "Номинальная геометрия. Монтажные допуски и посадки требуют утверждения."),
              text(15, 36, "Для проверки R5. FreeCAD TechDraw / OCCT")]
    if die:
        header.append(text(15, 46, "Габарит X на XZ и XY включает допуск геометрического ядра."))
    tail = [line(15, footer-10, width-15, footer-10),
            text(15, footer, "Спецификация"),
            line(15, footer+2, width-15, footer+2),
            line(15, footer-10, 15, footer+8*len(bom)+2),
            line(width-15, footer-10, width-15, footer+8*len(bom)+2)]
    for row, record in enumerate(bom, 1):
        tail.extend((text(18, footer+8*row, record),
                     line(15, footer+8*row+2, width-15, footer+8*row+2)))
    tail.append(text(15, height-12, "REV / R4    |    Итерация 04    |    1:1 мм    |    1 / 1"))

    def frame(content):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}mm" height="{height:g}mm" '
                f'viewBox="0 0 {width:g} {height:g}" font-family="Arial, sans-serif">'
                f'<rect x="5" y="5" width="{width-10:g}" height="{height-10:g}" fill="white" '
                'stroke="black" stroke-width="0.35"/>' + "".join(content) + '</svg>')

    template_file = temporary / f"{name}.svg"
    template_file.write_text(frame(header+tail), encoding="utf-8")
    page = doc.addObject("TechDraw::DrawPage", "IssuePage")
    page.Label = name
    template = doc.addObject("TechDraw::DrawSVGTemplate", "IssueTemplate")
    template.Template = str(template_file)
    page.Template = template
    page.Scale = 1
    drawn = []
    for label, direction, right, cx, cy, w, h in views:
        view = add_view(doc, page, "Projection"+label, objects, direction, right, (cx, height-cy))
        view.Scale = 1
        drawn.append((view, label, cx, cy, w, h))
    section = None
    if die:
        shape = objects[0].Shape
        center = shape.BoundBox.Center
        section_x = 38+x/2
        section_y = section_top+y/2
        section = doc.addObject("TechDraw::DrawViewSection", "DieSection")
        section.BaseView = drawn[0][0]
        section.Source = objects
        section.SectionDirection = "Aligned"
        section.SectionNormal = App.Vector(0, 0, 1)
        section.SectionOrigin = center
        section.Direction = App.Vector(0, 0, 1)
        section.XDirection = App.Vector(1, 0, 0)
        section.SectionSymbol = "A"
        page.addView(section)
        section.ScaleType = "Custom"
        section.Scale = 1
        section.X, section.Y = section_x, height-section_y
    doc.recompute()
    deadline = time.monotonic() + 30
    while not (all(view.getVisibleEdges() for view, *_ in drawn)
               and (section is None or section.getVisibleEdges())):
        if time.monotonic() > deadline:
            raise RuntimeError(f"TechDraw projection timeout: {name}")
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.02)
    svg = header.copy()
    for view, label, cx, cy, w, h in drawn:
        fragment = TechDraw.viewPartAsSvg(view).replace('stroke-width="0.7"', 'stroke-width="0.35"')
        if not any(tag in fragment for tag in ("<path", "<circle", "<ellipse", "<line", "<polyline")):
            raise ValueError(f"Empty projection {name}/{label}")
        svg += [f'<g transform="translate({cx:g},{cy:g})">{fragment}</g>',
                text(cx, cy-h/2-9, label),
                svg_dimension(cx, cy+h/2+12, w),
                svg_dimension(cx+w/2+11, cy, h, vertical=True)]
        for axis, span, xy in (("x", w, (0, -h/2-12)), ("y", h, (w/2+11, 0))):
            try:
                dim_name = f"Extent{label}{axis}_{page.Name}"
                dimension(doc, page, view, dim_name, axis, span, xy)
                doc.getObject(dim_name).FormatSpec = "%.3f"
            except ValueError:
                extent = TechDraw.makeExtentDim(view, [], int(axis == "y"))
                extent.X, extent.Y = xy
                extent.FormatSpec = "%.3f"
    section_lines = []
    if section is not None:
        svg.append(f'<g id="section-AA" transform="translate({section_x:g},{section_y:g})">'
                   f'{TechDraw.viewPartAsSvg(section)}</g>')
        svg.append(text(38, section_top-8, "Разрез A–A (Z по середине фильеры)"))
        vertices = [v.Point for wire in shape.slice(App.Vector(0, 0, 1), center.z)
                    for v in wire.Vertexes]
        for label, edge_x, baseline in (("Вход", min(v.x for v in vertices), section_top+y+25),
                                        ("Выход", max(v.x for v in vertices), section_top+y+50)):
            stops = sorted({round(v.y, 6) for v in vertices if abs(v.x-edge_x) < 1e-6})
            if len(stops) != 4:
                raise ValueError(f"Die chain requires four section vertices at {label}: {name}")
            positions = [38 + stop - stops[0] for stop in stops]
            svg.append(text(38, baseline-9, label + " · размерная цепь по Y"))
            for left, right in zip(positions, positions[1:]):
                svg.append(text((left+right)/2-5, baseline-3, f"{right-left:.3f}"))
                section_lines.append((left, baseline, right, baseline))
            section_lines.extend((pos, baseline-5, pos, baseline+3) for pos in positions)
        svg.extend(line(*segment) for segment in section_lines)
    doc.recompute()
    base = output / name
    svg_file = base.with_suffix(".svg")
    image = identify_svg(frame(svg+tail), name)
    svg_file.write_bytes(ElementTree.tostring(image, encoding="utf-8"))
    page_data = {"page": page.Name, "size_mm": [width, height],
                 "objects": [obj.Name for obj in objects],
                 "extents_mm": [x, y, z], "section": section.Name if section else None}
    if svg_only:
        return page_data
    pdf_file = base.with_suffix(".pdf")
    draft_pdf = temporary / pdf_file.name
    user_unit = 2 if max(width, height)*72/25.4 > 14400 else 1
    pdf_width, pdf_height = width*72/(25.4*user_unit), height*72/(25.4*user_unit)
    writer = QtGui.QPdfWriter(str(draft_pdf))
    writer.setResolution(72)
    layout = QtGui.QPageLayout(QtGui.QPageSize(QtCore.QSizeF(width/user_unit, height/user_unit), QtGui.QPageSize.Millimeter,
                                               name, QtGui.QPageSize.ExactMatch),
                               QtGui.QPageLayout.Portrait, QtCore.QMarginsF(0,0,0,0))
    if not writer.setPageLayout(layout):
        raise ValueError(f"PDF page rejected: {name}")
    writer.setTitle(name)
    labels = image.findall(f"{{{SVG_NAMESPACE}}}text")
    for label in labels:
        image.remove(label)
    renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(ElementTree.tostring(image)))
    painter = QtGui.QPainter(writer)
    if not renderer.isValid() or not painter.isActive():
        raise ValueError(f"Cannot render {name}")
    renderer.render(painter, QtCore.QRectF(0, 0, pdf_width, pdf_height))
    painter.end()
    del painter, writer
    pdf = PdfWriter(clone_from=str(draft_pdf))
    pdf.pdf_header = "%PDF-1.6"
    pdf.pages[0].mediabox = RectangleObject((0, 0, pdf_width, pdf_height))
    overlay = BytesIO()
    canvas = Canvas(overlay, pagesize=(pdf_width, pdf_height))
    points_per_mm = 72 / (25.4 * user_unit)
    for label in labels:
        canvas.setFont("W02", float(label.get("font-size")) * points_per_mm)
        canvas.drawString(float(label.get("x")) * points_per_mm,
                          (height - float(label.get("y"))) * points_per_mm, label.text)
    canvas.showPage()
    canvas.save()
    overlay.seek(0)
    pdf.pages[0].merge_page(PdfReader(overlay).pages[0])
    if user_unit != 1:
        pdf.pages[0][NameObject("/UserUnit")] = FloatObject(user_unit)
    with pdf_file.open("wb") as stream:
        pdf.write(stream)
    dxf_file = base.with_suffix(".dxf")
    TechDraw.writeDXFPage(page, str(dxf_file))
    drawing = ezdxf.readfile(dxf_file)
    layout = drawing.modelspace()
    dimensions = list(layout.query("DIMENSION"))
    expected = [span for *_, w, h in drawn for span in (w, h)]
    for dim, span in zip(dimensions, expected, strict=True):
        if abs(dim.get_measurement() - span) <= 0.01:
            continue
        if "-402-33" not in name or abs(dim.get_measurement() - span + 0.2) > 0.01:
            raise ValueError(f"Unexpected DXF measurement in {name}: {dim.get_measurement()} vs {span}")
        start = min(dim.dxf.defpoint2.x, dim.dxf.defpoint3.x)
        center = start + dim.get_measurement() / 2
        fixed = layout.add_linear_dim(base=dim.dxf.defpoint,
                                      p1=(center-span/2, dim.dxf.defpoint2.y),
                                      p2=(center+span/2, dim.dxf.defpoint3.y),
                                      text=f"{span:g}", dimstyle=dim.dxf.dimstyle,
                                      dxfattribs={"layer": dim.dxf.layer})
        fixed.render()
        layout.delete_entity(dim)
    for label in labels:
        layout.add_text(label.text, dxfattribs={
            "insert": (float(label.get("x")), height-float(label.get("y"))),
            "height": float(label.get("font-size")),
        })
    for x1, y1, x2, y2 in section_lines:
        layout.add_line((x1, height-y1), (x2, height-y2))
    with dxf_file.open("w", encoding=drawing.output_encoding, errors="dxfreplace", newline="\n") as stream:
        drawing.write(stream)
    return page_data


def run(output, variant_list, svg_only=False):
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError(f"Use an empty output directory: {output}")
    inputs = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    catalog = CATALOG.read_text(encoding="utf-8")
    for key in COTS.values():
        if f"  {key}:" not in catalog:
            raise ValueError(f"COTS key absent: {key}")
    manifest = {"geometry_commit": "83407d0844c34735a11af2fbdd2698e5cd909354",
                "versions": {"FreeCAD": ".".join(App.Version()[:3]), "OpenCASCADE": Part.OCC_VERSION},
                "inputs": {p.relative_to(ROOT).as_posix(): digest(p) for p in AUDITED_INPUTS},
                "variants": {}}
    with tempfile.TemporaryDirectory(prefix="W02-04-") as directory:
        for variant in variant_list:
            print(variant, flush=True)
            source = SOURCE / (variant + ".FCStd")
            if digest(source) != inputs["variants"][variant]["sha256"]:
                raise ValueError(f"Source hash: {variant}")
            manifest["inputs"][source.relative_to(ROOT).as_posix()] = digest(source)
            doc = App.openDocument(str(source))
            solids = [obj for obj in doc.Objects if hasattr(obj, "BOMItem")]
            groups = defaultdict(list)
            all_rows = defaultdict(list)
            for obj in solids:
                groups[geometry_key(obj)].append(obj)
                all_rows[obj.BOMItem].append(obj)
            rows = {}
            data = inputs["variants"][variant]["drawing_basis"]["bom"]
            for code, entry in data.items():
                label = B_NAMES.get(code, entry["description"])
                spec = entry["specification"].split(", COTS:")[0]
                catalog_ref = f" | COTS {COTS[code]}" if code in COTS else ""
                rows[code] = f'{code} | {entry["quantity"]} | {label} | {spec}{catalog_ref}'
            prefix = "W02-" + variant
            pages = {prefix: sheet(doc, prefix, solids, list(rows.values()), output, Path(directory), svg_only)}
            for index, group in enumerate(groups.values(), 1):
                obj = group[0]
                name = f"{prefix}-{obj.BOMItem[-3:]}-{index:02d}"
                detail = [rows[obj.BOMItem], f"CAD: {', '.join(item.Name for item in group)}"]
                pages[name] = sheet(doc, name, [obj], detail, output, Path(directory), svg_only)
                pages[name]["instances"] = [item.Name for item in group]
            doc.recompute()
            if not svg_only:
                doc.saveAs(str(output / f"{prefix}.FCStd"))
            App.closeDocument(doc.Name)
            manifest["variants"][variant] = pages
    extensions = (".svg",) if svg_only else (".svg", ".pdf", ".dxf")
    filenames = {name + ext for pages in manifest["variants"].values() for name in pages
                 for ext in extensions}
    if not svg_only:
        filenames.update(f"W02-{v}.FCStd" for v in variant_list)
    manifest["sha256"] = {name: digest(output / name) for name in sorted(filenames)}
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--variants", nargs="+", default=["A-V1", "A-V2", "B-V1", "B-V2"])
    parser.add_argument("--svg-only", action="store_true", help="Export only SVG sheets and their manifest")
    parser.add_argument("--font", type=Path,
                        default=Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/arial.ttf")
    args = parser.parse_args()
    qt = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    if not args.svg_only:
        pdfmetrics.registerFont(TTFont("W02", str(args.font)))
    run(args.out.resolve(), args.variants, args.svg_only)
