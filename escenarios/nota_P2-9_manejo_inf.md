# Nota — Manejo de potencia cero / SINR = -inf (P2-9)

**Contexto:** `noise_model.db(x)` devuelve `-inf` cuando `x <= 0` (SINR=0,
es decir, cero potencia recibida en ese canal). Esto ocurre legítimamente
en los canales **crudos** LOS o DIFF por separado, típicamente en FOV muy
angostos (10°-20°) donde ningún rayo cae dentro del ángulo de aceptancia,
o en el LOS de un asiento totalmente bloqueado (ej. Rx6 en
`bloqueo_persona_*`, LOS=-inf hasta FOV≈70°).

**Regla adoptada:** ningún promedio o estadística agregada debe calcularse
sobre las columnas crudas `SINR_LOS_dB` / `SINR_DIFF_dB` (pueden contener
`-inf`, lo que corrompe silenciosamente cualquier suma/promedio que las
incluya). Todas las agregaciones (promedio, mínimo, comparaciones entre
escenarios) se calculan exclusivamente sobre `SINR_hybrid_dB`
(`= max(LOS, DIFF)`), que está protegido por construcción: siempre hay al
menos un canal con señal real, por lo que `SINR_hybrid_dB` nunca es `-inf`
(verificado sobre los 9×9×4=324 valores de los escenarios oficiales).

**Dónde se aplica esta regla:**
- `codigo_comun/generar_tablas_graficos_oficial.py`: el único promedio
  calculado (`sinr_hybrid_prom_fov90`) usa `SINR_hybrid_dB`.
- Cualquier script futuro que agregue metricas nuevas debe seguir la misma
  regla: usar `SINR_hybrid_dB` para promedios, y tratar `SINR_LOS_dB`/
  `SINR_DIFF_dB` como valores de diagnóstico por canal (no agregables
  directamente).

**Interpretación de `-inf` en las tablas CSV crudas:** significa "cero
potencia detectada en ese canal, en ese FOV" (bloqueo total o FOV
insuficiente para capturar el rayo), no un error de cálculo.
