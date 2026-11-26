"""Machine mass increments over the T-1.7c free-channel budget."""
from math import fsum,pi


def steel_kg(volume_mm3):
    return volume_mm3*7.85e-6


def rounded_area_mm2(width_mm,height_mm,radius_mm):
    return width_mm*height_mm-(4-pi)*radius_mm**2


def plate_kg(thickness_mm, gate_travel_mm, wing_mm=0., shoulder='side'):
    """Integrate the base perforated section and the tapered upstream ribs."""
    from math import sqrt
    from scipy.integrate import quad

    height_mm = 212.+gate_travel_mm-75.
    base_kg = steel_kg((rounded_area_mm2(260.,height_mm,5.)-
                        rounded_area_mm2(158.,65.,3.))*thickness_mm)
    if not wing_mm:
        return base_kg
    if shoulder == 'side':
        def strip_mm2(x_mm):
            t = min(1., (x_mm-80.)/45.)
            height = height_mm
            if x_mm>125.:
                height -= 2.*(5.-sqrt(25.-(x_mm-125.)**2))
            return t*t*(3.-2.*t)*height
        volume_mm3 = 2.*wing_mm*quad(strip_mm2,80.,130.,points=[125.])[0]
    else:
        # Bounding volume for the central-section step screen. The concept has
        # independent collision and relief requirements.
        volume_mm3 = wing_mm*260.*(height_mm-65.)
    return base_kg+steel_kg(volume_mm3)


def update_budget(baseline, geometry, plate_mass_kg, cylinder_deltas):
    plate_delta_kg = plate_mass_kg-plate_kg(38.,75.)
    columns_delta_kg = -steel_kg(4*pi/4*70.**2*(geometry['column_shortening_mm']-245.))
    rows = [
        dict(item='Оконная плита и рёбра',delta_kg=plate_delta_kg,source='Интеграл сечения R5 − окно R3, mass_budget.py'),
        dict(item='Четыре гладких участка колонн Ø70',delta_kg=columns_delta_kg,source='frame.t17.yaml и layout.py'),
    ]
    for delta in cylinder_deltas:
        rows.append(dict(item=delta['id'],delta_kg=delta['count']*delta['delta_filled_each_kg'],
                         source='Объёмы гильзы, штока, стяжек, масла по T-1.3 и design/cylinders.t16.yaml'))
    delta_kg = fsum(row['delta_kg'] for row in rows)
    nominal_kg = baseline['nominal_kg']+delta_kg
    lower_kg = baseline['lower_kg']+delta_kg
    upper_kg = baseline['upper_kg']+delta_kg
    return dict(delta_rows=rows, delta_kg=delta_kg, baseline_kg=baseline['nominal_kg'],
                baseline_source='calc/T-1.7c/results.json / mass',
                uncertainty_source='Вилка T-1.7c с переносом расчётной дельты объёма. Карманы под рёбра без вычета массы.',
                nominal_kg=nominal_kg, lower_kg=lower_kg, upper_kg=upper_kg,
                margin_to_4850_kg=4850.-nominal_kg, margin_to_5000_kg=5000.-nominal_kg,
                upper_margin_to_5000_kg=5000.-upper_kg)

