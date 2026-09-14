"""
M9 (feedback de revision): tabla de validacion Zemax-vs-analitico (canal
Lambertiano, Ec. 5 del paper), para los 4 asientos en el estado LOS
despejado (sin bloqueo, pitch=0, FOV=90).

Geometria extraida directamente del .zmx (texto plano, lineas NSOP: X Y Z
TiltX TiltY TiltZ), sin abrir Zemax -- ver conversacion/commit para el
detalle de como se identifico. Las 4 lamparas LOS (Tx2-5) y sus 4
receptores propios (Rx6-9) comparten X e Y; solo difieren en Z por 53
unidades del modelo, con phi=psi=0 (perfectamente enfrentados).

*** PENDIENTE DE CONFIRMAR (ver mensaje adjunto): si esas 53 unidades de
separacion en Z ya estan en mm reales o necesitan el factor de escala 1:5
documentado en P0-1 (que aplica, segun la propia nota de P0-1, a la
proporcion en X -- no necesariamente a Z). Con Z sin escalar (d=53mm) el
error vs. Zemax es +6.0% a +6.3% en los 4 asientos (consistente, plausible
como resultado de validacion). Con Z escalado x5 (d=265mm) el error es
+2550% (fisicamente inconsistente). Este script usa por defecto Z SIN
escalar; cambiar Z_SCALE_FACTOR a 5.0 si se confirma lo contrario.
"""
import os, csv, math
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

# --- Geometria extraida del .zmx (ver docstring) ---
D_MODEL_UNITS = 53.0            # separacion Tx-Rx propia, unidades del modelo, eje Z
Z_SCALE_FACTOR = 1.0            # <-- PENDIENTE DE CONFIRMAR: 1.0 (sin escalar) o 5.0
D_REAL_M = D_MODEL_UNITS * Z_SCALE_FACTOR / 1000.0
PHI_DEG = 0.0                   # angulo de irradiancia en el Tx (perfectamente enfrentado)
PSI_DEG = 0.0                   # angulo de incidencia en el Rx

FOV_REF = 90.0
POPT_W = 2.0

g = nm.concentrator_gain(FOV_REF)
H_analitico = ((nm.RESPONSIVITY * 0 + 1) * 0)  # placeholder removed below
m = 1.0
H_analitico = ((m + 1) * nm.DETECTOR_AREA / (2 * math.pi * D_REAL_M ** 2)
               * math.cos(math.radians(PHI_DEG)) ** m
               * nm.FILTER_TRANSMISSION * g * math.cos(math.radians(PSI_DEG)))
Pr_analitico_mW = POPT_W * H_analitico * 1000.0

import json
SEATS = {"Seat 1 (RX6)": 6, "Seat 2 (RX7)": 7, "Seat 3 (RX8)": 8, "Seat 4 (RX9)": 9}
path = os.path.join(_PROJECT_ROOT, "escenarios", "sin_bloqueo_0grados", "resultados", "sinr_hibrido_oficial.json")
with open(path, encoding="utf-8") as f:
    d = json.load(f)
fila90 = next(f for f in d["filas"] if f["fov_deg"] == FOV_REF)

rows = []
for label, rx in SEATS.items():
    pr_zemax_mW = fila90["asientos"][str(rx)]["Pr_own_LOS_mW"]
    err_pct = 100.0 * (pr_zemax_mW - Pr_analitico_mW) / Pr_analitico_mW
    rows.append({"seat": label, "pr_zemax": pr_zemax_mW, "err_pct": err_pct})

# ---------- CSV ----------
csv_path = os.path.join(_TABLES_DIR, "analytical_validation.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Seat", "H_analytical", "Pr_analytical_mW", "Pr_Zemax_mW", "Relative_error_%"])
    for r in rows:
        w.writerow([r["seat"], f"{H_analitico:.6e}", f"{Pr_analitico_mW:.4f}",
                    f"{r['pr_zemax']:.4f}", f"{r['err_pct']:+.2f}"])

# ---------- PNG (table) ----------
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "figure.facecolor": "white", "axes.facecolor": "white",
})
col_labels = ["Seat", "Pr,analytical\n(mW)", "Pr,Zemax\n(mW)", "Relative\nerror (%)"]
cell_text = [[r["seat"], f"{Pr_analitico_mW:.3f}", f"{r['pr_zemax']:.3f}", f"{r['err_pct']:+.2f}%"] for r in rows]
fig, ax = plt.subplots(figsize=(9, 0.42 * (len(rows) + 1) + 1.0), dpi=200)
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
ax.set_title(f"Zemax vs. Analytical Lambertian Channel (m={int(m)}, d={D_REAL_M*1000:.0f} mm, FOV=90°, no blockage)",
             fontsize=11.5, pad=14, loc="left", weight="bold")
fig.text(0.01, -0.05,
          "PENDING CONFIRMATION: Tx-Rx vertical separation extracted from the .zmx (53 model units) is assumed\n"
          "already in real mm here (Z_SCALE_FACTOR=1.0), not scaled by the 1:5 CAD factor documented for the\n"
          "lateral (X) axis in P0-1. If Z also requires x5 scaling, this table must be regenerated -- see project notes.",
          fontsize=7.5, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_GRAPHS_DIR, "analytical_validation.png"), bbox_inches="tight")
plt.close(fig)

print(f"D_REAL_M = {D_REAL_M} m (Z_SCALE_FACTOR={Z_SCALE_FACTOR})")
print(f"H_analitico = {H_analitico:.6e}   Pr_analitico = {Pr_analitico_mW:.4f} mW")
for r in rows:
    print(f"  {r['seat']}: Pr_Zemax={r['pr_zemax']:.4f} mW  error={r['err_pct']:+.2f}%")
print(f"\nSaved to: {_GENERALES_DIR}")
print("  - tables/analytical_validation.csv")
print("  - graphs/analytical_validation.png")
