"""Export W02 iteration 04 nominal geometry at 1:1 using FreeCAD's bundled Python."""
import argparse
from collections import defaultdict
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import FreeCAD as App
import Part
import TechDraw
from PySide import QtCore, QtGui, QtSvg, QtWidgets
from pypdf import PdfWriter
from pypdf.generic import FloatObject, NameObject, RectangleObject

from redesign_1p5mn.prepare import add_view, dimension

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cad/source/force_geometry/redesign_1p5mn_04"
CATALOG = ROOT / "drives/cots_catalog.yaml"
VERDICT = ROOT / "cae/cases/T-R3-FORCE-CALC-05/engineering_verdict.json"
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
        return (line(x, y-half, x, y+half) + line(x-2, y-half, x+2, y-half)
                + line(x-2, y+half, x+2, y+half) + text(x+3, y, f"{span:g}"))
    return (line(x-half, y, x+half, y) + line(x-half, y-2, x-half, y+2)
            + line(x+half, y-2, x+half, y+2) + text(x-5, y-3, f"{span:g}"))


def sheet(doc, name, objects, bom, output, temporary):
    x, y, z = size(objects)
    width = max(x+y+120, 450)
    top = 65 + z/2
    bottom = z+120+y/2
    footer = z+y+155
    height = footer + 8*len(bom)+38
    views = [
        ("XZ", (0,-1,0), (1,0,0), 38+x/2, top, x,z),
        ("XY", (0,0,1), (1,0,0), 38+x/2, bottom, x,y),
        ("YZ", (1,0,0), (0,1,0), x+80+y/2, top, y,z),
    ]
    header = [text(15, 16, name + "  |  W02  |  REV 04  |  1:1  |  mm", 6),
              text(15, 26, "Номинальная геометрия. Монтажные допуски и посадки требуют утверждения."),
              text(15, 36, "Для проверки R5. FreeCAD TechDraw / OCCT")]
    tail = [line(15, footer-10, width-15, footer-10),
            text(15, footer, "Спецификация")]
    for row, record in enumerate(bom, 1):
        tail.append(text(15, footer+8*row, record))
    tail.append(text(15, height-12, "REV / R4    |    Итерация 04    |    1:1 мм    |    1 / 1"))

    def frame(content):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}mm" height="{height:g}mm" '
                f'viewBox="0 0 {width:g} {height:g}" font-family="DejaVu Sans">'
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
    doc.recompute()
    deadline = time.monotonic() + 30
    while not all(view.getVisibleEdges() for view, *_ in drawn):
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
    doc.recompute()
    base = output / name
    svg_file = base.with_suffix(".svg")
    svg_file.write_text(frame(svg+tail), encoding="utf-8")
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
    renderer = QtSvg.QSvgRenderer(str(svg_file))
    painter = QtGui.QPainter(writer)
    if not renderer.isValid() or not painter.isActive():
        raise ValueError(f"Cannot render {name}")
    renderer.render(painter, QtCore.QRectF(0, 0, pdf_width, pdf_height))
    painter.end()
    del painter, writer
    pdf = PdfWriter(clone_from=str(draft_pdf))
    pdf.pdf_header = "%PDF-1.6"
    pdf.pages[0].mediabox = RectangleObject((0, 0, pdf_width, pdf_height))
    if user_unit != 1:
        pdf.pages[0][NameObject("/UserUnit")] = FloatObject(user_unit)
    with pdf_file.open("wb") as stream:
        pdf.write(stream)
    TechDraw.writeDXFPage(page, str(base.with_suffix(".dxf")))
    return {"page": page.Name, "size_mm": [width, height],
            "objects": [obj.Name for obj in objects]}


def run(output, variant_list):
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
            pages = {prefix: sheet(doc, prefix, solids, list(rows.values()), output, Path(directory))}
            for index, group in enumerate(groups.values(), 1):
                obj = group[0]
                name = f"{prefix}-{obj.BOMItem[-3:]}-{index:02d}"
                detail = [rows[obj.BOMItem], f"CAD: {', '.join(item.Name for item in group)}"]
                pages[name] = sheet(doc, name, [obj], detail, output, Path(directory))
                pages[name]["instances"] = [item.Name for item in group]
            doc.recompute()
            doc.saveAs(str(output / f"{prefix}.FCStd"))
            App.closeDocument(doc.Name)
            manifest["variants"][variant] = pages
    filenames = {name + ext for pages in manifest["variants"].values() for name in pages
                 for ext in (".svg", ".pdf", ".dxf")}
    filenames.update(f"W02-{v}.FCStd" for v in variant_list)
    manifest["sha256"] = {name: digest(output / name) for name in sorted(filenames)}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--variants", nargs="+", default=["A-V1", "A-V2", "B-V1", "B-V2"])
    args = parser.parse_args()
    qt = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    run(args.out.resolve(), args.variants)
