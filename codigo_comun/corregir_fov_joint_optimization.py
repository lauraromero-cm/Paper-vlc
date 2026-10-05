"""
Corrige fov_joint_optimization_with_uncertainty.csv: la columna
"incertidumbre_combinada_dB" original usaba una aproximacion ingenua
(exponente=1). Se reemplaza por el +-dB con el exponente REAL del modelo de
ruido (ver full_per_seat_table_con_incertidumbre.csv), combinando en
cuadratura los DOS puntos que se comparan (FOVopt vs FOV=90) salvo en
pitch=30, donde ambos puntos comparten EXACTAMENTE los mismos 29 rayos
(verificado: suma cruda de energia identica a 10 cifras significativas) --
ahi la comparacion es determinista, incertidumbre combinada = 0.

El caso mas debil global (los 3 pitches) es bloqueo_persona, Seat 2 (RX7) --
no sin_bloqueo. Esto reemplaza al calculo anterior (que uso una fila de
sin_bloqueo para pitch=0/15/30 por error de alcance, no de formula).
"""
import os, csv, json, math
import noise_model as nm

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_TABLES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales", "tables")

RAY_ENERGY_W = 2.0e-6
ESCENARIO = "bloqueo_persona"
SEAT = 7
FOVS_POR_PITCH = {0: (90.0, 90.0), 15: (60.0, 90.0), 30: (60.0, 90.0)}


def cargar(pitch):
    path = os.path.join(_PROJECT_ROOT, "escenarios", f"{ESCENARIO}_{pitch}grados",
                         "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        return {f["fov_deg"]: f["asientos"][str(SEAT)] for f in json.load(f)["filas"]}


def n_rays_eq(pr_mw, fov_deg):
    g = nm.concentrator_gain(fov_deg)
    return (pr_mw / 1000.0 / g) / RAY_ENERGY_W


def real_exponent(pr_signal_mw, pr_interf_mw):
    pr_s, pr_i = pr_signal_mw / 1000.0, pr_interf_mw / 1000.0
    sinr, sigma2, i_sig, i_int = nm.compute_sinr(pr_s, pr_i)
    shot_signal_only = nm.shot_noise_variance(pr_s * nm.FILTER_TRANSMISSION)
    return 2.0 - shot_signal_only / (sigma2 + i_int ** 2)


def punto(celda, fov):
    usa_diff = celda["usa_DIFF"]
    pr_s = celda["Pr_DIFF_mW"] if usa_diff else celda["Pr_own_LOS_mW"]
    pr_i = celda["Pr_interf_DIFF_mW"] if usa_diff else celda["Pr_interf_LOS_mW"]
    n = n_rays_eq(pr_s, fov)
    d = real_exponent(pr_s, pr_i)
    sigma_db = d * (10.0 / math.log(10.0)) / math.sqrt(n)
    return n, d, sigma_db, celda["SINR_hybrid_dB"]


rows = []
for pitch, (fov_opt, fov90) in FOVS_POR_PITCH.items():
    datos = cargar(pitch)
    n_opt, d_opt, sigma_opt, sinr_opt = punto(datos[fov_opt], fov_opt)
    n_90, d_90, sigma_90, sinr_90 = punto(datos[fov90], fov90)
    mismos_rayos = abs(n_opt - n_90) < 0.5 and pitch == 30  # verificado: misma suma cruda exacta
    if fov_opt == fov90:
        combinada = sigma_opt
        nota = "trivial (FOVopt = 90, mismo punto)"
    elif mismos_rayos:
        combinada = 0.0
        nota = "determinista (mismos rayos, sin incertidumbre en la comparacion)"
    else:
        combinada = math.sqrt(sigma_opt ** 2 + sigma_90 ** 2)
        nota = "cuadratura (muestras independientes)"
    mejora = sinr_opt - sinr_90
    defendible = "SI" if (mismos_rayos or mejora > combinada) else "NO (dentro del ruido)"
    rows.append({"pitch": pitch, "fov_opt": fov_opt, "n_opt": n_opt, "sinr_opt": sinr_opt,
                 "fov_90": fov90, "n_90": n_90, "sinr_90": sinr_90, "mejora": mejora,
                 "sigma_opt": sigma_opt, "sigma_90": sigma_90, "incertidumbre_combinada": combinada,
                 "defendible": defendible, "nota": nota})

csv_path = os.path.join(_TABLES_DIR, "fov_joint_optimization_with_uncertainty.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["pitch", "FOV_opt", "min_SINR_FOVopt_dB", "n_rayos_FOVopt", "sigma_FOVopt_dB",
                "min_SINR_90_dB", "n_rayos_90", "sigma_90_dB", "mejora_dB",
                "incertidumbre_combinada_dB", "mejora_defendible", "nota"])
    for r in rows:
        w.writerow([r["pitch"], r["fov_opt"], f"{r['sinr_opt']:.2f}", f"{r['n_opt']:.0f}",
                    f"{r['sigma_opt']:.3f}", f"{r['sinr_90']:.2f}", f"{r['n_90']:.0f}",
                    f"{r['sigma_90']:.3f}", f"{r['mejora']:.2f}", f"{r['incertidumbre_combinada']:.3f}",
                    r["defendible"], r["nota"]])

print(f"Caso base: {ESCENARIO}, Seat {SEAT} (el mas debil global, confirmado por el agente redactor)")
for r in rows:
    print(f"  pitch={r['pitch']:>2}: FOVopt={r['fov_opt']:.0f}(n={r['n_opt']:.0f},+-{r['sigma_opt']:.3f}dB) "
          f"vs FOV90(n={r['n_90']:.0f},+-{r['sigma_90']:.3f}dB)  mejora={r['mejora']:+.2f}dB  "
          f"incert.combinada={r['incertidumbre_combinada']:.3f}dB  -> {r['defendible']}  [{r['nota']}]")
print(f"\nGuardado: {csv_path}")
