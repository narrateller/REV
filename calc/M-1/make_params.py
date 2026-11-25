"""Build design/params.m1.yaml from the M-1 base case (GK, 25.11.2026).
Strokes are split into pressure bands; each phase pressure = MAX oil pressure in its band (conservative for the
serial constant-pressure-per-phase model of G-CYCLE)."""
import sys, math
sys.path.insert(0, 'calc/M-1')
import m1_calc as m
r = m.run()
D, d = 0.280, 0.200; A, a, Ann = m.cyl(D, d); eta = 0.95
Lp = 0.200; L_die = r['L_die_mm'] / 1e3; travel = Lp - L_die
EDGES = [20, 50, 100, 150, 200, 250, 1e9]          # bar band upper limits

def bands(samples):                                 # samples: (dx m, p bar, regen) -> merged phases
    out = []
    for dx, p, regen in samples:
        hi = next(e for e in EDGES if p <= e)
        if out and out[-1][2] == regen and out[-1][3] == hi:
            out[-1][0] += dx; out[-1][1] = max(out[-1][1], p)
        else:
            out.append([dx, p, regen, hi])
    return out

n = 4000; main = []
for i in range(n):
    L0 = Lp - travel * i / n; L1 = Lp - travel * (i + 1) / n
    F = m.p_of_rho(m.M_DOSE / (m.A_B * (L0 + L1) / 2)) * 1e6 * m.A_B / eta
    main.append((L0 - L1, F / a / 1e5, True) if F / a < 120e5 else (L0 - L1, F / A / 1e5, False))
plan = 0.150 * Lp; preA = math.pi * 0.1**2 / 4; H0 = r['loose_h90_mm'] / 1e3 + 0.060; Hc = 0.060
pre_cap = r['pre_force_kN'] * 1e3; pre = [(0.010, 5.0, False)]
for i in range(n):
    Ha = H0 - (H0 - Hc) * i / n; Hb = H0 - (H0 - Hc) * (i + 1) / n
    F = min(m.p_of_rho(m.M_DOSE / (plan * (Ha + Hb) / 2)) * 1e6 * plan, pre_cap) / eta
    pre.append((Ha - Hb, max(F / preA / 1e5, 5.0), False))
mb = bands(main); pb = bands(pre)
pre_stroke = round(sum(x[0] for x in pb) * 1e3, 1)
eject = round((L_die + 0.010) * 1e3, 1)
lines = []
for i, (dx, p, _, _) in enumerate(pb):
    lines.append(f"  - {{name: Подпрессовка {i+1}, actuator: precompaction, stroke_mm: {round(dx*1e3,1)}, direction: extend, "
                 f"pressure_bar: {math.ceil(p)}, speed_mm_s: pump, regeneration: false, dwell_s: 0}}")
main_strokes = []
for i, (dx, p, regen, _) in enumerate(mb):
    last = i == len(mb) - 1
    s = round(dx * 1e3, 1); main_strokes.append(s)
    lines.append(f"  - {{name: {'Финальное прессование' if last else f'Прессование {i+1}'}, actuator: main_cylinder, stroke_mm: {s}, "
                 f"direction: extend, pressure_bar: {270 if last else math.ceil(p)}, speed_mm_s: pump, regeneration: {str(regen).lower()}, "
                 f"{'press: true, dwell_s: 0.35' if last else 'dwell_s: 0'}}}")
ret = round(sum(main_strokes) + eject, 1)
lines += [
 "  - {name: Открытие шибера, actuator: slide_gate, stroke_mm: 70, direction: retract, pressure_bar: 100, speed_mm_s: 280, regeneration: false, dwell_s: 0}",
 f"  - {{name: Выталкивание, actuator: main_cylinder, stroke_mm: {eject}, direction: extend, force_N: 150000, speed_mm_s: pump, regeneration: true, dwell_s: 0}}",
 f"  - {{name: Возврат пуансона, actuator: main_cylinder, stroke_mm: {ret}, direction: retract, pressure_bar: 20, speed_mm_s: pump, regeneration: false, dwell_s: 0}}",
 "  - {name: Закрытие шибера, actuator: slide_gate, stroke_mm: 70, direction: extend, pressure_bar: 30, speed_mm_s: 280, regeneration: false, dwell_s: 0}",
 f"  - {{name: Возврат подпрессовки, actuator: precompaction, stroke_mm: {pre_stroke}, direction: retract, pressure_bar: 15, speed_mm_s: pump, regeneration: false, dwell_s: 0}}"]
y = f"""# M-1 master calculation, base case (GK, 25.11.2026). Source: calc/M-1/m1_calc.py, docs/M-1_master_calc.md.
# Status: PRELIMINARY — compaction curve is a placeholder until T-1.1; values are fixed only at D1.
schema_version: 1
description: "M-1 base case: closed die 150x60, one main cylinder D280/d200, vertical precompaction D100, slide gate"
product: {{section_mm: [150, 60], length_range_mm: [40, 110], density_kg_m3: 1000}}
raw: {{bulk_density_kg_m3: [90, 160], dose_kg: 0.83}}
main_cylinder:
  n: 1
  bore_mm: 280
  rod_mm: 200
  stroke_mm: 230
  p_work_bar: 270
  p_relief_bar: 300
  eta: 0.95
  nominal_force_N: 1520000   # 166.7 MPa x 9000 mm2 = 1.5003 MN; 1.5 MN gives 166.67 < 166.7
chamber:
  section_mm: [150, 60]
  length_mm: 300
  clearance_per_side_mm: 0.2
  ejection_stroke_mm: {eject}
  approach_stroke_mm: 0
  in_die_density_kg_m3: 1180
precompaction:
  section_mm: [150, 200]
  loose_fill_length_mm: {round(r['loose_h90_mm'] + 5)}
  stroke_mm: {pre_stroke}
  post_precompaction_density_kg_m3: {round(r['rho_pre'])}
  cylinder: {{n: 1, bore_mm: 100, rod_mm: 56, stroke_mm: 330, eta: 0.95}}
drive:
  motor_kW: 30
  installed_kW: 34   # 30 main + ~4 feed screw, cooler, control (estimate, T-1.4)
  pump_max_flow_L_min: 360
  eta: 0.85
  slide_gate_cylinder: {{n: 1, bore_mm: 80, rod_mm: 45, stroke_mm: 70, eta: 0.95}}
cycle:
""" + "\n".join(lines) + "\n"
open('design/params.m1.yaml', 'w', encoding='utf-8', newline='\n').write(y)
print(f"phases: pre {len(pb)}, main {len(mb)}, pre_stroke {pre_stroke}, main extend {sum(main_strokes)+eject:.1f} ret {ret}", file=sys.stderr)
