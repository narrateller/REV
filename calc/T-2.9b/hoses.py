"""Run the frozen qualification gate on the approved input and K sensitivity."""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARAMS = HERE / "params/params.t29.yaml"
REFERENCE = ROOT / "calc/T-2.6/params/params.t26a.yaml"


def build_params():
    original = REFERENCE.read_bytes()
    old = b"shell_L: 18.4"
    assert original.count(old) == 1
    PARAMS.parent.mkdir(exist_ok=True)
    PARAMS.write_bytes(original.replace(
        old, b"shell_L: 17.8  # Parker MSG10-4082/UK p.5, EHV 10837101125 (sources.yaml: parker_lp)"))


def gate(params, output):
    process = subprocess.run([
        sys.executable, str(ROOT / "ops/gates/calc_gates.py"),
        "--params", str(params), "--criteria", str(ROOT / "ops/criteria/design_criteria.yaml"),
        "--out", str(output),
    ], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                  env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"})
    if process.returncode not in (0, 1) or not output.exists():
        raise RuntimeError(process.stdout + process.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def cycle_row(result, K_Pa):
    entry = next(item for item in result["gates"] if item["id"] == "G-CYCLE")
    evidence = entry["details"]
    cycle_s = evidence["cycle_s"]
    rms_kW = evidence["rms_power_kW"]
    return {
        "K_Pa": K_Pa, "cycle_s": cycle_s, "rms_kW": rms_kW,
        "method": evidence["method"], "gate_status": entry["status"],
        "card_pass": entry["status"] == "PASS" and round(cycle_s, 9) <= 5.95 and round(rms_kW, 9) <= 30.0,
    }


def effective_bulk_modulus(volume_m3, oil_K_Pa, hose_compliances_m3_Pa):
    return volume_m3 / (volume_m3 / oil_K_Pa + sum(hose_compliances_m3_Pa))


def hose_inventory(K_threshold_Pa):
    """Calculate known catalog compliance and the admissible main-line budget."""
    from math import pi

    sources = yaml.safe_load((HERE / "sources.yaml").read_text(encoding="utf-8"))
    params = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))
    oil = params["cycle_model"]["oil"]
    oil_K = oil["bulk_modulus_Pa"]
    diameter_m = params["main_cylinder"]["bore_mm"] / 1000
    cap_m2 = pi * diameter_m**2 / 4
    cap_dead_m3 = oil["cap_dead_L"] / 1000
    end_mm = params["chamber"]["approach_stroke_mm"] + params["cycle_model"]["mechanics"]["roof_mm"] + 200
    points = (("closed_ports", 5), ("press_end_upper_volume", end_mm), ("full_stroke_upper_volume", 396))
    compliance_limit = [{
        "state": phase, "ram_mm": x, "cap_and_dead_L": (cap_dead_m3 + cap_m2 * x / 1000) * 1000,
        "extra_compliance_mL_per_bar_at_scan_threshold": (
            (cap_dead_m3 + cap_m2 * x / 1000) * (1 / K_threshold_Pa - 1 / oil_K) * 1e11),
    } for phase, x in points]
    hoses = []
    for item in sources["flexible_sections"]:
        row = dict(item)
        if "slope_cc_ft_psi" in row:
            area_m2 = pi / 4 * (row["catalog_id_mm"] / 1000)**2
            per_m_m3_Pa = row["slope_cc_ft_psi"] * 1e-6 / (.3048 * 6894.757293)
            row["expansion_mL_per_m_bar"] = per_m_m3_Pa * 1e11
            row["expansion_mL_per_m_at_design_range"] = row["expansion_mL_per_m_bar"] * row["dp_range_bar"]
            row["segment_K_eff_Pa"] = effective_bulk_modulus(area_m2, oil_K, [per_m_m3_Pa])
        hoses.append(row)
    return {
        "main_hose_K_eff_Pa": effective_bulk_modulus(cap_dead_m3, oil_K, []),
        "main_hose_count": 0, "main_pipe_material": "EN 10305-4 or equivalent for high pressure",
        "main_dead_volume_model_L": oil["cap_dead_L"], "main_compliance_budget": compliance_limit,
        "flexible_sections": hoses,
        "phase_isolation": {
            "closed_ports_regen_press": "CYM.A + MA + inner MF/ZSF caps; MB/MC/MR and the P path up to P1 are rigid.",
            "hold_decompression": "MP/MHOLD and MRC/MBT isolate the source and work volumes; CYM.A, MA, D1 and dump stubs remain rigid.",
            "prefill_eject_return": "PF to TF remains rigid for transient control; TF is mechanically isolated from high pressure by ZSF, MF and MBT.",
            "external": "Pilot and auxiliary cylinders, downstream tank return, service connections. Review the actual tube lengths and support at T-2.3.",
        },
    }


def no_gate_boost_check():
    params = yaml.safe_load(PARAMS.read_text(encoding="utf-8"))
    cycle_model = params["cycle_model"]
    cycle_model["lp"]["routes"] = [route for route in cycle_model["lp"]["routes"]
                                         if route not in ("gate_open", "gate_close")]
    with TemporaryDirectory(prefix="no_gate_lp_", dir=HERE) as folder:
        directory = Path(folder)
        candidate = directory / "alternative.yaml"
        candidate.write_text(yaml.safe_dump(params, sort_keys=False), encoding="utf-8")
        return cycle_row(gate(candidate, directory / "gate.json"), cycle_model["oil"]["bulk_modulus_Pa"])


def scan():
    base = PARAMS.read_text(encoding="utf-8")
    pattern = r"(\bbulk_modulus_Pa: *)[0-9.eE+]+"
    rows = {}
    with TemporaryDirectory(prefix="k_scan_", dir=HERE) as directory:
        directory = Path(directory)

        def run(K_GPa):
            K_Pa = int(K_GPa * 10**9)
            params = directory / "sensitivity.yaml"
            output = directory / "gate.json"
            changed, count = re.subn(pattern, lambda m: m[1] + str(K_Pa), base)
            assert count == 1
            params.write_text(changed, encoding="utf-8")
            output.unlink(missing_ok=True)
            rows[K_GPa] = cycle_row(gate(params, output), K_Pa)
            return rows[K_GPa]["card_pass"]

        for value in (100, *range(120, 141, 2)):
            run(Decimal(value) / 100)
        # Refine every coarse PASS/FAIL transition. RMS is not assumed monotone.
        coarse = sorted(value for value in rows if value >= Decimal("1.2"))
        for low, high in zip(coarse, coarse[1:]):
            if rows[low]["card_pass"] != rows[high]["card_pass"]:
                for step in range(1, 10):
                    run(low + step * Decimal("0.002"))
    passing = [value for value in rows if rows[value]["card_pass"]]
    threshold = min(passing)
    return {
        "hose_K_threshold_Pa": rows[threshold]["K_Pa"],
        "highest_sampled_failing_K_Pa": max(row["K_Pa"] for row in rows.values() if not row["card_pass"]),
        "k_scan": [rows[value] for value in sorted(rows)],
    }


if __name__ == "__main__":
    from oil_modulus import scan as scan_revision

    print(json.dumps(scan_revision(), indent=2, ensure_ascii=False))
