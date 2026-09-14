"""
M5 (feedback de revision): el paper solo muestra LOS-only y Hybrid; falta
DIFF-only y un mapa de que enlace selecciona el combinador en cada
asiento/FOV. Los datos ya existen en cada sinr_hibrido_oficial.json
(SINR_DIFF_dB y usa_DIFF por asiento y FOV) -- este script solo los
consolida, sin recalcular ni resimular nada.

Genera dos entregables (ingles, mismo patron que los demas *_ingles.py):

1. tables/diff_only_summary.csv + graphs/diff_only_summary.png
   DIFF-only SINR (min/avg/max entre los 4 asientos) por escenario, a
   FOV=90, en el mismo formato que los_vs_hybrid_summary (Tabla 4).

2. tables/selection_map.csv + graphs/selection_map.png
   Para cada escenario y asiento, el porcentaje de los 9 valores de FOV
   del barrido (10-90) en los que el combinador selecciona DIFF por sobre
   LOS (usa_DIFF=True). Responde directamente al pedido de "selection map
   o porcentaje de seleccion LOS/DIFF" del revisor.
"""
import os, csv, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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
RX_IDXS = [6, 7, 8, 9]
SEAT_LABEL = {rx: i + 1 for i, rx in enumerate(RX_IDXS)}


def cargar(nombre):
    path = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


DATA = {nombre: cargar(nombre) for nombre in ESCENARIOS}

# =========== 1) DIFF-only summary at FOV=90 ===========
diff_rows = []
for nombre in ESCENARIOS:
    fila90 = next(f for f in DATA[nombre]["filas"] if f["fov_deg"] == 90.0)
    diff_vals = [v["SINR_DIFF_dB"] for v in fila90["asientos"].values()]
    diff_rows.append({"escenario": NOMBRE_EN[nombre], "min": min(diff_vals),
                       "avg": sum(diff_vals) / len(diff_vals), "max": max(diff_vals)})

csv_path = os.path.join(_TABLES_DIR, "diff_only_summary.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Scenario", "DIFF_min_dB", "DIFF_avg_dB", "DIFF_max_dB"])
    for r in diff_rows:
        w.writerow([r["escenario"], f"{r['min']:.2f}", f"{r['avg']:.2f}", f"{r['max']:.2f}"])

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "figure.facecolor": "white", "axes.facecolor": "white",
})
col_labels = ["Scenario", "DIFF-only SINR\nmin (dB)", "DIFF-only SINR\navg (dB)", "DIFF-only SINR\nmax (dB)"]
cell_text = [[r["escenario"], f"{r['min']:.2f}", f"{r['avg']:.2f}", f"{r['max']:.2f}"] for r in diff_rows]
fig, ax = plt.subplots(figsize=(9, 0.42 * (len(diff_rows) + 1) + 1.0), dpi=200)
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
ax.set_title("DIFF-Only SINR at FOV=90° (Min/Avg/Max Across the Four Seats)", fontsize=12.5, pad=14, loc="left", weight="bold")
fig.text(0.01, -0.05,
          "DIFF-only baseline (gamma_DIFF alone, no selection combining), directly from the already-exported\n"
          "SINR_DIFF_dB field -- no new simulation. Compare against Table 4 (LOS-only) and Table 6 (Hybrid).",
          fontsize=8, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_GRAPHS_DIR, "diff_only_summary.png"), bbox_inches="tight")
plt.close(fig)

# =========== 2) Selection map: % of FOV sweep where DIFF is selected ===========
sel_rows = []
for nombre in ESCENARIOS:
    filas = DATA[nombre]["filas"]
    n_fov = len(filas)
    row = {"escenario": NOMBRE_EN[nombre]}
    for rx in RX_IDXS:
        n_diff = sum(1 for fila in filas if fila["asientos"][str(rx)]["usa_DIFF"])
        row[f"seat{SEAT_LABEL[rx]}_pct"] = 100.0 * n_diff / n_fov
    sel_rows.append(row)

csv_path2 = os.path.join(_TABLES_DIR, "selection_map.csv")
with open(csv_path2, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Scenario", "Seat1_%DIFF_selected", "Seat2_%DIFF_selected",
                "Seat3_%DIFF_selected", "Seat4_%DIFF_selected"])
    for r in sel_rows:
        w.writerow([r["escenario"], f"{r['seat1_pct']:.0f}", f"{r['seat2_pct']:.0f}",
                    f"{r['seat3_pct']:.0f}", f"{r['seat4_pct']:.0f}"])

# Heatmap PNG
mat = np.array([[r[f"seat{s}_pct"] for s in range(1, 5)] for r in sel_rows])
fig, ax = plt.subplots(figsize=(6.5, 6), dpi=200)
im = ax.imshow(mat, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
ax.set_xticks(range(4))
ax.set_xticklabels([f"Seat {s}" for s in range(1, 5)])
ax.set_yticks(range(len(sel_rows)))
ax.set_yticklabels([r["escenario"] for r in sel_rows])
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax.text(j, i, f"{mat[i,j]:.0f}%", ha="center", va="center",
                 color="#0b0b0b", fontsize=9.5)
ax.set_title("Selection Map: % of FOV Sweep (10°-90°) Where DIFF is Selected", fontsize=11.5, pad=12)
cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("% of FOV sweep DIFF selected")
fig.text(0.01, -0.04,
          "100% = DIFF selected at every evaluated FOV (10°-90°) for that seat; the hybrid combiner never falls\n"
          "back to LOS in that case. Directly from the already-exported usa_DIFF flag -- no new simulation.",
          fontsize=7.5, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_GRAPHS_DIR, "selection_map.png"), bbox_inches="tight")
plt.close(fig)

print("Saved to:", _GENERALES_DIR)
print("  - tables/diff_only_summary.csv, graphs/diff_only_summary.png")
print("  - tables/selection_map.csv, graphs/selection_map.png")
