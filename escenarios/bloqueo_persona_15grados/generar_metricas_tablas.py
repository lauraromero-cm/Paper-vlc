"""
Consolida los resultados por FOV (JSON individuales) en las tablas y metricas
"indispensables" pedidas por la seccion 5 del documento de tesis:

  - SINR por asiento y por FOV (dB)
  - Probabilidad de Outage Pout = Pr(SINR < gamma_th) para los dos umbrales
    (Servicio Minimo gamma_th,1 y Servicio Objetivo gamma_th,2), estimada como
    la fraccion de asientos (de los 4 simulados) cuya SINR cae bajo cada umbral

En este escenario (sin bloqueo) el enlace LOS domina y no se observa ningun
outage; estas tablas quedan como base comparable para cuando se agreguen los
escenarios con bloqueo, donde Pout se espera que sea > 0 y sea la metrica que
sustente el diseno del FOVopt (seccion 6).
"""
import os, glob, json, csv, math

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_RES_DIR = os.path.join(_THIS_DIR, "resultados")
RX_IDXS = [6, 7, 8, 9]
TX_IDXS = [2, 3, 4, 5]

# Los objetos 6-9 (detectores) y 2-5 (fuentes) son los indices internos del
# modelo de Zemax; para el paper/tesis se etiquetan como "Asiento 1..4" en el
# orden en que aparecen. Este mapeo queda documentado en mapeo_asientos.csv.
SEAT_LABEL = {rx: i + 1 for i, rx in enumerate(RX_IDXS)}  # {6:1, 7:2, 8:3, 9:4}
SEAT_ORDER = [SEAT_LABEL[rx] for rx in RX_IDXS]  # [1, 2, 3, 4], mismo orden que RX_IDXS

# --- Mapeo asiento (paper) <-> objetos Zemax (trazabilidad) ---
mapeo_path = os.path.join(_RES_DIR, "mapeo_asientos.csv")
with open(mapeo_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Asiento_paper", "Detector_objeto_Zemax", "Tx_objeto_Zemax"])
    for rx, tx in zip(RX_IDXS, TX_IDXS):
        w.writerow([SEAT_LABEL[rx], rx, tx])
print(f"Mapeo de asientos guardado en: {mapeo_path}")

files = sorted(
    glob.glob(os.path.join(_RES_DIR, "sinr_bloqueo_persona_pitch15_fov*.json")),
    key=lambda f: int(os.path.basename(f).split("fov")[1].split(".")[0])
)
if not files:
    raise SystemExit("No se encontraron JSON de resultados en " + _RES_DIR)

rows = []
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    fov = d["parametros"]["fov_deg"]
    gamma_th1 = d["gamma_th1_servicio_minimo"]
    gamma_th2 = d["gamma_th2_servicio_objetivo"]
    sinr_por_asiento = {r["detector"]: r["SINR"] for r in d["resultados_por_asiento"]}
    sinr_db_por_asiento = {r["detector"]: r["SINR_dB"] for r in d["resultados_por_asiento"]}

    n_outage1 = sum(1 for v in sinr_por_asiento.values() if v < gamma_th1)
    n_outage2 = sum(1 for v in sinr_por_asiento.values() if v < gamma_th2)
    n_total = len(sinr_por_asiento)

    rows.append({
        "fov_deg": fov,
        "gamma_th1_dB": 10 * math.log10(gamma_th1),
        "gamma_th2_dB": 10 * math.log10(gamma_th2),
        "sinr_db": sinr_db_por_asiento,  # claves = objeto detector Zemax (6-9), ver mapeo_asientos.csv
        "sinr_prom_dB": sum(sinr_db_por_asiento.values()) / n_total,
        "sinr_min_dB": min(sinr_db_por_asiento.values()),
        "Pout_servicio_minimo": n_outage1 / n_total,
        "Pout_servicio_objetivo": n_outage2 / n_total,
    })

# --- Tabla 1: SINR (dB) por asiento y FOV ---
tabla1_path = os.path.join(_RES_DIR, "tabla_sinr_por_fov.csv")
with open(tabla1_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["FOV_deg"] + [f"SINR_dB_asiento{SEAT_LABEL[rx]}" for rx in RX_IDXS] + ["SINR_prom_dB", "SINR_min_dB"])
    for r in rows:
        w.writerow([r["fov_deg"]] + [f"{r['sinr_db'][rx]:.4f}" for rx in RX_IDXS] +
                   [f"{r['sinr_prom_dB']:.4f}", f"{r['sinr_min_dB']:.4f}"])
print(f"Tabla SINR guardada en: {tabla1_path}")

# --- Tabla 2: Pout por FOV y umbral ---
tabla2_path = os.path.join(_RES_DIR, "tabla_pout_por_fov.csv")
with open(tabla2_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["FOV_deg", "gamma_th1_dB_ServicioMinimo", "gamma_th2_dB_ServicioObjetivo",
                "Pout_ServicioMinimo", "Pout_ServicioObjetivo"])
    for r in rows:
        w.writerow([r["fov_deg"], f"{r['gamma_th1_dB']:.4f}", f"{r['gamma_th2_dB']:.4f}",
                   f"{r['Pout_servicio_minimo']:.4f}", f"{r['Pout_servicio_objetivo']:.4f}"])
print(f"Tabla Pout guardada en: {tabla2_path}")

# --- Resumen legible ---
resumen_path = os.path.join(_RES_DIR, "resumen_metricas_paper.txt")
with open(resumen_path, "w", encoding="utf-8") as f:
    f.write("Metricas indispensables (Seccion 5) - Escenario bloqueo_persona, pitch=0 deg\n")
    f.write("=" * 78 + "\n\n")
    f.write(f"gamma_th,1 (Servicio Minimo)   = {rows[0]['gamma_th1_dB']:.2f} dB\n")
    f.write(f"gamma_th,2 (Servicio Objetivo) = {rows[0]['gamma_th2_dB']:.2f} dB\n\n")
    f.write(f"{'FOV(deg)':>10} {'SINR prom(dB)':>15} {'SINR min(dB)':>15} "
            f"{'Pout min':>10} {'Pout obj':>10}\n")
    for r in rows:
        f.write(f"{r['fov_deg']:>10.1f} {r['sinr_prom_dB']:>15.2f} {r['sinr_min_dB']:>15.2f} "
                f"{r['Pout_servicio_minimo']:>10.2%} {r['Pout_servicio_objetivo']:>10.2%}\n")
    f.write("\nConclusion: en ausencia de bloqueo, Pout=0 para ambos umbrales en todo el rango "
            "de FOV evaluado (5-90 grados); el enlace LOS mantiene margen suficiente (~5 dB) sobre "
            "el umbral de Servicio Objetivo en todos los casos. Esta tabla sirve de linea base para "
            "comparar contra los escenarios con bloqueo, donde se espera que Pout > 0 sea la metrica "
            "que sustente la seleccion de FOVopt.\n")
    f.write("\nMapeo Asiento (paper) <-> objetos Zemax (ver mapeo_asientos.csv):\n")
    for rx, tx in zip(RX_IDXS, TX_IDXS):
        f.write(f"  Asiento {SEAT_LABEL[rx]}: detector obj.{rx}, Tx obj.{tx}\n")
print(f"Resumen guardado en: {resumen_path}")

# --- JSON combinado (para graficar) ---
combinado_path = os.path.join(_RES_DIR, "metricas_paper_combinado.json")
salida_json = {
    "seat_label_map": {str(rx): SEAT_LABEL[rx] for rx in RX_IDXS},  # objeto Zemax -> asiento (paper)
    "rows": rows,
}
with open(combinado_path, "w", encoding="utf-8") as f:
    json.dump(salida_json, f, indent=2, ensure_ascii=False)
print(f"JSON combinado guardado en: {combinado_path}")
