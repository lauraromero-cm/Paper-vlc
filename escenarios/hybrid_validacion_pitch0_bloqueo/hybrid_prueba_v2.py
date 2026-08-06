"""
PRUEBA de la nueva metodologia (no reemplaza aun el pipeline oficial):
  - 1 solo trazado por Tx (en vez de 1 por cada FOV) -- el FOV nativo de
    Zemax no filtraba nada (ver test_validacion_fov.py), asi que ahora el
    corte angular se aplica en post-proceso con filter_hits_by_fov()
    sobre los mismos hits, para todos los FOV de una sola pasada.
  - Incluye el enlace DIFF (objeto 10, luz de pasillo/respaldo) ademas de
    los 4 LOS propios.
  - Calcula SINR_LOS-only, SINR_DIFF-only y SINR_hybrid = max(LOS, DIFF)
    (selection combining) por asiento y por FOV.

Corre sobre escenarios/hybrid_validacion_pitch0_bloqueo/modelo/Avion_Bloqueo_persona_DIFF.zmx
(pitch=0, sin bloqueo, ya con la luz DIFF agregada).
"""
import os, math, sys, json, datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "codigo_comun"))
from zemax_lifi_common import (
    PythonStandaloneApplication, get_par_double, set_par_int, set_par_double,
    set_fov, get_global_z_axis, run_nsc_trace, read_zrd_hits_on_objects,
    find_zrd_file, filter_hits_by_fov
)
import noise_model as nm

zos = PythonStandaloneApplication()
ZOSAPI = zos.ZOSAPI
TheSystem = zos.TheSystem

filepath = os.path.join(_THIS_DIR, "modelo", "Avion_Bloqueo_persona_DIFF.zmx")
zos.OpenFile(filepath, False)
TheNCE = TheSystem.NCE

TX_LOS_IDXS = [2, 3, 4, 5]
DIFF_TX = 11
ALL_TX_IDXS = TX_LOS_IDXS + [DIFF_TX]
RX_IDXS = [6, 7, 8, 9]
own_tx_of = dict(zip(RX_IDXS, TX_LOS_IDXS))  # 6<->2, 7<->3, 8<->4, 9<->5
RAYS_PER_SOURCE = 1000000
LAYOUT_RAYS = 100000
POPT_W = 2.0
PITCH_DEG = 0.0
ESCENARIO = "hybrid_validacion_bloqueo_persona"

FOV_LIST = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]

lambert_m1 = [1.0, math.cos(math.radians(22.5)), math.cos(math.radians(45)),
              math.cos(math.radians(67.5)), 0.0]
for src_idx in ALL_TX_IDXS:
    src = TheNCE.GetObjectAt(src_idx)
    for i, val in enumerate(lambert_m1):
        set_par_double(src, ZOSAPI, 11 + i, val)
    set_par_int(src, ZOSAPI, 1, LAYOUT_RAYS)
    set_par_int(src, ZOSAPI, 2, 0)  # se activan una por una abajo

normals = {}
for rx_idx in RX_IDXS:
    rx = TheNCE.GetObjectAt(rx_idx)
    rx.TiltAboutY = PITCH_DEG
    set_fov(rx, ZOSAPI, 90.0)  # aceptancia total nativa; el corte real es en post-proceso
    normal, _ = get_global_z_axis(TheNCE, rx_idx)
    normals[rx_idx] = normal

zrd_format_full = ZOSAPI.Tools.RayTrace.ZRDFormatType.CompressedFullData

# --- 1 trazado por Tx (LOS x4 + DIFF x1 = 5 trazados totales) ---
hits_por_tx = {}
for active_tx in ALL_TX_IDXS:
    for src_idx in ALL_TX_IDXS:
        src = TheNCE.GetObjectAt(src_idx)
        set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE if src_idx == active_tx else 0)
        assert get_par_double(src, ZOSAPI, 3) == POPT_W

    t0 = datetime.datetime.now()
    print(f"[{t0.isoformat(timespec='seconds')}] Trazando Tx {active_tx} "
          f"({RAYS_PER_SOURCE} rayos)...", flush=True)
    zrd_name = f"hybrid_only_tx{active_tx}.ZRD"
    total_energy = run_nsc_trace(TheSystem, save_rays_file=zrd_name, zrd_format=zrd_format_full,
                                  scatter=True, split=False, polarization=False)
    assert abs(total_energy - POPT_W) < 1e-6, f"Energia inesperada: {total_energy}"
    zrd_path = find_zrd_file(zrd_name, [os.path.join(_THIS_DIR, "modelo"), _THIS_DIR, _PROJECT_ROOT])
    hits = read_zrd_hits_on_objects(TheSystem, zrd_path, RX_IDXS, progress_every=200000)
    os.remove(zrd_path)
    hits_por_tx[active_tx] = hits
    t1 = datetime.datetime.now()
    print(f"  Tx {active_tx} completado en {(t1-t0).total_seconds():.1f}s. "
          f"Hits totales: {sum(len(hits[rx]) for rx in RX_IDXS)}", flush=True)

for src_idx in ALL_TX_IDXS:
    src = TheNCE.GetObjectAt(src_idx)
    set_par_int(src, ZOSAPI, 2, RAYS_PER_SOURCE)

# --- Umbrales y post-proceso por FOV (sin retrazar) ---
gamma_th1 = nm.sinr_threshold_from_shannon(nm.R_MIN_BPS, nm.BANDWIDTH_HZ)
gamma_th2 = nm.sinr_threshold_from_ber(nm.BER_MAX)
print(f"\ngamma_th,1 = {gamma_th1:.4f} ({nm.db(gamma_th1):.2f} dB)  "
      f"gamma_th,2 = {gamma_th2:.4f} ({nm.db(gamma_th2):.2f} dB)")

filas = []
for fov in FOV_LIST:
    g = nm.concentrator_gain(fov)
    fila = {"fov_deg": fov, "gamma_th1_dB": nm.db(gamma_th1), "gamma_th2_dB": nm.db(gamma_th2),
            "asientos": {}}
    print(f"\n=== FOV = {fov} deg (g={g:.4f}) ===")
    for rx_idx in RX_IDXS:
        own_tx = own_tx_of[rx_idx]
        normal = normals[rx_idx]

        # Potencia cruda (sin ganancia de concentrador) de CADA una de las 5
        # fuentes hacia este receptor, ya filtrada por el FOV real.
        Pr_raw = {}
        for tx in ALL_TX_IDXS:
            hits_tx = filter_hits_by_fov(hits_por_tx[tx][rx_idx], normal, fov)
            Pr_raw[tx] = sum(h[6] for h in hits_tx)

        # Arquitectura de canal separado (WDM/TDMA): el LOS propio interfiere
        # solo con los otros 3 LOS (comparten canal entre si); el DIFF esta en
        # un canal aislado, sin interferencia de las luces de lectura (su
        # limitante es el ruido, no la interferencia co-canal).
        Pr_own = Pr_raw[own_tx] * g
        Pr_interf_LOS = sum(Pr_raw[tx] for tx in TX_LOS_IDXS if tx != own_tx) * g

        Pr_diff = Pr_raw[DIFF_TX] * g
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
        }
        print(f"  Rx{rx_idx}: LOS={nm.db(sinr_los):7.2f}dB  DIFF={nm.db(sinr_diff):7.2f}dB  "
              f"Hybrid={nm.db(sinr_hybrid):7.2f}dB  {'[usa DIFF]' if sinr_diff > sinr_los else ''}")
    filas.append(fila)

out_dir = os.path.join(_THIS_DIR, "resultados")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "hybrid_prueba_v2_resultados.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"escenario": ESCENARIO, "pitch_deg": PITCH_DEG, "filas": filas}, f, indent=2)
print(f"\nGuardado en: {out_path}")

del zos
zos = None
