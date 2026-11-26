"""Recalculate reference T-1.4b duty with the candidate travelling mass."""
import argparse
from dataclasses import replace
from math import pi
from pathlib import Path

from drive import ROOT, configuration, evaluated_run, get_inputs, scenario, source_data, write_json


def evaluate(new_parts_kg, added_opening_drag_N=0.):
    data, inputs = source_data(), get_inputs()
    config = data["engineering_inputs"]
    rows = []
    for cap_kW in (config["shaft_limit_kW"],36.):
        model,cylinder,settings,_,_ = configuration(inputs,data=data,limit_kW=cap_kW)
        for density in (90,160):
            reference,_ = scenario(inputs,"base",density,.83,None,model.gate_speed_m_s,model.losses_bar)
            base = replace(model,in_die_kg_m3=reference.in_die_kg_m3,overtravel_m=reference.overtravel_m,
                           pre_travel_m=reference.pre_travel_m)
            changed = replace(base,gate_mass_kg=base.gate_mass_kg+new_parts_kg,
                              gate_added_weight_N=new_parts_kg*9.81,
                              gate_added_opening_drag_N=added_opening_drag_N)
            cycles = [evaluated_run(m,cylinder,settings,data,"realistic",density,.64,None,
                                     (.0025,.00125,.000625,.0003125)) for m in (base,changed)]
            row = {"shaft_setting_kW":cap_kW,"bulk_density_kg_m3":density,
                   "cycle_T14b_s":cycles[0]["cycle_s"],"cycle_T17b_s":cycles[1]["cycle_s"],
                   "delta_cycle_s":cycles[1]["cycle_s"]-cycles[0]["cycle_s"],
                   "peak_T17b_kW":cycles[1]["shaft_peak_with_tolerance_kW"],
                   "rms_T17b_kW":cycles[1]["shaft_rms_with_tolerance_kW"]}
            rows.append(row)
            print(row,flush=True)
    mass_kg = model.gate_mass_kg + new_parts_kg
    cap_mm2, annulus_mm2 = pi*80**2/4, pi*(80**2-45**2)/4
    speed_m_s, accel_m_s2 = .6, config["gate_accel_m_s2"]
    # Apply the adverse gravity sign in both directions for a conservative pressure bound.
    return {
        "cycle_comparison":rows,"added_moving_mass_kg":new_parts_kg,"reference_moving_mass_kg":model.gate_mass_kg,"moving_mass_kg":mass_kg,
        "drive_bore_mm":80.,"drive_rod_mm":45.,"velocity_m_s":speed_m_s,"acceleration_m_s2":accel_m_s2,
        "ramp_s":speed_m_s/accel_m_s2,"ramp_distance_mm":500*speed_m_s**2/accel_m_s2,
        "opening_force_with_gravity_and_inertia_N":10000+added_opening_drag_N+mass_kg*(9.81+accel_m_s2),
        "closing_force_with_gravity_and_inertia_N":8000+mass_kg*(9.81+accel_m_s2),
        "opening_pressure_mechanical_bar":10*(10000+added_opening_drag_N+mass_kg*(9.81+accel_m_s2))/annulus_mm2,
        "closing_pressure_mechanical_bar":10*(8000+mass_kg*(9.81+accel_m_s2))/cap_mm2,
        "opening_supply_L_min":.06*speed_m_s*annulus_mm2,"closing_supply_L_min":.06*speed_m_s*cap_mm2,
        "extra_opening_drag_N":added_opening_drag_N,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("added_moving_mass_kg",type=float)
    parser.add_argument('--opening-drag-N',type=float,default=0.)
    parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent.parent/'cycle_comparison.json')
    args = parser.parse_args()
    write_json(args.out,evaluate(args.added_moving_mass_kg,args.opening_drag_N))

