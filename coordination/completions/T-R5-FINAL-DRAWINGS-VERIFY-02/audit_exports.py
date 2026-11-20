"""Audit all W02 drawing exports against the pinned nominal model."""
from collections import Counter, defaultdict
import json
from math import isclose
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET

import ezdxf
from pypdf import PdfReader
import yaml

OUT = Path("drawings/W02/output")
NS = "{http://www.w3.org/2000/svg}"
AXES = [(0, 2), (0, 1), (1, 2)]
DIRECTIONS = [[0, -1, 0], [0, 0, 1], [1, 0, 0]]
native = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
manifest = json.loads((OUT / "manifest.json").read_bytes())
source = json.loads(Path("cad/source/force_geometry/redesign_1p5mn_04/manifest.json").read_bytes())
catalog = yaml.safe_load(Path("drives/cots_catalog.yaml").read_bytes())["components"]
failures = defaultdict(dict)
minimum = {ext: min(p.stat().st_size for p in OUT.glob(f"*.{ext}")) for ext in ("pdf", "svg")}
bom_formats = Counter()


def check(criterion, name, passed, detail):
    if not passed:
        failures[criterion][name] = detail


def same(values, expected, tolerance):
    return len(values) == len(expected) and all(
        isclose(a, b, rel_tol=0, abs_tol=tolerance) for a, b in zip(values, expected)
    )


for variant, sheets in manifest["variants"].items():
    assembly = f"W02-{variant}"
    bom = source["variants"][variant]["drawing_basis"]["bom"]
    for name, entry in sheets.items():
        base = OUT / name
        native_page = native["variants"][variant]["pages"][name]
        extents = native_page["extents"]
        expected = [extents[i] for pair in AXES for i in pair]
        check("native_projections", name, native_page["scales"] == [1] * 4
              and native_page["sources_match"] and native_page["directions"] == DIRECTIONS
              and len(native_page["dimension_names"]) == 6, native_page)

        pdf_file = base.with_suffix(".pdf")
        data = pdf_file.read_bytes()
        check("pdf_header_size", name, data.startswith(b"%PDF-") and len(data) > 5120, len(data))
        reader = PdfReader(pdf_file, strict=True)
        page = reader.pages[0]
        pdf_mm = [float(value * page.user_unit) * 25.4 / 72 for value in (page.mediabox.width, page.mediabox.height)]
        check("pdf_page", name, len(reader.pages) == 1 and same(pdf_mm, entry["size_mm"], .01)
              and bool(page.get_contents().get_data()), pdf_mm)

        svg_file = base.with_suffix(".svg")
        svg = ET.parse(svg_file).getroot()
        check("svg_namespace", name, svg.tag == NS + "svg", svg.tag)
        check("svg_size", name, svg_file.stat().st_size > 5120, svg_file.stat().st_size)
        svg_mm = [float(svg.attrib[key].removesuffix("mm")) for key in ("width", "height")]
        view_box = list(map(float, svg.attrib["viewBox"].split()))
        groups = svg.findall(NS + "g")
        labels = [element.text or "" for element in svg.findall(NS + "text")]
        numeric = [float(label) for label in labels if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", label)]
        check("svg_projections", name, same(view_box, [0, 0, *svg_mm], .00001)
              and len(groups) == 3 and all(re.fullmatch(r"translate\([\d., -]+\)", group.get("transform", ""))
                                           and len(group) for group in groups)
              and all(label in labels for label in ("XZ", "XY", "YZ"))
              and same(numeric, expected, .01), {"measured": numeric, "expected": expected})

        rows = [text.split(" | ") for text in labels if re.match(r"W02-\d{3} \| ", text)]
        expected_codes = set(bom) if name == assembly else {"W02-" + name.split("-")[-2]}
        check("svg_bom", name, "Спецификация" in labels and len(rows) == len(expected_codes)
              and {row[0] for row in rows} == expected_codes
              and all(int(row[1]) == bom[row[0]]["quantity"]
                      and row[3] == bom[row[0]]["specification"].split(", COTS:")[0] for row in rows),
              rows)
        refs = [field.removeprefix("COTS ") for row in rows for field in row[4:] if field.startswith("COTS ")]
        check("cots_refs", name, all(ref in catalog for ref in refs)
              and ("W02-201" not in expected_codes or "hydraulic_cylinder" in refs), refs)

        dxf = ezdxf.readfile(base.with_suffix(".dxf"))
        space = dxf.modelspace()
        audit = dxf.audit()
        layers = {layer.dxf.name for layer in dxf.layers}
        check("dxf_parse_layers_entities", name, len(layers) > 1 and len(space) > 0
              and not audit.errors, {"layers": sorted(layers), "errors": len(audit.errors)})
        dims = {dim.dxf.layer: dim.get_measurement() for dim in space.query("DIMENSION")}
        expected_layers = native_page["dimension_names"]
        measures = [dims.get(layer, -1) for layer in expected_layers]
        check("dxf_projections", name, dxf.units == 4 and same(measures, expected, .01)
              and all(any(entity.dxf.layer == view for entity in space) for view in native_page["view_names"]),
              {"measured": measures, "expected": expected, "layers": list(dims)})
        bom_formats["svg_with_bom_rows"] += bool(rows)
        operations = page.get_contents().operations
        scales = [float(matrix[0]) * float(page.user_unit) * 25.4 / 72
                  for matrix, operator in operations if operator == b"cm" and matrix[0] == matrix[3]]
        check("pdf_projection_scale", name, bool(scales) and all(isclose(scale, 1, abs_tol=.001) for scale in scales), scales)
        bom_formats["pdf_with_text_operators"] += any(operator in (b"Tj", b"TJ") for _, operator in operations)
        bom_formats["dxf_with_text_entities"] += bool(space.query("TEXT MTEXT"))

print(json.dumps({
    "minimum_bytes": minimum,
    "counts": Counter(p.suffix for p in OUT.iterdir() if p.suffix != ".json"),
    "parser_versions": {"ezdxf": ezdxf.__version__},
    "native": {
        "versions": {key: native[key] for key in ("FreeCAD", "OpenCASCADE")},
        "documents": {variant: {**{key: value for key, value in doc.items() if key != "pages"},
                                "pages": len(doc["pages"])} for variant, doc in native["variants"].items()},
    },
    "bom_formats": bom_formats,
    "failure_counts": {key: len(value) for key, value in failures.items()},
    "failures": failures,
}, indent=2, ensure_ascii=True))
