"""
Genera una tabla (PNG + CSV) que documenta la derivacion de los dos umbrales
de SINR (gamma_th,1 y gamma_th,2) usados en toda la Seccion 5 del paper.
Estos umbrales son constantes del sistema (dependen de Rmin, ancho de banda
y BER objetivo, no de la geometria/escenario), por eso se documentan una
sola vez aqui en vez de repetirse en cada carpeta de escenario.
"""
import os, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import noise_model as nm

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_OUT_DIR = os.path.join(os.path.dirname(_THIS_DIR), "resultados_generales")
os.makedirs(_OUT_DIR, exist_ok=True)

gamma_th1 = nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, nm.BANDWIDTH_HZ)
gamma_th2 = nm.sinr_threshold_from_ber(nm.BER_MAX)
gamma_th1_dB = nm.db(gamma_th1)
gamma_th2_dB = nm.db(gamma_th2)

rows = [
    {
        "umbral": "γth,1\nServicio Mínimo",
        "criterio": f"Capacidad de Shannon-Hartley:\nR ≥ Rmin = {nm.R_MIN_BPS/1e6:.1f} Mbps",
        "formula": "γth = 2^(Rmin/B) − 1",
        "parametros": f"Rmin = {nm.R_MIN_BPS/1e6:.1f} Mbps\nB = {nm.BANDWIDTH_HZ/1e6:.1f} MHz",
        "valor_lineal": gamma_th1,
        "valor_dB": gamma_th1_dB,
    },
    {
        "umbral": "γth,2\nServicio Objetivo",
        "criterio": f"BER objetivo, modulación OOK:\nBER ≤ {nm.BER_MAX:.0e}",
        "formula": "BER = Q(√γth)\n⇒ γth = [Q⁻¹(BER)]²",
        "parametros": f"BER_max = {nm.BER_MAX:.0e}",
        "valor_lineal": gamma_th2,
        "valor_dB": gamma_th2_dB,
    },
]

# ---------- CSV ----------
csv_path = os.path.join(_OUT_DIR, "tabla_umbrales_sinr.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Umbral", "Criterio", "Formula", "Parametros", "Valor (lineal)", "Valor (dB)"])
    for r in rows:
        w.writerow([r["umbral"], r["criterio"], r["formula"], r["parametros"],
                    f"{r['valor_lineal']:.4f}", f"{r['valor_dB']:.2f}"])

# ---------- PNG (tabla) ----------
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

col_labels = ["Umbral", "Criterio", "Fórmula", "Parámetros", "Valor\n(lineal)", "Valor\n(dB)"]
cell_text = [[r["umbral"], r["criterio"], r["formula"], r["parametros"],
              f"{r['valor_lineal']:.4f}", f"{r['valor_dB']:.2f} dB"] for r in rows]

fig, ax = plt.subplots(figsize=(13, 3.2), dpi=200)
ax.axis("off")
tabla = ax.table(cellText=cell_text, colLabels=col_labels, cellLoc="center", loc="center",
                  colWidths=[0.14, 0.26, 0.20, 0.20, 0.10, 0.10])
tabla.auto_set_font_size(False)
tabla.set_fontsize(9.5)
tabla.scale(1, 3.2)
for (row_i, col_i), cell in tabla.get_celld().items():
    cell.set_edgecolor("#e1e0d9")
    cell.set_text_props(ha="center", va="center")
    if row_i == 0:
        cell.set_facecolor("#f2f1ee")
        cell.set_text_props(weight="bold", color="#0b0b0b", ha="center", va="center")
    elif row_i % 2 == 0:
        cell.set_facecolor("#f7f6f3")
ax.set_title("Umbrales de SINR (γth) usados en la Sección 5", fontsize=13, pad=16, loc="left", weight="bold")
fig.text(0.01, -0.05,
          "B = ancho de banda eléctrico del receptor (supuesto de literatura VLC, ver noise_model.py). "
          "Estos umbrales son constantes del sistema, iguales en todos los escenarios y FOVs.",
          fontsize=8, color="#898781")
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "tabla_umbrales_sinr.png"), bbox_inches="tight")
plt.close(fig)

# ---------- PNG (barras comparativas en dB) ----------
fig, ax = plt.subplots(figsize=(6, 4.5), dpi=200)
labels = ["γth,1\nServicio Mínimo", "γth,2\nServicio Objetivo"]
values = [gamma_th1_dB, gamma_th2_dB]
colors = ["#2a78d6", "#e34948"]
bars = ax.bar(labels, values, color=colors, width=0.5)
margin = 0.08 * (max(values) - min(values))
for b, v in zip(bars, values):
    va = "bottom" if v >= 0 else "top"
    offset = margin if v >= 0 else -margin
    ax.text(b.get_x() + b.get_width()/2, v + offset, f"{v:.2f} dB",
             ha="center", va=va, fontsize=11, weight="bold")
ax.axhline(0, color="#c3c2b7", linewidth=0.8)
ax.set_ylabel("SINR umbral (dB)")
ax.set_title("Comparación de umbrales de SINR")
ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
ax.set_axisbelow(True)
ax.set_ylim(min(values) - 3 * margin, max(values) + 3 * margin)
fig.tight_layout()
fig.savefig(os.path.join(_OUT_DIR, "comparacion_umbrales_sinr.png"), bbox_inches="tight")
plt.close(fig)

print(f"Guardado en: {_OUT_DIR}")
print("  - tabla_umbrales_sinr.csv")
print("  - tabla_umbrales_sinr.png")
print("  - comparacion_umbrales_sinr.png")
