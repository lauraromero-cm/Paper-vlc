"""
Genera versiones en ingles de las tablas (CSV) a partir de los
sinr_hibrido_oficial.json, en carpetas separadas de las version en
espanol (no las pisa, no las modifica). Complemento de
generar_graficos_ingles.py (mismo criterio: todo resultado en ingles va
en una carpeta "en" aparte).

Por escenario: escenarios/<nombre>/resultados/tables/
  - sinr_hybrid_by_fov.csv
  - outage_by_fov.csv
  - seat_mapping.csv

Consolidado: resultados_generales/tables/
  - scenario_comparison_table.csv
"""
import os, csv, json

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_GENERALES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales")

RX_IDXS = [6, 7, 8, 9]
TX_IDXS = [2, 3, 4, 5]
SEAT_LABEL = {rx: i + 1 for i, rx in enumerate(RX_IDXS)}

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

    tables_dir = os.path.join(res_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)

    # --- SINR by seat/FOV (LOS, DIFF, Hybrid) ---
    with open(os.path.join(tables_dir, "sinr_hybrid_by_fov.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["FOV_deg"]
        for rx in RX_IDXS:
            s = SEAT_LABEL[rx]
            header += [f"Seat{s}_LOS_dB", f"Seat{s}_DIFF_dB", f"Seat{s}_Hybrid_dB", f"Seat{s}_usesDIFF"]
        w.writerow(header)
        for fila in filas:
            row = [fila["fov_deg"]]
            for rx in RX_IDXS:
                v = fila["asientos"][str(rx)]
                row += [f"{v['SINR_LOS_dB']:.4f}", f"{v['SINR_DIFF_dB']:.4f}",
                        f"{v['SINR_hybrid_dB']:.4f}", v["usa_DIFF"]]
            w.writerow(row)

    # --- Outage by FOV ---
    with open(os.path.join(tables_dir, "outage_by_fov.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["FOV_deg", "Outage_MinimumService", "Outage_TargetService"])
        for fila in filas:
            asientos = fila["asientos"].values()
            n = len(asientos)
            pout1 = sum(1 for v in asientos if v["outage_servicio_minimo"]) / n
            pout2 = sum(1 for v in asientos if v["outage_servicio_objetivo"]) / n
            w.writerow([fila["fov_deg"], f"{pout1:.4f}", f"{pout2:.4f}"])

    # --- Seat <-> Zemax object mapping ---
    with open(os.path.join(tables_dir, "seat_mapping.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Seat_paper", "Zemax_Detector_Object", "Zemax_Tx_Object"])
        for rx, tx in zip(RX_IDXS, TX_IDXS):
            w.writerow([SEAT_LABEL[rx], rx, tx])

    fila90 = next(f for f in filas if f["fov_deg"] == 90.0)
    sinr_hybrid_90 = [v["SINR_hybrid_dB"] for v in fila90["asientos"].values()]
    asientos90 = fila90["asientos"].values()
    n = len(asientos90)
    pout_min_90 = 100 * sum(1 for v in asientos90 if v["outage_servicio_minimo"]) / n
    pout_obj_90 = 100 * sum(1 for v in asientos90 if v["outage_servicio_objetivo"]) / n
    return {
        "nombre": nombre,
        "titulo_en": NOMBRE_EN[nombre],
        "sinr_hybrid_min_fov90": min(sinr_hybrid_90),
        "sinr_hybrid_prom_fov90": sum(sinr_hybrid_90) / len(sinr_hybrid_90),
        "pout_min_fov90": pout_min_90,
        "pout_obj_fov90": pout_obj_90,
    }


resumen = []
for nombre in ESCENARIOS:
    print(f"Processing {nombre}...")
    r = procesar_escenario(nombre)
    if r:
        resumen.append(r)

# --- Consolidated comparison table ---
tables_gen_dir = os.path.join(_GENERALES_DIR, "tables")
os.makedirs(tables_gen_dir, exist_ok=True)
comp_csv = os.path.join(tables_gen_dir, "scenario_comparison_table.csv")
with open(comp_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Scenario", "SINR_Hybrid_min_dB(FOV90)", "SINR_Hybrid_avg_dB(FOV90)",
                "Outage_MinimumService(FOV90)_%", "Outage_TargetService(FOV90)_%"])
    for r in resumen:
        w.writerow([r["titulo_en"], f"{r['sinr_hybrid_min_fov90']:.2f}", f"{r['sinr_hybrid_prom_fov90']:.2f}",
                    f"{r['pout_min_fov90']:.1f}", f"{r['pout_obj_fov90']:.1f}"])
print(f"\nComparison table saved to: {comp_csv}")
print("\n=== DONE ===")
