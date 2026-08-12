"""
P1-8 (feedback del revisor): la cabina se queda con rho=0.70 (sin cambios),
pero los objetos de bloqueo (cilindro=persona, bloque=carrito) deben tener
su propio coeficiente de reflectividad segun literatura, en vez de heredar
el default (sin scatter = absorcion total).

Asigna scatter Lambertiano con ScatterFraction=rho en las caras validas
(Front/Back) del ultimo objeto NSC de cada modelo (el obstaculo de bloqueo),
y guarda el archivo en el mismo lugar.

Valores (ajustables, tipicos de literatura VLC/optica):
  - Persona (ropa, cilindro):     rho = 0.40  (rango tipico 0.30-0.50)
  - Carrito (metal/plastico):     rho = 0.65  (rango tipico 0.60-0.70)
"""
import os, sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _THIS_DIR)
from zemax_lifi_common import PythonStandaloneApplication

RHO_PERSONA = 0.40
RHO_CARRITO = 0.65

MODELOS = [
    ("escenarios/bloqueo_persona_0grados/modelo/Avion_Bloqueo_persona.zmx", RHO_PERSONA, "Cylinder Volume"),
    ("escenarios/bloqueo_persona_15grados/modelo/Avion_Bloqueo_persona.zmx", RHO_PERSONA, "Cylinder Volume"),
    ("escenarios/bloqueo_persona_30grados/modelo/Avion_Bloqueo_persona.zmx", RHO_PERSONA, "Cylinder Volume"),
    ("escenarios/bloqueo_carrito_0grados/modelo/Avion_Bloqueo_carrito.zmx", RHO_CARRITO, "Rectangular Volume"),
    ("escenarios/bloqueo_carrito_15grados/modelo/Avion_Bloqueo_carrito.zmx", RHO_CARRITO, "Rectangular Volume"),
    ("escenarios/bloqueo_carrito_30grados/modelo/Avion_Bloqueo_carrito.zmx", RHO_CARRITO, "Rectangular Volume"),
]

zos = PythonStandaloneApplication()
ZOSAPI = zos.ZOSAPI
TheSystem = zos.TheSystem
Lambertian = ZOSAPI.Editors.NCE.ObjectScatteringTypes.Lambertian

for rel_path, rho, expected_type in MODELOS:
    filepath = os.path.join(_PROJECT_ROOT, rel_path)
    print(f"\n=== {rel_path} (rho={rho}) ===")
    zos.OpenFile(filepath, False)
    TheNCE = TheSystem.NCE
    n_obj = TheNCE.NumberOfObjects
    obj = TheNCE.GetObjectAt(n_obj)
    assert obj.TypeName == expected_type, f"Esperaba {expected_type}, encontre {obj.TypeName}"

    csd = obj.CoatScatterData
    assert csd.IsCoatScatterAvailable
    for f in range(1, csd.NumberOfFaces + 1):
        fd = csd.GetFaceData(f)
        if not fd.IsValid or fd.IsReadOnly:
            continue
        settings = fd.CreateScatterModelSettings(Lambertian)
        # settings.ScatterFraction = rho no persiste (Python.NET no resuelve el
        # setter real via la interfaz base IObjectScatteringSettings); se fuerza
        # via reflexion .NET, igual que se uso para leer el diagnostico.
        prop = settings.GetType().GetProperty("ScatterFraction")
        prop.SetValue(settings, rho, None)
        fd.ChangeScatterModelSettings(settings)

        fd2 = csd.GetFaceData(f)
        applied_type = fd2.CurrentScatterModel
        applied_settings = fd2.CurrentScatterModelSettings
        applied_frac = applied_settings.GetType().GetProperty("ScatterFraction").GetValue(applied_settings, None)
        print(f"  Cara {f} ({fd.FaceName}): scatter={applied_type}, fraction={applied_frac}")

    TheSystem.SaveAs(filepath)
    print(f"  Guardado.")

del zos
zos = None
