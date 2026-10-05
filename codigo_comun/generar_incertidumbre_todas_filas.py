"""
Extiende full_per_seat_table.csv (324 filas: 9 escenarios x 9 FOV x 4 asientos)
con n (rayos equivalentes), exponente real d y +-dB (1 sigma) del canal que
efectivamente gana (hybrid = max(LOS,DIFF)), para cada fila -- pedido del
agente redactor como continuacion de generar_incertidumbre_sinr_minimo.py
(que solo cubria las 3 filas de FOVopt). Mismo metodo: ver docstring de ese
script para la derivacion de d y de n.
"""
import os, csv, json, math
import noise_model as nm

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_TABLES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales", "tables")

RAY_ENERGY_W = 2.0e-6  # Popt/N_RAYS = 2W / 1e6 rayos
ESCENARIOS = [
    "sin_bloqueo_0grados", "sin_bloqueo_15grados", "sin_bloqueo_30grados",
    "bloqueo_carrito_0grados", "bloqueo_carrito_15grados", "bloqueo_carrito_30grados",
    "bloqueo_persona_0grados", "bloqueo_persona_15grados", "bloqueo_persona_30grados",
]
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
    if denom <= 0:
        return float("nan")
    return 2.0 - shot_signal_only / denom


rows = []
for esc in ESCENARIOS:
    path = os.path.join(_PROJECT_ROOT, "escenarios", esc, "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        filas = json.load(f)["filas"]
    for fila in filas:
        fov = fila["fov_deg"]
        for rx in RX_IDXS:
            a = fila["asientos"][str(rx)]
            usa_diff = a["usa_DIFF"]
            pr_signal = a["Pr_DIFF_mW"] if usa_diff else a["Pr_own_LOS_mW"]
            pr_interf = a["Pr_interf_DIFF_mW"] if usa_diff else a["Pr_interf_LOS_mW"]
            n = n_rays_eq(pr_signal, fov)
            if n <= 0:
                d, sigma_db = float("nan"), float("inf")
            else:
                d = real_exponent(pr_signal, pr_interf)
                sigma_db = d * (10.0 / math.log(10.0)) / math.sqrt(n)
            rows.append({
                "scenario": esc, "fov_deg": fov, "seat": rx,
                "channel": "DIFF" if usa_diff else "LOS",
                "SINR_hybrid_dB": a["SINR_hybrid_dB"],
                "n_rayos": n, "exponente_d": d, "sigma_dB_1sigma": sigma_db,
            })

csv_path = os.path.join(_TABLES_DIR, "full_per_seat_table_con_incertidumbre.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Scenario", "FOV_deg", "Seat_RX", "Channel_used", "SINR_hybrid_dB",
                "n_rays_eq", "Real_exponent_d", "+-dB_1sigma"])
    for r in rows:
        n_str = f"{r['n_rayos']:.1f}" if r["n_rayos"] == r["n_rayos"] else "0.0"
        d_str = f"{r['exponente_d']:.3f}" if r["exponente_d"] == r["exponente_d"] else "nan"
        s_str = f"{r['sigma_dB_1sigma']:.3f}" if r["sigma_dB_1sigma"] != float("inf") else "inf"
        w.writerow([r["scenario"], r["fov_deg"], r["seat"], r["channel"], f"{r['SINR_hybrid_dB']:.2f}",
                    n_str, d_str, s_str])

print(f"{len(rows)} filas escritas en {csv_path}")
print("Muestra (primeras 10):")
for r in rows[:10]:
    print(f"  {r['scenario']:<25} FOV={r['fov_deg']:>5.1f} seat=RX{r['seat']} ch={r['channel']:<4} "
          f"SINR={r['SINR_hybrid_dB']:>6.2f}dB n={r['n_rayos']:>7.1f} d={r['exponente_d']:.3f} "
          f"+-{r['sigma_dB_1sigma']:.3f}dB")
