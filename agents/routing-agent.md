# Routing Agent — Agente de Rutas Inteligentes

## 1. Objetivo del Agente

Generar rutas óptimas, seguras y personalizadas para turistas en la ciudad de Tarija, considerando la ubicación del usuario, el destino, el modo de transporte, el horario, el nivel de riesgo de las zonas y las preferencias de movilidad del usuario.

---

## 2. Responsabilidades

- Calcular rutas entre origen y destino integrando Google Maps API y OpenStreetMap.
- Filtrar rutas según nivel de seguridad contextual (consultando safety-agent).
- Adaptar rutas al modo de transporte: caminata, taxi, transporte público, vehículo propio.
- Estimar tiempo de desplazamiento y distancia.
- Presentar hasta 3 alternativas de ruta cuando estén disponibles.
- Integrar puntos de interés turístico dentro de rutas cuando sea pertinente.

---

## 3. Entradas

| Campo              | Tipo     | Descripción                                          |
| ------------------ | -------- | ---------------------------------------------------- |
| `origin`           | GeoPoint | Ubicación de origen del usuario                      |
| `destination`      | string   | Nombre o coordenadas del destino                     |
| `transport_mode`   | enum     | `walking`, `taxi`, `public_transport`, `car`         |
| `timestamp`        | datetime | Fecha y hora del viaje (afecta seguridad y horarios) |
| `user_preferences` | object   | Preferencias de ruta (caminata, accesibilidad, etc.) |
| `safety_context`   | object   | Datos de seguridad por zona (del safety-agent)       |
| `budget`           | float    | Presupuesto disponible en BOB (Bolivianos)           |

---

## 4. Salidas

| Campo               | Tipo     | Descripción                                         |
| ------------------- | -------- | --------------------------------------------------- |
| `routes`            | object[] | Lista de rutas alternativas (máximo 3)              |
| `recommended_route` | object   | Ruta principal recomendada                          |
| `estimated_time`    | int      | Tiempo estimado en minutos                          |
| `distance_km`       | float    | Distancia en kilómetros                             |
| `safety_score`      | float    | Puntuación de seguridad de la ruta (0.0 a 1.0)      |
| `transport_cost`    | float    | Costo estimado en BOB (si aplica)                   |
| `waypoints`         | object[] | Puntos de interés turístico en el camino (opcional) |
| `warnings`          | string[] | Advertencias sobre tramos de la ruta                |

---

## 5. Restricciones

- No recomendar rutas que atraviesen zonas de riesgo alto durante la noche.
- No sugerir modos de transporte no disponibles en Tarija en tiempo real.
- No generar rutas sin verificar que el destino existe en la base de datos o en las APIs externas.
- Las rutas peatonales no deben exceder 5 km sin advertencia explícita al usuario.
- No exponer datos de seguridad a nivel granular que puedan comprometer la privacidad de reportes.

---

## 6. Reglas de Negocio

```
IF horario = noche AND zona_ruta = riesgo_alto
  THEN excluir esa ruta y avisar al usuario

IF transport_mode = walking AND distancia > 5km
  THEN advertir sobre la distancia y sugerir transporte público

IF presupuesto = bajo
  THEN priorizar rutas con transporte público o caminata

IF usuario_prefiere_accesibilidad = true
  THEN filtrar rutas sin escaleras, terreno irregular o pendientes altas

IF destino_no_encontrado
  THEN sugerir lugares similares cercanos

IF existen_multiples_rutas
  THEN ordenar por: 1) seguridad, 2) tiempo, 3) costo

IF waypoints_turisticos_disponibles AND desvio < 10min
  THEN incluir puntos de interés en la ruta sugerida
```

---

## 7. Ejemplos de Uso

**Consulta:** "¿Cómo llego caminando desde la Plaza Central hasta la Bodega Kohlberg?"

**Flujo:**

1. Origen: Plaza Luis de Fuentes (centro de Tarija)
2. Destino: Bodega Kohlberg (San Lorenzo)
3. Modo: walking
4. Verificación de seguridad: zona segura en horario diurno
5. Distancia estimada: 18 km → advertencia automática
6. Respuesta: "La distancia caminando es de 18 km (~4 horas). Te recomiendo usar taxi o transporte público. El costo aproximado en micro es de 3 BOB."

---

**Consulta:** "Quiero llegar al Mercado Central en taxi, son las 11 PM."

**Flujo:**

1. Modo: taxi
2. Horario: noche (23:00)
3. Zona evaluada: moderada (consulta a safety-agent)
4. Ruta recomendada: evita calles perimetrales, prioriza Av. Las Américas
5. Respuesta: "Ruta nocturna disponible. Tiempo estimado: 12 min. Costo aprox: 15–20 BOB. Se recomienda solicitar taxi por aplicación y compartir la ruta con alguien de confianza."

---

## 8. Consideraciones Éticas

- No debe presentarse una sola ruta como "la correcta" — siempre mostrar alternativas cuando existan.
- Las advertencias de seguridad deben ser informativas, no alarmistas.
- Accesibilidad debe ser un criterio de primer nivel, no opcional.
- No deben compartirse detalles de rutas con terceros sin consentimiento.

---

## 9. Consideraciones de Seguridad

- Las coordenadas del usuario no deben registrarse en logs persistentes.
- El origen y destino deben validarse y sanitizarse antes de enviar a APIs externas.
- Las claves de Google Maps API deben manejarse exclusivamente desde variables de entorno en el backend.
- No exponer el endpoint de rutas directamente desde el frontend sin autenticación.
- Los datos de seguridad de zonas son de solo lectura para este agente.

---

## 10. Casos Límite

| Caso                                         | Comportamiento esperado                                         |
| -------------------------------------------- | --------------------------------------------------------------- |
| Destino fuera de Tarija                      | Informar que el sistema cubre solo la ciudad de Tarija          |
| API de Google Maps no disponible             | Usar OpenStreetMap como fallback y notificar al usuario         |
| Sin conexión a internet                      | Usar rutas cacheadas previamente descargadas                    |
| Usuario sin ubicación activa                 | Solicitar ubicación manual o usar Plaza Central como referencia |
| Ruta solo disponible por zona de alto riesgo | Informar y sugerir horario alternativo (diurno)                 |
| Destino cerrado en el horario solicitado     | Advertir y sugerir horarios de apertura o destinos alternativos |
