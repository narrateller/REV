"""Project the T-1.4b reference into the schema-v1 cycle model."""

from bisect import bisect_right
from copy import deepcopy
from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
from math import ceil, fsum, pi, sqrt
import sys

import yaml

from drive import HERE, ROOT, configuration, get_inputs
from x1_calc import BAR_PA, motions

TAIL_GROUP = "eject_return_close"
BASE_DENSITY_KG_M3 = 90
FEED_S = .64


def gate_module():
    path = ROOT / "ops/gates/calc_gates.py"
    spec = spec_from_file_location("calc_gates_readonly", path)
    gate = module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = gate
    try:
        spec.loader.exec_module(gate)
    finally:
        sys.path.pop(0)
    return gate


def ramp_time_s(motion, x_m):
    """Time along an ideal acceleration-limited trajectory at unlimited flow."""
    stroke_m, speed_m_s, accel_m_s2 = motion.stroke_m, motion.speed_m_s, motion.accel_m_s2
    ramp_m = min(stroke_m / 2, speed_m_s**2 / (2 * accel_m_s2))

    def one_way_s(distance_m):
        return sqrt(2 * min(ramp_m, distance_m) / accel_m_s2) + max(0., distance_m - ramp_m) / speed_m_s

    if x_m <= stroke_m / 2:
        return one_way_s(x_m)
    return 2 * one_way_s(stroke_m / 2) - one_way_s(max(0., stroke_m - x_m))


def swept_bands(motion, breakpoints_m, boost_bar, standby_bar):
    """Use maximum pressure on each band and integrate oil at the midpoint."""
    forced_m = set(breakpoints_m)
    if motion.marker_m:
        forced_m.add(motion.marker_m)
    if motion.accel_m_s2:
        ramp_m = min(motion.stroke_m / 2, motion.speed_m_s**2 / (2 * motion.accel_m_s2))
        for n in range(1, 5):
            x_m = n * ramp_m / 4
            forced_m.update((x_m, motion.stroke_m - x_m))
    segments = ceil(motion.stroke_m / .0001)
    sample_m = sorted({motion.stroke_m * i / segments for i in range(segments)} | forced_m | {motion.stroke_m})
    bands = []
    for lo_m, hi_m in zip(sample_m, sample_m[1:]):
        if hi_m - lo_m < 1e-12:
            continue
        # On the cam boundary evaluate the left limit for the outgoing band.
        edge_m = hi_m - 1e-9 if hi_m == motion.marker_m else hi_m
        bar = max(standby_bar, motion.pressure_bar(lo_m), motion.pressure_bar(edge_m))
        if motion.accel_m_s2 and lo_m < ramp_m - 1e-12:
            bar += motion.mass_kg * motion.accel_m_s2 / (motion.flow_area_m2 * motion.cylinder.eta * BAR_PA)
        midpoint_m = (lo_m + hi_m) / 2
        speed_m_s = motion.speed_at_m_s(midpoint_m)
        # Finer bands on the nonlinear press side, coarser in the tail.
        bandwidth_bar = 10 if motion.name in ("press", "regen") else 15
        key = (bisect_right(range(0, 301, bandwidth_bar), bar), bar <= boost_bar, speed_m_s)
        volume_m3 = (motion.flow_area_m2 + motion.storage_area_m2(midpoint_m)) * (hi_m - lo_m)
        if bands and lo_m not in forced_m and bands[-1][0] == key:
            _, start_m, _, past_bar, past_m3 = bands[-1]
            bands[-1] = key, start_m, hi_m, max(bar, past_bar), past_m3 + volume_m3
        else:
            bands.append((key, lo_m, hi_m, bar, volume_m3))
    return bands


def equivalent_rod_mm(cap_m2, press_volume_m3, other_ext_m3, retract_m3):
    """Match extension and retraction in equivalent coordinates at exact volumes."""
    lo_m2, hi_m2 = 0., cap_m2
    for _ in range(60):
        rod_m2 = (lo_m2 + hi_m2) / 2
        extend_m = press_volume_m3 / cap_m2 + other_ext_m3 / rod_m2
        retract_m = retract_m3 / (cap_m2 - rod_m2)
        if extend_m > retract_m:
            lo_m2 = rod_m2
        else:
            hi_m2 = rod_m2
    return 2000 * sqrt((lo_m2 + hi_m2) / (2 * pi))


def motion_rows(motion, bands, equivalent_area_m2, breakpoints_m, group=None, use_boost=False):
    rows, markers = [], {}
    metering_mode = motion.mode
    if motion.name in ("prefill", "eject"):
        metering_mode = "regen"  # schema's rod-area proxy for the rapid cylinder pair
    if motion.entry_compress_m3:
        rows.append(dict(name="closed ports oil compression", actuator="main_cylinder",
                         direction="extend", regeneration=True, speed_mm_s="pump", dwell_s=0,
                         max_speed_mm_s=1000, pressure_bar=motion.pressure_bar(0),
                         stroke_mm=1000 * motion.entry_compress_m3 / equivalent_area_m2))
    for (_, boost_covered, speed_m_s), lo_m, hi_m, pressure_bar, oil_m3 in bands:
        if motion.accel_m_s2:
            duration_s = ramp_time_s(motion, hi_m) - ramp_time_s(motion, lo_m)
        else:
            duration_s = (hi_m - lo_m) / speed_m_s
        equivalent_stroke_mm = 1000 * oil_m3 / equivalent_area_m2
        rows.append(dict(name=f"{motion.name} {len(rows) + 1}", actuator=motion.actuator,
                         stroke_mm=equivalent_stroke_mm, pressure_bar=pressure_bar,
                         direction="retract" if metering_mode == "retract" else "extend",
                         regeneration=metering_mode == "regen", dwell_s=0,
                         speed_mm_s="pump", max_speed_mm_s=min(1000., equivalent_stroke_mm / duration_s)))
        if use_boost and boost_covered:
            rows[-1]["use_accumulator"] = True
        if hi_m in breakpoints_m:
            markers[breakpoints_m[hi_m]] = rows[-1]["name"]
    for previous, row in zip(rows, rows[1:]):
        if previous.get("use_accumulator", False) == row.get("use_accumulator", False):
            row["continues"] = True
    if group:
        for row in rows:
            row["group"] = group
    if motion.name == "press":
        rows[-1]["press"] = True
    return rows, markers


def tail_end_times(gate, params, rows):
    cylinders = gate.actuators(params)
    positions = {name: [0.] for name in cylinders}
    evaluated, _, _ = gate.evaluate_timed_phases(rows, cylinders, params["drive"], positions,
                                                  gate.CyclePower(params["drive"]["idle_kW"]), [])
    return {row["name"]: row["motion_end_s"] for row in evaluated if "motion_end_s" in row}


def close_projected_coordinates(cycle):
    """Cancel only accumulated floating-point roundoff at the final step."""
    for actuator in ("main_cylinder", "precompaction", "slide_gate"):
        rows = [row for row in cycle if row["actuator"] == actuator]
        position_mm = 0.
        for row in rows[:-1]:
            direction = 1 if row["direction"] == "extend" else -1
            position_mm += direction * row["stroke_mm"]
        last = rows[-1]
        final_stroke_mm = position_mm if last["direction"] == "retract" else -position_mm
        assert abs(final_stroke_mm - last["stroke_mm"]) <= 1e-8
        last["stroke_mm"] = final_stroke_mm


def make_candidate(inputs, configuration_result=None):
    model, main, settings, projection, charge = configuration_result or configuration(inputs)
    sequence = motions(model, main, BASE_DENSITY_KG_M3, settings["prefill"])
    breaks_m = {
        "eject": {settings["unlock_x_m"] - model.press_end_m: "unlock"},
        "return": {model.overtravel_m + .010: "gate_clear"},
    }
    boost_bar = charge["min_delivery_pressure_bar"]
    standby_bar = settings["pump"].standby_bar
    bands = {name: swept_bands(motion, breaks_m.get(name, {}), boost_bar, standby_bar)
             for name, motion in sequence.items()}

    def volume_m3(name):
        return fsum(band[-1] for band in bands[name]) + sequence[name].entry_compress_m3

    candidate = deepcopy(inputs[1])
    candidate["description"] = (
        "T-1.4b V2, D-GK-01, base 90 kg/m3, 0.83 kg, feed 0.64 s. "
        "Cycle-only equivalent main rod and strokes conserve oil volume, not physical geometry."
    )
    virtual_rod_mm = equivalent_rod_mm(main.cap_m2, volume_m3("press"),
                                      fsum(volume_m3(name) for name in ("prefill", "regen", "eject")),
                                      volume_m3("return"))
    equivalent_main = replace(main, rod_mm=virtual_rod_mm)
    candidate["main_cylinder"].update(rod_mm=virtual_rod_mm, eta=main.eta, p_relief_bar=315,
                                      p_work_bar=sequence["press"].pressure_bar(sequence["press"].stroke_m))
    candidate["drive"].update(projection, accumulator=charge)

    def build(name, group=None):
        motion = sequence[name]
        area_m2 = motion.flow_area_m2
        if motion.actuator == "main_cylinder":
            area_m2 = {"press": equivalent_main.cap_m2, "return": equivalent_main.annulus_m2}.get(
                name, equivalent_main.rod_m2)
        return motion_rows(motion, bands[name], area_m2, breaks_m.get(name, {}), group,
                           use_boost=name in settings["boost_branches"])

    cycle = []
    for name in ("pre_down", "prefill", "regen", "press"):
        cycle.extend(build(name)[0])
    cycle.extend(dict(name=name, actuator="none", dwell_s=settings[name + "_s"]) for name in ("hold", "unload"))
    cycle.extend(build("gate_open")[0])
    eject, eject_markers = build("eject", TAIL_GROUP)
    retract, return_markers = build("return", TAIL_GROUP)
    pre_up, _ = build("pre_up", TAIL_GROUP)
    gate_close, _ = build("gate_close", TAIL_GROUP)
    gate = gate_module()
    ends_s = tail_end_times(gate, candidate, eject)
    retract[0]["start_delay_s"] = ends_s[eject[-1]["name"]]
    pre_up[0]["start_delay_s"] = ends_s[eject_markers["unlock"]]
    ends_s = tail_end_times(gate, candidate, eject + retract + pre_up)
    gate_close[0]["start_delay_s"] = ends_s[return_markers["gate_clear"]]
    cycle.extend(eject + retract + gate_close + pre_up)
    cycle.append(dict(name="feed", actuator="none", dwell_s=FEED_S))
    close_projected_coordinates(cycle)
    candidate["cycle"] = cycle
    gate.validate_params(candidate)
    return candidate


def main():
    candidate = make_candidate(get_inputs())
    path = HERE / "params_reference_replay.yaml"
    path.write_text(
        "# Generated by calc/T-1.4b/make_params_t14b.py. G-CYCLE projection only.\n"
        "# Physical main cylinder: Ø280/200, installed stroke 289 mm. Rapid drive: 2 x Ø90/50.\n"
        "# main_cylinder.rod_mm and main movement strokes are equivalent hydraulic coordinates.\n"
        "# Rod-area proxy rows named prefill/eject represent floating main cylinder and rapid pair.\n"
        "# Real PLC uses measured positions, pressure, valve feedback and 70 ms control budget.\n"
        + yaml.safe_dump(candidate, allow_unicode=True, sort_keys=False),
        encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
