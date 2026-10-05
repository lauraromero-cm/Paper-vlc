"""
Pedido del agente redactor: (1) columna "+-dB (1sigma)" en la tabla de SINR
minimo (fov_opt_table.csv / tabla_fovopt.csv), usando el exponente REAL del
modelo de ruido (no asumir SINR ~ n^1); (2) barrido del SINR del asiento mas
debil con I_bg en {20, 200, 2000} uA (solo calculo, sin nueva simulacion).

Exponente real: SINR(n) = (I_signal)^2 / (sigma2(n) + I_interf^2), con
I_signal, shot_signal ~ n (n = num. de rayos equivalentes que llegan al
detector) y sigma2_fijo = termico + fondo + oscuro + I_interf^2 independiente
de n. Entonces:
    d(ln SINR)/d(ln n) = 2 - shot_signal / (shot_signal + sigma2_fijo + I_interf^2)
que vale 2 en el limite sin ruido de piso (shot-noise puro) y 0 cuando el
ruido esta completamente dominado por el piso fijo. El error relativo del
conteo de rayos por Poisson es 1/sqrt(n), así que:
    sigma_dB(SINR) = d * (10/ln10) / sqrt(n)
en vez de asumir d=1 (que fue la aproximacion usada en una iteracion previa).

n (num. de rayos equivalentes) se recupera de la potencia ya exportada:
Pr_raw_W = Pr_exportado_mW/1000 / g(FOV); n = Pr_raw_W / (Popt/N_RAYS),
con Popt=2W y N_RAYS=1e6 (energia por rayo = 2 microW) -- confirmado contra
ray_count_and_uncertainty.csv (coincide exactamente, p.ej. n=108/33/103 para
las 3 filas de FOVopt).
"""
import os, csv, json, math
import noise_model as nm

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_TABLES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales", "tables")
os.makedirs(_TABLES_DIR, exist_ok=True)

RAY_ENERGY_W = 2.0e-6  # Popt/N_RAYS = 2W / 1e6 rayos (pipeline_oficial.py), confirmado
                        # contra ray_count_and_uncertainty.csv (coincide exacto)
PITCHES = [0, 15, 30]
RX_IDXS = [6, 7, 8, 9]


def n_rays_eq(pr_mw, fov_deg):
    g = nm.concentrator_gain(fov_deg)
    pr_raw_w = (pr_mw / 1000.0) / g
    return pr_raw_w / RAY_ENERGY_W


def real_exponent(pr_signal_mw, pr_interf_mw):
    pr_s = pr_signal_mw / 1000.0
    pr_i = pr_interf_mw / 1000.0
    sinr, sigma2, i_sig, i_int = nm.compute_sinr(pr_s, pr_i)
    shot_signal_only = nm.shot_noise_variance(pr_s * nm.FILTER_TRANSMISSION)
    denom = sigma2 + i_int ** 2
    d = 2.0 - shot_signal_only / denom
    return d, sinr


def cargar(escenario, pitch):
    path = os.path.join(_PROJECT_ROOT, "escenarios", f"{escenario}_{pitch}grados",
                         "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["filas"]


# ====================== 1) +-dB (1 sigma) para la tabla FOVopt ======================
DATA = {p: cargar("sin_bloqueo", p) for p in PITCHES}
rows = []
for p in PITCHES:
    filas = DATA[p]
    min_por_fov = []
    for fila in filas:
        vals = [(rx, fila["asientos"][str(rx)]) for rx in RX_IDXS]
        rx_min, a_min = min(vals, key=lambda t: t[1]["SINR_hybrid_dB"])
        min_por_fov.append((fila["fov_deg"], a_min["SINR_hybrid_dB"], rx_min, a_min))
    fov_opt, sinr_min_opt, rx_min, a_min = max(min_por_fov, key=lambda t: t[1])

    usa_diff = a_min["usa_DIFF"]
    pr_signal = a_min["Pr_DIFF_mW"] if usa_diff else a_min["Pr_own_LOS_mW"]
    pr_interf = a_min["Pr_interf_DIFF_mW"] if usa_diff else a_min["Pr_interf_LOS_mW"]
    n = n_rays_eq(pr_signal, fov_opt)
    d, _ = real_exponent(pr_signal, pr_interf)
    sigma_db = d * (10.0 / math.log(10.0)) / math.sqrt(n)

    rows.append({"pitch": p, "fov_opt": fov_opt, "seat_rx": rx_min, "channel": "DIFF" if usa_diff else "LOS",
                 "sinr_min_dB": sinr_min_opt, "n_rayos": n, "exponente_d": d, "sigma_dB_1sigma": sigma_db})

csv_path = os.path.join(_TABLES_DIR, "fov_opt_table_con_incertidumbre.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Pitch (deg)", "FOVopt (deg)", "Weakest seat (RX)", "Channel", "Min Hybrid SINR (dB)",
                "n_rays (eq.)", "Real exponent d", "+-dB (1 sigma, real d)"])
    for r in rows:
        w.writerow([r["pitch"], int(r["fov_opt"]), r["seat_rx"], r["channel"], f"{r['sinr_min_dB']:.2f}",
                    f"{r['n_rayos']:.1f}", f"{r['exponente_d']:.3f}", f"{r['sigma_dB_1sigma']:.3f}"])

print("=== 1) +-dB (1 sigma) con exponente real, tabla FOVopt (sin_bloqueo) ===")
for r in rows:
    print(f"  pitch={r['pitch']:>2}  FOVopt={r['fov_opt']:.0f}  seat=RX{r['seat_rx']}({r['channel']})  "
          f"SINR_min={r['sinr_min_dB']:.2f}dB  n={r['n_rayos']:.0f}  d={r['exponente_d']:.3f}  "
          f"+-{r['sigma_dB_1sigma']:.3f}dB(1sigma)  [naive d=1 daria +-{(10/math.log(10))/math.sqrt(r['n_rayos']):.3f}dB]")
print(f"Guardado: {csv_path}")

# ====================== 2) Barrido de I_bg para el asiento/celda mas debil ======================
# Caso mas debil global (ya identificado en noise_budget_breakdown.csv / sesion previa):
# bloqueo_persona_30grados, Seat2 (RX7), FOV=60 (FOVopt de esa fila), canal DIFF, n=29 rayos.
filas_persona30 = cargar("bloqueo_persona", 30)
fila60 = next(f for f in filas_persona30 if f["fov_deg"] == 60.0)
celda = fila60["asientos"]["7"]
pr_diff_mw = celda["Pr_DIFF_mW"]
pr_interf_mw = celda["Pr_interf_DIFF_mW"]

I_BG_VALUES_A = [20e-6, 200e-6, 2000e-6]
sweep_rows = []
for i_bg in I_BG_VALUES_A:
    pr_s = pr_diff_mw / 1000.0
    pr_i = pr_interf_mw / 1000.0
    pr_s_eff = pr_s * nm.FILTER_TRANSMISSION
    pr_i_eff = pr_i * nm.FILTER_TRANSMISSION
    i_sig = nm.RESPONSIVITY * pr_s_eff
    i_int = nm.RESPONSIVITY * pr_i_eff
    sigma2 = nm.total_noise_variance(pr_s_eff + pr_i_eff, I_bg=i_bg)
    sinr = (i_sig ** 2) / (sigma2 + i_int ** 2)
    gamma_th2_db = nm.db(nm.sinr_threshold_from_ber())
    sweep_rows.append({"I_bg_uA": i_bg * 1e6, "SINR_DIFF_dB": nm.db(sinr),
                        "margen_sobre_gamma_th2_dB": nm.db(sinr) - gamma_th2_db})

csv_path2 = os.path.join(_TABLES_DIR, "sweep_I_bg_asiento_mas_debil.csv")
with open(csv_path2, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["I_bg (uA)", "SINR_DIFF (dB)", "Margen sobre gamma_th2=19.56dB (dB)"])
    for r in sweep_rows:
        w.writerow([f"{r['I_bg_uA']:.0f}", f"{r['SINR_DIFF_dB']:.2f}", f"{r['margen_sobre_gamma_th2_dB']:+.2f}"])

print("\n=== 2) Barrido I_bg, caso mas debil (bloqueo_persona_30grados, Seat2/RX7, FOV=60, DIFF, n=29) ===")
print(f"  Pr_DIFF={pr_diff_mw:.4f} mW, Pr_interf_DIFF={pr_interf_mw:.4f} mW (valor por defecto: I_bg=200uA)")
for r in sweep_rows:
    print(f"  I_bg={r['I_bg_uA']:>6.0f} uA  ->  SINR_DIFF={r['SINR_DIFF_dB']:.2f} dB  "
          f"(margen sobre gamma_th,2=19.56dB: {r['margen_sobre_gamma_th2_dB']:+.2f} dB)")
print(f"Guardado: {csv_path2}")
