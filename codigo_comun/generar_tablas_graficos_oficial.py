"""
Genera tablas (CSV) y graficos (PNG) a partir de los sinr_hibrido_oficial.json
producidos por pipeline_oficial.py, para los 9 escenarios oficiales.

Por escenario (en escenarios/<nombre>/resultados/):
  - tabla_sinr_hibrido_por_fov.csv: SINR LOS/DIFF/Hybrid por asiento y FOV
  - tabla_pout_por_fov.csv: Pout (servicio minimo/objetivo) por FOV
  - graficos/sinr_vs_fov.png: SINR LOS/DIFF/Hybrid vs FOV (lineas por asiento)
  - graficos/pout_vs_fov.png: Pout vs FOV

Consolidado (en resultados_generales/):
  - tabla_comparativa_escenarios.csv: SINR_hybrid minimo/promedio y Pout a
    FOV=90 para los 9 escenarios
  - comparacion_sinr_hybrid_escenarios.png: comparacion visual
"""
import os, csv, json, glob
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


def procesar_escenario(nombre):
    res_dir = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados")
    json_path = os.path.join(res_dir, "sinr_hibrido_oficial.json")
    if not os.path.exists(json_path):
        print(f"  [omitido] no existe {json_path}")
        return None
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)
    filas = d["filas"]
    gamma_th1 = d["parametros"]["gamma_th1_servicio_minimo_dB"]
    gamma_th2 = d["parametros"]["gamma_th2_servicio_objetivo_dB"]
    fovs = [f["fov_deg"] for f in filas]

    # --- CSV: SINR por asiento/FOV (LOS, DIFF, Hybrid) ---
    csv1_path = os.path.join(res_dir, "tabla_sinr_hibrido_por_fov.csv")
    with open(csv1_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["FOV_deg"]
        for rx in RX_IDXS:
            s = SEAT_LABEL[rx]
            header += [f"Asiento{s}_LOS_dB", f"Asiento{s}_DIFF_dB", f"Asiento{s}_Hybrid_dB", f"Asiento{s}_usaDIFF"]
        w.writerow(header)
        for fila in filas:
            row = [fila["fov_deg"]]
            for rx in RX_IDXS:
                v = fila["asientos"][str(rx)]
                row += [f"{v['SINR_LOS_dB']:.4f}", f"{v['SINR_DIFF_dB']:.4f}",
                        f"{v['SINR_hybrid_dB']:.4f}", v["usa_DIFF"]]
            w.writerow(row)

    # --- CSV: Pout por FOV ---
    csv2_path = os.path.join(res_dir, "tabla_pout_por_fov.csv")
    with open(csv2_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["FOV_deg", "Pout_ServicioMinimo", "Pout_ServicioObjetivo"])
        for fila in filas:
            asientos = fila["asientos"].values()
            n = len(asientos)
            pout1 = sum(1 for v in asientos if v["outage_servicio_minimo"]) / n
            pout2 = sum(1 for v in asientos if v["outage_servicio_objetivo"]) / n
            w.writerow([fila["fov_deg"], f"{pout1:.4f}", f"{pout2:.4f}"])

    # --- Graficos ---
    graf_dir = os.path.join(res_dir, "graficos")
    os.makedirs(graf_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    for rx in RX_IDXS:
        s = SEAT_LABEL[rx]
        color = COLORS_BY_SEAT[s]
        y_hybrid = [fila["asientos"][str(rx)]["SINR_hybrid_dB"] for fila in filas]
        y_los = [fila["asientos"][str(rx)]["SINR_LOS_dB"] for fila in filas]
        y_diff = [fila["asientos"][str(rx)]["SINR_DIFF_dB"] for fila in filas]
        ax.plot(fovs, y_hybrid, marker="o", markersize=5, linewidth=2.2, color=color,
                label=f"Asiento {s} — Hybrid")
        ax.plot(fovs, y_los, linestyle="--", linewidth=1.2, color=color, alpha=0.6)
        ax.plot(fovs, y_diff, linestyle=":", linewidth=1.2, color=color, alpha=0.6)
    ax.axhline(gamma_th2, color=COLOR_TH2, linestyle="--", linewidth=1.5,
               label=f"$\\gamma_{{th,2}}$ = {gamma_th2:.2f} dB")
    ax.set_xlabel("FOV del receptor (grados)")
    ax.set_ylabel("SINR (dB)")
    ax.set_title(f"SINR vs FOV (Hybrid sólido, LOS punteado, DIFF punteado fino) — {nombre}")
    ax.set_xticks(fovs)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.38), ncol=3, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(graf_dir, "sinr_vs_fov.png"), bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4), dpi=200)
    x = range(len(fovs))
    w_bar = 0.35
    pout1 = []
    pout2 = []
    for fila in filas:
        asientos = fila["asientos"].values()
        n = len(asientos)
        pout1.append(100 * sum(1 for v in asientos if v["outage_servicio_minimo"]) / n)
        pout2.append(100 * sum(1 for v in asientos if v["outage_servicio_objetivo"]) / n)
    ax.bar([i - w_bar/2 for i in x], pout1, width=w_bar, color=COLOR_POUT1, label="Pout — Servicio Mínimo")
    ax.bar([i + w_bar/2 for i in x], pout2, width=w_bar, color=COLOR_POUT2, label="Pout — Servicio Objetivo")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{int(f)}°" for f in fovs])
    ax.set_xlabel("FOV del receptor (grados)")
    ax.set_ylabel("Pout (%)")
    ax.set_ylim(0, 100)
    ax.set_title(f"Probabilidad de Outage vs FOV — {nombre}")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(os.path.join(graf_dir, "pout_vs_fov.png"), bbox_inches="tight")
    plt.close(fig)

    fila90 = next(f for f in filas if f["fov_deg"] == 90.0)
    sinr_hybrid_90 = [v["SINR_hybrid_dB"] for v in fila90["asientos"].values()]
    return {
        "nombre": nombre,
        "sinr_hybrid_min_fov90": min(sinr_hybrid_90),
        "sinr_hybrid_prom_fov90": sum(sinr_hybrid_90) / len(sinr_hybrid_90),
        "pout_min_fov90": pout1[-1] if pout1 else None,
        "pout_obj_fov90": pout2[-1] if pout2 else None,
    }


resumen = []
for nombre in ESCENARIOS:
    print(f"Procesando {nombre}...")
    r = procesar_escenario(nombre)
    if r:
        resumen.append(r)

# --- Consolidado comparativo ---
os.makedirs(_GENERALES_DIR, exist_ok=True)
comp_csv = os.path.join(_GENERALES_DIR, "tabla_comparativa_escenarios_oficial.csv")
with open(comp_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Escenario", "SINR_Hybrid_min_dB(FOV90)", "SINR_Hybrid_prom_dB(FOV90)",
                "Pout_ServicioMinimo(FOV90)_%", "Pout_ServicioObjetivo(FOV90)_%"])
    for r in resumen:
        w.writerow([r["nombre"], f"{r['sinr_hybrid_min_fov90']:.2f}", f"{r['sinr_hybrid_prom_fov90']:.2f}",
                    f"{r['pout_min_fov90']:.1f}", f"{r['pout_obj_fov90']:.1f}"])
print(f"\nTabla comparativa guardada en: {comp_csv}")

fig, ax = plt.subplots(figsize=(10, 5), dpi=200)
nombres = [r["nombre"] for r in resumen]
mins = [r["sinr_hybrid_min_fov90"] for r in resumen]
proms = [r["sinr_hybrid_prom_fov90"] for r in resumen]
x = range(len(nombres))
w_bar = 0.35
ax.bar([i - w_bar/2 for i in x], mins, width=w_bar, color="#2a78d6", label="SINR Hybrid mínimo (peor asiento)")
ax.bar([i + w_bar/2 for i in x], proms, width=w_bar, color="#008300", label="SINR Hybrid promedio")
ax.set_xticks(list(x))
ax.set_xticklabels(nombres, rotation=35, ha="right", fontsize=8.5)
ax.set_ylabel("SINR (dB)")
ax.set_title("Comparación SINR híbrido (FOV=90°) entre los 9 escenarios oficiales")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.35), ncol=2, frameon=False, fontsize=9.5)
fig.tight_layout()
comp_png = os.path.join(_GENERALES_DIR, "comparacion_sinr_hybrid_escenarios_oficial.png")
fig.savefig(comp_png, bbox_inches="tight")
plt.close(fig)
print(f"Grafico comparativo guardado en: {comp_png}")

print("\n=== LISTO ===")
