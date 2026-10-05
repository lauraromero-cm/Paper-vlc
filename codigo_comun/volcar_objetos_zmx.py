"""
Volcado de objetos NSC (indice, tipo, posicion/tilt, comentario, parametros
Par1-17) leido directamente del .zmx como texto plano (UTF-16LE), sin
necesitar Zemax/ZOS-API (no disponible en este sandbox -- ver
inspeccionar_nce.py, que hace lo mismo via API real en Windows).

CORRECCION (catch del agente redactor, confirmada de forma independiente):
una version anterior de este script asociaba cada NSOH/NOID con el NSOP que
aparece INMEDIATAMENTE ANTES en el texto. Es la asociacion incorrecta. El
orden real de un bloque de objeto NSC es:

    NSOH <TIPO> ...
    NOID <indice>        <- tipo e indice SI estan pegados entre si
    NSOA ...
    NSCS ...  (coatings, puede haber decenas de lineas)
    NSOP X Y Z TiltX TiltY TiltZ [comentario]   <- posicion de ESTE objeto,
    NSOV / NSOU / NSOW / NSOS / NSOO / NSOQ        pero aparece DESPUES de
    NSOD 1 ... / NSOD 2 ... / ...                  su propio tipo/indice
    [NSOH <TIPO del SIGUIENTE objeto> ...]

Verificado de forma concluyente contra un dato independiente: la fuente DIFF
tiene posicion conocida de antemano (0, 330, -260, tilt 180) por ser una
constante ya usada en agregar_diff_a_escenarios.py. Con la asociacion vieja
(NSOP-antes-de-NSOH) esa posicion NUNCA aparecia en los 11 objetos
extraidos. Con la asociacion corregida (NSOP-despues-de-NSOH), el ultimo
objeto NSC_SRAD del archivo cae exactamente en (0,330,-260,180) -- la fuente
DIFF -- cerrando la verificacion. Con esta misma correccion los otros 10
objetos tambien caen en lugares fisicamente sensatos (4 lamparas LOS, 4
detectores, 1 obstaculo), ver salida de este script.
"""
import os, csv

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))


def parse_zmx_objects(zmx_path):
    with open(zmx_path, encoding="utf-16le", errors="ignore") as f:
        lines = [l.strip() for l in f]

    objetos = []
    cur = None  # objeto en construccion: {"tipo":, "noid":, "pos":None, "params":{}}
    for i, line in enumerate(lines):
        if line.startswith("NSOH "):
            if cur is not None:
                objetos.append(cur)
            parts = line.split()
            cur = {"tipo": parts[1], "noid": None, "pos": None, "params": {}}
        elif line.startswith("NOID ") and cur is not None and cur["noid"] is None:
            cur["noid"] = line.split()[1]
        elif line.startswith("NSOP ") and cur is not None:
            cur["pos"] = line
            cur["params"] = {}  # NSOD que vienen DESPUES de este NSOP son los suyos
        elif line.startswith("NSOD ") and cur is not None and cur["pos"] is not None:
            parts = line.split()
            cur["params"][int(parts[1])] = parts[2]
    if cur is not None:
        objetos.append(cur)
    return objetos


def volcar(zmx_path, csv_path, max_par=17):
    objetos = parse_zmx_objects(zmx_path)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["NOID", "Tipo", "X_mm", "Y_mm", "Z_mm", "TiltX_deg", "TiltY_deg", "TiltZ_deg", "Comentario"]
        header += [f"Par{k}" for k in range(1, max_par + 1)]
        w.writerow(header)
        for o in objetos:
            pos_fields = o["pos"].split() if o["pos"] else []
            x, y, z = pos_fields[1:4] if len(pos_fields) >= 4 else ("", "", "")
            tx, ty, tz = pos_fields[4:7] if len(pos_fields) >= 7 else ("", "", "")
            comentario = " ".join(pos_fields[7:]) if len(pos_fields) > 7 else ""
            row = [o["noid"], o["tipo"], x, y, z, tx, ty, tz, comentario]
            row += [o["params"].get(k, "") for k in range(1, max_par + 1)]
            w.writerow(row)
    return objetos


if __name__ == "__main__":
    zmx_path = os.path.join(_PROJECT_ROOT, "escenarios", "bloqueo_persona_0grados",
                             "modelo", "Avion_Bloqueo_persona.zmx")
    csv_path = os.path.join(_PROJECT_ROOT, "resultados_generales", "tables",
                             "volcado_objetos_bloqueo_persona.csv")
    objetos = volcar(zmx_path, csv_path)
    print(f"{len(objetos)} objetos NSC volcados desde {zmx_path}")
    print(f"Guardado: {csv_path}\n")
    for o in objetos:
        pos_fields = o["pos"].split() if o["pos"] else []
        x, y, z = (pos_fields[1:4] if len(pos_fields) >= 4 else ("?", "?", "?"))
        tx, ty, tz = (pos_fields[4:7] if len(pos_fields) >= 7 else ("?", "?", "?"))
        comentario = " ".join(pos_fields[7:]) if len(pos_fields) > 7 else ""
        extra = f"  [{comentario}]" if comentario else ""
        nz = {k: v for k, v in o["params"].items() if float(v) != 0.0}
        print(f"  NOID={o['noid']:<3} {o['tipo']:<10} pos=({x}, {y}, {z})  tilt=({tx}, {ty}, {tz}){extra}")
        if nz:
            print(f"           Par != 0: {nz}")

    tipos = {}
    for o in objetos:
        tipos[o["tipo"]] = tipos.get(o["tipo"], 0) + 1
    print(f"\nConteo por tipo: {tipos}")

    # Verificacion cruzada contra la posicion DIFF conocida de antemano
    diff_esperado = ("0.000000000000E+00", "3.300000000000E+02", "-2.600000000000E+02")
    diff_obj = next((o for o in objetos if o["pos"] and o["pos"].split()[1:4] == list(diff_esperado)), None)
    if diff_obj:
        print(f"\nOK: fuente DIFF encontrada en NOID={diff_obj['noid']} (tipo {diff_obj['tipo']}), "
              f"posicion (0,330,-260) coincide con la constante conocida (agregar_diff_a_escenarios.py).")
    else:
        print("\nADVERTENCIA: no se encontro un objeto en la posicion DIFF esperada (0,330,-260).")
