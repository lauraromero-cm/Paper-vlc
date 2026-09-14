"""
M2 (feedback de revision): eta (capacitancia fija del fotodetector) estaba en
112 pF/m^2 en vez de 112 pF/cm^2 (el valor clasico de Komine-Nakagawa), una
diferencia de 10^4 en la unidad de area. Ya corregido en noise_model.py.

Este script NO vuelve a correr Zemax ni traza ningun rayo: recalcula
SINR_LOS_dB, SINR_DIFF_dB, SINR_hybrid_dB, usa_DIFF y los flags de outage
directamente a partir de las potencias opticas (Pr_own_LOS_mW,
Pr_interf_LOS_mW, Pr_DIFF_mW, Pr_interf_DIFF_mW) ya exportadas por el
pipeline oficial y guardadas en cada sinr_hibrido_oficial.json -- esas
potencias no dependen del modelo de ruido, solo de la geometria/trazado ya
hecho, asi que la correccion es pura post-procesamiento.

Sobrescribe los 9 JSON en su lugar (agrega un campo de auditoria
'correccion_M2_ruido_termico' documentando el cambio), para que todos los
scripts de tablas/graficos que ya existen lean automaticamente los valores
corregidos la proxima vez que se corran.
"""
import os, sys, json, datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _THIS_DIR)
import noise_model as nm

ESCENARIOS = [
    "sin_bloqueo_0grados", "sin_bloqueo_15grados", "sin_bloqueo_30grados",
    "bloqueo_carrito_0grados", "bloqueo_carrito_15grados", "bloqueo_carrito_30grados",
    "bloqueo_persona_0grados", "bloqueo_persona_15grados", "bloqueo_persona_30grados",
]

gamma_th1 = nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, nm.BANDWIDTH_HZ)
gamma_th2 = nm.sinr_threshold_from_ber(nm.BER_MAX)

resumen_deltas = []

for nombre in ESCENARIOS:
    path = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados", "sinr_hibrido_oficial.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)

    max_delta_hybrid = 0.0
    for fila in d["filas"]:
        for rx, v in fila["asientos"].items():
            Pr_own = v["Pr_own_LOS_mW"] / 1000.0
            Pr_interf_LOS = v["Pr_interf_LOS_mW"] / 1000.0
            Pr_diff = v["Pr_DIFF_mW"] / 1000.0
            Pr_interf_DIFF = v["Pr_interf_DIFF_mW"] / 1000.0

            sinr_los, _, _, _ = nm.compute_sinr(Pr_own, Pr_interf_LOS)
            sinr_diff, _, _, _ = nm.compute_sinr(Pr_diff, Pr_interf_DIFF)
            sinr_hybrid = max(sinr_los, sinr_diff)

            old_hybrid_dB = v["SINR_hybrid_dB"]
            new_hybrid_dB = nm.db(sinr_hybrid)
            if old_hybrid_dB != float("-inf") and new_hybrid_dB != float("-inf"):
                max_delta_hybrid = max(max_delta_hybrid, abs(new_hybrid_dB - old_hybrid_dB))

            v["SINR_LOS_dB"] = nm.db(sinr_los)
            v["SINR_DIFF_dB"] = nm.db(sinr_diff)
            v["SINR_hybrid_dB"] = new_hybrid_dB
            v["usa_DIFF"] = sinr_diff > sinr_los
            v["outage_servicio_minimo"] = sinr_hybrid < gamma_th1
            v["outage_servicio_objetivo"] = sinr_hybrid < gamma_th2

    d["gamma_th1_servicio_minimo_dB"] = nm.db(gamma_th1)
    d["gamma_th2_servicio_objetivo_dB"] = nm.db(gamma_th2)
    d["correccion_M2_ruido_termico"] = {
        "aplicada": True,
        "fecha": datetime.datetime.now().isoformat(),
        "nota": ("eta (capacitancia fija del fotodetector) corregida de 112 pF/m^2 a "
                 "112 pF/cm^2 = 1.12e-6 F/m^2 (valor clasico Komine-Nakagawa). "
                 "sigma2_th paso de ~6.55e-21 A^2 a ~1.01e-16 A^2. Recalculado por "
                 "post-procesamiento puro sobre las potencias opticas ya exportadas "
                 "(Pr_own_LOS_mW, Pr_interf_LOS_mW, Pr_DIFF_mW, Pr_interf_DIFF_mW); "
                 "no se volvio a correr Zemax ni a trazar rayos."),
        f"delta_max_SINR_hybrid_dB_{nombre}": round(max_delta_hybrid, 4),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

    resumen_deltas.append((nombre, max_delta_hybrid))
    print(f"{nombre}: max |delta SINR_hybrid| = {max_delta_hybrid:.4f} dB")

print("\n=== Resumen ===")
print(f"gamma_th1 = {nm.db(gamma_th1):.4f} dB (sin cambios, no depende del ruido)")
print(f"gamma_th2 = {nm.db(gamma_th2):.4f} dB (sin cambios, no depende del ruido)")
print(f"Delta maximo global en SINR_hybrid: {max(d for _, d in resumen_deltas):.4f} dB")
