import os, math, sys, json, datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "codigo_comun"))
from zemax_lifi_common import (
    PythonStandaloneApplication, get_par_double, set_par_int, set_par_double,
    set_fov, run_nsc_trace, read_zrd_hits_on_objects, find_zrd_file
)
import noise_model as nm

# Barrido de FOV para el escenario "sin bloqueo, pitch=0 deg". FOV=90 ya se
# corrio por separado (sinr_sin_bloqueo_0grados.py); aqui se cubren los
# valores restantes para construir la curva SINR-vs-FOV (busqueda de FOVopt).
FOV_LIST_DEG = [5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]

TX_IDXS = [2, 3, 4, 5]
RX_IDXS = [6, 7, 8, 9]
RAYS_PER_SOURCE = 1000000
LAYOUT_RAYS = 100000
POPT_W = 2.0
ESCENARIO = "bloqueo_persona"
PITCH_DEG = 30.0
own_tx_of = dict(zip(RX_IDXS, TX_IDXS))


def run_one_fov(TheSystem, TheNCE, ZOSAPI, fov_deg):
    tag = f"{ESCENARIO}_pitch{int(PITCH_DEG)}_fov{int(fov_deg)}"
    print(f"\n{'='*70}\n=== FOV = {fov_deg} deg ({tag}) ===\n{'='*70}", flush=True)

    for rx_idx in RX_IDXS:
        rx = TheNCE.GetObjectAt(rx_idx)
        rx.TiltAboutY = PITCH_DEG
        set_fov(rx, ZOSAPI, fov_deg)

    Pr_matrix = {tx: {} for tx in TX_IDXS}

    for active_tx in TX_IDXS:
        for src_idx in TX_IDXS:
            src = TheNCE.GetObjectAt(src_idx)
            set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE if src_idx == active_tx else 0)
            assert get_par_double(src, ZOSAPI, 3) == POPT_W, "Power no deberia tocarse"

        t0 = datetime.datetime.now()
        print(f"[{t0.isoformat(timespec='seconds')}] FOV={fov_deg}: trazado Tx {active_tx} activo "
              f"({RAYS_PER_SOURCE} rayos)...", flush=True)
        zrd_name = f"sinr_fov{int(fov_deg)}_tx{active_tx}.ZRD"
        zrd_format_full = ZOSAPI.Tools.RayTrace.ZRDFormatType.CompressedFullData
        total_energy = run_nsc_trace(TheSystem, save_rays_file=zrd_name,
                                      zrd_format=zrd_format_full, scatter=True, split=True, polarization=False)
        t1 = datetime.datetime.now()
        print(f"[{t1.isoformat(timespec='seconds')}] Tx {active_tx} completado en "
              f"{(t1 - t0).total_seconds():.1f}s. Energia = {total_energy} W (esperado ~{POPT_W} W)", flush=True)
        assert abs(total_energy - POPT_W) < 1e-6, \
            f"Energia lanzada inesperada ({total_energy} W): aislacion de fuentes fallo"

        zrd_path = find_zrd_file(zrd_name, [
            os.path.join(_THIS_DIR, "modelo"), _THIS_DIR, _PROJECT_ROOT,
        ])
        hits_por_detector = read_zrd_hits_on_objects(TheSystem, zrd_path, RX_IDXS, progress_every=200000)

        for rx_idx in RX_IDXS:
            hits = hits_por_detector[rx_idx]
            Pr = sum(h[6] for h in hits)
            Pr_matrix[active_tx][rx_idx] = Pr
            print(f"  -> Detector {rx_idx}: {Pr*1000:.4f} mW ({len(hits)} hits)", flush=True)

        os.remove(zrd_path)

    for src_idx in TX_IDXS:
        src = TheNCE.GetObjectAt(src_idx)
        set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE)

    gamma_th1 = nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, nm.BANDWIDTH_HZ)
    gamma_th2 = nm.sinr_threshold_from_ber(nm.BER_MAX)
    g_concentrador = nm.concentrator_gain(fov_deg)
    print(f"Ganancia del concentrador g(FOV={fov_deg} deg) = {g_concentrador:.4f}", flush=True)

    resultados_por_asiento = []
    for rx_idx in RX_IDXS:
        own_tx = own_tx_of[rx_idx]
        Pr_signal_raw = Pr_matrix[own_tx][rx_idx]
        Pr_interference_raw = sum(Pr_matrix[tx][rx_idx] for tx in TX_IDXS if tx != own_tx)
        Pr_signal = Pr_signal_raw * g_concentrador
        Pr_interference = Pr_interference_raw * g_concentrador
        sinr, sigma2, Isig, Iint = nm.compute_sinr(Pr_signal, Pr_interference)
        outage1 = sinr < gamma_th1
        outage2 = sinr < gamma_th2
        print(f"Detector {rx_idx} (Tx propio {own_tx}): Pr_signal={Pr_signal*1000:.4f} mW "
              f"Pr_interference={Pr_interference*1000:.4f} mW SINR={sinr:.4f} ({nm.db(sinr):.2f} dB) "
              f"| Outage min: {'SI' if outage1 else 'no'} | Outage obj: {'SI' if outage2 else 'no'}", flush=True)
        resultados_por_asiento.append({
            "detector": rx_idx, "tx_propio": own_tx,
            "Pr_signal_sin_concentrador_W": Pr_signal_raw,
            "Pr_interference_sin_concentrador_W": Pr_interference_raw,
            "Pr_signal_W": Pr_signal, "Pr_interference_W": Pr_interference,
            "sigma2": sigma2, "SINR": sinr, "SINR_dB": nm.db(sinr),
            "outage_servicio_minimo": outage1, "outage_servicio_objetivo": outage2,
        })

    resultados_dir = os.path.join(_THIS_DIR, "resultados")
    os.makedirs(resultados_dir, exist_ok=True)
    salida = {
        "escenario": ESCENARIO,
        "timestamp": datetime.datetime.now().isoformat(),
        "parametros": {
            "pitch_deg": PITCH_DEG, "fov_deg": fov_deg,
            "rayos_analisis_por_fuente": RAYS_PER_SOURCE, "Popt_W": POPT_W,
            "bandwidth_Hz": nm.BANDWIDTH_HZ, "temperatura_K": nm.TEMPERATURE_K,
            "R_min_bps": nm.R_MIN_BPS, "BER_max": nm.BER_MAX,
            "concentrador_indice_refraccion": nm.CONCENTRATOR_REFRACTIVE_INDEX,
            "concentrador_ganancia_g": g_concentrador,
        },
        "gamma_th1_servicio_minimo": gamma_th1,
        "gamma_th2_servicio_objetivo": gamma_th2,
        "Pr_matrix_W": {str(tx): {str(rx): Pr_matrix[tx][rx] for rx in RX_IDXS} for tx in TX_IDXS},
        "resultados_por_asiento": resultados_por_asiento,
    }
    json_path = os.path.join(resultados_dir, f"sinr_{tag}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"Resultados guardados en: {json_path}", flush=True)
    return salida


if __name__ == '__main__':
    zos = PythonStandaloneApplication()
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem

    filepath = os.path.join(_THIS_DIR, "modelo", "Avion_Bloqueo_persona.zmx")
    zos.OpenFile(filepath, False)
    TheNCE = TheSystem.NCE

    lambert_m1 = [1.0, math.cos(math.radians(22.5)), math.cos(math.radians(45)),
                  math.cos(math.radians(67.5)), 0.0]
    for src_idx in TX_IDXS:
        src = TheNCE.GetObjectAt(src_idx)
        for i, val in enumerate(lambert_m1):
            set_par_double(src, ZOSAPI, 11 + i, val)
        set_par_int(src, ZOSAPI, 1, LAYOUT_RAYS)
        set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE)

    resumen = []
    t_sweep_start = datetime.datetime.now()
    for fov_deg in FOV_LIST_DEG:
        tag = f"{ESCENARIO}_pitch{int(PITCH_DEG)}_fov{int(fov_deg)}"
        existing_json = os.path.join(_THIS_DIR, "resultados", f"sinr_{tag}.json")
        if os.path.exists(existing_json):
            print(f"\nFOV={fov_deg}: ya existe {existing_json}, se omite (borralo si quieres recalcularlo).",
                  flush=True)
            with open(existing_json, "r", encoding="utf-8") as f:
                salida = json.load(f)
        else:
            salida = run_one_fov(TheSystem, TheNCE, ZOSAPI, fov_deg)
        avg_sinr_db = sum(r["SINR_dB"] for r in salida["resultados_por_asiento"]) / len(salida["resultados_por_asiento"])
        any_outage_min = any(r["outage_servicio_minimo"] for r in salida["resultados_por_asiento"])
        any_outage_obj = any(r["outage_servicio_objetivo"] for r in salida["resultados_por_asiento"])
        resumen.append({"fov_deg": fov_deg, "avg_SINR_dB": avg_sinr_db,
                         "outage_minimo": any_outage_min, "outage_objetivo": any_outage_obj})

    t_sweep_done = datetime.datetime.now()
    print(f"\n{'='*70}\n=== BARRIDO COMPLETO en {(t_sweep_done - t_sweep_start).total_seconds()/60:.1f} min ===", flush=True)
    print(f"{'FOV (deg)':>10} {'SINR prom (dB)':>16} {'Outage min':>12} {'Outage obj':>12}")
    for r in resumen:
        print(f"{r['fov_deg']:>10.1f} {r['avg_SINR_dB']:>16.2f} "
              f"{'SI' if r['outage_minimo'] else 'no':>12} {'SI' if r['outage_objetivo'] else 'no':>12}")

    resumen_path = os.path.join(_THIS_DIR, "resultados", "sinr_fov_sweep_resumen.json")
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)
    print(f"\nResumen del barrido guardado en: {resumen_path}", flush=True)

    del zos
    zos = None
