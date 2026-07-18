import os, math, sys, json, datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "codigo_comun"))
from zemax_lifi_common import (
    PythonStandaloneApplication, get_par_double, set_par_int, set_par_double,
    set_fov, get_global_z_axis, run_nsc_trace, read_zrd_hits_on_object, find_zrd_file
)
import noise_model as nm

if __name__ == '__main__':
    zos = PythonStandaloneApplication()
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    filepath = os.path.join(_THIS_DIR, "modelo", "Avion_SinBloqueo_0grados_inspect.zmx")
    zos.OpenFile(filepath, False)

    TheNCE = TheSystem.NCE
    TX_IDXS = [2, 3, 4, 5]
    RX_IDXS = [6, 7, 8, 9]
    RAYS_PER_SOURCE = 200000
    POPT_W = 2.0
    ESCENARIO = "sin_bloqueo"
    PITCH_DEG = 0.0
    FOV_DEG = 90.0
    TAG = f"{ESCENARIO}_pitch{int(PITCH_DEG)}_fov{int(FOV_DEG)}"

    lambert_m1 = [1.0, math.cos(math.radians(22.5)), math.cos(math.radians(45)),
                  math.cos(math.radians(67.5)), 0.0]
    for src_idx in TX_IDXS:
        src = TheNCE.GetObjectAt(src_idx)
        for i, val in enumerate(lambert_m1):
            set_par_double(src, ZOSAPI, 11 + i, val)
        set_par_int(src, ZOSAPI, 1, 1000)
        set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE)

    for rx_idx in RX_IDXS:
        rx = TheNCE.GetObjectAt(rx_idx)
        rx.TiltAboutY = PITCH_DEG
        set_fov(rx, ZOSAPI, FOV_DEG)

    # Matriz Pr_matrix[tx][rx] = potencia que aporta la fuente tx al detector rx,
    # obtenida corriendo 4 trazados, cada uno con UNA sola fuente activa.
    # IMPORTANTE: Zemax no permite Power=0 (lo clampea silenciosamente a 1.0W,
    # confirmado empiricamente), asi que la fuente se "apaga" poniendo sus
    # Analysis Rays (Par2) en 0 en vez de tocar la potencia (Par3), que se deja
    # siempre en POPT_W.
    Pr_matrix = {tx: {} for tx in TX_IDXS}

    for active_tx in TX_IDXS:
        for src_idx in TX_IDXS:
            src = TheNCE.GetObjectAt(src_idx)
            set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE if src_idx == active_tx else 0)
            assert get_par_double(src, ZOSAPI, 3) == POPT_W, "Power no deberia tocarse"

        zrd_name = f"sinr_only_tx{active_tx}.ZRD"
        zrd_format_full = ZOSAPI.Tools.RayTrace.ZRDFormatType.CompressedFullData
        total_energy = run_nsc_trace(TheSystem, save_rays_file=zrd_name,
                                      zrd_format=zrd_format_full, scatter=True, split=False, polarization=False)
        print(f"Trazado con solo Tx {active_tx} activo: energia lanzada = {total_energy} W "
              f"(esperado ~{POPT_W} W)")
        assert abs(total_energy - POPT_W) < 1e-6, \
            f"Energia lanzada inesperada ({total_energy} W): la aislacion de fuentes fallo"

        zrd_path = find_zrd_file(zrd_name, [
            os.path.join(_THIS_DIR, "modelo"),
            _THIS_DIR,
            _PROJECT_ROOT,
        ])
        print(f"  ZRD encontrado en: {zrd_path}")

        for rx_idx in RX_IDXS:
            hits = read_zrd_hits_on_object(TheSystem, zrd_path, rx_idx)
            Pr = sum(h[6] for h in hits)
            Pr_matrix[active_tx][rx_idx] = Pr
            print(f"  -> Detector {rx_idx}: {Pr*1000:.4f} mW ({len(hits)} hits)")

        os.remove(zrd_path)

    # Restaurar Analysis Rays originales en las 4 fuentes por si se reutiliza el archivo
    for src_idx in TX_IDXS:
        src = TheNCE.GetObjectAt(src_idx)
        set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE)

    print("\n=== Matriz Pr[Tx][Rx] (mW) ===")
    header = "Tx\\Rx  " + "  ".join(f"{rx:>8}" for rx in RX_IDXS)
    print(header)
    for tx in TX_IDXS:
        row = f"Tx{tx:>3}  " + "  ".join(f"{Pr_matrix[tx][rx]*1000:>8.4f}" for rx in RX_IDXS)
        print(row)

    own_tx_of = dict(zip(RX_IDXS, TX_IDXS))  # rx 6<->tx2, 7<->tx3, 8<->tx4, 9<->tx5 (por diseno del CAD)

    print("\n=== Umbrales SINR ===")
    gamma_th1 = nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, nm.BANDWIDTH_HZ)
    gamma_th2 = nm.sinr_threshold_from_ber(nm.BER_MAX)
    print(f"gamma_th,1 (Servicio Minimo) = {gamma_th1:.4f} ({nm.db(gamma_th1):.2f} dB)")
    print(f"gamma_th,2 (Servicio Objetivo) = {gamma_th2:.4f} ({nm.db(gamma_th2):.2f} dB)")

    print(f"\n=== SINR por asiento ({TAG}) ===")
    resultados_por_asiento = []
    for rx_idx in RX_IDXS:
        own_tx = own_tx_of[rx_idx]
        Pr_signal = Pr_matrix[own_tx][rx_idx]
        Pr_interference = sum(Pr_matrix[tx][rx_idx] for tx in TX_IDXS if tx != own_tx)
        sinr, sigma2, Isig, Iint = nm.compute_sinr(Pr_signal, Pr_interference)
        outage1 = sinr < gamma_th1
        outage2 = sinr < gamma_th2
        print(f"Detector {rx_idx} (Tx propio {own_tx}): Pr_signal={Pr_signal*1000:.4f} mW  "
              f"Pr_interference={Pr_interference*1000:.4f} mW  "
              f"SINR={sinr:.4f} ({nm.db(sinr):.2f} dB)  "
              f"| Outage minimo: {'SI' if outage1 else 'no'}  "
              f"| Outage objetivo: {'SI' if outage2 else 'no'}")
        resultados_por_asiento.append({
            "detector": rx_idx, "tx_propio": own_tx,
            "Pr_signal_W": Pr_signal, "Pr_interference_W": Pr_interference,
            "sigma2": sigma2, "SINR": sinr, "SINR_dB": nm.db(sinr),
            "outage_servicio_minimo": outage1, "outage_servicio_objetivo": outage2,
        })

    # --- Guardar resultados en el proyecto (antes solo se imprimian por consola) ---
    resultados_dir = os.path.join(_THIS_DIR, "resultados")
    os.makedirs(resultados_dir, exist_ok=True)

    salida = {
        "escenario": ESCENARIO,
        "timestamp": datetime.datetime.now().isoformat(),
        "parametros": {
            "pitch_deg": PITCH_DEG, "fov_deg": FOV_DEG,
            "rayos_analisis_por_fuente": RAYS_PER_SOURCE, "Popt_W": POPT_W,
            "bandwidth_Hz": nm.BANDWIDTH_HZ, "temperatura_K": nm.TEMPERATURE_K,
            "R_min_bps": nm.R_MIN_BPS, "BER_max": nm.BER_MAX,
        },
        "gamma_th1_servicio_minimo": gamma_th1,
        "gamma_th2_servicio_objetivo": gamma_th2,
        "Pr_matrix_W": {str(tx): {str(rx): Pr_matrix[tx][rx] for rx in RX_IDXS} for tx in TX_IDXS},
        "resultados_por_asiento": resultados_por_asiento,
    }

    json_path = os.path.join(resultados_dir, f"sinr_{TAG}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"\nResultados guardados en: {json_path}")

    txt_path = os.path.join(resultados_dir, f"sinr_{TAG}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Escenario: {ESCENARIO}, pitch={PITCH_DEG} deg, FOV={FOV_DEG} deg\n")
        f.write(f"Generado: {salida['timestamp']}\n\n")
        f.write(f"gamma_th,1 (Servicio Minimo) = {gamma_th1:.4f} ({nm.db(gamma_th1):.2f} dB)\n")
        f.write(f"gamma_th,2 (Servicio Objetivo) = {gamma_th2:.4f} ({nm.db(gamma_th2):.2f} dB)\n\n")
        f.write("Matriz Pr[Tx][Rx] (mW):\n")
        f.write(header + "\n")
        for tx in TX_IDXS:
            row = f"Tx{tx:>3}  " + "  ".join(f"{Pr_matrix[tx][rx]*1000:>8.4f}" for rx in RX_IDXS)
            f.write(row + "\n")
        f.write("\nSINR por asiento:\n")
        for r in resultados_por_asiento:
            f.write(f"Detector {r['detector']} (Tx propio {r['tx_propio']}): "
                    f"Pr_signal={r['Pr_signal_W']*1000:.4f} mW  "
                    f"Pr_interference={r['Pr_interference_W']*1000:.4f} mW  "
                    f"SINR={r['SINR']:.4f} ({r['SINR_dB']:.2f} dB)  "
                    f"| Outage minimo: {'SI' if r['outage_servicio_minimo'] else 'no'}  "
                    f"| Outage objetivo: {'SI' if r['outage_servicio_objetivo'] else 'no'}\n")
    print(f"Resumen legible guardado en: {txt_path}")

    del zos
    zos = None
