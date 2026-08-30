"""
LOS-only vs. Hybrid SINR summary table (English), requested by the reviewer
to make auditable the "SINR_LOS ~= 13-30 dB" / "SINR_hybrid ~= 66-90 dB"
ranges quoted in prose in Section 6.3. Computed at FOV=90 deg (the
representative operating point used in the prose claim) across the 9
official scenarios, straight from sinr_hibrido_oficial.json -- no new
simulation, just consolidation of numbers that already exist.

The blocked seat under bloqueo_persona (SINR_LOS = -inf) is excluded from
the LOS min/avg/max and reported separately, since it is not part of the
"typical LOS" range being audited (it is the exact case the DIFF channel
is designed to rescue).

Output (English only, same convention as the other *_ingles.py scripts):
  resultados_generales/tables/los_vs_hybrid_summary.csv
  resultados_generales/graphs/los_vs_hybrid_summary.png
"""
import os, csv, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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

rows = []
for nombre in ESCENARIOS:
    path = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    fila90 = next(f for f in d["filas"] if f["fov_deg"] == 90.0)
    asientos = fila90["asientos"].values()

    los_all = [v["SINR_LOS_dB"] for v in asientos]
    los_finite = [x for x in los_all if x != float("-inf")]
    n_blocked = len(los_all) - len(los_finite)
    hyb = [v["SINR_hybrid_dB"] for v in asientos]

    rows.append({
        "escenario": NOMBRE_EN[nombre],
        "los_min": min(los_finite), "los_avg": sum(los_finite) / len(los_finite), "los_max": max(los_finite),
        "n_blocked": n_blocked,
        "hyb_min": min(hyb), "hyb_avg": sum(hyb) / len(hyb), "hyb_max": max(hyb),
    })

# ---------- CSV ----------
csv_path = os.path.join(_TABLES_DIR, "los_vs_hybrid_summary.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Scenario", "LOS_min_dB", "LOS_avg_dB", "LOS_max_dB", "LOS_fully_blocked_seats",
                "Hybrid_min_dB", "Hybrid_avg_dB", "Hybrid_max_dB"])
    for r in rows:
        w.writerow([r["escenario"], f"{r['los_min']:.2f}", f"{r['los_avg']:.2f}", f"{r['los_max']:.2f}",
                    r["n_blocked"], f"{r['hyb_min']:.2f}", f"{r['hyb_avg']:.2f}", f"{r['hyb_max']:.2f}"])

# ---------- PNG (table) ----------
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

col_labels = ["Scenario", "LOS SINR\nmin (dB)", "LOS SINR\navg (dB)", "LOS SINR\nmax (dB)",
              "LOS fully\nblocked seats", "Hybrid SINR\nmin (dB)", "Hybrid SINR\navg (dB)", "Hybrid SINR\nmax (dB)"]
cell_text = [[r["escenario"], f"{r['los_min']:.2f}", f"{r['los_avg']:.2f}", f"{r['los_max']:.2f}",
              str(r["n_blocked"]) if r["n_blocked"] else "—",
              f"{r['hyb_min']:.2f}", f"{r['hyb_avg']:.2f}", f"{r['hyb_max']:.2f}"] for r in rows]

fig, ax = plt.subplots(figsize=(13.5, 0.42 * (len(rows) + 1) + 1.0), dpi=200)
ax.axis("off")
tabla = ax.table(cellText=cell_text, colLabels=col_labels, cellLoc="center", loc="center",
                  colWidths=[0.20, 0.11, 0.11, 0.11, 0.13, 0.11, 0.11, 0.11])
tabla.auto_set_font_size(False)
tabla.set_fontsize(9.5)
tabla.scale(1, 2.4)
for (row_i, col_i), cell in tabla.get_celld().items():
    cell.set_edgecolor("#e1e0d9")
    cell.set_text_props(ha="center", va="center")
    if row_i == 0:
        cell.set_facecolor("#f2f1ee")
        cell.set_text_props(weight="bold", color="#0b0b0b", ha="center", va="center")
    elif row_i % 2 == 0:
        cell.set_facecolor("#f7f6f3")
ax.set_title("LOS-only vs. Hybrid SINR — Summary at FOV=90° (Section 6.3)", fontsize=13, pad=16, loc="left", weight="bold")
fig.text(0.01, -0.05,
          "Min/avg/max computed across the 4 seats at FOV=90 deg, straight from sinr_hibrido_oficial.json (no new\n"
          "simulation). The blocked seat under Passenger Blockage (SINR_LOS = -inf) is excluded from the LOS range\n"
          "and counted separately in 'LOS fully blocked seats' -- it is the exact case the DIFF/Hybrid channel rescues.",
          fontsize=8, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_GRAPHS_DIR, "los_vs_hybrid_summary.png"), bbox_inches="tight")
plt.close(fig)

print(f"Saved to: {_GENERALES_DIR}")
print("  - tables/los_vs_hybrid_summary.csv")
print("  - graphs/los_vs_hybrid_summary.png")
