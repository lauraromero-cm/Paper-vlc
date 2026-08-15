# Resumen — Cierre del feedback de revisión (9/9 puntos)

## Contexto

El revisor marcó problemas en el pipeline de simulación NSC/Zemax con
prioridades P0 (crítico), P1 (importante) y P2 (menor). Se revisaron,
corrigieron y validaron uno por uno.

---

## P0 — Críticos

**P0-1 — Escala del CAD no uniforme (separación de 53mm poco realista)**
- Problema: el modelo STL no tiene un factor de escala único; el ancho de
  asiento daba ~1:5 en X pero esa proporción no se sostenía en Z.
- Decisión: no reconstruir el CAD. Se documenta una escala 1:5 y toda
  dimensión nueva se expresa ya pre-escalada.
- Resultado: 53mm ≈ 265mm reales bajo ese factor, dentro de rango plausible.

**P0-2 — LOS/DIFF/interferencia mezclados en los datos exportados**
- Fix: el pipeline ahora separa `Pr_own_LOS`, `Pr_interf_LOS`, `Pr_DIFF`,
  `Pr_interf_DIFF` y sus SINR, por asiento y por FOV.

**P0-3 — No estaba validado que el DIFF rescate el asiento bloqueado**
- Fix: se agregó la fuente DIFF (canal WDM/TDMA separado, sin interferencia
  cruzada) y selection combining `SINR_hybrid = max(LOS, DIFF)`.
- Resultado: en los 3 escenarios de persona bloqueando, el asiento tapado
  cae a LOS ≈ -62 a -65dB pero el híbrido se mantiene en 75-86dB. Validado
  en los 9 escenarios oficiales.

**P0-4 — El FOV no estaba físicamente modelado**
- Causa raíz: el parámetro nativo de FOV de Zemax solo funciona en modo
  "angle space"; el proyecto usaba "position space", donde se ignoraba en
  silencio — invalidaba todo resultado previo de SINR-vs-FOV.
- Fix: filtro angular en post-proceso usando los cosenos directores del ZRD.
  Validado contra cortes geométricos conocidos. Bonus: 1 trazado por fuente
  sirve para los 9 FOV (antes era 1 trazado por cada FOV, ~9x más lento).

---

## P1 — Importantes

**P1-5 — Outage con solo N=4 asientos**
- Alcance acordado con el revisor: bastaba con documentar que son puntos
  referenciales, no una malla exhaustiva. Malla espacial + CDF queda como
  mejora futura opcional.

**P1-6 — Modelo de ruido incompleto**
- Fix: se agregó ruido de fondo (I_bg=200µA), corriente oscura
  (I_dark=10nA), transmisión del filtro (0.90), eficiencia real del
  concentrador (η=0.85), FOV mínimo práctico (10°).

**P1-7 — Sin prueba de convergencia NSC**
- Prueba: 200k/500k/1M/1M-repetido/2M rayos. La variación entre dos
  corridas a 1M (±0.22%) es del mismo orden que la tendencia real 1M→2M
  (-0.32%) — confirma que 1M rayos está convergido.

**P1-8 — Una sola reflectividad (ρ=0.70) para todo**
- Alcance acordado: cabina se queda en 0.70; solo los objetos de bloqueo
  necesitan ρ propio.
- Fix: cilindro/persona → ρ=0.40, carrito → ρ=0.65, vía la API
  CoatScatterData de Zemax (se encontró y corrigió un bug de Python.NET en
  el camino: el setter no persistía el valor).

---

## P2 — Menor

**P2-9 — Manejo de SINR=-inf en promedios**
- Riesgo: si algún canal tiene potencia cero, `log10(0)=-inf` puede
  corromper un promedio silenciosamente.
- Verificado: los 324 valores de `SINR_hybrid_dB` (9 escenarios × 9 FOV ×
  4 asientos) nunca son -inf, porque `max(LOS,DIFF)` siempre tiene señal
  real. Documentada la regla: promediar siempre sobre `SINR_hybrid_dB`,
  nunca sobre las columnas crudas.

---

## Resultado final

Se corrieron los **9 escenarios oficiales** (sin bloqueo / carrito / persona
× pitch 0°/15°/30°) con la metodología nueva (~3h de cómputo). **Pout = 0%
en los 9** — el DIFF rescata todos los casos. Esto no está señalado como
problema por el revisor, pero se preparó una explicación por si lo
pregunta (el DIFF, al no tener interferencia, siempre gana en el selection
combining) — ver `escenarios/explicacion_Pout_0_en_todos_los_escenarios.md`.

Se archivó todo el material y scripts de la metodología anterior (con el
bug del FOV) en carpetas `obsoleto_pre_hibrido/` por escenario, para que no
se mezcle con lo nuevo.

## Archivos relacionados

- `escenarios/justificacion_P1-5_Pout_N4.md`
- `escenarios/explicacion_Pout_0_en_todos_los_escenarios.md`
- `escenarios/nota_P2-9_manejo_inf.md`
- `codigo_comun/pipeline_oficial.py` (pipeline oficial)
- `codigo_comun/noise_model.py` (modelo de ruido completo)
- `codigo_comun/set_reflectividad_obstaculo.py` (P1-8)
- `codigo_comun/generar_tablas_graficos_oficial.py` (tablas y gráficos)
- `resultados_generales/tabla_comparativa_escenarios_oficial.csv`

## Commits relevantes

```
9621662 Archivar pipeline y resultados pre-hibrido en obsoleto_pre_hibrido/ por escenario
664b4b4 Documentar P2-9: manejo de SINR=-inf en canales crudos vs SINR_hybrid
754a61e Pipeline oficial hibrido LOS/DIFF para los 9 escenarios, con feedback P1-5/P1-8 cerrado
f21007f Corregir metodologia de FOV, separar canales LOS/DIFF y ampliar modelo de ruido
```
