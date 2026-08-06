"""
Validacion del filtro de FOV en post-procesamiento (reemplaza Par12-15, que
no funciona -- ver test_validacion_fov.py). Traza UNA vez con el detector en
aceptancia total (FOV nativo = 90, sin efecto real de todas formas) y aplica
el corte angular en Python sobre los hits ya leidos, comparando contra los
angulos geometricos conocidos: Rx6/Rx8 = 62.08 deg, Rx7/Rx9 = 73.59 deg
(fuente DIFF, objeto 10, en el pasillo).
"""
import os, math, sys, json

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "codigo_comun"))
from zemax_lifi_common import (
    PythonStandaloneApplication, set_par_int, set_par_double,
    set_fov, get_global_z_axis, run_nsc_trace, read_zrd_hits_on_objects,
    find_zrd_file, filter_hits_by_fov
)

zos = PythonStandaloneApplication()
ZOSAPI = zos.ZOSAPI
TheSystem = zos.TheSystem

filepath = os.path.join(_THIS_DIR, "Avion_SinBloqueo_Base.zmx")
zos.OpenFile(filepath, False)
TheNCE = TheSystem.NCE

TX_IDXS = [2, 3, 4, 5, 10]
RX_IDXS = [6, 7, 8, 9]
DIFF_TX = 10
RAYS = 300000
LAYOUT_RAYS = 1000
PITCH_DEG = 0.0

lambert_m1 = [1.0, math.cos(math.radians(22.5)), math.cos(math.radians(45)),
              math.cos(math.radians(67.5)), 0.0]
for src_idx in TX_IDXS:
    src = TheNCE.GetObjectAt(src_idx)
    for i, val in enumerate(lambert_m1):
        set_par_double(src, ZOSAPI, 11 + i, val)
    set_par_int(src, ZOSAPI, 1, LAYOUT_RAYS)
    set_par_int(src, ZOSAPI, 2, RAYS if src_idx == DIFF_TX else 0)

normals = {}
for rx_idx in RX_IDXS:
    rx = TheNCE.GetObjectAt(rx_idx)
    rx.TiltAboutY = PITCH_DEG
    set_fov(rx, ZOSAPI, 90.0)
    normal, _ = get_global_z_axis(TheNCE, rx_idx)
    normals[rx_idx] = normal
    print(f"Rx{rx_idx} normal global = {normal}")

zrd_format_full = ZOSAPI.Tools.RayTrace.ZRDFormatType.CompressedFullData
zrd_name = "test_fov_v2.ZRD"
total_energy = run_nsc_trace(TheSystem, save_rays_file=zrd_name, zrd_format=zrd_format_full,
                              scatter=True, split=False, polarization=False)
zrd_path = find_zrd_file(zrd_name, [os.path.join(_THIS_DIR), _THIS_DIR])
hits_all = read_zrd_hits_on_objects(TheSystem, zrd_path, RX_IDXS)
os.remove(zrd_path)

print(f"\nTotal hits sin filtrar: Rx6={len(hits_all[6])} Rx7={len(hits_all[7])} "
      f"Rx8={len(hits_all[8])} Rx9={len(hits_all[9])}")

FOV_LIST = [5, 10, 20, 30, 40, 50, 55, 58, 60, 61, 62, 62.08, 63, 64, 65, 68, 70,
            72, 73, 73.59, 74, 75, 78, 80, 85, 90]

print(f"\n{'FOV':>7} | {'Rx6(cut=62.08)':>16} | {'Rx7(cut=73.59)':>16} | "
      f"{'Rx8(cut=62.08)':>16} | {'Rx9(cut=73.59)':>16}")
resultados = []
for fov in FOV_LIST:
    row = {"fov": fov}
    vals = []
    for rx_idx in RX_IDXS:
        kept = filter_hits_by_fov(hits_all[rx_idx], normals[rx_idx], fov)
        Pr_mW = sum(h[6] for h in kept) * 1000
        row[f"Rx{rx_idx}_mW"] = Pr_mW
        row[f"Rx{rx_idx}_nhits"] = len(kept)
        vals.append(Pr_mW)
    resultados.append(row)
    print(f"{fov:>7} | {vals[0]:>16.5f} | {vals[1]:>16.5f} | {vals[2]:>16.5f} | {vals[3]:>16.5f}")

with open(os.path.join(_THIS_DIR, "resultados_generales", "validacion_fov_postproc.json"), "w") as f:
    json.dump(resultados, f, indent=2)

del zos
zos = None
