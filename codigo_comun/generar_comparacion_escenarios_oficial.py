"""
Reemplaza a resultados_generales/obsoleto_pre_hibrido/generar_comparacion_escenarios.py
(que usaba metricas_paper_combinado.json, LOS-only, pre-DIFF), con la misma
sintesis comparativa de la Seccion 6 pero calculada sobre los
sinr_hibrido_oficial.json del pipeline oficial (LOS+DIFF+Hybrid, FOV
corregido). Genera version en espanol y en ingles.

  1. FOVopt: FOV que maximiza el peor caso de SINR hibrido entre asientos,
     a partir de sin_bloqueo (unico escenario sin obstaculo).
  2. Pout comparativo: Pout promedio (SINR hibrido) por escenario y pitch.
  3. Validacion de Resiliencia: SINR LOS vs Hybrid del asiento bloqueado
     (Rx6/Tx2), comparando sin_bloqueo / bloqueo_carrito / bloqueo_persona,
     un panel por pitch -- a diferencia de la version vieja, aqui SI se
     espera que el Hybrid rescate el servicio bajo bloqueo_persona.
"""
import os, json, csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_GENERALES_DIR = os.path.join(_PROJECT_ROOT, "resultados_generales")

ESCENARIOS = ["sin_bloqueo", "bloqueo_carrito", "bloqueo_persona"]
PITCHES = [0, 15, 30]
ASIENTO_RX = 6  # detector Zemax del Asiento 1 (el que se bloquea en bloqueo_persona)

COLOR_ESCENARIO = {"sin_bloqueo": "#2a78d6", "bloqueo_carrito": "#008300", "bloqueo_persona": "#e34948"}

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#0b0b0b",
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.8,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def cargar(escenario, pitch):
    path = os.path.join(_PROJECT_ROOT, "escenarios", f"{escenario}_{pitch}grados",
                         "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d["filas"]


DATA = {(esc, p): cargar(esc, p) for esc in ESCENARIOS for p in PITCHES}
RX_IDXS = sorted(int(k) for k in DATA[("sin_bloqueo", 0)][0]["asientos"].keys())


def dibujar_tabla(cell_text, col_labels, titulo, nota, out_path, figwidth=9.5, row_h=1.6):
    fig, ax = plt.subplots(figsize=(figwidth, 0.42 * (len(cell_text) + 1) + 0.7), dpi=200)
    ax.axis("off")
    tabla = ax.table(cellText=cell_text, colLabels=col_labels, cellLoc="center", loc="center")
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(9.5)
    tabla.scale(1, row_h)
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


def generar(lang):
    es = (lang == "es")
    out_dir = _GENERALES_DIR if es else os.path.join(_GENERALES_DIR, "tables")
    graf_dir = _GENERALES_DIR if es else os.path.join(_GENERALES_DIR, "graphs")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(graf_dir, exist_ok=True)

    ESC_LABEL = ({"sin_bloqueo": "Sin bloqueo", "bloqueo_carrito": "Bloqueo carrito", "bloqueo_persona": "Bloqueo persona"}
                 if es else
                 {"sin_bloqueo": "No Blockage", "bloqueo_carrito": "Cart Blockage", "bloqueo_persona": "Passenger Blockage"})

    # =========== 1) FOVopt (a partir de sin_bloqueo) ===========
    fovopt_rows = []
    for p in PITCHES:
        filas = DATA[("sin_bloqueo", p)]
        min_por_fov = []
        for fila in filas:
            vals = [fila["asientos"][str(rx)]["SINR_hybrid_dB"] for rx in RX_IDXS]
            min_por_fov.append((fila["fov_deg"], min(vals), sum(vals) / len(vals)))
        fov_opt, sinr_min_opt, sinr_prom_opt = max(min_por_fov, key=lambda t: t[1])
        spread = max(m for _, m, _ in min_por_fov) - min(m for _, m, _ in min_por_fov)
        fovopt_rows.append({"pitch_deg": p, "fov_opt_deg": fov_opt, "sinr_min_dB": sinr_min_opt,
                             "sinr_prom_dB": sinr_prom_opt, "spread_dB": spread})

    if es:
        csv_path = os.path.join(_GENERALES_DIR, "csv_backup", "tabla_fovopt.csv")
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Pitch (deg)", "FOVopt (deg)", "SINR minimo hibrido en FOVopt (dB)",
                        "SINR promedio hibrido en FOVopt (dB)", "Variacion SINR minimo en 10-90 (dB)"])
            for r in fovopt_rows:
                w.writerow([r["pitch_deg"], int(r["fov_opt_deg"]), f"{r['sinr_min_dB']:.2f}",
                            f"{r['sinr_prom_dB']:.2f}", f"{r['spread_dB']:.2f}"])
        col_labels = ["Pitch (°)", "FOVopt\nrecomendado (°)", "SINR mínimo\nhíbrido (dB)",
                      "SINR promedio\nhíbrido (dB)", "Variación SINR mínimo\nen 10°-90° (dB)"]
        titulo = "Diseño Óptico Óptimo — FOVopt (SINR híbrido)"
        nota = ("FOVopt = FOV que maximiza el peor caso de SINR híbrido entre los 4 asientos, calculado sobre\n"
                "el escenario sin bloqueo. A diferencia del analisis anterior (pre-DIFF), el SINR SI varia con\n"
                "el FOV (el filtro de FOV ahora es real); FOVopt puede no ser 90 grados.")
    else:
        csv_path = os.path.join(out_dir, "fov_opt_table.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Pitch (deg)", "FOVopt (deg)", "Min Hybrid SINR at FOVopt (dB)",
                        "Avg Hybrid SINR at FOVopt (dB)", "Min SINR variation over 10-90 (dB)"])
            for r in fovopt_rows:
                w.writerow([r["pitch_deg"], int(r["fov_opt_deg"]), f"{r['sinr_min_dB']:.2f}",
                            f"{r['sinr_prom_dB']:.2f}", f"{r['spread_dB']:.2f}"])
        col_labels = ["Pitch (°)", "Recommended\nFOVopt (°)", "Min Hybrid\nSINR (dB)",
                      "Avg Hybrid\nSINR (dB)", "Min SINR variation\nover 10°-90° (dB)"]
        titulo = "Optimal Optical Design — FOVopt (Hybrid SINR)"
        nota = ("FOVopt = the FOV that maximizes the worst-case hybrid SINR across the 4 seats, computed on\n"
                "the no-blockage scenario. Unlike the earlier pre-DIFF analysis, SINR now genuinely varies with\n"
                "FOV (the FOV filter is now physically real); FOVopt is not necessarily 90 degrees.")

    cell_text = [[f"{r['pitch_deg']}", f"{int(r['fov_opt_deg'])}", f"{r['sinr_min_dB']:.2f}",
                  f"{r['sinr_prom_dB']:.2f}", f"± {r['spread_dB']:.2f}"] for r in fovopt_rows]
    fname = "tabla_fovopt.png" if es else "fov_opt_table.png"
    dibujar_tabla(cell_text, col_labels, titulo, nota, os.path.join(graf_dir, fname), figwidth=9.5, row_h=2.2)

    # =========== 2) Pout comparativo ===========
    pout_rows = []
    for esc in ESCENARIOS:
        for p in PITCHES:
            filas = DATA[(esc, p)]
            pout_min_vals, pout_obj_vals = [], []
            for fila in filas:
                asientos = fila["asientos"].values()
                n = len(asientos)
                pout_min_vals.append(sum(1 for v in asientos if v["outage_servicio_minimo"]) / n)
                pout_obj_vals.append(sum(1 for v in asientos if v["outage_servicio_objetivo"]) / n)
            pout_rows.append({"escenario": esc, "pitch_deg": p,
                               "pout_prom_minimo_pct": 100 * sum(pout_min_vals) / len(pout_min_vals),
                               "pout_prom_objetivo_pct": 100 * sum(pout_obj_vals) / len(pout_obj_vals)})

    if es:
        csv_path2 = os.path.join(_GENERALES_DIR, "csv_backup", "tabla_pout_comparativa.csv")
        with open(csv_path2, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Escenario", "Pitch (deg)", "Pout promedio Serv. Minimo (%)", "Pout promedio Serv. Objetivo (%)"])
            for r in pout_rows:
                w.writerow([ESC_LABEL[r["escenario"]], r["pitch_deg"], f"{r['pout_prom_minimo_pct']:.1f}",
                            f"{r['pout_prom_objetivo_pct']:.1f}"])
        col_labels_pout = ["Escenario", "Pitch (°)", "Pout Serv. Mínimo\n(%, híbrido)", "Pout Serv. Objetivo\n(%, híbrido)"]
        titulo_pout = "Probabilidad de Outage comparada entre escenarios (SINR híbrido, promedio FOV 10°-90°)"
    else:
        csv_path2 = os.path.join(out_dir, "outage_comparison_table.csv")
        with open(csv_path2, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Scenario", "Pitch (deg)", "Avg Outage Min. Service (%)", "Avg Outage Target Service (%)"])
            for r in pout_rows:
                w.writerow([ESC_LABEL[r["escenario"]], r["pitch_deg"], f"{r['pout_prom_minimo_pct']:.1f}",
                            f"{r['pout_prom_objetivo_pct']:.1f}"])
        col_labels_pout = ["Scenario", "Pitch (°)", "Outage Min. Svc\n(%, hybrid)", "Outage Target Svc\n(%, hybrid)"]
        titulo_pout = "Outage Probability Compared Across Scenarios (Hybrid SINR, averaged over FOV 10°-90°)"

    cell_text_pout = [[ESC_LABEL[r["escenario"]], f"{r['pitch_deg']}", f"{r['pout_prom_minimo_pct']:.1f}%",
                        f"{r['pout_prom_objetivo_pct']:.1f}%"] for r in pout_rows]
    fname2 = "tabla_pout_comparativa.png" if es else "outage_comparison_table.png"
    dibujar_tabla(cell_text_pout, col_labels_pout, titulo_pout, "", os.path.join(graf_dir, fname2), figwidth=8.5)

    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    x = range(len(PITCHES))
    w_bar = 0.25
    for i, esc in enumerate(ESCENARIOS):
        vals = [next(r["pout_prom_objetivo_pct"] for r in pout_rows if r["escenario"] == esc and r["pitch_deg"] == p)
                for p in PITCHES]
        offset = (i - 1) * w_bar
        bars = ax.bar([xi + offset for xi in x], vals, width=w_bar, color=COLOR_ESCENARIO[esc], label=ESC_LABEL[esc])
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width()/2, v + 1.0, f"{v:.0f}%", ha="center", fontsize=9, weight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{p}°" for p in PITCHES])
    ax.set_xlabel("Pitch (grados)" if es else "Pitch (degrees)")
    ax.set_ylabel("Pout promedio — Serv. Objetivo (%)" if es else "Avg Outage — Target Service (%)")
    ax.set_ylim(0, 35)
    ax.set_title(titulo_pout)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False, fontsize=9.5)
    fig.tight_layout()
    fname3 = "comparacion_pout_escenarios.png" if es else "outage_comparison.png"
    fig.savefig(os.path.join(graf_dir, fname3), bbox_inches="tight")
    plt.close(fig)

    # =========== 3) Validacion de Resiliencia ===========
    import noise_model as nm
    gamma_th2_dB = nm.db(nm.sinr_threshold_from_ber(nm.BER_MAX))
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=200, sharey=True)
    all_finite = []
    for p in PITCHES:
        for esc in ESCENARIOS:
            for fila in DATA[(esc, p)]:
                for key in ("SINR_LOS_dB", "SINR_hybrid_dB"):
                    v = fila["asientos"][str(ASIENTO_RX)][key]
                    if v != float("-inf"):
                        all_finite.append(v)
    all_finite.append(gamma_th2_dB)
    floor_dB = min(all_finite) - 5.0

    for ax, p in zip(axes, PITCHES):
        fovs_ref = None
        for esc in ESCENARIOS:
            filas = DATA[(esc, p)]
            fovs = [fila["fov_deg"] for fila in filas]
            fovs_ref = fovs
            y_hybrid_raw = [fila["asientos"][str(ASIENTO_RX)]["SINR_hybrid_dB"] for fila in filas]
            y_los_raw = [fila["asientos"][str(ASIENTO_RX)]["SINR_LOS_dB"] for fila in filas]
            y_hybrid = [floor_dB if v == float("-inf") else v for v in y_hybrid_raw]
            y_los = [floor_dB if v == float("-inf") else v for v in y_los_raw]
            ax.plot(fovs, y_hybrid, marker="o", markersize=5, linewidth=2.2, linestyle="-",
                    color=COLOR_ESCENARIO[esc], label=f"{ESC_LABEL[esc]} — Hybrid" if es else f"{ESC_LABEL[esc]} — Hybrid")
            ax.plot(fovs, y_los, marker="^", markersize=4, linewidth=1.2, linestyle="--",
                    color=COLOR_ESCENARIO[esc], alpha=0.65, label=f"{ESC_LABEL[esc]} — LOS")
            bloqueados = [f for f, v in zip(fovs, y_los_raw) if v == float("-inf")]
            if bloqueados:
                ax.scatter(bloqueados, [floor_dB] * len(bloqueados), marker="x", s=60,
                           color=COLOR_ESCENARIO[esc], zorder=5, linewidths=2.0)
        ax.axhline(gamma_th2_dB, color="#0b0b0b", linestyle="--", linewidth=1.0, alpha=0.6)
        ax.set_title(f"Pitch {p}°")
        ax.set_xlabel("FOV del receptor (°)" if es else "Receiver FOV (°)")
        ax.set_xticks(fovs_ref)
        ax.tick_params(axis='x', labelrotation=45)
    axes[0].set_ylabel(("SINR (dB) — Asiento 1" if es else "SINR (dB) — Seat 1"))
    axes[0].set_ylim(floor_dB - 1.0, max(all_finite) + 1.0)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False, fontsize=9)
    if es:
        fig.suptitle("Validación de Resiliencia — SINR del asiento bloqueado vs FOV (LOS vs Hybrid)", fontsize=13, y=1.02)
        fig.text(0.01, -0.18, "× = LOS totalmente bloqueado (-∞ dB), graficado en el piso solo para visualización.\n"
                 "Línea punteada = γth,2 Servicio Objetivo. El canal DIFF (Hybrid) restaura el servicio incluso "
                 "bajo bloqueo total del LOS (bloqueo_persona).", fontsize=8, color="#898781")
    else:
        fig.suptitle("Resilience Validation — Blocked-Seat SINR vs FOV (LOS vs Hybrid)", fontsize=13, y=1.02)
        fig.text(0.01, -0.18, "× = LOS fully blocked (-∞ dB), plotted at the floor for visualization only.\n"
                 "Dashed line = γth,2 Target Service. The DIFF channel (Hybrid) restores service even under\n"
                 "total LOS blockage (Passenger Blockage).", fontsize=8, color="#898781")
    fig.tight_layout()
    fname4 = "validacion_resiliencia_asiento_bloqueado.png" if es else "resilience_validation.png"
    fig.savefig(os.path.join(graf_dir, fname4), bbox_inches="tight")
    plt.close(fig)

    print(f"[{lang}] Guardado en: {graf_dir}")


generar("es")
generar("en")
print("\n=== LISTO ===")
