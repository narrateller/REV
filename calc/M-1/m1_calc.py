"""M-1 master calculation (GK, hand-level model, 25.11.2026). Pure Python, no deps.
All forks (vilki) are evaluated; numbers feed design/params.m1.yaml and docs/M-1_master_calc.md.
Compaction curve p(rho): RAM-FACE pressure vs MEAN in-die density (wall friction included) — ORDER-OF-MAGNITUDE placeholder for sawdust 8-12 % moisture, to be replaced by T-1.1
(literature fit with DOI). Points: rho [kg/m3] -> p [MPa].
"""
import math, json, sys

A_B = 0.150 * 0.060                 # m2, briquette = chamber section (C-PROD-01, D0)
P_FACE = 166.7e6                    # Pa (C-PFACE-01)
F_NOM = 1.5e6                       # N
M_DOSE = 0.83                       # kg (C-PERF-01)
CURVE = [(90, 0.005), (200, 0.15), (300, 0.5), (369, 1.0), (400, 2.0), (600, 8.0), (800, 30.0), (1000, 80.0), (1150, 150.0), (1180, 166.7)]

def p_of_rho(r):                    # log-linear interpolation, MPa
    for (r0, p0), (r1, p1) in zip(CURVE, CURVE[1:]):
        if r <= r1:
            t = (r - r0) / (r1 - r0)
            return math.exp(math.log(p0) + t * (math.log(p1) - math.log(p0)))
    return CURVE[-1][1]

def cyl(D, d):                      # areas m2
    A = math.pi * D**2 / 4; a = math.pi * d**2 / 4
    return A, a, A - a

def run(D=0.280, d=0.200, eta_cyl=0.95, Lp=0.200, rho_die=1180.0, springback=0.10, mu_factor=1.00,
        Qmax_Lmin=360.0, motor_kW=30.0, eta_drive=0.85, pre_D=0.100, pre_d=0.056, gate_D=0.063, gate_d=0.036,
        gate_stroke=0.070, eject_extra=0.010, hold_s=0.2, decomp_s=0.15, switch_s=0.1, regen_approach=True,
        regen_eject=True, eject_force=150e3, pre_p_MPa=None, pre_margin=1.3, gate_min_s=0.25, verbose=False):
    A, a, Ann = cyl(D, d)
    out = {}
    # force / pressure
    p_nom = F_NOM / (A * eta_cyl)
    out.update(D_mm=D*1e3, d_mm=d*1e3, A_m2=A, p_for_1p5MN_bar=p_nom/1e5,
               F_at_300bar_MN=A*30e6*eta_cyl/1e6, F_relief_315_ideal_MN=A*31.5e6/1e6,
               face_p_at_relief_MPa=A*31.5e6/A_B/1e6)
    # dose geometry
    L_die = M_DOSE / (rho_die * A_B)                      # in-die length at full pressure
    L_out = L_die * (1 + springback)                      # after exit (axial springback)
    rho_out = M_DOSE / (A_B * L_out)
    rho_pre = M_DOSE / (A_B * Lp)
    press_travel = Lp - L_die
    eject = L_die + eject_extra
    stroke_req = Lp + eject_extra
    out.update(L_die_mm=L_die*1e3, L_out_mm=L_out*1e3, rho_out=rho_out, rho_pre=rho_pre,
               press_travel_mm=press_travel*1e3, eject_mm=eject*1e3, stroke_req_mm=stroke_req*1e3)
    # precompaction chamber: plan 150 x Lp, loose heights
    plan = 0.150 * Lp
    h90 = M_DOSE / 90 / plan; h160 = M_DOSE / 160 / plan
    pre_stroke = h90 + 0.010                               # ram from above loose fill down to channel roof
    preA, prea, preAnn = cyl(pre_D, pre_d)
    if pre_p_MPa is None:
        pre_p_MPa = p_of_rho(rho_pre) * pre_margin          # precompaction pressure to reach rho_pre, + margin
    pre_F = pre_p_MPa * 1e6 * plan
    out.update(pre_plan_mm=[150, Lp*1e3], loose_h90_mm=h90*1e3, loose_h160_mm=h160*1e3,
               pre_stroke_mm=pre_stroke*1e3, pre_force_kN=pre_F/1e3, pre_p_oil_bar=pre_F/(preA*eta_cyl)/1e5)
    # compaction work: integrate p dV along press travel
    n = 2000; W = 0.0; xs = []
    for i in range(n):
        L0 = Lp - press_travel * i / n; L1 = Lp - press_travel * (i + 1) / n
        r = M_DOSE / (A_B * (L0 + L1) / 2)
        p = p_of_rho(r) * 1e6
        W += p * A_B * (L0 - L1)
        xs.append((L0 - L1, p * A_B * mu_factor))       # ram force incl. wall friction factor
    out.update(W_compaction_kJ=W/1e3, W_ram_kJ=W*mu_factor/1e3)
    Qmax = Qmax_Lmin / 60e3; Ph = motor_kW * 1e3 * eta_drive
    def tQ(V, p):                                          # time for volume V at oil pressure p (Pa)
        return V / min(Qmax, Ph / max(p, 1.0))
    # main forward: integrate along travel, choose regen while oil pressure on rod area <= regen limit
    t_fwd = 0.0; V_fwd = 0.0; t_regen = 0.0
    for dx, F in xs:
        F = F / eta_cyl
        if regen_approach and F / a < 120e5:              # differential while <120 bar on rod area
            V = a * dx; p = F / a; t_regen += tQ(V, p)
        else:
            V = A * dx; p = F / A
        t_fwd += tQ(V, p); V_fwd += V
    # eject
    if regen_eject:
        V_ej = a * eject; p_ej = eject_force / eta_cyl / a
    else:
        V_ej = A * eject; p_ej = eject_force / eta_cyl / A
    t_ej = tQ(V_ej, p_ej)
    # retract main (full stroke), low pressure ~20 bar
    V_ret = Ann * stroke_req; t_ret = tQ(V_ret, 20e5)
    # precompaction down / up
    # precompaction down: column height H from (h90 + 60 mm) to 60 mm, force = p(rho) * plan; first 10 mm free
    H0 = h90 + 0.060; Hc = 0.060; t_pd = tQ(preA * 0.010, 5e5); V_pd = preA * 0.010; k = 400
    for i in range(k):
        Ha = H0 - (H0 - Hc) * i / k; Hb = H0 - (H0 - Hc) * (i + 1) / k
        r = M_DOSE / (plan * (Ha + Hb) / 2)
        F = min(p_of_rho(r) * 1e6, pre_p_MPa * 1e6) * plan / eta_cyl
        V = preA * (Ha - Hb); V_pd += V; t_pd += tQ(V, max(F / preA, 5e5))
    V_pu = preAnn * pre_stroke; t_pu = tQ(V_pu, 15e5)
    gA, ga, gAnn = cyl(gate_D, gate_d)
    t_go = max(gate_min_s, tQ(gAnn * gate_stroke, 30e5)); t_gc = max(gate_min_s, tQ(gA * gate_stroke, 30e5))
    phases = [("prepress_down", t_pd), ("main_forward", t_fwd), ("hold", hold_s), ("decompress", decomp_s),
              ("gate_open", t_go), ("eject", t_ej), ("main_retract", t_ret), ("gate_close", t_gc), ("prepress_up", t_pu)]
    serial = sum(t for _, t in phases) + switch_s * len(phases)
    # overlap per D0 sequence: prepress_up || (eject+retract) ; gate_close || retract
    overlap = serial - t_pu - t_gc - 2 * switch_s
    V_cycle = V_pd + V_fwd + V_ej + V_ret + V_pu + gAnn * gate_stroke + gA * gate_stroke
    E_hyd = W * mu_factor / eta_cyl + 0.5e6 * (V_cycle - A * press_travel)   # + ~5 bar flow losses on rest
    out.update(phases_s={k: round(v, 3) for k, v in phases}, cycle_serial_s=serial, cycle_overlap_s=overlap,
               V_cycle_L=V_cycle*1e3, P_avg_motor_kW=E_hyd/eta_drive/serial/1e3,
               t_compaction_highp_s=t_fwd - t_regen)
    return out

if __name__ == "__main__":
    base = run()
    print(json.dumps(base, ensure_ascii=False, indent=1))
    print("\n--- forks")
    for label, kw in [("D=250", dict(D=0.250, d=0.180)), ("D=320 d=220", dict(D=0.320, d=0.220)),
                      ("Lp=180", dict(Lp=0.180)), ("Lp=220", dict(Lp=0.220)), ("pre D110", dict(pre_D=0.110, pre_d=0.063)), ("rho_die=1100", dict(rho_die=1100.0)),
                      ("Qmax=260", dict(Qmax_Lmin=260.0)), ("no regen", dict(regen_approach=False, regen_eject=False)),
                      ("work x1.3", dict(mu_factor=1.3)), ("d=180", dict(d=0.180))]:
        r = run(**kw)
        print(f"{label:14s} pre={r['pre_force_kN']:4.0f}kN/{r['pre_p_oil_bar']:4.0f}bar p1.5MN={r['p_for_1p5MN_bar']:6.1f} bar  stroke={r['stroke_req_mm']:5.0f}  "
              f"rho_pre={r['rho_pre']:4.0f}  Wram={r['W_ram_kJ']:5.1f} kJ  serial={r['cycle_serial_s']:4.2f}  "
              f"overlap={r['cycle_overlap_s']:4.2f}  V={r['V_cycle_L']:5.1f} L  Pavg={r['P_avg_motor_kW']:5.1f}")
