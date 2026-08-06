"""
Prueba de convergencia del trazado NSC (P1-7 del feedback de revision):
corre el mismo trazado aislado (solo Tx2 activo, modelo sin bloqueo) con
distintos numeros de rayos, y repite el numero "estandar" (1,000,000) dos
veces, para cuantificar cuanto varia la potencia recibida por ruido de
Monte Carlo vs. por el numero de rayos elegido.

Si la variacion entre repeticiones al mismo N de rayos es comparable a las
diferencias que veiamos entre puntos de FOV en el barrido, confirma que
esas diferencias eran ruido, no una tendencia fisica real.
"""
import os, math, sys, json, datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "codigo_comun"))
from zemax_lifi_common import (
    PythonStandaloneApplication, get_par_double, set_par_int, set_par_double,
    set_fov, get_global_z_axis, run_nsc_trace, read_zrd_hits_on_objects, find_zrd_file
)

zos = PythonStandaloneApplication()
ZOSAPI = zos.ZOSAPI
TheSystem = zos.TheSystem

filepath = os.path.join(_THIS_DIR, "modelo", "Avion_SinBloqueo_Base.zmx")
zos.OpenFile(filepath, False)
TheNCE = TheSystem.NCE

TX_IDXS = [2, 3, 4, 5, 10]
RX_IDXS = [6, 7, 8, 9]
ACTIVE_TX = 2
LAYOUT_RAYS = 1000
PITCH_DEG = 0.0

# (etiqueta, numero_de_rayos)
CORRIDAS = [
    ("200k", 200000),
    ("500k", 500000),
    ("1M_a", 1000000),
    ("1M_b", 1000000),   # repeticion al mismo N, para medir ruido puro
    ("2M", 2000000),
]

lambert_m1 = [1.0, math.cos(math.radians(22.5)), math.cos(math.radians(45)),
              math.cos(math.radians(67.5)), 0.0]
for src_idx in TX_IDXS:
    src = TheNCE.GetObjectAt(src_idx)
    for i, val in enumerate(lambert_m1):
        set_par_double(src, ZOSAPI, 11 + i, val)
    set_par_int(src, ZOSAPI, 1, LAYOUT_RAYS)

for rx_idx in RX_IDXS:
    rx = TheNCE.GetObjectAt(rx_idx)
    rx.TiltAboutY = PITCH_DEG
    set_fov(rx, ZOSAPI, 90.0)

zrd_format_full = ZOSAPI.Tools.RayTrace.ZRDFormatType.CompressedFullData

resultados = []
for label, n_rays in CORRIDAS:
    for src_idx in TX_IDXS:
        src = TheNCE.GetObjectAt(src_idx)
        set_par_int(src, ZOSAPI, 2, n_rays if src_idx == ACTIVE_TX else 0)

    t0 = datetime.datetime.now()
    print(f"[{t0.isoformat(timespec='seconds')}] Corrida {label} ({n_rays} rayos)...", flush=True)
    zrd_name = f"conv_{label}.ZRD"
    total_energy = run_nsc_trace(TheSystem, save_rays_file=zrd_name, zrd_format=zrd_format_full,
                                  scatter=True, split=False, polarization=False)
    zrd_path = find_zrd_file(zrd_name, [os.path.join(_THIS_DIR, "modelo"), _THIS_DIR, _PROJECT_ROOT])
    hits = read_zrd_hits_on_objects(TheSystem, zrd_path, RX_IDXS)
    os.remove(zrd_path)
    t1 = datetime.datetime.now()

    Pr = {rx: sum(h[6] for h in hits[rx]) * 1000 for rx in RX_IDXS}  # mW
    n_hits = {rx: len(hits[rx]) for rx in RX_IDXS}
    resultados.append({"label": label, "n_rays": n_rays, "Pr_mW": Pr, "n_hits": n_hits,
                        "t_s": (t1 - t0).total_seconds()})
    print(f"  {label}: {(t1-t0).total_seconds():.1f}s | " +
          "  ".join(f"Rx{rx}={Pr[rx]:.4f}mW({n_hits[rx]})" for rx in RX_IDXS), flush=True)

print("\n=== Resumen de convergencia (Rx6, senal propia del Tx2) ===")
for r in resultados:
    print(f"{r['label']:>6} ({r['n_rays']:>8} rayos): Pr(Rx6) = {r['Pr_mW'][6]:.4f} mW  "
          f"({r['n_hits'][6]} hits, {r['t_s']:.1f}s)")

ref = next(r for r in resultados if r["label"] == "1M_a")["Pr_mW"][6]
print(f"\nDiferencia relativa vs 1M_a (Rx6):")
for r in resultados:
    diff_pct = 100.0 * (r["Pr_mW"][6] - ref) / ref
    print(f"  {r['label']:>6}: {diff_pct:+.2f}%")

out_dir = os.path.join(_THIS_DIR, "resultados")
os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, "convergencia_nsc.json"), "w") as f:
    json.dump(resultados, f, indent=2)
print(f"\nGuardado en: {os.path.join(out_dir, 'convergencia_nsc.json')}")

del zos
zos = None
