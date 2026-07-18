import clr, os, winreg
from itertools import islice

class PythonStandaloneApplication(object):
    class LicenseException(Exception):
        pass
    class ConnectionException(Exception):
        pass
    class InitializationException(Exception):
        pass
    class SystemNotPresentException(Exception):
        pass

    def __init__(self, path=None):
        aKey = winreg.OpenKey(winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER), r"Software\Zemax", 0, winreg.KEY_READ)
        zemaxData = winreg.QueryValueEx(aKey, 'ZemaxRoot')
        NetHelper = os.path.join(os.sep, zemaxData[0], r'ZOS-API\Libraries\ZOSAPI_NetHelper.dll')
        winreg.CloseKey(aKey)
        clr.AddReference(NetHelper)
        import ZOSAPI_NetHelper

        if path is None:
            isInitialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize()
        else:
            isInitialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(path)

        if isInitialized:
            dir = ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory()
        else:
            raise PythonStandaloneApplication.InitializationException("Unable to locate Zemax OpticStudio.")

        clr.AddReference(os.path.join(os.sep, dir, "ZOSAPI.dll"))
        clr.AddReference(os.path.join(os.sep, dir, "ZOSAPI_Interfaces.dll"))
        import ZOSAPI

        self.ZOSAPI = ZOSAPI
        self.TheConnection = ZOSAPI.ZOSAPI_Connection()

        if self.TheConnection is None:
            raise PythonStandaloneApplication.ConnectionException("Unable to initialize .NET connection to ZOSAPI")

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
        if self.TheSystem is None:
            raise PythonStandaloneApplication.SystemNotPresentException("Unable to acquire Primary system")
        self.TheSystem.LoadFile(filepath, saveIfNeeded)


if __name__ == '__main__':
    zos = PythonStandaloneApplication()
    ZOSAPI = zos.ZOSAPI
    TheApplication = zos.TheApplication
    TheSystem = zos.TheSystem

    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Avion_SinBloqueo_0grados_inspect.zmx")
    zos.OpenFile(filepath, False)

    if TheSystem.Mode != ZOSAPI.SystemType.NonSequential:
        print("ADVERTENCIA: el sistema no esta en modo No Secuencial (NSC).")

    TheNCE = TheSystem.NCE
    n = TheNCE.NumberOfObjects
    print(f"Numero de objetos NCE: {n}\n")

    print(f"{'#':>3} | {'Tipo':<20} | {'Comentario':<30} | {'X':>10} | {'Y':>10} | {'Z':>10} | {'Tilt X':>8} | {'Tilt Y':>8} | {'Tilt Z':>8}")
    print("-" * 130)

    for i in range(1, n + 1):
        obj = TheNCE.GetObjectAt(i)
        tipo = obj.TypeName
        comentario = obj.Comment
        x = obj.XPosition
        y = obj.YPosition
        z = obj.ZPosition
        tx = obj.TiltAboutX
        ty = obj.TiltAboutY
        tz = obj.TiltAboutZ
        print(f"{i:>3} | {tipo:<20} | {comentario:<30} | {x:>10.3f} | {y:>10.3f} | {z:>10.3f} | {tx:>8.3f} | {ty:>8.3f} | {tz:>8.3f}")

    del zos
    zos = None
