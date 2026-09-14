"""
M9 (feedback del revisor): extrae la posicion 3D global y la normal de cada
transmisor LOS y cada receptor, directamente del modelo ya construido, para
poder comparar la ganancia de canal analitica (Ec. 5 del paper, Lambertiano)
contra la Pr_own_LOS_mW ya exportada por el pipeline oficial.

Importante: este script NO traza ni un solo rayo. Solo consulta la matriz de
transformacion de cada objeto (TheNCE.GetMatrix), igual que ya hace
get_global_z_axis() en zemax_lifi_common.py. Es una lectura geometrica
instantanea sobre el modelo ya existente, no una simulacion nueva.

Correr sobre escenarios/sin_bloqueo_0grados/modelo/Avion_SinBloqueo_0grados_inspect.zmx
(el unico estado sin ningun obstaculo, que es el que se usa para la
validacion analitica segun el paper).

Imprime, para cada Tx LOS (2-5) y cada Rx (6-9): posicion global (x,y,z) y
normal global (eje Z local). Con eso, en Python puro (sin Zemax) se puede
calcular d_k,i, phi_k,i, psi_k,i y H_k,i(pi) via la Ec. 1-3 y 5-6 del paper.
"""
import os, sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _THIS_DIR)
from zemax_lifi_common import PythonStandaloneApplication, get_global_z_axis

MODELO = os.path.join(_PROJECT_ROOT, "escenarios", "sin_bloqueo_0grados", "modelo",
                       "Avion_SinBloqueo_0grados_inspect.zmx")

TX_LOS_IDXS = [2, 3, 4, 5]
RX_IDXS = [6, 7, 8, 9]

zos = PythonStandaloneApplication()
ZOSAPI = zos.ZOSAPI
TheSystem = zos.TheSystem
zos.OpenFile(MODELO, False)
TheNCE = TheSystem.NCE

print("=== Transmisores LOS (reading lamps) ===")
for idx in TX_LOS_IDXS:
    normal, pos = get_global_z_axis(TheNCE, idx)
    print(f"Tx{idx}: pos_global=({pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f})  "
          f"normal_global=({normal[0]:.6f}, {normal[1]:.6f}, {normal[2]:.6f})")

print("\n=== Receptores (pitch=0) ===")
for idx in RX_IDXS:
    normal, pos = get_global_z_axis(TheNCE, idx)
    print(f"Rx{idx}: pos_global=({pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f})  "
          f"normal_global=({normal[0]:.6f}, {normal[1]:.6f}, {normal[2]:.6f})")

del zos
zos = None
