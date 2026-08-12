"""
Replica el objeto DIFF (Source Radial, luz de pasillo/techo, canal de
backup WDM/TDMA) en los 9 modelos oficiales de escenario, usando exactamente
la misma geometria ya validada en Avion_SinBloqueo_Base.zmx y
Avion_Bloqueo_persona_DIFF.zmx:
  X=0, Y=330, Z=-260, TiltAboutX=180, Potencia=2.0 W.

No modifica ningun objeto existente (Tx LOS, Rx, obstaculo); solo agrega
un objeto nuevo al final de la lista NSC de cada archivo y lo guarda en el
mismo lugar (igual que se hizo para las reflectividades de P1-8).
"""
import os, sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _THIS_DIR)
from zemax_lifi_common import PythonStandaloneApplication, set_par_double

DIFF_X, DIFF_Y, DIFF_Z = 0.0, 330.0, -260.0
DIFF_TILT_X = 180.0
DIFF_POWER_W = 2.0

MODELOS = [
    "escenarios/sin_bloqueo_0grados/modelo/Avion_SinBloqueo_0grados_inspect.zmx",
    "escenarios/sin_bloqueo_15grados/modelo/Avion_SinBloqueo_15grados_inspect.zmx",
    "escenarios/sin_bloqueo_30grados/modelo/Avion_SinBloqueo_30grados_inspect.zmx",
    "escenarios/bloqueo_carrito_0grados/modelo/Avion_Bloqueo_carrito.zmx",
    "escenarios/bloqueo_carrito_15grados/modelo/Avion_Bloqueo_carrito.zmx",
    "escenarios/bloqueo_carrito_30grados/modelo/Avion_Bloqueo_carrito.zmx",
    "escenarios/bloqueo_persona_0grados/modelo/Avion_Bloqueo_persona.zmx",
    "escenarios/bloqueo_persona_15grados/modelo/Avion_Bloqueo_persona.zmx",
    "escenarios/bloqueo_persona_30grados/modelo/Avion_Bloqueo_persona.zmx",
]

zos = PythonStandaloneApplication()
ZOSAPI = zos.ZOSAPI
TheSystem = zos.TheSystem

for rel_path in MODELOS:
    filepath = os.path.join(_PROJECT_ROOT, rel_path)
    print(f"\n=== {rel_path} ===")
    zos.OpenFile(filepath, False)
    TheNCE = TheSystem.NCE

    n_obj_antes = TheNCE.NumberOfObjects
    tx_ref = TheNCE.GetObjectAt(2)  # LOS Tx2, "Source Radial" de referencia
    assert tx_ref.TypeName == "Source Radial", f"Esperaba Source Radial en obj 2, encontre {tx_ref.TypeName}"

    if TheNCE.GetObjectAt(n_obj_antes).TypeName == "Source Radial" and \
            TheNCE.GetObjectAt(n_obj_antes).YPosition == DIFF_Y and \
            TheNCE.GetObjectAt(n_obj_antes).ZPosition == DIFF_Z and \
            TheNCE.GetObjectAt(n_obj_antes).XPosition == DIFF_X:
        print(f"  Ya tiene DIFF en obj {n_obj_antes}, se omite.")
        continue

    new_obj = TheNCE.AddObject()
    settings = new_obj.GetObjectTypeSettings(tx_ref.Type)
    new_obj.ChangeType(settings)

    new_obj.XPosition = DIFF_X
    new_obj.YPosition = DIFF_Y
    new_obj.ZPosition = DIFF_Z
    new_obj.TiltAboutX = DIFF_TILT_X
    new_obj.TiltAboutY = 0.0
    new_obj.TiltAboutZ = 0.0
    set_par_double(new_obj, ZOSAPI, 3, DIFF_POWER_W)

    n_obj_despues = TheNCE.NumberOfObjects
    print(f"  Agregado objeto {n_obj_despues} (DIFF): X={new_obj.XPosition} Y={new_obj.YPosition} "
          f"Z={new_obj.ZPosition} TiltX={new_obj.TiltAboutX} Power={DIFF_POWER_W}W")

    TheSystem.SaveAs(filepath)
    print(f"  Guardado.")

del zos
zos = None
