"""Stroke, package length, and filled mass changes using the T-1.3 volume model."""
from math import pi, sqrt

STEEL_KG_MM3 = 7.85e-6
OIL_KG_MM3 = 870e-9
ANCILLARY_FRACTION = .06
E_MPA = 210000.


def area_mm2(diameter_mm):
    return pi*diameter_mm**2/4


def stability(row, effective_mm, compressive_force_N):
    diameter_mm = row['rod_end_thread']['root_min_mm']
    yield_MPa = row['piston_and_rod_Rp02_min_MPa']
    slenderness = 4*effective_mm/diameter_mm
    transition = sqrt(2*pi*pi*E_MPA/yield_MPa)
    euler_MPa = pi*pi*E_MPA/slenderness**2
    johnson_MPa = yield_MPa*(1.-yield_MPa*slenderness**2/(4*pi*pi*E_MPA))
    critical_N = (johnson_MPa if slenderness < transition else euler_MPa)*area_mm2(diameter_mm)
    return dict(method='Johnson' if slenderness < transition else 'Euler',
                critical_force_N=critical_N, compressive_force_N=compressive_force_N,
                safety_factor=critical_N/compressive_force_N, root_diameter_mm=diameter_mm)


def cylinder_delta(row, working_add_mm, installed_add_mm, max_operating_add_mm, bore_mm=None):
    bore_mm = bore_mm or row['bore_mm']
    bore_delta_mm = bore_mm-row['bore_mm']
    old_cap_mm2, cap_mm2 = area_mm2(row['bore_mm']),area_mm2(bore_mm)
    old_OD_mm, barrel_OD_mm = row['barrel_OD_mm'],row['barrel_OD_mm']+bore_delta_mm
    barrel_length_mm = row['barrel_length_mm']+installed_add_mm
    tube_mm3 = ((area_mm2(barrel_OD_mm)-cap_mm2)*barrel_length_mm
                -(area_mm2(old_OD_mm)-old_cap_mm2)*row['barrel_length_mm'])
    rod_mm3 = area_mm2(row['rod_mm'])*installed_add_mm
    ties_mm3 = row['tie_rods']['n']*area_mm2(row['tie_rods']['diameter_mm'])*installed_add_mm
    piston_mm3 = (cap_mm2-old_cap_mm2)*row['piston_thickness_mm']
    oil_mm3 = cap_mm2*(row['stroke_installed_mm']+installed_add_mm)-old_cap_mm2*row['stroke_installed_mm']
    dry_add_kg = STEEL_KG_MM3*(tube_mm3+rod_mm3+ties_mm3+piston_mm3)*(1.+ANCILLARY_FRACTION)
    filled_add_kg = dry_add_kg+OIL_KG_MM3*oil_mm3
    lengths = {k:row[k]+installed_add_mm for k in (
        'barrel_length_mm','body_length_mm','rod_tip_retracted_length_mm')}
    lengths['rod_tip_extended_length_mm'] = row['rod_tip_extended_length_mm']+2*installed_add_mm
    # T-1.3 uses a conservatively extended effective length including guide compliance.
    effective_mm = row['column_effective_length_max_mm']+installed_add_mm
    buckling = stability(row,effective_mm,.1*row['design_pressure_bar']*cap_mm2)
    changed = dict(id=row['id'],stroke_working_mm=row['stroke_working_mm']+working_add_mm,
                   stroke_installed_mm=row['stroke_installed_mm']+installed_add_mm,**lengths,
                   column_effective_length_max_mm=effective_mm,
                   dry_mass_each_kg=row['dry_mass_each_kg']+dry_add_kg,
                   filled_mass_each_kg=row['filled_mass_each_kg']+filled_add_kg)
    if 'max_operating_stroke_mm' in row:
        changed['max_operating_stroke_mm'] = row['max_operating_stroke_mm']+max_operating_add_mm
    if bore_delta_mm:
        changed.update(bore_mm=bore_mm, barrel_OD_mm=barrel_OD_mm,cap_area_mm2=cap_mm2,
                       annulus_area_mm2=cap_mm2-area_mm2(row['rod_mm']))
    changed = {key:value for key,value in changed.items() if key=="id" or value!=row.get(key)}
    return changed,dict(count=row['n'], delta_dry_each_kg=dry_add_kg,
                        delta_filled_each_kg=filled_add_kg, stability=buckling)


def opening(bore_mm, rod_mm, moving_kg, assumptions, main_area_mm2, residual_N=201000.,
            accel_m_s2=20., speed_m_s=.60):
    cap_mm2 = area_mm2(bore_mm)
    annulus_mm2 = cap_mm2-area_mm2(rod_mm)
    hydro_N = .1*assumptions['pressure_main_after_decompression_bar']*main_area_mm2
    idle_N = assumptions['noncontact_drag_N']+moving_kg*(9.81+accel_m_s2)
    force_N = idle_N+assumptions['friction_coefficient']*(residual_N+hydro_N)
    available_N = .1*(assumptions['drive_eta']*300.*annulus_mm2-
                       assumptions['assumed_gate_return_pressure_bar']*cap_mm2)
    speed_mm_s = 1000.*speed_m_s
    return dict(required_N=force_N, available_N=available_N, safety_factor=available_N/force_N,
                residual_product_N=residual_N, residual_hydraulic_N=hydro_N, moving_mass_kg=moving_kg,
                cap_mm2=cap_mm2,annulus_mm2=annulus_mm2,
                acceleration_m_s2=accel_m_s2, command_speed_m_s=speed_m_s,
                retract_flow_L_min=annulus_mm2*speed_mm_s*60.e-6,
                extend_flow_L_min=cap_mm2*speed_mm_s*60.e-6,
                maximum_residual_product_for_2x_N=(available_N/2-idle_N)/assumptions['friction_coefficient']-hydro_N)

