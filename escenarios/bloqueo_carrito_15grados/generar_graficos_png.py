"""
Genera las figuras (PNG, 200 dpi, aptas para insertar en la tesis) y las
tablas (PNG + CSV) correspondientes a las metricas indispensables de la
Seccion 5: SINR vs FOV y Probabilidad de Outage (Pout) vs FOV, a partir del
JSON combinado producido por generar_metricas_tablas.py.

Ejecutar generar_metricas_tablas.py primero si resultados/metricas_paper_combinado.json
no existe o esta desactualizado.
"""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_RES_DIR = os.path.join(_THIS_DIR, "resultados")
_OUT_DIR = os.path.join(_RES_DIR, "graficos")
os.makedirs(_OUT_DIR, exist_ok=True)

combinado_path = os.path.join(_RES_DIR, "metricas_paper_combinado.json")
if not os.path.exists(combinado_path):
    raise SystemExit(f"No existe {combinado_path}. Corre primero generar_metricas_tablas.py")

_combinado = json.load(open(combinado_path, encoding="utf-8"))
rows = _combinado["rows"]
seat_label_map = {int(k): v for k, v in _combinado["seat_label_map"].items()}  # obj Zemax -> asiento (paper)
RX_IDXS = sorted(seat_label_map.keys())
SEAT_ORDER = [seat_label_map[rx] for rx in RX_IDXS]  # [1, 2, 3, 4]

# Paleta categorica (misma que la de las skill de dataviz: azul, verde, magenta, amarillo),
# indexada por la etiqueta de asiento del paper (1-4), no por el objeto Zemax.
COLORS_BY_SEAT = {1: "#2a78d6", 2: "#008300", 3: "#e87ba4", 4: "#eda100"}
COLORS = {rx: COLORS_BY_SEAT[seat_label_map[rx]] for rx in RX_IDXS}
COLOR_TH = "#e34948"
COLOR_POUT1 = "#2a78d6"
COLOR_POUT2 = "#e34948"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": "#0b0b0b",
    "xtick.color": "#52514e",
    "ytick.color": "#52514e",
    "axes.grid": True,
    "grid.color": "#e1e0d9",
    "grid.linewidth": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

fovs = [r["fov_deg"] for r in rows]
gamma_th2_dB = rows[0]["gamma_th2_dB"]
gamma_th1_dB = rows[0]["gamma_th1_dB"]

# ---------- Figura 1: SINR vs FOV ----------
fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
for rx in RX_IDXS:
    y = [r["sinr_db"][str(rx)] for r in rows]
    ax.plot(fovs, y, marker="o", markersize=5, linewidth=2, color=COLORS[rx],
            label=f"Asiento {seat_label_map[rx]}")
ax.axhline(gamma_th2_dB, color=COLOR_TH, linestyle="--", linewidth=1.5,
           label=f"$\\gamma_{{th,2}}$ Servicio Objetivo = {gamma_th2_dB:.2f} dB")
ax.set_xlabel("FOV del receptor (grados)")
ax.set_ylabel("SINR (dB)")
ax.set_title("SINR vs FOV — Escenario bloqueo carrito, pitch 15°")
ax.set_xticks(fovs)
all_sinr = [r["sinr_db"][str(rx)] for r in rows for rx in RX_IDXS] + [gamma_th2_dB]
ax.set_ylim(min(all_sinr) - 1.0, max(all_sinr) + 1.0)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=3, frameon=False, fontsize=9.5)
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "sinr_vs_fov.png"), bbox_inches="tight")
plt.close(fig)

# ---------- Figura 2: Pout vs FOV ----------
fig, ax = plt.subplots(figsize=(9, 4), dpi=200)
x = range(len(fovs))
w = 0.35
pout1 = [r["Pout_servicio_minimo"] * 100 for r in rows]
pout2 = [r["Pout_servicio_objetivo"] * 100 for r in rows]
ax.bar([i - w/2 for i in x], pout1, width=w, color=COLOR_POUT1, label="Pout — Servicio Mínimo")
ax.bar([i + w/2 for i in x], pout2, width=w, color=COLOR_POUT2, label="Pout — Servicio Objetivo")
ax.set_xticks(list(x))
ax.set_xticklabels([f"{int(f)}°" for f in fovs])
ax.set_xlabel("FOV del receptor (grados)")
ax.set_ylabel("Pout (%)")
ax.set_ylim(0, 100)
ax.set_title("Probabilidad de Outage vs FOV — Escenario bloqueo carrito, pitch 15°")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False, fontsize=9.5)
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "pout_vs_fov.png"), bbox_inches="tight")
plt.close(fig)

# ---------- Tabla 1 (imagen): SINR por asiento y FOV ----------
col_labels = ["FOV (°)"] + [f"Asiento {seat_label_map[rx]}\n(dB)" for rx in RX_IDXS] + ["Promedio\n(dB)", "Mínimo\n(dB)"]
cell_text = []
for r in rows:
    fila = [f"{int(r['fov_deg'])}"] + [f"{r['sinr_db'][str(rx)]:.2f}" for rx in RX_IDXS] + \
           [f"{r['sinr_prom_dB']:.2f}", f"{r['sinr_min_dB']:.2f}"]
    cell_text.append(fila)

fig, ax = plt.subplots(figsize=(9, 0.42 * (len(rows) + 1) + 0.6), dpi=200)
ax.axis("off")
tabla = ax.table(cellText=cell_text, colLabels=col_labels, cellLoc="center", loc="center")
tabla.auto_set_font_size(False)
tabla.set_fontsize(9.5)
tabla.scale(1, 1.6)
for (row_i, col_i), cell in tabla.get_celld().items():
    cell.set_edgecolor("#e1e0d9")
    if row_i == 0:
        cell.set_facecolor("#f2f1ee")
        cell.set_text_props(weight="bold", color="#0b0b0b")
    elif row_i % 2 == 0:
        cell.set_facecolor("#f7f6f3")
ax.set_title("Tabla 1 — SINR por asiento y FOV (dB)", fontsize=12, pad=14, loc="left", weight="bold")
mapeo_txt = "  ·  ".join(f"Asiento {seat_label_map[rx]} = detector Zemax obj.{rx}" for rx in RX_IDXS)
fig.text(0.01, -0.02, f"Mapeo: {mapeo_txt} (ver mapeo_asientos.csv)", fontsize=7.5, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "tabla_sinr_por_fov.png"), bbox_inches="tight")
plt.close(fig)

# ---------- Tabla 2 (imagen): Pout por FOV ----------
col_labels2 = ["FOV (°)", "γth,1 (dB)", "γth,2 (dB)", "Pout Serv. Mínimo", "Pout Serv. Objetivo"]
cell_text2 = []
for r in rows:
    fila = [f"{int(r['fov_deg'])}", f"{r['gamma_th1_dB']:.2f}", f"{r['gamma_th2_dB']:.2f}",
            f"{r['Pout_servicio_minimo']*100:.1f}%", f"{r['Pout_servicio_objetivo']*100:.1f}%"]
    cell_text2.append(fila)

fig, ax = plt.subplots(figsize=(8, 0.42 * (len(rows) + 1) + 0.6), dpi=200)
ax.axis("off")
tabla2 = ax.table(cellText=cell_text2, colLabels=col_labels2, cellLoc="center", loc="center")
tabla2.auto_set_font_size(False)
tabla2.set_fontsize(9.5)
tabla2.scale(1, 1.6)
for (row_i, col_i), cell in tabla2.get_celld().items():
    cell.set_edgecolor("#e1e0d9")
    if row_i == 0:
        cell.set_facecolor("#f2f1ee")
        cell.set_text_props(weight="bold", color="#0b0b0b")
    elif row_i % 2 == 0:
        cell.set_facecolor("#f7f6f3")
ax.set_title("Tabla 2 — Probabilidad de Outage por FOV", fontsize=12, pad=14, loc="left", weight="bold")
fig.text(0.01, -0.02, "Pout estimada como fraccion de los 4 asientos (ver mapeo_asientos.csv) bajo cada umbral", fontsize=7.5, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "tabla_pout_por_fov.png"), bbox_inches="tight")
plt.close(fig)

print(f"Graficos y tablas PNG guardados en: {_OUT_DIR}")
for fn in ["sinr_vs_fov.png", "pout_vs_fov.png", "tabla_sinr_por_fov.png", "tabla_pout_por_fov.png"]:
    print(f"  - {fn}")
