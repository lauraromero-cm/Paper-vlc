"""
M9 (feedback de revision): la convergencia del trazado NSC se afirma en el
texto (+-0.22% entre corridas a 1M, -0.32% de 1M a 2M) pero nunca se mostro
como tabla/figura auditable. El dato ya existe en
escenarios/hybrid_validacion_pitch0/resultados/convergencia_nsc.json (5
corridas: 200k, 500k, 1M, 1M repetido, 2M rayos, trazado aislado con solo
Tx2 activo, modelo sin bloqueo, pitch=0). Este script solo tabula/grafica
ese resultado ya existente -- no dispara ningun trazado nuevo.

Output (ingles, mismo patron que los demas *_ingles.py):
  resultados_generales/tables/ray_count_convergence.csv
  resultados_generales/graphs/ray_count_convergence.png
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

src = os.path.join(_PROJECT_ROOT, "escenarios", "hybrid_validacion_pitch0",
                    "resultados", "convergencia_nsc.json")
with open(src, encoding="utf-8") as f:
    runs = json.load(f)

RX_REF = "6"  # Rx6 = Seat 1, directly under the traced source (Tx2), largest/most stable signal

rows = []
prev_pr = None
for run in runs:
    pr = run["Pr_mW"][RX_REF]
    delta_pct = None if prev_pr is None else 100.0 * (pr - prev_pr) / prev_pr
    rows.append({"label": run["label"], "n_rays": run["n_rays"], "pr_mw": pr,
                 "n_hits": run["n_hits"][RX_REF], "t_s": run["t_s"], "delta_pct": delta_pct})
    prev_pr = pr

# 1M_a -> 1M_b is a repeat at the same ray count (Monte Carlo noise, not a trend);
# recompute that specific delta against 1M_a explicitly for the caption.
pr_1Ma = next(r["pr_mw"] for r in rows if r["label"] == "1M_a")
pr_1Mb = next(r["pr_mw"] for r in rows if r["label"] == "1M_b")
pr_2M = next(r["pr_mw"] for r in rows if r["label"] == "2M")
delta_1M_repeat_pct = 100.0 * (pr_1Mb - pr_1Ma) / pr_1Ma
delta_1M_to_2M_pct = 100.0 * (pr_2M - pr_1Ma) / pr_1Ma

# ---------- CSV ----------
csv_path = os.path.join(_TABLES_DIR, "ray_count_convergence.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Run", "N_rays", "Pr_Rx6_mW", "N_hits_Rx6", "Trace_time_s", "Delta_vs_previous_run_%"])
    for r in rows:
        w.writerow([r["label"], r["n_rays"], f"{r['pr_mw']:.4f}", r["n_hits"], f"{r['t_s']:.1f}",
                    "" if r["delta_pct"] is None else f"{r['delta_pct']:.2f}"])

# ---------- PNG (table + curve) ----------
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#0b0b0b",
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.8,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

fig, (ax_tab, ax_curve) = plt.subplots(1, 2, figsize=(14, 4.2), dpi=200,
                                        gridspec_kw={"width_ratios": [1.15, 1]})
ax_tab.axis("off")
col_labels = ["Run", "N rays", "Pr,Rx6\n(mW)", "N hits\n(Rx6)", "Δ vs prev.\nrun (%)"]
cell_text = [[r["label"], f"{r['n_rays']:,}", f"{r['pr_mw']:.4f}", f"{r['n_hits']}",
              "—" if r["delta_pct"] is None else f"{r['delta_pct']:+.2f}%"] for r in rows]
tabla = ax_tab.table(cellText=cell_text, colLabels=col_labels, cellLoc="center", loc="center")
tabla.auto_set_font_size(False)
tabla.set_fontsize(9.5)
tabla.scale(1, 2.2)
for (row_i, col_i), cell in tabla.get_celld().items():
    cell.set_edgecolor("#e1e0d9")
    if row_i == 0:
        cell.set_facecolor("#f2f1ee")
        cell.set_text_props(weight="bold", color="#0b0b0b")
    elif row_i % 2 == 0:
        cell.set_facecolor("#f7f6f3")
ax_tab.set_title("Ray-Count Convergence (Rx6, isolated Tx2 trace,\nno-blockage model, pitch=0°)",
                  fontsize=11.5, pad=12, loc="left", weight="bold")

labels_curve = [r["label"] for r in rows]
prs = [r["pr_mw"] for r in rows]
ax_curve.plot(range(len(rows)), prs, marker="o", markersize=7, linewidth=2, color="#2a78d6")
ax_curve.set_xticks(range(len(rows)))
ax_curve.set_xticklabels(labels_curve)
ax_curve.set_xlabel("Run (ray count)")
ax_curve.set_ylabel("Received power at Rx6 (mW)")
ax_curve.set_title("Received Power vs. Ray Count", fontsize=11.5)

fig.text(0.01, -0.06,
          f"1M repeated run vs. first 1M run: {delta_1M_repeat_pct:+.2f}% (Monte Carlo noise at fixed ray count). "
          f"1M -> 2M trend: {delta_1M_to_2M_pct:+.2f}%. Both are of the same order, confirming 1M rays is an "
          "adequate operating point for the nine-scenario campaign (Sec. Ray Count Convergence).",
          fontsize=8, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_GRAPHS_DIR, "ray_count_convergence.png"), bbox_inches="tight")
plt.close(fig)

print(f"1M repeat delta: {delta_1M_repeat_pct:+.2f}%   1M->2M delta: {delta_1M_to_2M_pct:+.2f}%")
print(f"Saved to: {_GENERALES_DIR}")
print("  - tables/ray_count_convergence.csv")
print("  - graphs/ray_count_convergence.png")
