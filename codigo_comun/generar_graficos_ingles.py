"""
Genera versiones en ingles de los graficos (PNG) a partir de los
sinr_hibrido_oficial.json, en carpetas separadas de las version en
espanol (no las pisa, no las modifica).

Por escenario: escenarios/<nombre>/resultados/graphs/
  - sinr_vs_fov.png
  - pout_vs_fov.png

Consolidado: resultados_generales/graphs/
  - comparison_sinr_hybrid_scenarios.png

Requiere que pipeline_oficial.py ya se haya corrido (usa los mismos
sinr_hibrido_oficial.json que generar_tablas_graficos_oficial.py).
"""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_GENERALES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales")

RX_IDXS = [6, 7, 8, 9]
SEAT_LABEL = {rx: i + 1 for i, rx in enumerate(RX_IDXS)}
COLORS_BY_SEAT = {1: "#2a78d6", 2: "#008300", 3: "#e87ba4", 4: "#eda100"}
COLOR_TH2 = "#e34948"
COLOR_POUT1 = "#2a78d6"
COLOR_POUT2 = "#e34948"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#0b0b0b",
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.8,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

ESCENARIOS = [
    "sin_bloqueo_0grados", "sin_bloqueo_15grados", "sin_bloqueo_30grados",
    "bloqueo_carrito_0grados", "bloqueo_carrito_15grados", "bloqueo_carrito_30grados",
    "bloqueo_persona_0grados", "bloqueo_persona_15grados", "bloqueo_persona_30grados",
]

NOMBRE_EN = {
    "sin_bloqueo_0grados": "No Blockage – 0°",
    "sin_bloqueo_15grados": "No Blockage – 15°",
    "sin_bloqueo_30grados": "No Blockage – 30°",
    "bloqueo_carrito_0grados": "Cart Blockage – 0°",
    "bloqueo_carrito_15grados": "Cart Blockage – 15°",
    "bloqueo_carrito_30grados": "Cart Blockage – 30°",
    "bloqueo_persona_0grados": "Passenger Blockage – 0°",
    "bloqueo_persona_15grados": "Passenger Blockage – 15°",
    "bloqueo_persona_30grados": "Passenger Blockage – 30°",
}


def procesar_escenario(nombre):
    res_dir = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados")
    json_path = os.path.join(res_dir, "sinr_hibrido_oficial.json")
    if not os.path.exists(json_path):
        print(f"  [skipped] {json_path} does not exist")
        return None
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)
    filas = d["filas"]
    gamma_th2 = d["parametros"]["gamma_th2_servicio_objetivo_dB"]
    fovs = [f["fov_deg"] for f in filas]
    titulo_en = NOMBRE_EN[nombre]

    graf_dir = os.path.join(res_dir, "graphs")
    os.makedirs(graf_dir, exist_ok=True)

    # ---------- SINR vs FOV ----------
    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    for rx in RX_IDXS:
        s = SEAT_LABEL[rx]
        color = COLORS_BY_SEAT[s]
        y_hybrid = [fila["asientos"][str(rx)]["SINR_hybrid_dB"] for fila in filas]
        y_los = [fila["asientos"][str(rx)]["SINR_LOS_dB"] for fila in filas]
        y_diff = [fila["asientos"][str(rx)]["SINR_DIFF_dB"] for fila in filas]
        ax.plot(fovs, y_hybrid, marker="o", markersize=5, linewidth=2.2, color=color,
                label=f"Seat {s} — Hybrid")
        ax.plot(fovs, y_los, linestyle="--", linewidth=1.2, color=color, alpha=0.6)
        ax.plot(fovs, y_diff, linestyle=":", linewidth=1.2, color=color, alpha=0.6)
    ax.axhline(gamma_th2, color=COLOR_TH2, linestyle="--", linewidth=1.5,
               label=f"$\\gamma_{{th,2}}$ = {gamma_th2:.2f} dB")
    ax.set_xlabel("Receiver FOV (degrees)")
    ax.set_ylabel("SINR (dB)")
    ax.set_title(f"SINR vs FOV (Hybrid solid, LOS dashed, DIFF dotted) — {titulo_en}")
    ax.set_xticks(fovs)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.38), ncol=3, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(graf_dir, "sinr_vs_fov.png"), bbox_inches="tight")
    plt.close(fig)

    # ---------- Pout vs FOV ----------
    fig, ax = plt.subplots(figsize=(9, 4), dpi=200)
    x = range(len(fovs))
    w_bar = 0.35
    pout1, pout2 = [], []
    for fila in filas:
        asientos = fila["asientos"].values()
        n = len(asientos)
        pout1.append(100 * sum(1 for v in asientos if v["outage_servicio_minimo"]) / n)
        pout2.append(100 * sum(1 for v in asientos if v["outage_servicio_objetivo"]) / n)
    ax.bar([i - w_bar/2 for i in x], pout1, width=w_bar, color=COLOR_POUT1, label="Pout — Minimum Service")
    ax.bar([i + w_bar/2 for i in x], pout2, width=w_bar, color=COLOR_POUT2, label="Pout — Target Service")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{int(f)}°" for f in fovs])
    ax.set_xlabel("Receiver FOV (degrees)")
    ax.set_ylabel("Outage Probability (%)")
    ax.set_ylim(0, 100)
    ax.set_title(f"Outage Probability vs FOV — {titulo_en}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(os.path.join(graf_dir, "pout_vs_fov.png"), bbox_inches="tight")
    plt.close(fig)

    fila90 = next(f for f in filas if f["fov_deg"] == 90.0)
    sinr_hybrid_90 = [v["SINR_hybrid_dB"] for v in fila90["asientos"].values()]
    return {
        "nombre": nombre,
        "titulo_en": titulo_en,
        "sinr_hybrid_min_fov90": min(sinr_hybrid_90),
        "sinr_hybrid_prom_fov90": sum(sinr_hybrid_90) / len(sinr_hybrid_90),
    }


resumen = []
for nombre in ESCENARIOS:
    print(f"Processing {nombre}...")
    r = procesar_escenario(nombre)
    if r:
        resumen.append(r)

# ---------- Comparison chart ----------
graf_gen_dir = os.path.join(_GENERALES_DIR, "graphs")
os.makedirs(graf_gen_dir, exist_ok=True)

fig, ax = plt.subplots(figsize=(10, 5), dpi=200)
titulos = [r["titulo_en"] for r in resumen]
mins = [r["sinr_hybrid_min_fov90"] for r in resumen]
proms = [r["sinr_hybrid_prom_fov90"] for r in resumen]
x = range(len(titulos))
w_bar = 0.35
ax.bar([i - w_bar/2 for i in x], mins, width=w_bar, color="#2a78d6", label="Minimum Hybrid SINR (worst seat)")
ax.bar([i + w_bar/2 for i in x], proms, width=w_bar, color="#008300", label="Average Hybrid SINR")
ax.set_xticks(list(x))
ax.set_xticklabels(titulos, rotation=35, ha="right", fontsize=8.5)
ax.set_ylabel("SINR (dB)")
ax.set_title("Hybrid SINR Comparison (FOV=90°) Across the 9 Official Scenarios")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=2, frameon=False, fontsize=9.5)
fig.tight_layout()
comp_png = os.path.join(graf_gen_dir, "comparison_sinr_hybrid_scenarios.png")
fig.savefig(comp_png, bbox_inches="tight")
plt.close(fig)
print(f"Comparison chart saved to: {comp_png}")

print("\n=== DONE ===")
