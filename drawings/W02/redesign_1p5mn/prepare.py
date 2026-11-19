"""Add a TechDraw drawing basis and a BOM to a native W02 assembly."""

from pathlib import Path

import FreeCAD as App
import TechDraw  # Registers the TechDraw document objects in the console runtime.

SCALE = 1 / 30

# CAD sub-solids of a cylinder are counted as one purchased assembly per axis.
ITEMS = {
    "W02-101": ("Rear frame head", "Thick structural block, 280 mm"),
    "W02-102": ("Reaction frame head", "Thick structural block, 280 mm"),
    "W02-103": ("Square frame tie with end studs", "180 mm square, 140 mm stud root"),
    "W02-104": ("Captive frame tie nut", "M160-equivalent, engagement 115 mm"),
    "W02-105": ("Machined box-way reaction beam", "425 x 450 x 3280 mm"),
    "W02-106": ("Fitted guide beam end dowel", "Diameter 60 mm, 100 mm engagement each side"),
    "W02-201": ("Double-acting hydraulic cylinder", "250/140 x 700 mm, COTS: hydraulic_cylinder"),
    "W02-202": ("Base and rod clevis ear", "90 mm, qualified full-penetration root"),
    "W02-203": ("Clevis pin", "Diameter 150 mm, double shear"),
    "W02-301": ("Moving crosshead with arms and spider", "280 mm primary plate, 600 mm guide stations"),
    "W02-302": ("Replaceable guide pad", "155 x 245 x 25 mm, COTS: guide_pads"),
    "W02-303": ("Forged guided punch", "300 x 220 mm, bilateral thrust/retention"),
    "W02-304": ("Rear punch retention collar", "360 x 320 x 65 mm"),
    "W02-305": ("Punch-collar tie", "M64 with 55 mm min root"),
    "W02-306": ("Fitted guide pad retainer", "30 mm minimum root, locations to be detailed"),
    "W02-401": ("Chamber and feed interface", "304 x 224 mm clear, 580 mm working length"),
    "W02-402": ("Tapered die", "150 x 60 mm target product section"),
    "W02-403": ("Continuation sleeve, family A", "304 x 224 mm clear"),
    "W02-404": ("Chamber support rib", "Mounts tool body to reaction frame"),
    "W02-501": ("Lifting receiver gate, family B", "640 x 300 x 210 mm, lift 370 mm"),
    "W02-502": ("Fixed receiver seat, family B", "Independent compressive load path"),
    "W02-503": ("Gate guide cheek, family B", "2 mm nominal running gap"),
    "W02-504": ("Receiver lock key, family B", "60 x 250 x 70 mm, drops 400 mm"),
    "W02-505": ("Reaction backing for lock key, family B", "Direct compressive path to reaction head"),
}


def add_view(doc, page, name, source, direction, right, xy):
    view = doc.addObject("TechDraw::DrawViewPart", name)
    view.Source = source
    view.Direction = App.Vector(*direction)
    view.XDirection = App.Vector(*right)
    view.ScaleType = "Custom"
    view.Scale = SCALE
    page.addView(view)
    view.X, view.Y = xy
    return view


def dimension(doc, page, view, name, axis, expected, xy):
    points = [view.getVertexByIndex(i).Point for i in range(len(view.getVisibleVertexes()))]
    horizontal = axis == "x"
    coord = (lambda p: p.x) if horizontal else (lambda p: p.y)
    other = (lambda p: p.y) if horizontal else (lambda p: p.x)
    lo = min(range(len(points)), key=lambda i: (round(coord(points[i]), 6), round(other(points[i]), 6)))
    hi = min(range(len(points)), key=lambda i: (-round(coord(points[i]), 6), round(other(points[i]), 6)))
    measured = abs(coord(points[hi]) - coord(points[lo]))
    if abs(measured - expected) > 1e-4:
        raise ValueError(f"{name}: model projection span {measured:g} != {expected:g} mm")
    obj = doc.addObject("TechDraw::DrawViewDimension", name)
    obj.Type = "DistanceX" if horizontal else "DistanceY"
    obj.References2D = [(view, (f"Vertex{lo}", f"Vertex{hi}"))]
    obj.FormatSpec = "%.0f"
    page.addView(obj)
    obj.X, obj.Y = xy
    return measured


def note(doc, page, name, lines, x, y, size=3):
    note = doc.addObject("TechDraw::DrawViewAnnotation", name)
    note.Text = lines
    note.Font = "DejaVu Sans"
    note.TextSize = size
    page.addView(note)
    note.X, note.Y = x, y


def new_page(doc, variant, name, template_name, sheet, scale, subtitle):
    page = doc.addObject("TechDraw::DrawPage", name)
    template = doc.addObject("TechDraw::DrawSVGTemplate", template_name)
    template.Template = str(Path(App.getResourceDir()) / "Mod/TechDraw/Templates/ISO/A3_Landscape_TD.svg")
    page.Template = template
    title = template.EditableTexts
    title.update({"AuthorName": "REV / R4", "CheckDate": "PENDING R5", "CreationDate": "2026-11-19",
                  "FC-Title": f"W02 {variant} | 1.5 MN", "SheetNumber": f"{sheet} / 2",
                  "Subtitle": subtitle, "SupervisorName": "PENDING",
                  "Weight": "TBD", "drawing_number": f"W02-{variant}-1P5MN", "scale": scale})
    template.EditableTexts = title
    return page, title["drawing_number"]


def prepare(doc, variant, solids, counts, dimensions, d, stroke):
    c, s = (d[k] for k in ("cylinder", "structure"))
    page, drawing_number = new_page(doc, variant, "AssemblyDrawing", "AssemblyTitleBlock", 1, "1:30",
                                    "DESIGN BASIS / REV 01")
    side = add_view(doc, page, "SideView", solids, (0, -1, 0), (1, 0, 0), (109, 220))
    add_view(doc, page, "PlanView", solids, (0, 0, 1), (1, 0, 0), (109, 110))
    end = add_view(doc, page, "OutletView", solids, (1, 0, 0), (0, 1, 0), (262, 220))
    internal = [obj for obj in solids if obj.BOMItem in {
        "W02-201", "W02-202", "W02-203", "W02-301", "W02-302", "W02-303", "W02-401", "W02-501", "W02-504",
    }]
    normal = (0, -1, 0) if variant.endswith("V1") else (0, 0, 1)
    add_view(doc, page, "LoadPathView", internal, normal, (1, 0, 0), (261, 111))
    doc.recompute()
    values = {
        "length_X_mm": dimension(doc, page, side, "OverallLength", "x", dimensions[0], (0, -47)),
        "width_Y_mm": dimension(doc, page, end, "OverallWidth", "x", dimensions[1], (0, -47)),
        "height_Z_mm": dimension(doc, page, end, "OverallHeight", "y", dimensions[2], (47, 0)),
    }
    note(doc, page, "SideLabel", ["SIDE  /  XZ"], 110, 269)
    note(doc, page, "PlanLabel", ["PLAN  /  XY"], 110, 155)
    note(doc, page, "OutletLabel", ["OUTLET  /  YZ"], 262, 269)
    note(doc, page, "LoadPathLabel", ["LOAD PATH  /  FRAME OMITTED"], 261, 155)
    note(doc, page, "KeyDimensions", [
        "Millimetres", f"Two cylinders: {c['bore']}/{c['rod']}",
        f"Stroke: {c['stroke']}", f"Working travel: {stroke['q_range_mm'][1]:.3f}",
        f"Guide stations: {s['guide_bogie_span']}", "Punch: 300 x 220", "Product: 150 x 60",
    ], 356, 147)
    note(doc, page, "FrameDatum", ["+X toward die, +Y transverse, +Z up",
                                  "Native BOM: PartsList sheet; drawing issue: preliminary"], 112, 53)
    bom = {}
    for item, (label, spec) in ITEMS.items():
        count = counts.get(item, 0)
        if item == "W02-201":
            count = c["quantity"]
        if item == "W02-306":
            count = counts["W02-302"] * s["guide_pad_fasteners"]
        if count:
            bom[item] = {"description": label, "quantity": count, "specification": spec}
    sheet = doc.addObject("Spreadsheet::Sheet", "PartsList")
    sheet.Label = "W02 bill of materials"
    for cell, text in zip("ABCD", ("Item", "Description", "Quantity", "Design specification / COTS")):
        sheet.set(f"{cell}1", text)
    sheet.setStyle("A1:D1", "bold")
    for row, (item, data) in enumerate(bom.items(), 2):
        for cell, value in zip("ABCD", (item, data["description"], str(data["quantity"]), data["specification"])):
            sheet.set(f"{cell}{row}", value)
    for column, width in zip("ABCD", (100, 275, 90, 400)):
        sheet.setColumnWidth(column, width)
    bom_page, _ = new_page(doc, variant, "BOMDrawing", "BOMTitleBlock", 2, "N/A", "BILL OF MATERIALS / REV 01")
    table = doc.addObject("TechDraw::DrawViewSpreadsheet", "BOMTable")
    table.Source = sheet
    table.CellEnd = f"D{len(bom) + 1}"
    table.TextSize = 8
    bom_page.addView(table)
    table.X, table.Y = 210, 174
    doc.recompute()
    return {"page": page.Name, "drawing_number": drawing_number, "format": "A3 landscape",
            "scale": "1:30", "views": ["SideView", "PlanView", "OutletView", "LoadPathView"],
            "associative_dimensions_mm": values, "bom_sheet": sheet.Name, "bom_page": bom_page.Name,
            "bom_view": table.Name, "bom": bom}
