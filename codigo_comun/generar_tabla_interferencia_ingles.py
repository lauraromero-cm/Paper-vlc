"""
Interference-breakdown table (English) backing the Discussion's claim that
the same physical obstacle blocking a seat's own LOS path can also
intercept the interference ray this seat's transmitter casts toward a
geometrically adjacent receiver.

Compares Pr_interf_LOS_mW and SINR_LOS_dB per seat between the no-blockage
and passenger-blockage scenarios, at FOV=90 deg, pitch=0 deg -- the only
condition under which this geometric mechanism was verified explicitly
(see Discussion limitations: "verified explicitly only at pitch=0 deg").
Straight from sinr_hibrido_oficial.json, no new simulation.

Output (English only, same convention as the other *_ingles.py scripts):
  resultados_generales/tables/interference_breakdown.csv
  resultados_generales/graphs/interference_breakdown.png
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

RX_IDXS = [6, 7, 8, 9]
SEAT_LABEL = {rx: i + 1 for i, rx in enumerate(RX_IDXS)}


def cargar(nombre):
    path = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return next(f for f in d["filas"] if f["fov_deg"] == 90.0)["asientos"]


base = cargar("sin_bloqueo_0grados")
blocked = cargar("bloqueo_persona_0grados")

rows = []
for rx in RX_IDXS:
    seat = SEAT_LABEL[rx]
    interf_base = base[str(rx)]["Pr_interf_LOS_mW"]
    interf_blk = blocked[str(rx)]["Pr_interf_LOS_mW"]
    sinr_base = base[str(rx)]["SINR_LOS_dB"]
    sinr_blk = blocked[str(rx)]["SINR_LOS_dB"]
    drop_x = interf_base / interf_blk if interf_blk > 0 else float("inf")
    rows.append({
        "seat": seat, "is_blocked": (rx == 6),
        "interf_base": interf_base, "interf_blk": interf_blk, "drop_x": drop_x,
        "sinr_base": sinr_base, "sinr_blk": sinr_blk,
    })

# ---------- CSV ----------
csv_path = os.path.join(_TABLES_DIR, "interference_breakdown.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Seat", "Pr_interf_LOS_NoBlockage_mW", "Pr_interf_LOS_PassengerBlockage_mW",
                "Interference_drop_x", "SINR_LOS_NoBlockage_dB", "SINR_LOS_PassengerBlockage_dB"])
    for r in rows:
        label = f"{r['seat']} (blocked)" if r["is_blocked"] else str(r["seat"])
        drop_str = "n/a (own link blocked)" if r["is_blocked"] else f"{r['drop_x']:.1f}x"
        w.writerow([label, f"{r['interf_base']:.4f}", f"{r['interf_blk']:.4f}", drop_str,
                    f"{r['sinr_base']:.2f}", f"{r['sinr_blk']:.2f}"])

# ---------- PNG (table) ----------
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

col_labels = ["Seat", "Pr_interf,LOS\nNo Blockage (mW)", "Pr_interf,LOS\nPassenger Blockage (mW)",
              "Interference\ndrop", "SINR_LOS\nNo Blockage (dB)", "SINR_LOS\nPassenger Blockage (dB)"]
cell_text = []
for r in rows:
    label = f"{r['seat']} (blocked)" if r["is_blocked"] else str(r["seat"])
    drop_str = "—" if r["is_blocked"] else f"~{r['drop_x']:.0f}×"
    cell_text.append([label, f"{r['interf_base']:.3f}", f"{r['interf_blk']:.3f}", drop_str,
                       f"{r['sinr_base']:.2f}", f"{r['sinr_blk']:.2f}"])

fig, ax = plt.subplots(figsize=(11, 0.42 * (len(rows) + 1) + 1.1), dpi=200)
ax.axis("off")
tabla = ax.table(cellText=cell_text, colLabels=col_labels, cellLoc="center", loc="center",
                  colWidths=[0.10, 0.20, 0.22, 0.14, 0.17, 0.17])
tabla.auto_set_font_size(False)
tabla.set_fontsize(9.5)
tabla.scale(1, 2.6)
for (row_i, col_i), cell in tabla.get_celld().items():
    cell.set_edgecolor("#e1e0d9")
    cell.set_text_props(ha="center", va="center")
    if row_i == 0:
        cell.set_facecolor("#f2f1ee")
        cell.set_text_props(weight="bold", color="#0b0b0b", ha="center", va="center")
    elif row_i % 2 == 0:
        cell.set_facecolor("#f7f6f3")
ax.set_title("Interference Breakdown — Neighboring-Seat Effect of LOS Blockage (pitch=0°, FOV=90°)",
             fontsize=12.5, pad=16, loc="left", weight="bold")
fig.text(0.01, -0.06,
          "Seat 2 sits geometrically adjacent to the obstacle blocking Seat 1's own LOS; the same obstacle also\n"
          "intercepts Seat 1's interference ray toward Seat 2, producing a ~30x drop in Pr_interf,LOS and raising\n"
          "Seat 2's SINR_LOS. Seats 3-4 show no meaningful change, confirming the effect is geometry-specific, not\n"
          "a general reduction of emitted interference. Verified explicitly at pitch=0 deg only (see Discussion limitations).",
          fontsize=8, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_GRAPHS_DIR, "interference_breakdown.png"), bbox_inches="tight")
plt.close(fig)

print(f"Saved to: {_GENERALES_DIR}")
print("  - tables/interference_breakdown.csv")
print("  - graphs/interference_breakdown.png")
