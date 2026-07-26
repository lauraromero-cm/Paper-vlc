"""
Sintesis comparativa entre los 3 escenarios (sin_bloqueo, bloqueo_carrito,
bloqueo_persona) x 3 pitches (0/15/30), para los entregables de la Seccion 6:

  1. Diseno Optico Optimo: FOVopt por zona de cabina (a partir de sin_bloqueo,
     el unico escenario sin outages, buscando el FOV que maximiza el peor caso
     de SINR entre asientos).
  2. Mapas de Cobertura / Pout comparativos: Pout promedio por escenario y
     pitch, mostrando que solo bloqueo_persona genera outages reales.
  3. Validacion de Resiliencia: comparacion directa de SINR vs FOV del asiento
     bloqueado (asiento 1) entre los 3 escenarios, mostrando que ningun FOV
     restaura el servicio bajo bloqueo total de linea de vista.

Requiere que los 9 metricas_paper_combinado.json ya existan (sin_bloqueo,
bloqueo_carrito, bloqueo_persona, cada uno en pitch 0/15/30).
"""
import os, json, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
_OUT_DIR = _THIS_DIR
os.makedirs(_OUT_DIR, exist_ok=True)

ESCENARIOS = ["sin_bloqueo", "bloqueo_carrito", "bloqueo_persona"]
ESCENARIO_LABEL = {"sin_bloqueo": "Sin bloqueo", "bloqueo_carrito": "Bloqueo carrito",
                    "bloqueo_persona": "Bloqueo persona"}
PITCHES = [0, 15, 30]

# Paleta categorica fija (misma usada en todo el proyecto): azul, verde, magenta.
# Aqui identifica ESCENARIO (no asiento), en el mismo orden fijo establecido.
COLOR_ESCENARIO = {"sin_bloqueo": "#2a78d6", "bloqueo_carrito": "#008300", "bloqueo_persona": "#e34948"}

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


def cargar(escenario, pitch):
    path = os.path.join(_PROJECT_ROOT, "escenarios", f"{escenario}_{pitch}grados",
                         "resultados", "metricas_paper_combinado.json")
    d = json.load(open(path, encoding="utf-8"))
    return d["rows"], {int(k): v for k, v in d["seat_label_map"].items()}


# Carga todo una sola vez
DATA = {}
for esc in ESCENARIOS:
    for p in PITCHES:
        rows, seat_map = cargar(esc, p)
        DATA[(esc, p)] = {"rows": rows, "seat_map": seat_map}

RX_IDXS = sorted(DATA[("sin_bloqueo", 0)]["seat_map"].keys())
SEAT_OF = DATA[("sin_bloqueo", 0)]["seat_map"]  # {6:1, 7:2, 8:3, 9:4}


# =====================================================================
# 1) Diseno Optico Optimo (FOVopt) -- a partir de sin_bloqueo (sin outages)
#
# Hallazgo clave: el SINR es practicamente invariante al FOV en ausencia de
# bloqueo (variacion <0.2 dB en todo el barrido 5-90 grados, dentro del ruido
# de Monte Carlo) -- la ganancia del concentrador multiplica por igual la
# senal propia y la interferencia, asi que su razon (el SINR) no cambia con
# el FOV; solo el ruido termico varia, y es un aporte marginal frente a
# senal/interferencia. Por eso NO se recomienda el FOV que maximiza el SINR
# puntual (seria ajustar al ruido), sino el FOVopt=90 grados (maximo posible):
# no cuesta nada en SINR nominal y maximiza el angulo de aceptancia, dando
# la mejor chance de capturar rutas NLOS/reflejadas si a futuro se modelan
# superficies difusoras en la cabina (la unica ventaja real de ampliar el FOV
# bajo el modelo actual, sin reflexiones, es esa robustez potencial).
# =====================================================================
FOV_RECOMENDADO = 90.0
fovopt_rows = []
for p in PITCHES:
    rows = DATA[("sin_bloqueo", p)]["rows"]
    sinr_min_vals = [r["sinr_min_dB"] for r in rows]
    rec = next(r for r in rows if r["fov_deg"] == FOV_RECOMENDADO)
    fovopt_rows.append({
        "pitch_deg": p,
        "fov_opt_deg": FOV_RECOMENDADO,
        "sinr_min_dB": rec["sinr_min_dB"],
        "sinr_prom_dB": rec["sinr_prom_dB"],
        "spread_dB": max(sinr_min_vals) - min(sinr_min_vals),
    })

csv_path = os.path.join(_OUT_DIR, "tabla_fovopt.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Pitch (deg)", "FOVopt (deg)", "SINR minimo en FOVopt (dB)", "SINR promedio en FOVopt (dB)",
                "Variacion SINR minimo en todo el barrido 5-90 (dB)"])
    for r in fovopt_rows:
        w.writerow([r["pitch_deg"], int(r["fov_opt_deg"]), f"{r['sinr_min_dB']:.2f}", f"{r['sinr_prom_dB']:.2f}",
                     f"{r['spread_dB']:.2f}"])

fig, ax = plt.subplots(figsize=(9.5, 2.6), dpi=200)
ax.axis("off")
col_labels = ["Pitch (°)", "FOVopt\nrecomendado (°)", "SINR mínimo\n(peor asiento, dB)", "SINR promedio\n(dB)",
              "Variación SINR mínimo\nen todo 5°-90° (dB)"]
cell_text = [[f"{r['pitch_deg']}", f"{int(r['fov_opt_deg'])}", f"{r['sinr_min_dB']:.2f}", f"{r['sinr_prom_dB']:.2f}",
              f"± {r['spread_dB']:.2f}"] for r in fovopt_rows]
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
ax.set_title("Diseño Óptico Óptimo — FOVopt = 90° (máximo) recomendado para todos los pitches", fontsize=12,
             pad=14, loc="left", weight="bold")
fig.text(0.01, -0.08,
          "El SINR es practicamente invariante al FOV sin bloqueo (variacion < 0.2 dB en 5°-90°, dentro del\n"
          "ruido de simulacion): la ganancia del concentrador escala por igual senal e interferencia. Se\n"
          "recomienda el FOV maximo (90°) porque no tiene costo en SINR nominal y maximiza el angulo de\n"
          "aceptancia, mejorando la posibilidad de captar rutas NLOS/reflejadas ante bloqueo.",
          fontsize=7.5, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "tabla_fovopt.png"), bbox_inches="tight")
plt.close(fig)

# =====================================================================
# 2) Mapas de Cobertura / Pout comparativos por escenario y pitch
# =====================================================================
pout_rows = []
for esc in ESCENARIOS:
    for p in PITCHES:
        rows = DATA[(esc, p)]["rows"]
        pout_prom_min = sum(r["Pout_servicio_minimo"] for r in rows) / len(rows) * 100
        pout_prom_obj = sum(r["Pout_servicio_objetivo"] for r in rows) / len(rows) * 100
        pout_rows.append({"escenario": esc, "pitch_deg": p,
                           "pout_prom_minimo_pct": pout_prom_min, "pout_prom_objetivo_pct": pout_prom_obj})

csv_path2 = os.path.join(_OUT_DIR, "tabla_pout_comparativa.csv")
with open(csv_path2, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Escenario", "Pitch (deg)", "Pout promedio Serv. Minimo (%)", "Pout promedio Serv. Objetivo (%)"])
    for r in pout_rows:
        w.writerow([ESCENARIO_LABEL[r["escenario"]], r["pitch_deg"],
                     f"{r['pout_prom_minimo_pct']:.1f}", f"{r['pout_prom_objetivo_pct']:.1f}"])

fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
x = range(len(PITCHES))
w = 0.25
for i, esc in enumerate(ESCENARIOS):
    vals = [next(r["pout_prom_objetivo_pct"] for r in pout_rows if r["escenario"] == esc and r["pitch_deg"] == p)
            for p in PITCHES]
    offset = (i - 1) * w
    bars = ax.bar([xi + offset for xi in x], vals, width=w, color=COLOR_ESCENARIO[esc], label=ESCENARIO_LABEL[esc])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v + 1.0, f"{v:.0f}%", ha="center", fontsize=9, weight="bold")
ax.set_xticks(list(x))
ax.set_xticklabels([f"{p}°" for p in PITCHES])
ax.set_xlabel("Pitch (grados)")
ax.set_ylabel("Pout promedio — Servicio Objetivo (%)")
ax.set_ylim(0, 35)
ax.set_title("Probabilidad de Outage comparada entre escenarios (promedio sobre FOV 5°-90°)")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False, fontsize=9.5)
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "comparacion_pout_escenarios.png"), bbox_inches="tight")
plt.close(fig)

# =====================================================================
# 3) Validacion de Resiliencia: SINR vs FOV del asiento 1 (el bloqueado),
#    comparando los 3 escenarios, un panel por pitch.
# =====================================================================
ASIENTO_OBJ = 6  # detector Zemax del Asiento 1 (el que se bloquea en bloqueo_persona)

fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=200, sharey=True)
all_finite = []
for p in PITCHES:
    for esc in ESCENARIOS:
        for r in DATA[(esc, p)]["rows"]:
            v = r["sinr_db"][str(ASIENTO_OBJ)]
            if v != float("-inf"):
                all_finite.append(v)
gamma_th2_dB = DATA[("sin_bloqueo", 0)]["rows"][0]["gamma_th2_dB"]
all_finite.append(gamma_th2_dB)
floor_dB = min(all_finite) - 5.0

LINESTYLE_ESCENARIO = {"sin_bloqueo": "-", "bloqueo_carrito": "--", "bloqueo_persona": "-"}
MARKER_ESCENARIO = {"sin_bloqueo": "o", "bloqueo_carrito": "^", "bloqueo_persona": "o"}

for ax, p in zip(axes, PITCHES):
    for esc in ESCENARIOS:
        rows = DATA[(esc, p)]["rows"]
        fovs = [r["fov_deg"] for r in rows]
        y_raw = [r["sinr_db"][str(ASIENTO_OBJ)] for r in rows]
        y = [floor_dB if v == float("-inf") else v for v in y_raw]
        ax.plot(fovs, y, marker=MARKER_ESCENARIO[esc], markersize=5, linewidth=2,
                linestyle=LINESTYLE_ESCENARIO[esc], color=COLOR_ESCENARIO[esc],
                label=ESCENARIO_LABEL[esc])
        bloqueados = [f for f, v in zip(fovs, y_raw) if v == float("-inf")]
        if bloqueados:
            ax.scatter(bloqueados, [floor_dB] * len(bloqueados), marker="x", s=70,
                       color=COLOR_ESCENARIO[esc], zorder=5, linewidths=2.2)
    ax.axhline(gamma_th2_dB, color="#0b0b0b", linestyle="--", linewidth=1.0, alpha=0.6)
    ax.set_title(f"Pitch {p}°")
    ax.set_xlabel("FOV del receptor (°)")
    ax.set_xticks(fovs)
    ax.tick_params(axis='x', labelrotation=45)
axes[0].set_ylabel("SINR (dB) — Asiento 1")
axes[0].set_ylim(floor_dB - 1.0, max(all_finite) + 1.0)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=3, frameon=False, fontsize=10)
fig.suptitle("Validación de Resiliencia — SINR del asiento bloqueado vs FOV, comparando escenarios",
             fontsize=13, y=1.02)
fig.text(0.01, -0.14, "× = bloqueo total de señal propia (-∞ dB), graficado en el piso solo para visualización. "
         "Línea punteada = γth,2 Servicio Objetivo. Ningún FOV restaura el servicio bajo bloqueo_persona.",
         fontsize=8, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "validacion_resiliencia_asiento_bloqueado.png"), bbox_inches="tight")
plt.close(fig)

print(f"Guardado en: {_OUT_DIR}")
for fn in ["tabla_fovopt.csv", "tabla_fovopt.png", "tabla_pout_comparativa.csv",
           "comparacion_pout_escenarios.png", "validacion_resiliencia_asiento_bloqueado.png"]:
    print(f"  - {fn}")
