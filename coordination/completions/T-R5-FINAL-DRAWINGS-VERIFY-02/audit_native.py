"""Read delivered FreeCAD documents without editing or regenerating them."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import FreeCAD as App
import Part
from PySide import QtWidgets


out = Path("drawings/W02/output").resolve()
manifest = json.loads((out / "manifest.json").read_bytes())
app = QtWidgets.QApplication([])
results = {}
for variant, sheets in manifest["variants"].items():
    doc = App.openDocument(str(out / f"W02-{variant}.FCStd"))
    invalid = [obj.Name for obj in doc.Objects if "Invalid" in obj.State]
    pages = {}
    for name, entry in sheets.items():
        page = doc.getObject(entry["page"])
        views = [view for view in page.Views if view.TypeId == "TechDraw::DrawViewPart"]
        dims = [view for view in page.Views if view.TypeId in ("TechDraw::DrawViewDimension", "TechDraw::DrawViewDimExtent")]
        box = App.BoundBox()
        for obj in entry["objects"]:
            box.add(doc.getObject(obj).Shape.BoundBox)
        pages[name] = {
            "extents": [box.XLength, box.YLength, box.ZLength],
            "scales": [page.Scale, *(view.Scale for view in views)],
            "sources_match": all([obj.Name for obj in view.Source] == entry["objects"] for view in views),
            "directions": [list(view.Direction) for view in views],
            "dimension_names": [dim.Name for dim in dims],
            "view_names": [view.Name for view in views],
        }
    solids = [obj for obj in doc.Objects if hasattr(obj, "BOMItem")]
    results[variant] = {
        "objects": len(doc.Objects),
        "solid_count": len(solids),
        "invalid_objects": invalid,
        "invalid_solids": [obj.Name for obj in solids if not obj.Shape.Solids or not obj.Shape.isValid()],
        "pages": pages,
    }
    App.closeDocument(doc.Name)
print(json.dumps({
    "FreeCAD": ".".join(App.Version()[:3]),
    "OpenCASCADE": Part.OCC_VERSION,
    "variants": results,
}))
