"""
Tabla de outage LOS-only con ambos umbrales (gamma_th,1 y gamma_th,2),
pedida tras la correccion del umbral objetivo (13.54dB -> 19.56dB, ver
noise_model.sinr_threshold_from_ber). Con el umbral nuevo, buena parte del
LOS-only sin bloqueo (~18.4dB en pitch=0) ya queda bajo el objetivo -- algo
que no se ve en ningun lado si solo se reporta el outage del Hybrid.

Consolidado a FOV=90, los 9 escenarios, sobre SINR_LOS_dB (no SINR_hybrid_dB).
"""
import os, csv, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import noise_model as nm

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_GENERALES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales")
_TABLES_DIR = os.path.join(_GENERALES_DIR, "tables")
_GRAPHS_DIR = os.path.join(_GENERALES_DIR, "graphs")
os.makedirs(_TABLES_DIR, exist_ok=True)
os.makedirs(_GRAPHS_DIR, exist_ok=True)

ESCENARIOS = [
    "sin_bloqueo_0grados", "sin_bloqueo_15grados", "sin_bloqueo_30grados",
    "bloqueo_carrito_0grados", "bloqueo_carrito_15grados", "bloqueo_carrito_30grados",
    "bloqueo_persona_0grados", "bloqueo_persona_15grados", "bloqueo_persona_30grados",
]
NOMBRE_EN = {
    "sin_bloqueo_0grados": "No Blockage – 0°", "sin_bloqueo_15grados": "No Blockage – 15°",
    "sin_bloqueo_30grados": "No Blockage – 30°", "bloqueo_carrito_0grados": "Cart Blockage – 0°",
    "bloqueo_carrito_15grados": "Cart Blockage – 15°", "bloqueo_carrito_30grados": "Cart Blockage – 30°",
    "bloqueo_persona_0grados": "Passenger Blockage – 0°", "bloqueo_persona_15grados": "Passenger Blockage – 15°",
    "bloqueo_persona_30grados": "Passenger Blockage – 30°",
}

gamma_th1_dB = nm.db(nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, nm.BANDWIDTH_HZ))
gamma_th2_dB = nm.db(nm.sinr_threshold_from_ber(nm.BER_MAX))

rows = []
for nombre in ESCENARIOS:
    path = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    fila90 = next(f for f in d["filas"] if f["fov_deg"] == 90.0)
    vals = [v["SINR_LOS_dB"] for v in fila90["asientos"].values()]
    n = len(vals)
    pout_min = 100.0 * sum(1 for x in vals if x < gamma_th1_dB) / n
    pout_obj = 100.0 * sum(1 for x in vals if x < gamma_th2_dB) / n
    rows.append({"escenario": NOMBRE_EN[nombre], "pout_min": pout_min, "pout_obj": pout_obj})

csv_path = os.path.join(_TABLES_DIR, "los_only_outage_both_thresholds.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Scenario", f"Outage_MinService_gamma1={gamma_th1_dB:.2f}dB_%",
                f"Outage_TargetService_gamma2={gamma_th2_dB:.2f}dB_%"])
    for r in rows:
        w.writerow([r["escenario"], f"{r['pout_min']:.1f}", f"{r['pout_obj']:.1f}"])

plt.rcParams.update({"font.family": "sans-serif", "font.size": 11,
                      "figure.facecolor": "white", "axes.facecolor": "white"})
col_labels = ["Scenario", f"Outage Min. Svc\n(γth,1={gamma_th1_dB:.2f}dB, %)",
              f"Outage Target Svc\n(γth,2={gamma_th2_dB:.2f}dB, %)"]
cell_text = [[r["escenario"], f"{r['pout_min']:.1f}%", f"{r['pout_obj']:.1f}%"] for r in rows]
fig, ax = plt.subplots(figsize=(8.5, 0.42 * (len(rows) + 1) + 1.0), dpi=200)
ax.axis("off")
tabla = ax.table(cellText=cell_text, colLabels=col_labels, cellLoc="center", loc="center")
tabla.auto_set_font_size(False)
tabla.set_fontsize(9.5)
tabla.scale(1, 2.4)
for (row_i, col_i), cell in tabla.get_celld().items():
    cell.set_edgecolor("#e1e0d9")
    if row_i == 0:
        cell.set_facecolor("#f2f1ee")
        cell.set_text_props(weight="bold", color="#0b0b0b")
    elif row_i % 2 == 0:
        cell.set_facecolor("#f7f6f3")
ax.set_title("LOS-Only Outage at FOV=90°, Both Service Thresholds", fontsize=12.5, pad=14, loc="left", weight="bold")
fig.text(0.01, -0.05,
          "Unlike the hybrid link (0% outage everywhere at FOV=90), LOS-only already shows substantial target-\n"
          "service outage with the corrected gamma_th,2=19.56dB -- including the no-blockage scenarios, since\n"
          "unblocked LOS SINR (~18.4dB at pitch=0) sits below this threshold even with no obstruction at all.",
          fontsize=7.5, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_GRAPHS_DIR, "los_only_outage_both_thresholds.png"), bbox_inches="tight")
plt.close(fig)

print(f"gamma_th1={gamma_th1_dB:.2f}dB  gamma_th2={gamma_th2_dB:.2f}dB")
for r in rows:
    print(f"  {r['escenario']}: Pout_min={r['pout_min']:.1f}%  Pout_obj={r['pout_obj']:.1f}%")
print("\nSaved to:", _GENERALES_DIR)
print("  - tables/los_only_outage_both_thresholds.csv")
print("  - graphs/los_only_outage_both_thresholds.png")
