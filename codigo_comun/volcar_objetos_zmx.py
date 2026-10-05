"""
Volcado de objetos NSC (indice, tipo, posicion/tilt, comentario, parametros
Par1-17) leido directamente del .zmx como texto plano (UTF-16LE), sin
necesitar Zemax/ZOS-API (no disponible en este sandbox -- ver
inspeccionar_nce.py, que hace lo mismo via API real en Windows).

Formato real de un bloque de objeto NSC en el .zmx (confirmado por lectura
directa, con varias rondas de verificacion cruzada tras errores de indexado
en una iteracion previa):

    NSOP X Y Z TiltX TiltY TiltZ [comentario]
    NSOV ...
    NSOU ...
    NSOW ...
    NSOS ...
    NSOO ...
    NSOQ ...
    NSOD 1 valor ...
    NSOD 2 valor ...
    ...
    NSOH <TIPO> ...
    NOID <indice>          <- el indice del objeto viene DESPUES de NSOH,
                              pegado inmediatamente a el (sin texto entre
                              medio); un parseo que use NOID como separador
                              de bloque antes de leer NSOH se desalinea un
                              objeto (ver commit 3e147df, corregido aqui).

Se parsea buscando, para cada "NSOH" en el archivo, el NSOP/NSOD mas
reciente (que pertenecen al mismo objeto, ya que aparecen antes de su
propio NSOH) y el NOID que viene inmediatamente despues.
"""
import os, csv, sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))


def parse_zmx_objects(zmx_path):
    with open(zmx_path, encoding="utf-16le", errors="ignore") as f:
        lines = [l.strip() for l in f]

    objetos = []
    cur_pos = None
    cur_params = {}
    for i, line in enumerate(lines):
        if line.startswith("NSOP "):
            cur_pos = line
            cur_params = {}
        elif line.startswith("NSOD "):
            parts = line.split()
            idx = int(parts[1])
            valor = parts[2]
            cur_params[idx] = valor
        elif line.startswith("NSOH "):
            parts = line.split()
            tipo = parts[1]
            # el NOID de este objeto es la siguiente linea no vacia
            noid = None
            for j in range(i + 1, min(i + 4, len(lines))):
                if lines[j].startswith("NOID "):
                    noid = lines[j].split()[1]
                    break
            pos_fields = cur_pos.split() if cur_pos else []
            # NSOP X Y Z TiltX TiltY TiltZ [comentario opcional]
            x, y, z = pos_fields[1:4] if len(pos_fields) >= 4 else ("", "", "")
            tx, ty, tz = pos_fields[4:7] if len(pos_fields) >= 7 else ("", "", "")
            comentario = " ".join(pos_fields[7:]) if len(pos_fields) > 7 else ""
            objetos.append({
                "noid": noid, "tipo": tipo,
                "X": x, "Y": y, "Z": z, "TiltX": tx, "TiltY": ty, "TiltZ": tz,
                "comentario": comentario, "params": dict(cur_params),
            })
    return objetos


def volcar(zmx_path, csv_path, max_par=17):
    objetos = parse_zmx_objects(zmx_path)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["NOID", "Tipo", "X_mm", "Y_mm", "Z_mm", "TiltX_deg", "TiltY_deg", "TiltZ_deg", "Comentario"]
        header += [f"Par{k}" for k in range(1, max_par + 1)]
        w.writerow(header)
        for o in objetos:
            row = [o["noid"], o["tipo"], o["X"], o["Y"], o["Z"], o["TiltX"], o["TiltY"], o["TiltZ"], o["comentario"]]
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
        extra = ""
        if o["comentario"]:
            extra = f"  [{o['comentario']}]"
        nz_params = {k: v for k, v in o["params"].items() if float(v) != 0.0}
        print(f"  NOID={o['noid']:<3} {o['tipo']:<10} pos=({o['X']}, {o['Y']}, {o['Z']}) "
              f"tilt=({o['TiltX']}, {o['TiltY']}, {o['TiltZ']}){extra}")
        if nz_params:
            print(f"           Par != 0: {nz_params}")

    # Verificacion cruzada: debe haber exactamente 1 STLO, 5 SRAD (4 LOS + 1 DIFF),
    # 4 DETE (Rx6-9) y objetos "ABSORB" repurposados = obstaculo real.
    tipos = {}
    for o in objetos:
        tipos[o["tipo"]] = tipos.get(o["tipo"], 0) + 1
    print(f"\nConteo por tipo: {tipos}")
