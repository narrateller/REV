"""Repeat the T-1.7b reference cover screen in the T-2.2 output directory."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "T-1.7b"))

import retained_cap


def main():
    # Upstream solver places scratch beside FEA and removes it on exit.
    retained_cap.FEA = HERE
    for mesh_level in (0, 1, 2):
        retained_cap.solve(mesh_level)


if __name__ == "__main__":
    main()

