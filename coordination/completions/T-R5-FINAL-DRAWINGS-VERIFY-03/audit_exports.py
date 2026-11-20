from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from hashlib import sha256
import json
import re
import ezdxf
from ezdxf.lldxf.encoding import decode_dxf_unicode
from pypdf import PdfReader
import yaml

root = Path("drawings/W02/output")
source = Path("cad/source/force_geometry/redesign_1p5mn_04/manifest.json")
base = json.loads(source.read_bytes())
catalog = yaml.safe_load(Path("drives/cots_catalog.yaml").read_bytes())["components"]
manifest = json.loads((root / "manifest.json").read_bytes())
svg_ns = "{http://www.w3.org/2000/svg}"
expected_cots = dict(zip(("105", "201", "302", "303", "401"), ("linear_guides", "hydraulic_cylinder", "guide_pads", "punch_plate", "chamber_liner")))
counts, failures = Counter(), {}
minima, duplicate_examples = {}, {}
def check(condition, criterion, sheet):
    if not condition:
        failures.setdefault(criterion, []).append(sheet)
def normalize(s):
    return " ".join(s.split())
for variant, sheets in manifest["variants"].items():
    bom = base["variants"][variant]["drawing_basis"]["bom"]
    for name in sheets:
        paths = {ext: root / (name + "." + ext) for ext in ("pdf", "dxf", "svg")}
        for ext, path in paths.items():
            data = path.read_bytes()
            counts[ext] += 1
            minima[ext] = min(minima.get(ext, len(data)), len(data))
            check(sha256(data).hexdigest() == manifest["sha256"][path.name], "sha256", name)
            if ext == "pdf":
                check(data.startswith(b"%PDF-") and len(data) > 5120, "pdf_header_size", name)
            if ext == "svg":
                check(len(data) > 500, "svg_size", name)
            if ext == "dxf":
                lines = data.splitlines()
                tags = list(zip(lines[::2], lines[1::2], strict=True))
                tokens = [(int(code), value.strip()) for code, value in tags]
                check(tokens[-1] == (0,b"EOF") and (0,b"SECTION") in tokens and (2,b"ENTITIES") in tokens and (0,b"ENDSEC") in tokens, "dxf_tags", name)
        svg = ET.parse(paths["svg"]).getroot()
        check(svg.tag == svg_ns + "svg" and bool(svg.findall(".//" + svg_ns + "path")), "svg_geometry", name)
        ids = Counter(el.get("id") for el in svg.iter() if el.get("id") is not None)
        repeated = sorted(k for k, v in ids.items() if v > 1)
        check(not repeated, "svg_duplicate_ids", name)
        if repeated and len(duplicate_examples) < 4:
            duplicate_examples[name] = dict((key, ids[key]) for key in repeated[:3])
        svg_text = [normalize(el.text or "") for el in svg.iter(svg_ns + "text")]
        raw_pdf = PdfReader(paths["pdf"], strict=True)
        check(len(raw_pdf.pages) == 1, "pdf_pages", name)
        pdf = normalize(raw_pdf.pages[0].extract_text())
        dxf = ezdxf.readfile(paths["dxf"])
        dx_text = [normalize(decode_dxf_unicode(e.dxf.text)) for e in dxf.modelspace().query("TEXT")]
        title = name + " | W02 | REV 04 | 1:1 | mm"
        footer = "REV / R4 | Итерация 04 | 1:1 мм | 1 / 1"
        check(all(s in svg_text and s in pdf and s in dx_text for s in (title, footer, "Спецификация")), "title_and_unicode", name)
        rows = [s for s in svg_text if re.match(r"W02-\d{3} \|", s)]
        row_ids = [row.split(" | ")[0] for row in rows]
        expected = list(bom) if name == "W02-" + variant else ["W02-" + name.split("-")[-2]]
        check(Counter(row_ids) == Counter(expected), "bom_inventory", name)
        for row in rows:
            code, quantity, label, spec, *refs = row.split(" | ")
            entry = bom[code]
            check(row in pdf and row in dx_text and int(quantity) == entry["quantity"] and spec == entry["specification"].split(", COTS:")[0] and (code.startswith("W02-50") or label == entry["description"]), "bom_content", name)
            cots = expected_cots.get(code[-3:])
            check(refs == (["COTS " + cots] if cots else []) and (not cots or cots in catalog), "bom_cots", name)
            if code == "W02-201":
                check(int(quantity) == catalog["hydraulic_cylinder"]["quantity"], "cots_cylinder_qty", name)
print(json.dumps({"counts": counts, "min_bytes": minima, "failure_counts": {k: len(set(v)) for k,v in failures.items()}, "failure_examples": {k: list(dict.fromkeys(v))[:6] for k,v in failures.items()}, "duplicate_id_examples": duplicate_examples}, ensure_ascii=True, indent=2))
