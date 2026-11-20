"""Verify the W02 iteration 04 delivery without regenerating drawings."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import re
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "drawings/W02/output"
SOURCE = ROOT / "cad/source/force_geometry/redesign_1p5mn_04"
SVG = "{http://www.w3.org/2000/svg}"
DECIMAL = re.compile(rb"-?\d+\.\d+")


def brep_geometry(raw):
    # TechDraw may set the Checked topology flag during projection. OCCT can
    # also round the last digits of floating-point coordinates on resaving.
    def round_decimal(match):
        value = round(float(match.group()), 8)
        return f"{value or 0:.8f}".encode()

    lines = [b"0101000" if line == b"0111000" else line for line in raw.splitlines()]
    return DECIMAL.sub(round_decimal, b"\n".join(lines))


def require(ok, name):
    if not ok:
        raise ValueError(str(name))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def git_matches(path, ref):
    raw = subprocess.check_output(["git", "show", f"{ref}:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT)
    if raw.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        require(f"oid sha256:{digest(path)}".encode() in raw.splitlines(), path)
        require(f"size {path.stat().st_size}".encode() in raw.splitlines(), path)
    else:
        require(raw == path.read_bytes(), path)


def verify_sheet(name, page, parse):
    stem = OUT / name
    svg_path = stem.with_suffix(".svg")
    svg = ET.parse(svg_path).getroot()
    require(svg.tag == SVG + "svg" and svg_path.stat().st_size > 5120, svg_path)
    width, height = page["size_mm"]
    require(svg.attrib["width"] == f"{width:g}mm" and svg.attrib["height"] == f"{height:g}mm", name)
    has_section = name.endswith("-402-33")
    require(bool(page["section"]) == has_section, name)
    require(len(svg.findall(f"{SVG}g[@transform]")) == 3 + has_section, name)
    require((svg.find(f"{SVG}g[@id='section-AA']") is not None) == has_section, name)
    svg_text = [item.text for item in svg.findall(SVG+"text")]
    require(all(label in svg_text for label in ("XZ", "XY", "YZ", "Спецификация")), name)
    pdf_path = stem.with_suffix(".pdf")
    require(pdf_path.stat().st_size > 5120 and pdf_path.read_bytes().startswith(b"%PDF-"), pdf_path)
    dxf_path = stem.with_suffix(".dxf")
    dxf = dxf_path.read_text(encoding="utf-8").splitlines()
    values = [line.strip() for line in dxf[1::2]]
    require(values[-1] == "EOF" and values.count("DIMENSION") == 6, dxf_path)
    if parse:
        import ezdxf
        from pypdf import PdfReader
        reader = PdfReader(pdf_path, strict=True)
        require(len(reader.pages) == 1, pdf_path)
        pdf = reader.pages[0]
        pdf_text = pdf.extract_text()
        require("Спецификация" in pdf_text and name in pdf_text, pdf_path)
        for row in svg_text:
            if " | " in row and row.startswith("W02-") and row != svg_text[0]:
                require(row in pdf_text, f"{pdf_path}: {row}")
        for points, mm in zip((pdf.mediabox.width, pdf.mediabox.height), (width, height)):
            require(abs(float(points * pdf.user_unit)*25.4/72-mm) < 0.01, pdf_path)
        document = ezdxf.readfile(dxf_path)
        require(document.units == 4 and not document.audit().errors, dxf_path)
        modelspace = document.modelspace()
        actual = sorted(dim.get_measurement() for dim in modelspace.query("DIMENSION"))
        expected = sorted(page["extents_mm"] * 2)
        require(all(abs(a-b) <= 0.01 for a, b in zip(actual, expected, strict=True)), dxf_path)
        require(any(entity.dxf.text == "Спецификация" for entity in modelspace.query("TEXT")), dxf_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--parse", action="store_true", help="Also parse every PDF and DXF with pypdf and ezdxf")
    options = parser.parse_args()
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    source_manifest = json.loads((SOURCE / "manifest.json").read_bytes())
    require(manifest["versions"] == {"FreeCAD": "1.1.4", "OpenCASCADE": "7.8.1"}, "CAD versions")
    require(set(manifest["variants"]) == set(source_manifest["variants"]), "Variants")
    for name, expected in manifest["inputs"].items():
        path = ROOT / name
        require(digest(path) == expected, path)
        if options.check_git:
            git_matches(path, "HEAD")
            if path.is_relative_to(SOURCE):
                git_matches(path, manifest["geometry_commit"])
    expected_counts = Counter()
    for variant, pages in manifest["variants"].items():
        prefix = f"W02-{variant}"
        model = OUT / (prefix + ".FCStd")
        with ZipFile(model) as native, ZipFile(SOURCE / (variant+".FCStd")) as upstream:
            require(native.testzip() is None, model)
            for member in upstream.namelist():
                if member.lower().endswith(".brp"):
                    require(brep_geometry(native.read(member)) == brep_geometry(upstream.read(member)), f"{model}: {member}")
            xml = ET.fromstring(native.read("Document.xml"))
            objects = {obj.attrib["name"] for obj in xml.findall("./Objects/Object")}
            require(all(page["page"] in objects for page in pages.values()), model)
            require(all(page["section"] in objects for page in pages.values() if page["section"]), model)
        covered = Counter(obj for name, page in pages.items() if name != prefix for obj in page["instances"])
        require(covered == Counter(pages[prefix]["objects"]), f"{variant}: coverage")
        require(sum(covered.values()) == source_manifest["variants"][variant]["native_solid_count"], variant)
        for name, page in pages.items():
            verify_sheet(name, page, options.parse)
        expected_counts.update({".FCStd": 1, ".pdf": len(pages), ".svg": len(pages), ".dxf": len(pages)})
    actual_counts = Counter(Path(name).suffix for name in manifest["sha256"])
    require(actual_counts == expected_counts, "File counts")
    require(set(manifest["sha256"]) == {path.name for path in OUT.iterdir() if path != manifest_path}, "Output inventory")
    for name, expected in manifest["sha256"].items():
        path = OUT / name
        require(digest(path) == expected, path)
        if options.check_git:
            git_matches(path, "HEAD")
    if options.check_git:
        git_matches(manifest_path, "HEAD")
        git_matches(Path(__file__).resolve(), "HEAD")
    print("PASS:", dict(actual_counts), "W02 iteration 04")


if __name__ == "__main__":
    main()
