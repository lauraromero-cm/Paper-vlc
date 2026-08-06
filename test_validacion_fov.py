"""
Prueba unitaria de validacion fisica del FOV (P0 del feedback de revision).

Usa la fuente DIFF (objeto 10, en el centro del pasillo) como fuente de
prueba a angulo conocido respecto a cada detector:
  - Rx6/Rx8 (asientos de pasillo, X=+-100): angulo = 62.08 grados
  - Rx7/Rx9 (asientos de ventana, X=+-180): angulo = 73.59 grados

Si el FOV nativo del detector realmente recorta los rayos por angulo de
incidencia, se espera:
  - Potencia ~0 en Rx6/Rx8 para FOV < 62.08 grados, y > 0 para FOV >= 62.08
  - Potencia ~0 en Rx7/Rx9 para FOV < 73.59 grados, y > 0 para FOV >= 73.59

Si las curvas no muestran esa transicion (potencia > 0 incluso con FOV muy
chico, o plana en todo el barrido), el FOV no esta siendo aplicado
fisicamente al detector.
"""
import os, math, sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "codigo_comun"))
from zemax_lifi_common import (
    PythonStandaloneApplication, set_par_int, set_par_double,
    set_fov, run_nsc_trace, read_zrd_hits_on_objects, find_zrd_file
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

FOV_LIST = [5, 10, 20, 30, 40, 50, 55, 58, 60, 61, 62, 63, 64, 65, 68, 70,
            72, 73, 74, 75, 78, 80, 85, 90]

lambert_m1 = [1.0, math.cos(math.radians(22.5)), math.cos(math.radians(45)),
              math.cos(math.radians(67.5)), 0.0]
for src_idx in TX_IDXS:
    src = TheNCE.GetObjectAt(src_idx)
    for i, val in enumerate(lambert_m1):
        set_par_double(src, ZOSAPI, 11 + i, val)
    set_par_int(src, ZOSAPI, 1, LAYOUT_RAYS)
    set_par_int(src, ZOSAPI, 2, RAYS if src_idx == DIFF_TX else 0)

zrd_format_full = ZOSAPI.Tools.RayTrace.ZRDFormatType.CompressedFullData

print(f"{'FOV':>5} | {'Rx6(62.08 esperado)':>20} | {'Rx7(73.59 esperado)':>20} | "
      f"{'Rx8(62.08 esperado)':>20} | {'Rx9(73.59 esperado)':>20}")
resultados = []
for fov in FOV_LIST:
    for rx_idx in RX_IDXS:
        rx = TheNCE.GetObjectAt(rx_idx)
        rx.TiltAboutY = PITCH_DEG
        set_fov(rx, ZOSAPI, float(fov))

    zrd_name = f"test_fov_{fov}.ZRD"
    total_energy = run_nsc_trace(TheSystem, save_rays_file=zrd_name, zrd_format=zrd_format_full,
                                  scatter=True, split=False, polarization=False)
    zrd_path = find_zrd_file(zrd_name, [os.path.join(_THIS_DIR), _THIS_DIR])
    hits = read_zrd_hits_on_objects(TheSystem, zrd_path, RX_IDXS)
    Pr = {rx: sum(h[6] for h in hits[rx]) * 1000 for rx in RX_IDXS}  # mW
    os.remove(zrd_path)

    resultados.append({"fov": fov, **{f"Rx{rx}_mW": Pr[rx] for rx in RX_IDXS}})
    print(f"{fov:>5} | {Pr[6]:>20.5f} | {Pr[7]:>20.5f} | {Pr[8]:>20.5f} | {Pr[9]:>20.5f}", flush=True)

import json
with open(os.path.join(_THIS_DIR, "resultados_generales", "validacion_fov_diff.json"), "w") as f:
    json.dump(resultados, f, indent=2)

del zos
zos = None
