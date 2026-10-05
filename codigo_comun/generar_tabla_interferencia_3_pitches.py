"""
Item 7 (pedido del agente redactor, feedback de revision): extiende el
desglose de interferencia LOS, hoy solo documentado para pitch=0 (ver
generar_tabla_interferencia_ingles.py), a los 3 pitches (0/15/30), con y sin
pasajero, a FOV=90. Los datos ya estaban exportados en los JSON de los 9
escenarios -- no se corre ninguna simulacion nueva, solo se leen.

Permite borrar la limitacion "el desglose de interferencia solo se exporto
para pitch 0" del texto y de Future Work.
"""
import os, csv, json

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_TABLES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales", "tables")
os.makedirs(_TABLES_DIR, exist_ok=True)

PITCHES = [0, 15, 30]
ESCENARIOS = ["sin_bloqueo", "bloqueo_persona"]
RX_IDXS = [6, 7, 8, 9]

rows = []
for pitch in PITCHES:
    for esc in ESCENARIOS:
        path = os.path.join(_PROJECT_ROOT, "escenarios", f"{esc}_{pitch}grados",
                             "resultados", "sinr_hibrido_oficial.json")
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        fila90 = next(f for f in d["filas"] if f["fov_deg"] == 90.0)
        for rx in RX_IDXS:
            a = fila90["asientos"][str(rx)]
            rows.append({
                "pitch_deg": pitch, "escenario": esc, "seat_rx": rx,
                "Pr_own_LOS_mW": a["Pr_own_LOS_mW"], "Pr_interf_LOS_mW": a["Pr_interf_LOS_mW"],
                "SINR_LOS_dB": a["SINR_LOS_dB"],
            })

csv_path = os.path.join(_TABLES_DIR, "interference_breakdown_3_pitches.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Pitch_deg", "Scenario", "Seat_RX", "Pr_own_LOS_mW", "Pr_interf_LOS_mW", "SINR_LOS_dB"])
    for r in rows:
        w.writerow([r["pitch_deg"], r["escenario"], r["seat_rx"], f"{r['Pr_own_LOS_mW']:.4f}",
                    f"{r['Pr_interf_LOS_mW']:.4f}", f"{r['SINR_LOS_dB']:.2f}"])

print(f"{len(rows)} filas (3 pitches x 2 escenarios x 4 asientos) en {csv_path}")
for r in rows:
    print(f"  pitch={r['pitch_deg']:>2} {r['escenario']:<15} RX{r['seat_rx']}  "
          f"Pr_interf_LOS={r['Pr_interf_LOS_mW']:.3f}mW  SINR_LOS={r['SINR_LOS_dB']:.2f}dB")
