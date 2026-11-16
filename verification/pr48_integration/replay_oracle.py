"""Replay the reviewed R5 oracle, preserving its original evidence files."""
from pathlib import Path
import hashlib
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
source = ROOT / 'verification/r5_force_path_output_review/independent.py'
assert hashlib.sha256(source.read_bytes()).hexdigest() == '09a45b31339d09cb8fbe9dd338d349a14d3a6925ecd1fa93bdc43b23e2e8c5c0'
spec = importlib.util.spec_from_file_location('pr48_r5_oracle', source)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
# HERE is used solely for its output path; ROOT and immutable C/H remain intact.
oracle.HERE = HERE
oracle.run()
expected = ROOT / 'verification/r5_force_path_output_review/independent_results.json'
assert (HERE / 'independent_results.json').read_bytes() == expected.read_bytes()
print('MATCH original R5 oracle evidence; original package unchanged')
