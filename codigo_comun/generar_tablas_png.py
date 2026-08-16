"""
Genera las tablas (CSV) como imagen PNG, en espanol e ingles, a partir de
los sinr_hibrido_oficial.json. El pipeline oficial (generar_tablas_graficos_oficial.py
y generar_tablas_ingles.py) ya genera las tablas en CSV; este script agrega
la version PNG para poder pegarlas directo en la tesis.

Espanol -> escenarios/<nombre>/resultados/graficos/ (junto a los graficos)
Ingles  -> escenarios/<nombre>/resultados/graphs/ (junto a los graficos)

Consolidado:
  resultados_generales/tabla_comparativa_escenarios_oficial.png (ES)
  resultados_generales/graphs/scenario_comparison_table.png (EN)
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

ESCENARIOS = [
    "sin_bloqueo_0grados", "sin_bloqueo_15grados", "sin_bloqueo_30grados",
    "bloqueo_carrito_0grados", "bloqueo_carrito_15grados", "bloqueo_carrito_30grados",
    "bloqueo_persona_0grados", "bloqueo_persona_15grados", "bloqueo_persona_30grados",
]

NOMBRE_ES = {
    "sin_bloqueo_0grados": "Sin bloqueo — 0°", "sin_bloqueo_15grados": "Sin bloqueo — 15°",
    "sin_bloqueo_30grados": "Sin bloqueo — 30°", "bloqueo_carrito_0grados": "Bloqueo carrito — 0°",
    "bloqueo_carrito_15grados": "Bloqueo carrito — 15°", "bloqueo_carrito_30grados": "Bloqueo carrito — 30°",
    "bloqueo_persona_0grados": "Bloqueo persona — 0°", "bloqueo_persona_15grados": "Bloqueo persona — 15°",
    "bloqueo_persona_30grados": "Bloqueo persona — 30°",
}
NOMBRE_EN = {
    "sin_bloqueo_0grados": "No Blockage – 0°", "sin_bloqueo_15grados": "No Blockage – 15°",
    "sin_bloqueo_30grados": "No Blockage – 30°", "bloqueo_carrito_0grados": "Cart Blockage – 0°",
    "bloqueo_carrito_15grados": "Cart Blockage – 15°", "bloqueo_carrito_30grados": "Cart Blockage – 30°",
    "bloqueo_persona_0grados": "Passenger Blockage – 0°", "bloqueo_persona_15grados": "Passenger Blockage – 15°",
    "bloqueo_persona_30grados": "Passenger Blockage – 30°",
}

plt.rcParams.update({"font.family": "sans-serif", "font.size": 11})


def dibujar_tabla(cell_text, col_labels, titulo, nota, out_path, figwidth=9.5):
    fig, ax = plt.subplots(figsize=(figwidth, 0.42 * (len(cell_text) + 1) + 0.7), dpi=200)
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
    ax.set_title(titulo, fontsize=12, pad=14, loc="left", weight="bold")
    if nota:
        fig.text(0.01, -0.02, nota, fontsize=7.5, color="#898781")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def procesar_escenario(nombre):
    res_dir = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados")
    json_path = os.path.join(res_dir, "sinr_hibrido_oficial.json")
    if not os.path.exists(json_path):
        print(f"  [omitido] no existe {json_path}")
        return
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)
    filas = d["filas"]
    gamma_th1 = d["parametros"]["gamma_th1_servicio_minimo_dB"]
    gamma_th2 = d["parametros"]["gamma_th2_servicio_objetivo_dB"]

    # ---------- Espanol: graficos/ ----------
    dir_es = os.path.join(res_dir, "graficos")
    os.makedirs(dir_es, exist_ok=True)

    col_labels = ["FOV (°)"] + [f"Asiento {SEAT_LABEL[rx]}\nHybrid (dB)" for rx in RX_IDXS]
    cell_text = []
    for fila in filas:
        row = [f"{int(fila['fov_deg'])}"]
        for rx in RX_IDXS:
            row.append(f"{fila['asientos'][str(rx)]['SINR_hybrid_dB']:.2f}")
        cell_text.append(row)
    dibujar_tabla(cell_text, col_labels, "Tabla 1 — SINR híbrido por asiento y FOV (dB)",
                  "Hybrid = max(LOS, DIFF). Ver tabla_sinr_hibrido_por_fov.csv para el detalle LOS/DIFF.",
                  os.path.join(dir_es, "tabla_sinr_hibrido_por_fov.png"))

    col_labels2 = ["FOV (°)", "γth,1 (dB)", "γth,2 (dB)", "Pout Serv. Mínimo", "Pout Serv. Objetivo"]
    cell_text2 = []
    for fila in filas:
        asientos = fila["asientos"].values()
        n = len(asientos)
        pout1 = sum(1 for v in asientos if v["outage_servicio_minimo"]) / n
        pout2 = sum(1 for v in asientos if v["outage_servicio_objetivo"]) / n
        cell_text2.append([f"{int(fila['fov_deg'])}", f"{gamma_th1:.2f}", f"{gamma_th2:.2f}",
                            f"{pout1*100:.1f}%", f"{pout2*100:.1f}%"])
    dibujar_tabla(cell_text2, col_labels2, "Tabla 2 — Probabilidad de Outage por FOV",
                  "Pout estimada como fraccion de los 4 asientos bajo cada umbral (SINR hibrido).",
                  os.path.join(dir_es, "tabla_pout_por_fov.png"), figwidth=8)

    # ---------- Ingles: graphs/ ----------
    dir_en = os.path.join(res_dir, "graphs")
    os.makedirs(dir_en, exist_ok=True)

    col_labels_en = ["FOV (°)"] + [f"Seat {SEAT_LABEL[rx]}\nHybrid (dB)" for rx in RX_IDXS]
    dibujar_tabla(cell_text, col_labels_en, "Table 1 — Hybrid SINR by Seat and FOV (dB)",
                  "Hybrid = max(LOS, DIFF). See sinr_hybrid_by_fov.csv for the LOS/DIFF breakdown.",
                  os.path.join(dir_en, "sinr_hybrid_by_fov.png"))

    col_labels2_en = ["FOV (°)", "γth,1 (dB)", "γth,2 (dB)", "Outage Min. Service", "Outage Target Service"]
    dibujar_tabla(cell_text2, col_labels2_en, "Table 2 — Outage Probability by FOV",
                  "Outage estimated as the fraction of the 4 seats below each threshold (hybrid SINR).",
                  os.path.join(dir_en, "outage_by_fov.png"), figwidth=8)


for nombre in ESCENARIOS:
    print(f"Procesando {nombre}...")
    procesar_escenario(nombre)

# ---------- Consolidado ----------
comp_csv_es = os.path.join(_GENERALES_DIR, "tabla_comparativa_escenarios_oficial.csv")
comp_csv_en = os.path.join(_GENERALES_DIR, "tables", "scenario_comparison_table.csv")

HEADER_CORTO_ES = ["Escenario", "SINR mín.\n(dB)", "SINR prom.\n(dB)", "Pout Serv.\nMínimo", "Pout Serv.\nObjetivo"]
HEADER_CORTO_EN = ["Scenario", "Min SINR\n(dB)", "Avg SINR\n(dB)", "Outage\nMin. Svc", "Outage\nTarget Svc"]

if os.path.exists(comp_csv_es):
    import csv as _csv
    with open(comp_csv_es, encoding="utf-8") as f:
        rows = list(_csv.reader(f))
    body = rows[1:]
    dibujar_tabla(body, HEADER_CORTO_ES, "Tabla comparativa — SINR híbrido y Pout (FOV=90°) por escenario", "",
                  os.path.join(_GENERALES_DIR, "tabla_comparativa_escenarios_oficial.png"), figwidth=10)

if os.path.exists(comp_csv_en):
    import csv as _csv
    with open(comp_csv_en, encoding="utf-8") as f:
        rows = list(_csv.reader(f))
    body = rows[1:]
    out_dir_en = os.path.join(_GENERALES_DIR, "graphs")
    os.makedirs(out_dir_en, exist_ok=True)
    dibujar_tabla(body, HEADER_CORTO_EN, "Scenario Comparison Table — Hybrid SINR and Outage (FOV=90°)", "",
                  os.path.join(out_dir_en, "scenario_comparison_table.png"), figwidth=10)

print("\n=== LISTO ===")
