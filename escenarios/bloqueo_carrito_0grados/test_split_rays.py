"""
Prueba rapida para decidir si conviene activar Split NSC Rays en el escenario
con bloqueo (carrito). Corre el trazado con solo Tx2 activo, una vez con
Split=False y otra con Split=True, mismo numero de rayos, y compara la
potencia recibida en los 4 detectores y el tiempo de computo.
"""
import os, math, sys, time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "codigo_comun"))
from zemax_lifi_common import (
    PythonStandaloneApplication, get_par_double, set_par_int, set_par_double,
    set_fov, run_nsc_trace, read_zrd_hits_on_objects, find_zrd_file
)

zos = PythonStandaloneApplication()
ZOSAPI = zos.ZOSAPI
TheSystem = zos.TheSystem

filepath = os.path.join(_THIS_DIR, "modelo", "Avion_Bloqueo_carrito.zmx")
zos.OpenFile(filepath, False)
TheNCE = TheSystem.NCE

TX_IDXS = [2, 3, 4, 5]
RX_IDXS = [6, 7, 8, 9]
ACTIVE_TX = 2
RAYS = 200000
LAYOUT_RAYS = 10000
POPT_W = 2.0
PITCH_DEG = 0.0
FOV_DEG = 90.0

lambert_m1 = [1.0, math.cos(math.radians(22.5)), math.cos(math.radians(45)),
              math.cos(math.radians(67.5)), 0.0]
for src_idx in TX_IDXS:
    src = TheNCE.GetObjectAt(src_idx)
    for i, val in enumerate(lambert_m1):
        set_par_double(src, ZOSAPI, 11 + i, val)
    set_par_int(src, ZOSAPI, 1, LAYOUT_RAYS)
    set_par_int(src, ZOSAPI, 2, RAYS if src_idx == ACTIVE_TX else 0)

for rx_idx in RX_IDXS:
    rx = TheNCE.GetObjectAt(rx_idx)
    rx.TiltAboutY = PITCH_DEG
    set_fov(rx, ZOSAPI, FOV_DEG)

zrd_format_full = ZOSAPI.Tools.RayTrace.ZRDFormatType.CompressedFullData

resultados = {}
for split_flag in (False, True):
    label = "split_ON" if split_flag else "split_OFF"
    t0 = time.time()
    zrd_name = f"test_{label}.ZRD"
    total_energy = run_nsc_trace(TheSystem, save_rays_file=zrd_name, zrd_format=zrd_format_full,
                                  scatter=True, split=split_flag, polarization=False)
    t1 = time.time()
    assert abs(total_energy - POPT_W) < 1e-6, f"Energia inesperada: {total_energy}"

    zrd_path = find_zrd_file(zrd_name, [os.path.join(_THIS_DIR, "modelo"), _THIS_DIR, _PROJECT_ROOT])
    hits = read_zrd_hits_on_objects(TheSystem, zrd_path, RX_IDXS)
    t2 = time.time()

    Pr = {rx: sum(h[6] for h in hits[rx]) for rx in RX_IDXS}
    n_hits = {rx: len(hits[rx]) for rx in RX_IDXS}
    os.remove(zrd_path)

    resultados[label] = {"Pr": Pr, "n_hits": n_hits, "t_trace": t1 - t0, "t_read": t2 - t1}
    print(f"\n=== {label} ===")
    print(f"  Tiempo trazado: {t1-t0:.1f}s | Tiempo lectura: {t2-t1:.1f}s")
    for rx in RX_IDXS:
        print(f"  Detector {rx}: {Pr[rx]*1000:.4f} mW ({n_hits[rx]} hits)")

print("\n=== Comparacion (split_ON vs split_OFF) ===")
for rx in RX_IDXS:
    p_off = resultados["split_OFF"]["Pr"][rx]
    p_on = resultados["split_ON"]["Pr"][rx]
    diff_pct = 100.0 * (p_on - p_off) / p_off if p_off > 0 else float('nan')
    print(f"Detector {rx}: OFF={p_off*1000:.4f} mW  ON={p_on*1000:.4f} mW  diff={diff_pct:+.2f}%")

t_off = resultados["split_OFF"]["t_trace"] + resultados["split_OFF"]["t_read"]
t_on = resultados["split_ON"]["t_trace"] + resultados["split_ON"]["t_read"]
print(f"\nTiempo total OFF={t_off:.1f}s | ON={t_on:.1f}s | factor={t_on/t_off:.2f}x")

del zos
zos = None
