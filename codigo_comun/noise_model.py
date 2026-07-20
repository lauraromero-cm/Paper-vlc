"""
Modelo de ruido y SINR para el enlace Li-Fi (fotodiodo PIN + TIA), basado en el
modelo estandar de VLC de Komine & Nakagawa, "Fundamental Analysis for Visible-Light
Communication System using LED Lights" (IEEE Trans. Consumer Electronics, 2004),
ampliamente reutilizado en la literatura de Li-Fi/VLC para el calculo de
ruido shot + termico de un receptor PIN con amplificador de transimpedancia.

Todas las constantes marcadas como "supuesto" son valores tipicos de la
literatura VLC (no estan en la Tabla 1 del documento) y deben ajustarse/justificarse
en la tesis si se dispone de datos reales del receptor.
"""
import math

# --- Constantes fisicas ---
Q_ELECTRON = 1.602176634e-19   # C
K_BOLTZMANN = 1.380649e-23     # J/K

# --- Parametros del sistema (Tabla 1 del documento) ---
RESPONSIVITY = 0.45            # A/W
DETECTOR_AREA = 1.0e-4         # m^2 (1 cm^2)
R_MIN_BPS = 5.0e6              # bps (Rmin = 5 Mbps)
BER_MAX = 1.0e-6               # BER maximo (OOK)

# --- Supuestos tipicos VLC / contexto aeronautico (AJUSTABLES) ---
TEMPERATURE_K = 300.0          # K, temperatura de cabina tipica (~27 C)
BANDWIDTH_HZ = 10.0e6          # Hz, ancho de banda electrico tipico de un receptor
                                # Li-Fi/VLC para tasas de Mbps (supuesto, ajustable)

# Parametros del amplificador de transimpedancia (TIA), valores clasicos de
# Komine & Nakagawa (2004), muy citados en la literatura VLC:
OPEN_LOOP_GAIN = 10.0           # G, ganancia de lazo abierto del amplificador
FIXED_CAPACITANCE_PER_AREA = 112e-12   # eta, F/m^2 (capacitancia fija del fotodiodo por unidad de area)
FET_CHANNEL_NOISE_FACTOR = 1.5  # Gamma
FET_TRANSCONDUCTANCE = 0.030    # gm, S (30 mS)
NOISE_BW_FACTOR_I2 = 0.562      # I2, integral de Personick (pulso raised-cosine)
NOISE_BW_FACTOR_I3 = 0.0868     # I3, integral de Personick (pulso raised-cosine)

# Ruido de fondo (luz ambiental): con el filtro optico de banda estrecha
# especificado en la Tabla 1, se asume que el ruido shot inducido por luz
# ambiental es despreciable frente al de la propia senal (supuesto razonable
# dado el filtrado espectral explicito del sistema).
NEGLECT_BACKGROUND_SHOT_NOISE = True

# Ganancia del concentrador optico (Tabla 1: "Implementacion FOV: Concentrador
# optico"). Un concentrador real (tipo CPC) no solo limita el angulo de
# aceptancia, tambien concentra/amplifica la luz que entra dentro de ese
# angulo. Formula clasica (Kahn & Barry, Komine & Nakagawa):
#   g(psi) = n^2 / sin^2(FOV)   para psi <= FOV,  0 en otro caso
# n = indice de refraccion del concentrador; 1.5 es un valor tipico de
# literatura VLC para un CPC de plastico/acrilico (supuesto, ajustable).
CONCENTRATOR_REFRACTIVE_INDEX = 1.5


def concentrator_gain(fov_deg, n=CONCENTRATOR_REFRACTIVE_INDEX):
    """g(FOV) = n^2 / sin^2(FOV). FOV=90 deg da g=n^2 (sin concentracion angular,
    solo la ganancia base del medio); FOV chico da ganancias grandes."""
    fov_rad = math.radians(fov_deg)
    return (n ** 2) / (math.sin(fov_rad) ** 2)


def shot_noise_variance(Pr_total_W, B=BANDWIDTH_HZ, R=RESPONSIVITY):
    """sigma^2_shot = 2*q*R*Pr_total*B  (ruido shot inducido por la potencia optica total incidente)."""
    return 2.0 * Q_ELECTRON * R * Pr_total_W * B


def thermal_noise_variance(B=BANDWIDTH_HZ, A=DETECTOR_AREA, T=TEMPERATURE_K):
    """sigma^2_thermal segun el modelo de Komine & Nakagawa (2004):
    termino de resistencia de realimentacion + termino de canal FET."""
    eta = FIXED_CAPACITANCE_PER_AREA
    term_R = (8 * math.pi * K_BOLTZMANN * T / OPEN_LOOP_GAIN) * eta * A * NOISE_BW_FACTOR_I2 * B**2
    term_FET = (16 * math.pi**2 * K_BOLTZMANN * T * FET_CHANNEL_NOISE_FACTOR / FET_TRANSCONDUCTANCE) \
        * (eta**2) * (A**2) * NOISE_BW_FACTOR_I3 * B**3
    return term_R + term_FET


def total_noise_variance(Pr_total_W, B=BANDWIDTH_HZ, A=DETECTOR_AREA, T=TEMPERATURE_K, R=RESPONSIVITY):
    return shot_noise_variance(Pr_total_W, B, R) + thermal_noise_variance(B, A, T)


def compute_sinr(Pr_signal_W, Pr_interference_W, B=BANDWIDTH_HZ, A=DETECTOR_AREA,
                  T=TEMPERATURE_K, R=RESPONSIVITY):
    """SINR = (I_signal)^2 / [sigma^2 + (I_interference)^2], con I = R*Pr."""
    I_signal = R * Pr_signal_W
    I_interference = R * Pr_interference_W
    Pr_total = Pr_signal_W + Pr_interference_W
    sigma2 = total_noise_variance(Pr_total, B, A, T, R)
    sinr = (I_signal ** 2) / (sigma2 + I_interference ** 2)
    return sinr, sigma2, I_signal, I_interference


def sinr_threshold_from_shannon(R_required_bps, B=BANDWIDTH_HZ):
    """gamma_th = 2^(R/B) - 1, a partir de la capacidad de Shannon-Hartley."""
    return 2.0 ** (R_required_bps / B) - 1.0


def q_function(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


def q_function_inverse(p, tol=1e-12, max_iter=200):
    """Inversa de Q(x)=p via biseccion (evita depender de scipy)."""
    lo, hi = 0.0, 40.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        if q_function(mid) > p:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def sinr_threshold_from_ber(ber_max=BER_MAX):
    """Para OOK con deteccion de umbral: BER = Q(sqrt(SINR))  =>  SINR_th = [Q^-1(BER)]^2."""
    x = q_function_inverse(ber_max)
    return x ** 2


def db(x):
    return 10.0 * math.log10(x) if x > 0 else float('-inf')


if __name__ == '__main__':
    gamma_th1 = sinr_threshold_from_shannon(R_MIN_BPS, BANDWIDTH_HZ)
    gamma_th2 = sinr_threshold_from_ber(BER_MAX)
    print("=== Umbrales SINR ===")
    print(f"B (ancho de banda, supuesto) = {BANDWIDTH_HZ/1e6:.1f} MHz")
    print(f"gamma_th,1 (Servicio Minimo, Shannon con Rmin={R_MIN_BPS/1e6:.1f} Mbps) = "
          f"{gamma_th1:.4f} ({db(gamma_th1):.2f} dB)")
    print(f"gamma_th,2 (Servicio Objetivo, BER<={BER_MAX:.0e} para OOK) = "
          f"{gamma_th2:.4f} ({db(gamma_th2):.2f} dB)")
