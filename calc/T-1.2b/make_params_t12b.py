"""Generate the schema-v1 T-1.2b diagnostic candidate.

Pressure steps use the T-1.2 band method. The simulation models concurrency.
"""
from math import fsum

import yaml

from shoe_load import DUMP_TIMES_S, ROOT, calculation, read_yaml
from x1_calc import Accumulator, IDLE_KW, M3_S_TO_L_MIN, MOTOR_KW, PUMP_ETA, motions

BAND_UPPER_BAR = (20, 50, 100, 150, 200, 250, float("inf"))
SAMPLES = 4000
DUMP_S = max(DUMP_TIMES_S)


def return_rows(motion, drive):
    pressure_bar = motion.pressure_bar(0)
    pump_L_min = min(drive["pump_max_flow_L_min"], 600 * drive["motor_kW"] * drive["eta"] / pressure_bar)
    area_mm2 = motion.flow_area_m2 * 1e6
    speed_mm_s = motion.speed_m_s * 1000
    target_L_min = 60 * area_mm2 * speed_mm_s / 1e6
    accumulator = drive["accumulator"]
    boost_L_min = min(accumulator["max_flow_L_min"], max(0.0, target_L_min - pump_L_min))
    total_mm = motion.stroke_m * 1000
    boost_mm = total_mm
    if boost_L_min:
        delivered_L_min = min(target_L_min, pump_L_min + boost_L_min)
        speed_mm_s = delivered_L_min * 1e6 / (60 * area_mm2)
        boost_mm = min(total_mm, speed_mm_s * 60 * accumulator["usable_oil_L"] / boost_L_min)
    common = {"actuator": motion.actuator, "direction": "retract", "pressure_bar": pressure_bar,
              "regeneration": False, "dwell_s": 0, "use_accumulator": True}
    rows = [{**common, "name": "return 1", "stroke_mm": boost_mm, "speed_mm_s": speed_mm_s}]
    if boost_mm < total_mm:
        rows.append({**common, "name": "return 2", "stroke_mm": total_mm - boost_mm,
                     "speed_mm_s": "pump", "continues": True})
    return rows


def motion_rows(motion, drive):
    if motion.name == "return":
        return return_rows(motion, drive)
    groups = []
    points_m = {motion.stroke_m * i / SAMPLES for i in range(SAMPLES + 1)}
    if motion.marker_m:
        points_m.add(motion.marker_m)
    points_m = sorted(points_m)
    for start_m, end_m in zip(points_m, points_m[1:]):
        speed_m_s = motion.speed_at_m_s((start_m + end_m) / 2)
        speed_mm_s = speed_m_s * 1000
        target_flow_L_min = speed_m_s * motion.flow_area_m2 * M3_S_TO_L_MIN
        pressure_bar = max(motion.pressure_bar(start_m), motion.pressure_bar(end_m))
        flow_L_min = min(drive["pump_max_flow_L_min"], 600 * drive["motor_kW"] * drive["eta"] / pressure_bar)
        speed = speed_mm_s if target_flow_L_min <= flow_L_min else "pump"
        band = next(edge for edge in BAND_UPPER_BAR if pressure_bar <= edge)
        if groups and groups[-1][0:2] == [band, speed]:
            groups[-1][2] = end_m
            groups[-1][3] = max(pressure_bar, groups[-1][3])
        else:
            groups.append([band, speed, end_m, pressure_bar])
    rows = []
    for _, speed, end_m, pressure_bar in groups:
        stroke_mm = end_m * 1000 - fsum(r["stroke_mm"] for r in rows)
        row = {"name": f"{motion.name} {len(rows) + 1}", "actuator": motion.actuator,
               "stroke_mm": stroke_mm, "direction": "retract" if motion.mode == "retract" else "extend",
               "pressure_bar": pressure_bar, "speed_mm_s": speed, "regeneration": motion.mode == "regen",
               "dwell_s": 0}
        if rows:
            row["continues"] = True
        rows.append(row)
    return rows



def main():
    results, model, cylinder = calculation()
    params = read_yaml("design/params.t12.yaml")
    axis = results["axis_A"]
    dimensions = results["alternatives"]["A"]["dimensions"]
    params["description"] = (
        "T-1.2b D0 diagnostic candidate A with mechanically locked shoe. "
        f"Sequential 0.83 kg base cycle, 257 mm shoe parking, {DUMP_S:.2f} s dump.")
    params["main_cylinder"].update(stroke_mm=axis["main_installed_stroke_mm"],
                                   working_range_mm=axis["max_operating_travel_mm"])
    params["chamber"].update(length_mm=axis["body_length_mm"],
                             approach_stroke_mm=axis["approach_stroke_mm"],
                             ejection_overtravel_mm=axis["ejection_overtravel_mm"])
    params["precompaction"]["stroke_mm"] = dimensions["max_pre_cylinder_travel_mm"]
    params["precompaction"]["cylinder"]["stroke_mm"] = dimensions["pre_installed_stroke_mm"]
    drive = params["drive"]
    drive["eta"] = PUMP_ETA * (MOTOR_KW - IDLE_KW) / MOTOR_KW
    drive["slide_gate_cylinder"]["stroke_mm"] = results["gate"]["gate_installed_stroke_mm"]

    charge = Accumulator()
    drive["accumulator"] = {
        "usable_oil_L": 1000 * (charge.oil_at_m3(charge.high_bar) - charge.oil_at_m3(charge.low_bar)),
        "max_flow_L_min": charge.delivery_L_min, "min_delivery_pressure_bar": charge.low_bar,
        "charge_pressure_bar": charge.high_bar + 3, "round_trip_eta": 1.0,
    }
    phase_rows = []
    for name, motion in motions(model, cylinder, 90).items():
        rows = motion_rows(motion, drive)
        if name == "press":
            rows[-1].update(press=True, dwell_s=0.55)  # T-1.2 hold, unload and their switches.
        if name == "pre_up":
            rows[-1]["dwell_s"] = DUMP_S
        phase_rows.extend(rows)
    params["cycle"] = phase_rows

    (ROOT / "design/params.t12b.yaml").write_text(
        "# Generated by calc/T-1.2b/make_params_t12b.py.\n"
        "# Each precompaction move contains 12 mm of mechanical cam travel.\n"
        "# Chamber overtravel is for the nominal base dose. Working range covers all screened doses.\n"
        "# Sequential phases and accumulator recharge per schema v1.\n"
        + yaml.safe_dump(params, allow_unicode=True, sort_keys=False), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
