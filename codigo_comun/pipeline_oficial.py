"""
Pipeline oficial de SINR hibrido LOS/DIFF, con la metodologia validada tras
el feedback del revisor:
  - 1 solo trazado NSC por fuente (4 LOS + 1 DIFF = 5 trazados totales por
    escenario), en vez de 1 trazado por cada valor de FOV. El FOV real se
    aplica en post-proceso sobre los mismos hits (filter_hits_by_fov), ya
    que el FOV nativo de Zemax no filtra en modo "position space" (ver
    incidencia en zemax_lifi_common.py).
  - Exporta LOS, DIFF e interferencia por separado (P0-2).
  - Incluye el enlace DIFF como canal WDM/TDMA independiente sin
    interferencia cruzada, con selection combining SINR_hybrid=max(LOS,DIFF)
    (P0-3).
  - Usa el modelo de ruido completo (fondo, corriente oscura, filtro,
    eficiencia real de concentrador) de noise_model.py (P1-6).
  - Usa las reflectividades ya asignadas al cilindro/carrito (P1-8); la
    cabina se deja en rho=0.70 sin cambios, segun acepto el revisor.
  - Pout se calcula sobre N=4 asientos, documentado como referencial (P1-5,
    ver escenarios/justificacion_P1-5_Pout_N4.md).

Corre los 9 escenarios oficiales (3 estados x 3 pitches). Es resumible: si
ya existe el JSON de resultados de un escenario, lo omite (borralo para
recalcularlo).
"""
import os, math, sys, json, datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _THIS_DIR)
from zemax_lifi_common import (
    PythonStandaloneApplication, get_par_double, set_par_int, set_par_double,
    set_fov, get_global_z_axis, run_nsc_trace, read_zrd_hits_on_objects,
    find_zrd_file, filter_hits_by_fov
)
import noise_model as nm

TX_LOS_IDXS = [2, 3, 4, 5]
RX_IDXS = [6, 7, 8, 9]
own_tx_of = dict(zip(RX_IDXS, TX_LOS_IDXS))
RAYS_PER_SOURCE = 1000000  # validado por convergencia NSC (P1-7): <1% de ruido
LAYOUT_RAYS = 100000
POPT_W = 2.0
FOV_LIST = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]

ESCENARIOS = [
    {"nombre": "sin_bloqueo_0grados", "pitch_deg": 0.0, "diff_tx": 10,
     "modelo": "escenarios/sin_bloqueo_0grados/modelo/Avion_SinBloqueo_0grados_inspect.zmx"},
    {"nombre": "sin_bloqueo_15grados", "pitch_deg": 15.0, "diff_tx": 10,
     "modelo": "escenarios/sin_bloqueo_15grados/modelo/Avion_SinBloqueo_15grados_inspect.zmx"},
    {"nombre": "sin_bloqueo_30grados", "pitch_deg": 30.0, "diff_tx": 10,
     "modelo": "escenarios/sin_bloqueo_30grados/modelo/Avion_SinBloqueo_30grados_inspect.zmx"},
    {"nombre": "bloqueo_carrito_0grados", "pitch_deg": 0.0, "diff_tx": 11,
     "modelo": "escenarios/bloqueo_carrito_0grados/modelo/Avion_Bloqueo_carrito.zmx"},
    {"nombre": "bloqueo_carrito_15grados", "pitch_deg": 15.0, "diff_tx": 11,
     "modelo": "escenarios/bloqueo_carrito_15grados/modelo/Avion_Bloqueo_carrito.zmx"},
    {"nombre": "bloqueo_carrito_30grados", "pitch_deg": 30.0, "diff_tx": 11,
     "modelo": "escenarios/bloqueo_carrito_30grados/modelo/Avion_Bloqueo_carrito.zmx"},
    {"nombre": "bloqueo_persona_0grados", "pitch_deg": 0.0, "diff_tx": 11,
     "modelo": "escenarios/bloqueo_persona_0grados/modelo/Avion_Bloqueo_persona.zmx"},
    {"nombre": "bloqueo_persona_15grados", "pitch_deg": 15.0, "diff_tx": 11,
     "modelo": "escenarios/bloqueo_persona_15grados/modelo/Avion_Bloqueo_persona.zmx"},
    {"nombre": "bloqueo_persona_30grados", "pitch_deg": 30.0, "diff_tx": 11,
     "modelo": "escenarios/bloqueo_persona_30grados/modelo/Avion_Bloqueo_persona.zmx"},
]


def resultado_ya_existe(nombre):
    path = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados", "sinr_hibrido_oficial.json")
    return os.path.exists(path)


def run_scenario(zos, cfg):
    ZOSAPI = zos.ZOSAPI
    TheSystem = zos.TheSystem
    nombre = cfg["nombre"]
    diff_tx = cfg["diff_tx"]
    pitch_deg = cfg["pitch_deg"]
    all_tx_idxs = TX_LOS_IDXS + [diff_tx]

    filepath = os.path.join(_PROJECT_ROOT, cfg["modelo"])
    print(f"\n{'='*70}\n=== Escenario: {nombre} (pitch={pitch_deg} deg) ===\n{'='*70}", flush=True)
    zos.OpenFile(filepath, False)
    TheNCE = TheSystem.NCE

    lambert_m1 = [1.0, math.cos(math.radians(22.5)), math.cos(math.radians(45)),
                  math.cos(math.radians(67.5)), 0.0]
    for src_idx in all_tx_idxs:
        src = TheNCE.GetObjectAt(src_idx)
        for i, val in enumerate(lambert_m1):
            set_par_double(src, ZOSAPI, 11 + i, val)
        set_par_int(src, ZOSAPI, 1, LAYOUT_RAYS)
        set_par_int(src, ZOSAPI, 2, 0)

    normals = {}
    for rx_idx in RX_IDXS:
        rx = TheNCE.GetObjectAt(rx_idx)
        rx.TiltAboutY = pitch_deg
        set_fov(rx, ZOSAPI, 90.0)  # aceptancia total nativa; el corte real es en post-proceso
        normal, _ = get_global_z_axis(TheNCE, rx_idx)
        normals[rx_idx] = normal

    zrd_format_full = ZOSAPI.Tools.RayTrace.ZRDFormatType.CompressedFullData

    # --- 1 trazado por Tx (LOS x4 + DIFF x1) ---
    hits_por_tx = {}
    for active_tx in all_tx_idxs:
        for src_idx in all_tx_idxs:
            src = TheNCE.GetObjectAt(src_idx)
            set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE if src_idx == active_tx else 0)
            assert get_par_double(src, ZOSAPI, 3) == POPT_W

        t0 = datetime.datetime.now()
        print(f"[{t0.isoformat(timespec='seconds')}] {nombre}: trazando Tx {active_tx} "
              f"({RAYS_PER_SOURCE} rayos)...", flush=True)
        zrd_name = f"{nombre}_tx{active_tx}.ZRD"
        total_energy = run_nsc_trace(TheSystem, save_rays_file=zrd_name, zrd_format=zrd_format_full,
                                      scatter=True, split=False, polarization=False)
        assert abs(total_energy - POPT_W) < 1e-6, f"Energia inesperada: {total_energy}"
        zrd_path = find_zrd_file(zrd_name, [os.path.join(os.path.dirname(filepath)), _THIS_DIR, _PROJECT_ROOT])
        hits = read_zrd_hits_on_objects(TheSystem, zrd_path, RX_IDXS, progress_every=200000)
        os.remove(zrd_path)
        hits_por_tx[active_tx] = hits
        t1 = datetime.datetime.now()
        print(f"  Tx {active_tx} completado en {(t1-t0).total_seconds():.1f}s. "
              f"Hits totales: {sum(len(hits[rx]) for rx in RX_IDXS)}", flush=True)

    for src_idx in all_tx_idxs:
        src = TheNCE.GetObjectAt(src_idx)
        set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE)

    # --- Post-proceso por FOV (sin retrazar) ---
    gamma_th1 = nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, nm.BANDWIDTH_HZ)
    gamma_th2 = nm.sinr_threshold_from_ber(nm.BER_MAX)

    filas = []
    for fov in FOV_LIST:
        g = nm.concentrator_gain(fov)
        fila = {"fov_deg": fov, "concentrador_g": g, "asientos": {}}
        for rx_idx in RX_IDXS:
            own_tx = own_tx_of[rx_idx]
            normal = normals[rx_idx]

            Pr_raw = {}
            for tx in all_tx_idxs:
                hits_tx = filter_hits_by_fov(hits_por_tx[tx][rx_idx], normal, fov)
                Pr_raw[tx] = sum(h[6] for h in hits_tx)

            Pr_own = Pr_raw[own_tx] * g
            Pr_interf_LOS = sum(Pr_raw[tx] for tx in TX_LOS_IDXS if tx != own_tx) * g
            Pr_diff = Pr_raw[diff_tx] * g
            Pr_interf_DIFF = 0.0

            sinr_los, _, _, _ = nm.compute_sinr(Pr_own, Pr_interf_LOS)
            sinr_diff, _, _, _ = nm.compute_sinr(Pr_diff, Pr_interf_DIFF)
            sinr_hybrid = max(sinr_los, sinr_diff)

            fila["asientos"][rx_idx] = {
                "Pr_own_LOS_mW": Pr_own * 1000, "Pr_interf_LOS_mW": Pr_interf_LOS * 1000,
                "Pr_DIFF_mW": Pr_diff * 1000, "Pr_interf_DIFF_mW": Pr_interf_DIFF * 1000,
                "SINR_LOS_dB": nm.db(sinr_los), "SINR_DIFF_dB": nm.db(sinr_diff),
                "SINR_hybrid_dB": nm.db(sinr_hybrid),
                "usa_DIFF": sinr_diff > sinr_los,
                "outage_servicio_minimo": sinr_hybrid < gamma_th1,
                "outage_servicio_objetivo": sinr_hybrid < gamma_th2,
            }
        filas.append(fila)
        pout_min = sum(1 for rx in RX_IDXS if fila["asientos"][rx]["outage_servicio_minimo"]) / len(RX_IDXS)
        print(f"  FOV={fov:>5.1f} deg: Pout_min={pout_min*100:.0f}%  " +
              "  ".join(f"Rx{rx}={fila['asientos'][rx]['SINR_hybrid_dB']:.1f}dB" for rx in RX_IDXS), flush=True)

    resultados_dir = os.path.join(_PROJECT_ROOT, "escenarios", nombre, "resultados")
    os.makedirs(resultados_dir, exist_ok=True)
    salida = {
        "escenario": nombre, "pitch_deg": pitch_deg,
        "timestamp": datetime.datetime.now().isoformat(),
        "parametros": {
            "rayos_analisis_por_fuente": RAYS_PER_SOURCE, "Popt_W": POPT_W,
            "gamma_th1_servicio_minimo_dB": nm.db(gamma_th1), "gamma_th2_servicio_objetivo_dB": nm.db(gamma_th2),
        },
        "filas": filas,
    }
    out_path = os.path.join(resultados_dir, "sinr_hibrido_oficial.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    print(f"Guardado: {out_path}", flush=True)


if __name__ == '__main__':
    zos = PythonStandaloneApplication()
    for cfg in ESCENARIOS:
        if resultado_ya_existe(cfg["nombre"]):
            print(f"\n{cfg['nombre']}: ya tiene resultados, se omite (borra el JSON para recalcular).", flush=True)
            continue
        run_scenario(zos, cfg)

    print("\n=== TODOS LOS ESCENARIOS COMPLETADOS ===", flush=True)
    del zos
    zos = None
