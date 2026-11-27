"""Mass ledger and axial thrust bearing screen."""

from math import fsum, pi

from hand import DENSITY_KG_MM3, moving_pair_kg
from loads import read_json

MACHINE_LIMIT_KG = 5000.
STATION_LIMIT_KG = 230.


def steel_kg(volume_mm3):
    return DENSITY_KG_MM3 * volume_mm3


def pair_kg(x_mm, y_mm, z_mm):
    return steel_kg(2. * x_mm * y_mm * z_mm)


def axial_stops(friction_315_N, transverse_bore_e_mm):
    y0_mm, y1_mm = 172., 203.
    dz_mm = 220.
    centre_mm = (y0_mm + y1_mm) / 2.
    area_mm2 = (y1_mm - y0_mm) * dz_mm
    high_N = friction_315_N / 2. * (1. + abs(transverse_bore_e_mm) / centre_mm)
    return {"x_mm": [295., 349.], "abs_y_mm": [y0_mm, y1_mm],
            "z_mm": [-dz_mm / 2., dz_mm / 2.], "net_contact_area_mm2": area_mm2,
            "min_315_N": friction_315_N - high_N, "max_315_N": high_N,
            "mean_300_MPa": high_N * 300. / 315. / area_mm2, "screen_300_MPa": 80.,
            "clearance_to_pocket_y_mm": y0_mm - 340.2/2.,
            "upper_thrust_couple_315_Nmm": (dz_mm / 4. - 30. * 150. / 210.) * friction_315_N / 2.,
            "mass_delta_kg": pair_kg(y1_mm-y0_mm, dz_mm, 54.) - pair_kg(29., 190., 54.)}


def trial(reference, option, axial, band_mass_kg, casting_removal_kg=0.):
    old = reference["mass"]
    machine = [r for r in old["machine_rows"] if r["part"] != "replacement_chamber"]
    chamber = [dict(part=k, **v) for k, v in old["chamber_rows"].items()]
    deltas = [
        {"part": "front_moving_pair_net",
         "mass_kg": moving_pair_kg(option) - old["chamber_rows"]["front_keys"]["mass_kg"],
         "source": "hand.py moving envelopes compared with T-2.2h keys"},
        {"part": "axial_rail_pair_net", "mass_kg": axial["mass_delta_kg"],
         "source": "mass.py axial_stops, 2 x 54 x (31 x 220 - 29 x 190) mm3"},
        {"part": "wider_liner_and_ring", "mass_kg": 0.,
         "source": "Identical exterior and working bore, full volume of ring plus backing"},
        {"part": "circular_band_trial", "mass_kg": band_mass_kg,
         "source": "preload.py circular collar, before round interface or joints"},
    ]
    if option.kind == "nose":
        deltas.append({"part": "socket_void_gross_credit",
                       "mass_kg": -pair_kg(option.bearing_length_mm, option.width_mm, option.height_mm),
                       "source": "hand.py gross slot, optimistic full volume, no rounding"})
    if casting_removal_kg:
        assert option.kind == "nose"
        deltas.append({"part": "old_front_casting_gross_credit", "mass_kg": -casting_removal_kg,
                       "source": "fea/volume.json, gross trimmed geometry at 12 mm mesh"})
    total_kg = fsum(r["mass_kg"] for r in (*machine, *chamber, *deltas))
    return {"fixed_machine_rows": machine, "reference_chamber_rows": chamber,
            "delta_rows": deltas, "machine_before_station_kg": total_kg,
            "station_reduction_kg": total_kg - MACHINE_LIMIT_KG,
            "mass_margin_kg": MACHINE_LIMIT_KG + STATION_LIMIT_KG - total_kg,
            "unquantified": ["removed front casting and wear lands where geometrically possible",
                             "new clevis body or nose actuator guides and linings",
                             "round interface or local axial stress relief"]}


def collar_kg(inner_r_mm, outer_r_mm, length_mm):
    return steel_kg(pi * (outer_r_mm**2 - inner_r_mm**2) * length_mm)

