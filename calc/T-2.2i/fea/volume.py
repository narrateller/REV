"""Reproduce the volume of the T-2.2h casting with front hardware removed.

Gmsh integrates engineering envelope volumes here. The trimmed geometry
retains the old floor and sides, so this calculation does not establish
that the new load path can use the trimmed casting.
"""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import numpy as np

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[1] / "T-2.2h"
sys.path[:0] = [str(OLD), str(OLD / "fea")]

from layout import Layout
from solver import mesh
import window_geometry


def volume(folder, size_mm, include_front):
    layout = Layout("forged", 128., 235., 235.)
    if not include_front:
        window_geometry.STATIONS = {"rear": window_geometry.STATIONS["rear"]}
    geo = window_geometry.cast(layout, size_mm, reinforcement=include_front)
    xyz, tets, _, _ = mesh(folder, geo)
    vertices = xyz[tets[:, :4]]
    volume_mm3 = np.abs(np.linalg.det(vertices[:, 1:] - vertices[:, :1])).sum()/6.
    return {"corner_volume_mm3": float(volume_mm3), "c3d10_element_count": len(tets)}


def run():
    rows = []
    original = window_geometry.STATIONS.copy()
    with TemporaryDirectory(dir=HERE, prefix="vol-") as temp:
        base = Path(temp)
        for size_mm in (18., 12.):
            full_folder, reduced_folder = base / f"full_{size_mm}", base / f"rear_{size_mm}"
            full_folder.mkdir()
            reduced_folder.mkdir()
            window_geometry.STATIONS = original.copy()
            full = volume(full_folder, size_mm, include_front=True)
            rear = volume(reduced_folder, size_mm, include_front=False)
            removed_mm3 = full["corner_volume_mm3"] - rear["corner_volume_mm3"]
            rows.append({"mesh_max_mm": size_mm, "full": full, "trimmed": rear,
                         "front_removed_mm3": removed_mm3, "front_removed_kg": 7.85e-6 * removed_mm3})
    return rows


if __name__ == "__main__":
    cli = ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, default=HERE / "volume.json")
    target = cli.parse_args().out
    target.write_text(json.dumps(run(), indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

