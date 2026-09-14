"""
M7 (feedback de revision): el 2.8% de "outage promedio sobre el barrido de
FOV" no es una probabilidad fisicamente interpretable (el FOV es una
variable de diseno controlada, no aleatoria) -- es 25%/9 colapsado en un
solo numero. Esta figura muestra Pout(target service) explicitamente para
cada combinacion escenario x FOV (matriz 9x9), a partir de los
outage_by_fov.csv que el pipeline ya exporta por escenario -- sin
recalcular ni resimular nada.

Output (ingles):
  resultados_generales/tables/outage_by_fov_matrix.csv
  resultados_generales/graphs/outage_by_fov_heatmap.png
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

fov_list = None
matrix_rows = []
for nombre in ESCENARIOS:
    path = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    row = []
    fovs = []
    for fila in d["filas"]:
        asientos = fila["asientos"].values()
        n = len(asientos)
        pout_obj_pct = 100.0 * sum(1 for v in asientos if v["outage_servicio_objetivo"]) / n
        row.append(pout_obj_pct)
        fovs.append(fila["fov_deg"])
    if fov_list is None:
        fov_list = fovs
    matrix_rows.append(row)

matrix = np.array(matrix_rows)

# ---------- CSV ----------
csv_path = os.path.join(_TABLES_DIR, "outage_by_fov_matrix.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Scenario"] + [f"FOV_{int(fov)}deg" for fov in fov_list])
    for nombre, row in zip(ESCENARIOS, matrix_rows):
        w.writerow([NOMBRE_EN[nombre]] + [f"{v:.0f}" for v in row])

# ---------- PNG (heatmap) ----------
plt.rcParams.update({"font.family": "sans-serif", "font.size": 11,
                      "figure.facecolor": "white", "axes.facecolor": "white"})
fig, ax = plt.subplots(figsize=(9, 6), dpi=200)
im = ax.imshow(matrix, cmap="RdYlGn_r", vmin=0, vmax=25, aspect="auto")
ax.set_xticks(range(len(fov_list)))
ax.set_xticklabels([f"{int(f)}°" for f in fov_list])
ax.set_yticks(range(len(ESCENARIOS)))
ax.set_yticklabels([NOMBRE_EN[n] for n in ESCENARIOS])
ax.set_xlabel("Receiver FOV")
for i in range(matrix.shape[0]):
    for j in range(matrix.shape[1]):
        v = matrix[i, j]
        label = f"{v:.0f}%" if v > 0 else "0"
        ax.text(j, i, label, ha="center", va="center",
                 color="#0b0b0b" if v == 0 else "#5a0000", fontsize=9,
                 weight="bold" if v > 0 else "normal")
ax.set_title("Target-Service Outage Fraction, Ψc × Scenario\n(seat-outage fraction, not a spatial probability — see Sec. Outage Probability)",
             fontsize=11, pad=14)
cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cbar.set_label("Outage fraction (%)")
fig.tight_layout()
fig.savefig(os.path.join(_GRAPHS_DIR, "outage_by_fov_heatmap.png"), bbox_inches="tight")
plt.close(fig)

print("Saved to:", _GENERALES_DIR)
print("  - tables/outage_by_fov_matrix.csv")
print("  - graphs/outage_by_fov_heatmap.png")
