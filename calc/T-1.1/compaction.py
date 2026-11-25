"""Reproduce the T-1.1 cold wood-sawdust screening calculation offline."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import accumulate
from math import exp, expm1, log, pi, sqrt
from pathlib import Path
import json

import numpy as np
from scipy.optimize import brentq, least_squares
import yaml

import x1_calc as x1


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCENARIOS = ("low", "base", "high")
SOURCE_FILE = HERE / "sources.yaml"


def average_over_face(K, mu, length_over_diameter):
    q = 4 * K * mu * length_over_diameter
    return -expm1(-q) / q if q else 1.0


def pressure_ratios(K, mu, length_mm, hydraulic_diameter_mm):
    q = 4 * K * mu * length_mm / hydraulic_diameter_mm
    return {
        "length_mm": length_mm,
        "average_over_face": average_over_face(K, mu, length_mm / hydraulic_diameter_mm),
        "gate_over_face": exp(-q),
    }


def loaded_specimen_aspect(source_id, point, source, density, axial, assumptions):
    diameter_mm = source["die"]["diameter_mm"]
    if source_id == "zhong1991":
        initial = source["points"][0]["rho_loaded_kg_m3"]
        return assumptions["zhong_initial_fill_H_over_D"] * initial / density
    if source_id == "li2000":
        return source["die"]["sample_relaxed_height_mm_approx"] / (1 + axial) / diameter_mm
    if source_id == "krizan2015":
        return assumptions["krizan_loaded_H_over_D"]
    mass_g = point.get("sample_mass_g", source["die"].get("sample_mass_g"))
    if mass_g is None:
        raise ValueError(f"Missing specimen mass for {source_id}")
    return mass_g * 1e6 / (density * pi * diameter_mm**3 / 4)


def external_density(point):
    relaxed = point["rho_relaxed_kg_m3"]
    if point.get("density_basis") == "dry":
        relaxed /= 1 - point["moisture_pct"] / 100
    return relaxed


@dataclass(frozen=True)
class Recovery:
    axial_immediate: float
    area_growth: float
    early_knots: tuple
    stable_knots: tuple
    unload_volume_ratio: float

    @classmethod
    def from_sources(cls, data):
        a, s = data["assumptions"], data["sources"]
        pairs = defaultdict(list)
        for point in s["krizan2015"]["points"]:
            pairs[point["rho_relaxed_kg_m3"]].append(point["rho_stabilized_kg_m3"])
        early = (0, *sorted(pairs))
        stable = (0, *(sum(pairs[rho]) / len(pairs[rho]) for rho in early[1:]))
        horabik = s["horabik2023"]
        return cls(a["springback_axial_immediate"], a["springback_area"], early, stable,
                   horabik["points"][0]["rho_loaded_kg_m3"]
                   / horabik["observations"]["rho_unloaded_in_die_kg_m3"])

    @property
    def volume_ratio(self):
        return (1 + self.axial_immediate) * (1 + self.area_growth)

    def stabilized_density(self, early_density):
        extra = max(0, early_density - self.early_knots[-1])
        return float(np.interp(early_density, self.early_knots, self.stable_knots)) + extra

    def early_from_stabilized(self, stabilized_density):
        extra = max(0, stabilized_density - self.stable_knots[-1])
        return float(np.interp(stabilized_density, self.stable_knots, self.early_knots)) + extra

    def loaded_density(self, density, stage):
        if stage == "loaded":
            return density
        if stage == "unloaded_in_die":
            return density * self.unload_volume_ratio
        if stage == "stabilized":
            density = self.early_from_stabilized(density)
        return density * self.volume_ratio

    def density_at_stage(self, loaded_density, stage):
        if stage == "loaded":
            return loaded_density
        if stage == "unloaded_in_die":
            return loaded_density / self.unload_volume_ratio
        early_density = loaded_density / self.volume_ratio
        if stage == "stabilized":
            return self.stabilized_density(early_density)
        return early_density

    def stabilized_axial(self, loaded_density):
        stable = self.density_at_stage(loaded_density, "stabilized")
        return loaded_density / (stable * (1 + self.area_growth)) - 1


@dataclass(frozen=True)
class Observation:
    source_id: str
    density_kg_m3: float
    bulk_kg_m3: float
    face_MPa: float
    average_MPa: float
    aspect: float
    direct: bool
    where: str


def make_oak_moisture_endpoint(source, moisture_pct):
    dry = {p["p_MPa"]: p for p in source["points"]
           if p["material"] == "oak" and p["moisture_pct"] == 8.9}
    wet = {p["p_MPa"]: p for p in source["points"]
           if p["material"] == "oak" and p["moisture_pct"] == 12.7}
    for pressure_MPa, lower in dry.items():
        upper = wet[pressure_MPa]
        fraction = (moisture_pct - lower["moisture_pct"]) / (upper["moisture_pct"] - lower["moisture_pct"])
        yield {
            "p_MPa": pressure_MPa, "moisture_pct": moisture_pct,
            "rho_relaxed_kg_m3": (1 - fraction) * external_density(lower)
                                + fraction * external_density(upper),
            "where": "Interpolation of Li & Liu Table 1 oak series (envelope only)",
            "basis": "interpolated",
        }


def observations(data, recovery):
    a, p, sources = data["assumptions"], data["project"], data["sources"]
    direct_high = sources["horabik2023"]["points"][0]
    ceiling = direct_high["rho_loaded_kg_m3"] + direct_high["rho_sd_kg_m3"]
    fit_rows = []
    exclusions = defaultdict(Counter)
    for source_id, source in sources.items():
        if source["fit_role"] not in {"loaded", "convert_relaxed"}:
            continue
        for point in source["points"]:
            if not point.get("fit", True) or point["p_MPa"] == 0:
                exclusions[source_id]["validation_or_zero_pressure"] += 1
                continue
            direct = "rho_loaded_kg_m3" in point
            density = (point["rho_loaded_kg_m3"] if direct
                       else recovery.loaded_density(external_density(point), "immediate"))
            if not direct and density > ceiling:
                exclusions[source_id]["converted_above_measured_range"] += 1
                continue
            aspect = loaded_specimen_aspect(source_id, point, source, density, recovery.axial_immediate, a)
            average = point["p_MPa"] * average_over_face(a["wall_K"]["base"], a["wall_mu"]["base"], aspect)
            bulk = p["bulk_kg_m3"]["base"]
            if source_id == "horabik2023":
                values = source["table3_initial_bulk_kg_m3"].values()
                bulk = sum(values) / len(values)
            if source_id == "zhong1991":
                bulk = source["points"][0]["rho_loaded_kg_m3"]
            if source_id == "spirchez2025":
                bulk = source["table1_bulk_kg_m3"][str(point["fraction_mm"][0])]
            fit_rows.append(Observation(source_id, density, bulk, point["p_MPa"], average, aspect,
                                        direct, point["where"]))
    return fit_rows, {key: dict(value) for key, value in exclusions.items()}


@dataclass(frozen=True)
class PressureModel:
    name: str
    scale_MPa: float
    exponent: float
    rho_limit_kg_m3: float
    reference_bulk_kg_m3: float
    bulk_transition_kg_m3: float

    def mean_MPa(self, density_kg_m3, bulk_kg_m3):
        delta_kg_m3 = max(0.0, density_kg_m3 - self.reference_bulk_kg_m3)
        onset = min(1.0, max(0.0, (density_kg_m3 - bulk_kg_m3)
                                  / (self.bulk_transition_kg_m3 - bulk_kg_m3)))
        if self.name == "power":
            x = delta_kg_m3 / 1000
        else:
            x = log(1 + delta_kg_m3 / (self.rho_limit_kg_m3 - density_kg_m3))
        return self.scale_MPa * x**self.exponent * onset * (2 - onset)


def fit_models(rows, data):
    a, p = data["assumptions"], data["project"]
    counts = Counter(item.source_id for item in rows)
    results = {}
    for name in ("power", "generalized_heckel"):
        def model(parameters):
            return PressureModel(name, exp(parameters[0]), float(parameters[1]), a["heckel_limit_kg_m3"],
                                 p["bulk_kg_m3"]["base"], a["bulk_transition_kg_m3"])

        def loss(parameters):
            fit = model(parameters)
            return [
                log(fit.mean_MPa(r.density_kg_m3, r.bulk_kg_m3) / r.average_MPa)
                / sqrt(counts[r.source_id])
                for r in rows
            ]

        solution = least_squares(loss, (log(60), 2), bounds=([-20, 0.5], [20, 12]),
                                 ftol=1e-12, xtol=1e-12, gtol=1e-12)
        if not solution.success:
            raise RuntimeError(solution.message)
        fit = model(solution.x)
        errors = defaultdict(list)
        for r in rows:
            predicted = fit.mean_MPa(r.density_kg_m3, r.bulk_kg_m3)
            errors[r.source_id].append((predicted - r.average_MPa, log(predicted / r.average_MPa)))
        by_source = {
            key: {
                "n_fit": len(error),
                "rmse_mean_pressure_MPa": sqrt(sum(pair[0]**2 for pair in error) / len(error)),
                "bias_mean_pressure_MPa": sum(pair[0] for pair in error) / len(error),
                "rmse_log_pressure": sqrt(sum(pair[1]**2 for pair in error) / len(error)),
            }
            for key, error in errors.items()
        }
        results[name] = {
            "model": fit,
            "source_errors": by_source,
            "source_balanced_rmse_log_pressure": sqrt(np.mean(np.square([
                v["rmse_log_pressure"] for v in by_source.values()
            ]))),
        }
    return results


@dataclass(frozen=True)
class Anchor:
    source: str
    where: str
    moisture_pct: float
    stage: str
    density_kg_m3: float
    loaded_kg_m3: float
    lab_face_MPa: float
    rev_face_MPa: float
    basis: str = "measured"


def envelope_anchors(data, recovery, curve, fit_rows):
    a, p, sources = data["assumptions"], data["project"], data["sources"]
    anchors = [
        Anchor(r.source_id, r.where, sources[r.source_id]["moisture_pct"], "loaded",
               r.density_kg_m3, r.density_kg_m3, r.face_MPa,
               r.average_MPa / curve.transfer(r.density_kg_m3))
        for r in fit_rows if r.source_id == "zhong1991"
    ]
    horabik = sources["horabik2023"]
    unload = horabik["observations"]
    for source_id in ("li2000", "krizan2015", "horabik2023", "spirchez2025"):
        source = sources[source_id]
        points = source["points"]
        if source_id == "li2000":
            points = [*points, *make_oak_moisture_endpoint(source, p["moisture_pct_range"][1])]
        if source_id == "horabik2023":
            points = [*points, {"p_MPa": points[0]["p_MPa"],
                                "rho_unloaded_in_die_kg_m3": unload["rho_unloaded_in_die_kg_m3"],
                                "where": "Results p. 55 (unloading in the mould)"}]
        for point in points:
            moisture = point.get("moisture_pct", source["moisture_pct"])
            if not p["moisture_pct_range"][0] <= moisture <= p["moisture_pct_range"][1]:
                continue
            stages = {
                "loaded": point.get("rho_loaded_kg_m3"),
                "unloaded_in_die": point.get("rho_unloaded_in_die_kg_m3"),
                "immediate": external_density(point) if "rho_relaxed_kg_m3" in point else None,
                "stabilized": point.get("rho_stabilized_kg_m3"),
            }
            for stage, density in stages.items():
                if density is None:
                    continue
                # The paired Kri?an geometries are unreported. Horabik used a known dose.
                # In both cases use the inferred loaded specimen geometry for wall transfer.
                loaded = recovery.loaded_density(density, stage)
                aspect = loaded_specimen_aspect(source_id, point, source, loaded, recovery.axial_immediate, a)
                lab_pressure = point["p_MPa"]
                mean_pressure = lab_pressure * average_over_face(a["wall_K"]["base"], a["wall_mu"]["base"], aspect)
                anchors.append(Anchor(source_id, point["where"], moisture, stage, density, loaded,
                                      lab_pressure, mean_pressure / curve.transfer(loaded),
                                      point.get("basis", "measured")))
    return anchors


def make_envelope(anchors, curve, recovery):
    # Work on early-exit equivalent densities. Transform to loaded density only
    # for use in the constitutive law and in the X-1 hydraulic simulation.
    bulk = curve.data["project"]["bulk_kg_m3"]["base"]
    slope = curve.data["assumptions"]["envelope_min_density_slope_kg_m3_per_MPa"]
    grouped = {0.0: [bulk / recovery.volume_ratio]}
    for anchor in anchors:
        pressures = (anchor.rev_face_MPa,) if anchor.source == "zhong1991" else (
            anchor.lab_face_MPa, anchor.rev_face_MPa)
        early = anchor.loaded_kg_m3 / recovery.volume_ratio
        for face_MPa in pressures:
            grouped.setdefault(face_MPa, []).append(early)
    face_MPa = sorted(grouped)
    minima = [min(grouped[p]) - slope * p for p in face_MPa]
    maxima = [max(grouped[p]) - slope * p for p in face_MPa]
    lower = list(accumulate(reversed(minima), min))[::-1]
    upper = list(accumulate(maxima, max))
    return {
        case: [(p, v + slope * p) for p, v in zip(face_MPa, bound)]
        for case, bound in (("low", upper), ("high", lower))
    }


@dataclass(frozen=True)
class ProjectCurve:
    fit: PressureModel
    data: dict
    recovery: Recovery
    envelope: dict | None = None

    def transfer(self, density, *, pre=False):
        p, a = self.data["project"], self.data["assumptions"]
        width = p["width_mm"]
        height = p["feed_length_mm"] if pre else p["height_mm"]
        section_mm2 = width * height
        diameter_mm = 2 * section_mm2 / (width + height)
        length_mm = p["dose_kg"] * 1e9 / (section_mm2 * density)
        return average_over_face(a["wall_K"]["base"], a["wall_mu"]["base"], length_mm / diameter_mm)

    def base_face(self, density, bulk=None):
        if bulk is None:
            bulk = self.data["project"]["bulk_kg_m3"]["base"]
        return self.fit.mean_MPa(density, bulk) / self.transfer(density)

    def empirical_face(self, density, case):
        knots = self.envelope[case]
        pressures, external_densities = zip(*knots)
        early = density / self.recovery.volume_ratio
        if early > external_densities[-1]:
            last_loaded = external_densities[-1] * self.recovery.volume_ratio
            return pressures[-1] + self.base_face(density) - self.base_face(last_loaded)
        return float(np.interp(early, external_densities, pressures))

    def face_MPa(self, density, case, *, pre=False, bulk=None):
        face = self.base_face(density, bulk)
        if case != "base":
            choose = min if case == "low" else max
            face = choose(face, self.empirical_face(density, case))
        if pre:
            return face * self.transfer(density) / self.transfer(density, pre=True)
        return face


@dataclass(frozen=True)
class CycleModel(x1.Model):
    curve: ProjectCurve = None
    case: str = "base"

    def axial_pressure_Pa(self, density_kg_m3):
        return self.curve.face_MPa(density_kg_m3, self.case) * 1e6

    def pre_force_N(self, travel_m, bulk_kg_m3):
        height_m = self.height_m + self.pre_travel_m - travel_m
        density = self.dose_kg / (self.pre_section_m2 * height_m)
        return self.pre_section_m2 * self.curve.face_MPa(density, self.case, pre=True, bulk=bulk_kg_m3) * 1e6


def find_density(pressure, face_MPa, upper, bulk):
    if face_MPa(upper) < pressure:
        return None
    return brentq(lambda density: face_MPa(density) - pressure, bulk, upper, xtol=1e-9)


def density_requirement(curve, case, max_density, *, bulk=None, axial_stabilized=None):
    p = curve.data["project"]
    target = p["target_relaxed_kg_m3"]
    recovery = curve.recovery
    densities = {stage: recovery.loaded_density(target, stage) for stage in ("immediate", "stabilized")}
    if axial_stabilized is not None:
        densities["stabilized"] = target * (1 + axial_stabilized) * (1 + recovery.area_growth)
    estimates = {}
    for stage, density in densities.items():
        pressure = curve.face_MPa(density, case, bulk=bulk) if density <= max_density else None
        estimates[stage] = {
            "loaded_density_kg_m3": density,
            "face_MPa": pressure,
            "main_supply_bar": (x1.supply_bar(x1.MAIN, pressure * p["width_mm"] * p["height_mm"], "extend")
                                if pressure is not None else None),
            "margin_to_nominal_MPa": p["nominal_face_MPa"] - pressure if pressure is not None else None,
        }
    return estimates


def stroke_above_threshold_mm(sequence, threshold_bar):
    press = sequence["press"]
    if press.pressure_bar(press.stroke_m) <= threshold_bar:
        return 0.0
    if press.pressure_bar(0) >= threshold_bar:
        return press.stroke_m * 1000
    crossing_m = brentq(lambda position: press.pressure_bar(position) - threshold_bar, 0, press.stroke_m)
    return (press.stroke_m - crossing_m) * 1000


def make_cycle_model(curve, case, density, face_MPa, *, axial_stabilized=None):
    p = curve.data["project"]
    if axial_stabilized is None:
        axial_stabilized = curve.recovery.stabilized_axial(density)
    return CycleModel(
        dose_kg=p["dose_kg"], width_m=p["width_mm"] / 1000, height_m=p["height_mm"] / 1000,
        feed_length_m=p["feed_length_mm"] / 1000,
        nominal_N=face_MPa * p["width_mm"] * p["height_mm"],
        in_die_kg_m3=density, axial_recovery=axial_stabilized,
        curve=curve, case=case,
    )


def run_cycle(model, project, dt_s=x1.DT_S):
    if project["accumulator_L"] != x1.Accumulator().shell_L:
        raise ValueError("Project accumulator size differs from the X-1 copy")
    return x1.simulate(model, max_L_min=project["pump_L_min"], overlap=True, accumulator=True,
                       feed_s=project["feed_s"], bulk_kg_m3=project["bulk_kg_m3"]["base"], dt_s=dt_s)


def target_cycle(curve, case, target, *, axial_stabilized=None, apply_concept_stop=False):
    p = curve.data["project"]
    face = target["face_MPa"]
    if face is None:
        return {"feasible": False, "reason": "density_domain"}
    if apply_concept_stop and face > p["nominal_face_MPa"]:
        return {"feasible": False, "reason": "base_target_triggers_concept_stop"}
    model = make_cycle_model(curve, case, target["loaded_density_kg_m3"], face,
                             axial_stabilized=axial_stabilized)
    return run_cycle(model, p)


def project_consequences(curve, case, limit_kg_m3):
    p = curve.data["project"]
    recovery = curve.recovery
    def face(density):
        return curve.face_MPa(density, case)

    bulk = p["bulk_kg_m3"]["base"]
    density = find_density(p["nominal_face_MPa"], face, limit_kg_m3, bulk)
    operating_density = density if density is not None else limit_kg_m3
    face_at_end = p["nominal_face_MPa"] if density is not None else face(operating_density)
    model = make_cycle_model(curve, case, operating_density, face_at_end)
    sequence = x1.motions(model, x1.MAIN, bulk)
    target = density_requirement(curve, case, limit_kg_m3)
    return {
        "target": target,
        "face_at_1000_loaded_MPa": face(p["loaded_comparison_kg_m3"]),
        "pre_end_density_kg_m3": model.pre_density_kg_m3,
        "pre_force_90_N": model.pre_force_N(model.pre_travel_m, bulk),
        "nominal_state": "at_nominal_face" if density is not None else "limited_to_density_domain",
        "operating_face_MPa": face_at_end,
        "operating_loaded_kg_m3": operating_density,
        "operating_immediate_kg_m3": recovery.density_at_stage(operating_density, "immediate"),
        "operating_stabilized_kg_m3": recovery.density_at_stage(operating_density, "stabilized"),
        "die_length_mm": model.die_length_m * 1000,
        "immediate_length_mm": model.die_length_m * (1 + recovery.axial_immediate) * 1000,
        "stabilized_length_mm": model.die_length_m * (1 + model.axial_recovery) * 1000,
        "stabilized_axial_recovery_fraction": model.axial_recovery,
        "work_from_pre_kJ": x1.integrated_work_J(model.dose_kg, model.axial_pressure_Pa,
                                                model.pre_density_kg_m3, operating_density) / 1000,
        "stroke_above_120_bar_mm": stroke_above_threshold_mm(sequence, p["pressure_threshold_bar"]),
        "stroke_in_cap_mode_mm": 1000 * sequence["press"].stroke_m,
        "cycle": run_cycle(model, p),
        "cycle_at_stabilized_target": target_cycle(curve, case, target["stabilized"],
                                                   apply_concept_stop=case == "base"),
    }


def excluded_residuals(data, fit):
    """Evaluate independent published observations with their stated state/geometry."""
    a = data["assumptions"]
    s = data["sources"]
    bulk = data["project"]["bulk_kg_m3"]["base"]
    diagnostic = {}
    for source_id, source in s.items():
        if source["fit_role"] != "validation":
            continue
        observed, predicted = [], []
        for point in source["points"]:
            if point["p_MPa"] <= 0:
                continue
            diameter = source["die"]["diameter_mm"]
            if "height_loaded_mm" in point:
                length_mm = point["height_loaded_mm"]
                mass_g = source["die"]["specimen_mass_g"][point["material"]]
                density = mass_g * 1e6 / (pi * diameter**2 / 4 * length_mm)
                initial = bulk
            else:
                density = point["rho_loaded_kg_m3"]
                mass_g = source["die"]["sample_mass_g"]
                length_mm = mass_g * 1e6 / (pi * diameter**2 / 4 * density)
                initial = source["points"][0]["rho_loaded_kg_m3"]
            ratio = average_over_face(a["wall_K"]["base"], a["wall_mu"]["base"], length_mm / diameter)
            observed.append(point["p_MPa"])
            predicted.append(fit.mean_MPa(density, initial) / ratio)
        diagnostic[source_id] = {
            "n_validation": len(observed),
            "rmse_face_MPa": sqrt(np.mean(np.square(np.array(predicted) - np.array(observed)))),
        }
    return diagnostic


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def nominal_recovery_sensitivity(curve, limit_kg_m3, base):
    p = curve.data["project"]
    density = base["operating_loaded_kg_m3"]
    face = base["operating_face_MPa"]
    area = curve.recovery.area_growth
    cases = {}
    for axial in curve.data["assumptions"]["cycle_axial_recovery_fractions"]:
        requirements = density_requirement(curve, "base", limit_kg_m3, axial_stabilized=axial)
        model = make_cycle_model(curve, "base", density, face, axial_stabilized=axial)
        cases[str(axial)] = {
            "axial_stabilized_fraction": axial,
            "stabilized_density_at_nominal_kg_m3": density / ((1 + axial) * (1 + area)),
            "stabilized_target": requirements["stabilized"],
            "cycle_at_stabilized_target": target_cycle(curve, "base", requirements["stabilized"],
                                                       axial_stabilized=axial),
            "cycle_at_nominal": run_cycle(model, p),
        }
    return cases


def coverage_checks(anchors, curve, upper):
    checks = []
    for anchor in anchors:
        lab = anchor.source != "zhong1991"
        pressures = {"rev_face_MPa": anchor.rev_face_MPa}
        if lab:
            pressures["lab_face_MPa"] = anchor.lab_face_MPa
        density = anchor.loaded_kg_m3
        lower_MPa = curve.face_MPa(density, "low")
        upper_MPa = curve.face_MPa(density, "high")
        covered = density <= upper and all(
            lower_MPa - 1e-8 <= p <= upper_MPa + 1e-8 for p in pressures.values()
        )
        checks.append({**vars(anchor), "bound_face_MPa": [lower_MPa, upper_MPa], "covered": covered})
    assert all(check["covered"] for check in checks)
    return checks


def densities_at_face(curve, pressure, case, upper):
    bulk = curve.data["project"]["bulk_kg_m3"]["base"]
    density = find_density(pressure, lambda rho: curve.face_MPa(rho, case), upper, bulk)
    if density is None:
        return None
    return {f"rho_{stage}_kg_m3": curve.recovery.density_at_stage(density, stage)
            for stage in ("loaded", "immediate", "stabilized")}


def moisture_endpoints(anchors, base_curve, upper):
    p = base_curve.data["project"]
    output = {}
    for moisture in p["moisture_pct_range"]:
        matching = [row for row in anchors if row.moisture_pct == moisture]
        recovery = base_curve.recovery
        curve = ProjectCurve(base_curve.fit, base_curve.data, recovery,
                             make_envelope(matching, base_curve, recovery))
        output[str(moisture)] = {
            "basis": "Screening bounds with moisture-specific anchors around the same pooled fit.",
            "anchor_sources": sorted({row.source for row in matching}),
            "at_nominal": {case: densities_at_face(curve, p["nominal_face_MPa"], case, upper) for case in SCENARIOS},
            "target": {case: density_requirement(curve, case, upper) for case in SCENARIOS},
        }
    return output


def model_parameters(fits):
    return {
        name: {"scale_MPa": entry["model"].scale_MPa, "exponent": entry["model"].exponent,
               "source_errors": entry["source_errors"],
               "source_balanced_rmse_log_pressure": entry["source_balanced_rmse_log_pressure"]}
        for name, entry in fits.items()
    }


def cycle_summary(run):
    return {key: run[key] for key in ("feasible", "cycle_s", "reason", "peak_working_bar",
                                      "required_peak_working_bar") if key in run}


def main():
    data = yaml.safe_load(SOURCE_FILE.read_text(encoding="utf-8"))
    a, p = data["assumptions"], data["project"]
    recovery = Recovery.from_sources(data)
    rows, excluded = observations(data, recovery)
    independent = len({row.source_id for row in rows})
    if independent < 3:
        raise ValueError("Fewer than three independent sources in fit")
    fits = fit_models(rows, data)
    omission_fits = fit_models([row for row in rows if row.source_id != "li2000"], data)
    selected = min(fits, key=lambda name: fits[name]["source_balanced_rmse_log_pressure"])
    base_curve = ProjectCurve(fits[selected]["model"], data, recovery)
    # Keep the model family fixed to isolate the effect of dropping one study.
    without_li = ProjectCurve(omission_fits[selected]["model"], data, recovery)
    sources = data["sources"]
    cap_basis = sources["horabik2023"]["observations"]["solid_density_kg_m3_by_species"]
    upper = min(cap_basis.values())
    anchors = envelope_anchors(data, recovery, base_curve, rows)
    envelope = make_envelope(anchors, base_curve, recovery)
    curve = ProjectCurve(base_curve.fit, data, recovery, envelope)
    coverage = coverage_checks(anchors, curve, upper)

    reference_face_MPa = dict(x1.M1_PRESSURE_POINTS)[1000]
    x1_reference = x1.Model()
    bulk = p["bulk_kg_m3"]["base"]
    x1_sequence = x1.motions(x1_reference, x1.MAIN, bulk)
    x1_reference_cycle = run_cycle(x1_reference, p)["cycle_s"]
    pressure = density_requirement(curve, "base", upper)["stabilized"]["face_MPa"]
    comparison_face = curve.face_MPa(p["loaded_comparison_kg_m3"], "base")
    checks = {
        "independent_sources_at_least_three": independent >= 3,
        "base_face_for_stabilized_target_at_most_nominal": pressure is not None and pressure <= p["nominal_face_MPa"],
        "base_face_at_1000_loaded_within_factor_two_of_M1": (
            reference_face_MPa / 2 <= comparison_face <= reference_face_MPa * 2
        ),
    }
    cases = {case: project_consequences(curve, case, upper) for case in SCENARIOS}
    cases["without_li2000"] = project_consequences(without_li, "base", upper)
    base = cases["base"]
    estimate_status = "literature_screening" if all(checks.values()) else "concept_stop"

    ratios = {
        case: [pressure_ratios(a["wall_K"][case], a["wall_mu"][case], length,
                               2 * p["width_mm"] * p["height_mm"] / (p["width_mm"] + p["height_mm"]))
               for length in (80, 95, 110)]
        for case in SCENARIOS
    }
    targets_by_bulk = {str(value): density_requirement(curve, "base", upper, bulk=value)
                       for value in p["bulk_kg_m3"].values()}
    axial_sensitivity = nominal_recovery_sensitivity(curve, upper, base)
    endpoints = moisture_endpoints(anchors, base_curve, upper)
    params = model_parameters(fits)
    table = [
        {"rho_loaded_kg_m3": density,
         "p_MPa": {case: round(curve.face_MPa(density, case), 8) for case in SCENARIOS}}
        for density in sorted(set(range(bulk, upper + 1, 25)) | {
            upper, 1250, 461, 1000, a["bulk_transition_kg_m3"], *p["bulk_kg_m3"].values(),
        })
    ]
    for previous, current in zip(table, table[1:]):
        assert 0 < current["rho_loaded_kg_m3"] - previous["rho_loaded_kg_m3"] <= 25
        assert all(current["p_MPa"][s] >= previous["p_MPa"][s] >= 0 for s in SCENARIOS)
    assert all(t["p_MPa"]["low"] <= t["p_MPa"]["base"] <= t["p_MPa"]["high"] for t in table)
    assert targets_by_bulk[str(bulk)] == targets_by_bulk[str(p["bulk_kg_m3"]["alternative"])]
    p_table = [
        {"p_face_MPa": face, **{case: densities_at_face(curve, face, case, upper) for case in SCENARIOS}}
        for face in sorted({p["nominal_face_MPa"], *range(0, 201, 10), *(
            row.lab_face_MPa for row in anchors if row.source != "zhong1991")})
    ]

    curve_doc = {
        "status": estimate_status,
        "definition": "REV punch-face pressure vs mean bulk density under load; wet mass. Fit stress is axial mean.",
        "inputs": SOURCE_FILE.name,
        "density_domain_kg_m3": [bulk, upper],
        "domain_basis": a["domain_basis"],
        "base_model": selected,
        "models": params,
        "formula": {
            "onset": "t = clamp((rho-rho_bulk)/(rho_join-rho_bulk), 0, 1); f = t*(2-t); delta = max(rho-rho_ref,0)",
            "rho_ref_kg_m3": bulk,
            "rho_join_kg_m3": a["bulk_transition_kg_m3"],
            "power": "p_mean_MPa = scale_MPa * (delta/1000)**exponent * f",
            "generalized_heckel": "p_mean_MPa = scale_MPa * log(1+delta/(rho_limit-rho))**exponent * f",
            "rho_limit_kg_m3": a["heckel_limit_kg_m3"],
            "janssen": "q=4*K*mu*L/Dh; p_mean/p_face=-expm1(-q)/q; p_gate/p_face=exp(-q)",
            "immediate_density": "rho_loaded/((1+springback_axial)*(1+transverse_area_growth))",
            "stabilized_density": "same recovery mapping for conversion and prediction; linear interpolation of knots",
        },
        "K": a["wall_K"], "mu": a["wall_mu"],
        "wall_values_used_for_curves": "base",
        "springback": {case: recovery.axial_immediate for case in SCENARIOS},
        "transverse_area_growth": recovery.area_growth,
        "stabilization_knots_kg_m3": [
            {"rho_immediate": early, "rho_stabilized": stable}
            for early, stable in zip(recovery.early_knots, recovery.stable_knots)
        ],
        "bulk_density_kg_m3": p["bulk_kg_m3"],
        "envelope": {
            "basis": a["envelope_basis"],
            "min_density_slope_kg_m3_per_MPa": a["envelope_min_density_slope_kg_m3_per_MPa"],
            "knots": {case: [{"p_face_MPa": face, "rho_immediate_equivalent_kg_m3": density}
                             for face, density in knots] for case, knots in envelope.items()},
        },
        "table": table,
        "face_to_density_table": p_table,
    }
    (HERE / "curve.yaml").write_text(yaml.safe_dump(curve_doc, sort_keys=False, allow_unicode=True),
                                    encoding="utf-8", newline="\n")

    base_nominal = make_cycle_model(curve, "base", base["operating_loaded_kg_m3"], base["operating_face_MPa"])
    sensitivity_residuals = model_parameters(omission_fits)
    results = {
        "status": estimate_status,
        "stop_checks": checks,
        "independent_fit_sources": independent,
        "excluded_point_counts": excluded,
        "density_domain_kg_m3": [bulk, upper],
        "fit_density_range_kg_m3": [min(r.density_kg_m3 for r in rows), max(r.density_kg_m3 for r in rows)],
        "fit_rows": [vars(row) for row in rows],
        "models": params,
        "models_without_li2000": sensitivity_residuals,
        "base_model": selected,
        "validation_excluded_sources": excluded_residuals(data, fits[selected]["model"]),
        "scenarios": cases,
        "target_by_bulk_kg_m3": targets_by_bulk,
        "moisture_endpoints_pct": endpoints,
        "envelope_coverage": coverage,
        "cycle_axial_sensitivity": axial_sensitivity,
        "base_fine_step_cycle": cycle_summary(run_cycle(base_nominal, p, x1.DT_S / 2)),
        "janssen_ratios": ratios,
        "M1_face_at_1000_loaded_MPa": reference_face_MPa,
        "X1_face_at_1000_loaded_MPa": x1_reference.axial_pressure_Pa(1000) / 1e6,
        "X1_reference": {
            "nominal_face_MPa": x1_reference.nominal_N / x1_reference.section_m2 / 1e6,
            "face_for_relaxed_target_MPa": x1_reference.axial_pressure_Pa(
                p["target_relaxed_kg_m3"] * (1 + x1_reference.axial_recovery)) / 1e6,
            "stroke_above_120_bar_mm": stroke_above_threshold_mm(x1_sequence, p["pressure_threshold_bar"]),
            "cycle_s": x1_reference_cycle,
        },
        "cycle_policy": ("The unchanged X-1 drive enforces the 300 bar hydraulic limit. "
                         "The concept stop also defers the pooled base and leave-one-source-out "
                         "target cycles above 166.7 MPa. Specified 15/30% sensitivities are diagnostic."),
    }
    write_json(HERE / "results.json", results)
    write_json(ROOT / "metrics.json", {
        key: results[key] for key in (
            "status", "independent_fit_sources", "base_model", "density_domain_kg_m3",
            "M1_face_at_1000_loaded_MPa", "X1_face_at_1000_loaded_MPa", "stop_checks", "target_by_bulk_kg_m3",
            "moisture_endpoints_pct",
        )
    } | {
        "scenarios": {case: {**estimate, "cycle": cycle_summary(estimate["cycle"]),
                             "cycle_at_stabilized_target": cycle_summary(estimate["cycle_at_stabilized_target"])}
                      for case, estimate in cases.items()},
        "cycle_axial_sensitivity": {key: {**value, "cycle_at_nominal": cycle_summary(value["cycle_at_nominal"]),
                                         "cycle_at_stabilized_target": cycle_summary(value["cycle_at_stabilized_target"])}
                                   for key, value in axial_sensitivity.items()},
        "envelope_covered_anchors": sum(point["covered"] for point in coverage),
        "envelope_total_anchors": len(coverage),
    })
    print(json.dumps({"status": estimate_status, "stop_checks": checks, "base_model": selected,
                      "base_face_for_stabilized_target_MPa": pressure,
                      "base_cycle_s": base["cycle"].get("cycle_s")},
                     ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
