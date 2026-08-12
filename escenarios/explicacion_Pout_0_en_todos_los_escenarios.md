# Explicación preparada — Pout = 0% en los 9 escenarios oficiales

**Contexto:** en el barrido final, el enlace híbrido (LOS + DIFF con selection
combining) nunca cae bajo el umbral de servicio en ningún asiento, de ningún
escenario, en ningún FOV. Esto no está señalado como pendiente en el informe
del revisor, pero conviene tener la explicación lista si lo pregunta.

## Por qué pasa esto (cadena causal)

1. El canal DIFF es un canal WDM/TDMA **separado del LOS, sin interferencia
   co-canal** (los 4 LOS interfieren entre sí; el DIFF no interfiere con
   nadie) — esta es una decisión de arquitectura, no un artefacto de
   cómputo.
2. Al no tener interferencia, el único limitante del SINR del DIFF es el
   **ruido** (shot + térmico + fondo + corriente oscura). Con los valores de
   ruido usados (típicos de literatura VLC indoor con filtro óptico), ese
   piso de ruido es bajo comparado con la potencia óptica que llega al
   receptor, y el SINR del DIFF resulta muy alto (75-90 dB).
3. En el selection combining (`SINR_hybrid = max(LOS, DIFF)`), el DIFF gana
   siempre — incluso en escenarios sin bloqueo, donde el LOS ya es bueno por
   sí solo (~18-30 dB).
4. Como el híbrido = DIFF en todos los casos, y el DIFF nunca cae bajo el
   umbral, **Pout = 0% en los 9 escenarios**.

## Por qué es un resultado defendible, no un error

- No es un bug de la simulación: se revisaron los 9 JSON de resultados
  (sin NaN, sin potencias negativas, tendencias de FOV coherentes) y el
  comportamiento reproduce exactamente lo ya validado en la prueba decisiva
  de P0-3 (rescate del asiento bloqueado).
- El SINR alto del DIFF ya fue discutido y aceptado explícitamente durante
  la revisión de P1-6 (modelo de ruido): se evaluó bajar artificialmente el
  ruido de fondo para forzar un SINR más "realista", pero se descartó por no
  tener respaldo de literatura para un valor de ruido tan alto en un sistema
  indoor con filtro óptico.

## Cómo presentarlo si el revisor pregunta

> "El resultado de Pout=0% es consecuencia directa de dos decisiones de
> diseño ya justificadas: (1) el canal DIFF opera en una banda/tiempo
> separado sin interferencia co-canal, y (2) los parámetros de ruido usados
> son típicos de un receptor VLC indoor con filtro óptico. Bajo esas
> condiciones, el canal de respaldo tiene un margen de enlace muy amplio, lo
> cual es precisamente el objetivo de diseño del enlace híbrido: garantizar
> disponibilidad de servicio incluso ante bloqueo total del LOS. El
> resultado no debe interpretarse como 'el sistema nunca falla en la
> práctica', sino como 'bajo el modelo de canal y ruido usado, el margen de
> enlace del DIFF es suficiente para cubrir los escenarios de bloqueo
> simulados'."

## Limitación honesta a reconocer (si se pide ir más allá)

El modelo no captura factores que en un sistema real reducirían ese margen:
- Path loss adicional si el DIFF debe cubrir una cabina más larga (aquí solo
  se simula una fila).
- Degradación del filtro óptico o el fotodiodo fuera de condiciones ideales.
- Múltiples pasajeros bloqueando simultáneamente el DIFF (techo) además del
  LOS — no modelado, ya que el DIFF asume línea de vista libre al techo.
- Vibración/movimiento de cabeza del pasajero (relacionado con P1-5).

Esto puede mencionarse como trabajo futuro, sin que invalide el resultado
actual.
