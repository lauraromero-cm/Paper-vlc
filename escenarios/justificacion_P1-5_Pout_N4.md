# Justificación — Cálculo de Pout con N=4 puntos de referencia (P1-5)

**Texto propuesto para incluir en la sección de metodología / limitaciones de la tesis:**

> La probabilidad de bloqueo (Pout) se calcula sobre N=4 puntos receptores,
> uno por cada asiento de la fila simulada, ubicados en la posición nominal
> de la cabeza del pasajero. Estos puntos son **referenciales**: representan
> la posición de diseño de cada asiento, no una malla espacial exhaustiva de
> posibles posturas u orientaciones del receptor. En consecuencia, Pout solo
> puede tomar los valores {0%, 25%, 50%, 75%, 100%}, correspondientes a la
> fracción de asientos (de los 4 simulados) cuyo SINR cae bajo el umbral de
> servicio.
>
> Esta elección se justifica porque el objetivo de la simulación es evaluar
> la **resiliencia del enlace híbrido LOS/DIFF ante un bloqueo físico
> discreto** (persona o carrito en el pasillo) en una configuración de
> cabina representativa, no estimar una distribución de probabilidad
> espacial continua de la señal. Los N=4 puntos son suficientes para
> demostrar el mecanismo de recuperación del enlace (selection combining
> LOS/DIFF) en cada asiento afectado y no afectado por el obstáculo.
>
> Se reconoce como limitación que este enfoque no captura la variabilidad
> de Pout ante cambios de postura del pasajero, orientación de la cabeza,
> o posiciones intermedias del obstáculo. Una extensión futura del trabajo
> podría abordar esto mediante una malla de posiciones receptoras y/o
> múltiples posiciones del obstáculo, reportando los resultados como una
> función de distribución acumulada (CDF) con percentiles, en vez de un
> valor puntual de Pout.

**Dónde ubicarlo:** en la sección donde definas la métrica de Pout (antes de
presentar los resultados de outage), o en la subsección de limitaciones del
estudio.

**Nota:** este texto resuelve el requisito mínimo que aceptó el revisor. La
distribución de probabilidad del coeficiente (mencionada como posible mejora)
queda como trabajo futuro opcional, no es necesaria para cerrar este punto.
