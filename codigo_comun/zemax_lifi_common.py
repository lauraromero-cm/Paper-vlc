import clr, os, winreg, glob


class PythonStandaloneApplication(object):
    class LicenseException(Exception): pass
    class ConnectionException(Exception): pass
    class InitializationException(Exception): pass
    class SystemNotPresentException(Exception): pass

    def __init__(self, path=None):
        aKey = winreg.OpenKey(winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER), r"Software\Zemax", 0, winreg.KEY_READ)
        zemaxData = winreg.QueryValueEx(aKey, 'ZemaxRoot')
        NetHelper = os.path.join(os.sep, zemaxData[0], r'ZOS-API\Libraries\ZOSAPI_NetHelper.dll')
        winreg.CloseKey(aKey)
        clr.AddReference(NetHelper)
        import ZOSAPI_NetHelper
        isInitialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize() if path is None else ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(path)
        if not isInitialized:
            raise PythonStandaloneApplication.InitializationException("Unable to locate Zemax OpticStudio.")
        dir_ = ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory()
        clr.AddReference(os.path.join(os.sep, dir_, "ZOSAPI.dll"))
        clr.AddReference(os.path.join(os.sep, dir_, "ZOSAPI_Interfaces.dll"))
        import ZOSAPI
        self.ZOSAPI = ZOSAPI
        self.TheConnection = ZOSAPI.ZOSAPI_Connection()
        self.TheApplication = self.TheConnection.CreateNewApplication()
        if self.TheApplication is None:
            raise PythonStandaloneApplication.InitializationException("Unable to acquire ZOSAPI application")
        if self.TheApplication.IsValidLicenseForAPI == False:
            raise PythonStandaloneApplication.LicenseException("License is not valid for ZOSAPI use")
        self.TheSystem = self.TheApplication.PrimarySystem
        if self.TheSystem is None:
            raise PythonStandaloneApplication.SystemNotPresentException("Unable to acquire Primary system")

    def __del__(self):
        if self.TheApplication is not None:
            self.TheApplication.CloseApplication()
            self.TheApplication = None
        self.TheConnection = None

    def OpenFile(self, filepath, saveIfNeeded):
        self.TheSystem.LoadFile(filepath, saveIfNeeded)


def get_par_double(obj, ZOSAPI, n):
    col = getattr(ZOSAPI.Editors.NCE.ObjectColumn, f"Par{n}")
    return obj.GetObjectCell(col).DoubleValue


def get_par_int(obj, ZOSAPI, n):
    col = getattr(ZOSAPI.Editors.NCE.ObjectColumn, f"Par{n}")
    return obj.GetObjectCell(col).IntegerValue


def set_par_int(obj, ZOSAPI, n, value):
    col = getattr(ZOSAPI.Editors.NCE.ObjectColumn, f"Par{n}")
    obj.GetObjectCell(col).IntegerValue = value


def set_par_double(obj, ZOSAPI, n, value):
    col = getattr(ZOSAPI.Editors.NCE.ObjectColumn, f"Par{n}")
    obj.GetObjectCell(col).DoubleValue = value


def set_fov(rx, ZOSAPI, fov_deg):
    """Fija el FOV nativo (rectangular, Par12-15) simetrico en X e Y."""
    set_par_double(rx, ZOSAPI, 12, -fov_deg)
    set_par_double(rx, ZOSAPI, 13, fov_deg)
    set_par_double(rx, ZOSAPI, 14, -fov_deg)
    set_par_double(rx, ZOSAPI, 15, fov_deg)


def get_global_z_axis(TheNCE, obj_index):
    """Devuelve el eje Z local del objeto expresado en coordenadas globales (vector unitario)."""
    ok, r11, r12, r13, r21, r22, r23, r31, r32, r33, xo, yo, zo = TheNCE.GetMatrix(
        obj_index, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    # Las columnas de la matriz de rotacion mapean ejes locales -> globales;
    # el eje local Z es la 3a columna: (r13, r23, r33)
    return (r13, r23, r33), (xo, yo, zo)


def run_nsc_trace(TheSystem, save_rays_file=None, zrd_format=None, scatter=True, split=False, polarization=False):
    """save_rays_file, si se da, DEBE ser solo el nombre de archivo (sin carpeta):
    Zemax decide donde lo guarda (ver find_zrd_file para localizarlo despues)."""
    NSCRayTrace = TheSystem.Tools.OpenNSCRayTrace()
    NSCRayTrace.ClearDetectors(0)
    NSCRayTrace.IgnoreErrors = True
    NSCRayTrace.ScatterNSCRays = scatter
    NSCRayTrace.SplitNSCRays = split
    NSCRayTrace.UsePolarization = polarization
    if save_rays_file:
        NSCRayTrace.SaveRays = True
        NSCRayTrace.SaveRaysFile = os.path.basename(save_rays_file)
        if zrd_format is not None:
            NSCRayTrace.ZRDFormat = zrd_format
    NSCRayTrace.RunAndWaitForCompletion()
    total_energy = NSCRayTrace.GetTotalRayEnergy()
    NSCRayTrace.Close()
    return total_energy


def find_zrd_file(filename, search_dirs):
    """Busca 'filename' en cada carpeta de search_dirs (recursivamente) y devuelve
    la primera ruta encontrada. Zemax guarda el ZRD junto al .zmx cargado o en su
    carpeta de datos por defecto, no necesariamente donde corre el script."""
    basename = os.path.basename(filename)
    for d in search_dirs:
        matches = glob.glob(os.path.join(d, "**", basename), recursive=True)
        if matches:
            return matches[0]
    raise FileNotFoundError(f"No se encontro '{basename}' en: {search_dirs}")


def read_zrd_hits_on_object(TheSystem, zrd_full_path, target_object):
    """Recorre el ZRD y devuelve una lista de (X,Y,Z,L,M,N,intensity) para cada
    segmento cuyo HitObject == target_object."""
    reader = TheSystem.Tools.OpenRayDatabaseReader()
    reader.ZRDFile = zrd_full_path
    reader.RunAndWaitForCompletion()
    if not reader.Succeeded:
        raise RuntimeError(f"No se pudo leer el ZRD: {reader.ErrorMessage}")
    results = reader.GetResults()

    hits = []
    while results.ReadNextRay():
        num_segs = results.NumSegments
        for _ in range(num_segs):
            if not results.ReadNextRaySegment():
                break
            if results.HitObject == target_object:
                hits.append((
                    results.X, results.Y, results.Z,
                    results.L, results.M, results.N,
                    results.Intensity,
                    results.SegmentLevel,
                    results.RayNumber,
                ))
    reader.Close()
    return hits
