"""
Item 3 (pedido del agente redactor): "presupuesto equivalente" en los 9
escenarios, a FOV=90, bajo 3 configuraciones:
  (a) LOS-only,    2 W,  B=10 MHz  (SINR_LOS_dB ya exportado, sin cambios)
  (b) DIFF-only,   2 W,  B=10 MHz  (SINR_DIFF_dB ya exportado, sin cambios)
  (c) Hibrido,     1 W por lampara y por respaldo, B=5 MHz por canal
      (la interferencia LOS tambien escala con las lamparas a 1 W, ya que
      Pr es lineal en la potencia transmitida -- se escalan Pr_own/
      Pr_interf/Pr_DIFF por 0.5 y se recalcula el SINR con B=5e6)

No se corre ninguna simulacion nueva: (a) y (b) ya estan en los JSON, y (c)
se obtiene reescalando esos mismos valores exportados (Pr es lineal en
potencia transmitida) y recalculando el modelo de ruido con B=5MHz.

Con B=5 MHz, gamma_th,1 = 2^(Rmin/B) - 1 = 2^(5/5) - 1 = 1 (0 dB) en vez de
2^(5/10)-1=0.414 (-3.83dB) con B=10MHz. gamma_th,2 (basado en BER, no en B)
no cambia (19.56dB).
"""
import os, csv, json
import noise_model as nm

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_TABLES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales", "tables")
os.makedirs(_TABLES_DIR, exist_ok=True)

ESCENARIOS = [
    "sin_bloqueo_0grados", "sin_bloqueo_15grados", "sin_bloqueo_30grados",
    "bloqueo_carrito_0grados", "bloqueo_carrito_15grados", "bloqueo_carrito_30grados",
    "bloqueo_persona_0grados", "bloqueo_persona_15grados", "bloqueo_persona_30grados",
]
RX_IDXS = [6, 7, 8, 9]
B_HYBRID = 5.0e6
POWER_SCALE_HYBRID = 0.5  # 1W / 2W (Pr exportado es lineal en potencia transmitida)

gamma_th1_10mhz_dB = nm.db(nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, nm.BANDWIDTH_HZ))
gamma_th1_5mhz_dB = nm.db(nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, B_HYBRID))
gamma_th2_dB = nm.db(nm.sinr_threshold_from_ber(nm.BER_MAX))

rows = []
for esc in ESCENARIOS:
    path = os.path.join(_PROJECT_ROOT, "escenarios", esc, "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    fila90 = next(f for f in d["filas"] if f["fov_deg"] == 90.0)

    sinr_los_db, sinr_diff_db, sinr_hyb_db = [], [], []
    for rx in RX_IDXS:
        a = fila90["asientos"][str(rx)]
        # (a) LOS-only, 2W, 10MHz: ya exportado
        sinr_los_db.append(a["SINR_LOS_dB"])
        # (b) DIFF-only, 2W, 10MHz: ya exportado
        sinr_diff_db.append(a["SINR_DIFF_dB"])
        # (c) Hibrido, 1W/5MHz: reescalar Pr y recalcular con B=5e6
        pr_own = a["Pr_own_LOS_mW"] / 1000.0 * POWER_SCALE_HYBRID
        pr_interf_los = a["Pr_interf_LOS_mW"] / 1000.0 * POWER_SCALE_HYBRID
        pr_diff = a["Pr_DIFF_mW"] / 1000.0 * POWER_SCALE_HYBRID
        pr_interf_diff = a["Pr_interf_DIFF_mW"] / 1000.0 * POWER_SCALE_HYBRID
        sinr_los_c, _, _, _ = nm.compute_sinr(pr_own, pr_interf_los, B=B_HYBRID)
        sinr_diff_c, _, _, _ = nm.compute_sinr(pr_diff, pr_interf_diff, B=B_HYBRID)
        sinr_hyb_db.append(nm.db(max(sinr_los_c, sinr_diff_c)))

    def resumen(vals, gth1, gth2):
        n = len(vals)
        pout1 = 100.0 * sum(1 for x in vals if x < gth1) / n
        pout2 = 100.0 * sum(1 for x in vals if x < gth2) / n
        return min(vals), sum(vals) / n, pout1, pout2

    min_los, avg_los, pout1_los, pout2_los = resumen(sinr_los_db, gamma_th1_10mhz_dB, gamma_th2_dB)
    min_diff, avg_diff, pout1_diff, pout2_diff = resumen(sinr_diff_db, gamma_th1_10mhz_dB, gamma_th2_dB)
    min_hyb, avg_hyb, pout1_hyb, pout2_hyb = resumen(sinr_hyb_db, gamma_th1_5mhz_dB, gamma_th2_dB)

    rows.append({
        "scenario": esc,
        "LOS_min_dB": min_los, "LOS_avg_dB": avg_los, "LOS_Pout1_%": pout1_los, "LOS_Pout2_%": pout2_los,
        "DIFF_min_dB": min_diff, "DIFF_avg_dB": avg_diff, "DIFF_Pout1_%": pout1_diff, "DIFF_Pout2_%": pout2_diff,
        "Hybrid1W5MHz_min_dB": min_hyb, "Hybrid1W5MHz_avg_dB": avg_hyb,
        "Hybrid1W5MHz_Pout1_%": pout1_hyb, "Hybrid1W5MHz_Pout2_%": pout2_hyb,
    })

csv_path = os.path.join(_TABLES_DIR, "presupuesto_equivalente_9_escenarios.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    header = ["Scenario",
               "LOS-only(2W,10MHz)_min_dB", "LOS-only_avg_dB", f"LOS-only_Pout@gth1={gamma_th1_10mhz_dB:.2f}dB_%",
               f"LOS-only_Pout@gth2={gamma_th2_dB:.2f}dB_%",
               "DIFF-only(2W,10MHz)_min_dB", "DIFF-only_avg_dB", f"DIFF-only_Pout@gth1={gamma_th1_10mhz_dB:.2f}dB_%",
               f"DIFF-only_Pout@gth2={gamma_th2_dB:.2f}dB_%",
               "Hybrid(1W+1W,5MHz)_min_dB", "Hybrid_avg_dB", f"Hybrid_Pout@gth1={gamma_th1_5mhz_dB:.2f}dB_%",
               f"Hybrid_Pout@gth2={gamma_th2_dB:.2f}dB_%"]
    w.writerow(header)
    for r in rows:
        w.writerow([r["scenario"], f"{r['LOS_min_dB']:.2f}", f"{r['LOS_avg_dB']:.2f}",
                    f"{r['LOS_Pout1_%']:.1f}", f"{r['LOS_Pout2_%']:.1f}",
                    f"{r['DIFF_min_dB']:.2f}", f"{r['DIFF_avg_dB']:.2f}",
                    f"{r['DIFF_Pout1_%']:.1f}", f"{r['DIFF_Pout2_%']:.1f}",
                    f"{r['Hybrid1W5MHz_min_dB']:.2f}", f"{r['Hybrid1W5MHz_avg_dB']:.2f}",
                    f"{r['Hybrid1W5MHz_Pout1_%']:.1f}", f"{r['Hybrid1W5MHz_Pout2_%']:.1f}"])

print(f"gamma_th1(10MHz)={gamma_th1_10mhz_dB:.2f}dB  gamma_th1(5MHz)={gamma_th1_5mhz_dB:.2f}dB  "
      f"gamma_th2={gamma_th2_dB:.2f}dB (no cambia con B)")
for r in rows:
    print(f"  {r['scenario']:<25} LOS min={r['LOS_min_dB']:>6.2f}dB  DIFF min={r['DIFF_min_dB']:>6.2f}dB  "
          f"Hybrid(1W,5MHz) min={r['Hybrid1W5MHz_min_dB']:>6.2f}dB  Pout@gth2={r['Hybrid1W5MHz_Pout2_%']:.1f}%")
print(f"\nGuardado: {csv_path}")
