# Recommendation Agent — Agente de Recomendaciones Inteligentes

## 1. Objetivo del Agente

Generar recomendaciones turísticas personalizadas y contextualizadas para turistas en Tarija, considerando sus preferencias, presupuesto, tiempo disponible, historial de interacciones y contexto de seguridad. Combina recuperación de información (RAG), reglas de inferencia y ML ligero para ofrecer sugerencias relevantes y explicables.

---

## 2. Responsabilidades

- Recomendar lugares turísticos, restaurantes, actividades y servicios en Tarija.
- Personalizar recomendaciones según perfil y preferencias del usuario.
- Filtrar y rankear opciones por relevancia, seguridad, precio y disponibilidad.
- Generar itinerarios básicos con los lugares recomendados.
- Explicar el motivo de cada recomendación.
- Aprender de las interacciones del usuario para mejorar futuros rankings (ML ligero).

---

## 3. Entradas

| Campo            | Tipo     | Descripción                                              |
| ---------------- | -------- | -------------------------------------------------------- |
| `user_location`  | GeoPoint | Ubicación actual del usuario                             |
| `preferences`    | object   | Preferencias declaradas: tipo_lugar, actividad, dieta... |
| `budget`         | float    | Presupuesto disponible en BOB                            |
| `available_time` | int      | Tiempo disponible en minutos                             |
| `timestamp`      | datetime | Fecha y hora de la consulta                              |
| `user_history`   | object[] | Historial de lugares visitados o valorados               |
| `travel_party`   | enum     | `solo`, `pareja`, `familia`, `grupo`                     |
| `query`          | string   | Consulta en lenguaje natural (opcional)                  |

---

## 4. Salidas

| Campo             | Tipo     | Descripción                                               |
| ----------------- | -------- | --------------------------------------------------------- |
| `recommendations` | object[] | Lista de lugares o actividades recomendadas (máx. 5)      |
| `explanation`     | string[] | Motivo de cada recomendación                              |
| `itinerary`       | object   | Itinerario básico sugerido (si aplica)                    |
| `alternatives`    | object[] | Opciones alternativas de menor prioridad                  |
| `filters_applied` | object   | Filtros utilizados (presupuesto, tiempo, seguridad, etc.) |

---

## 5. Restricciones

- No recomendar lugares cerrados o fuera de horario sin advertirlo.
- No priorizar negocios patrocinados sobre opciones más relevantes para el usuario.
- No generar itinerarios que superen el tiempo disponible declarado.
- No recomendar zonas de riesgo alto sin la validación del safety-agent.
- Máximo 5 recomendaciones principales por respuesta (evitar saturación).

---

## 6. Reglas de Negocio

```
IF presupuesto < 50 BOB
  THEN filtrar lugares con entrada_gratuita = true O costo_estimado < 30 BOB

IF tiempo_disponible < 4 horas
  THEN priorizar lugares a menos de 3 km del usuario

IF tiempo_disponible < 2 horas
  THEN recomendar máximo 2 lugares muy cercanos

IF travel_party = familia AND hay_niños = true
  THEN excluir lugares adultos y priorizar parques, museos interactivos

IF travel_party = pareja
  THEN incluir opciones románticas: viñedos, miradores, restaurantes con ambiente

IF usuario_prefiere = gastronomia
  THEN priorizar restaurantes típicos tarijeños: empanadas, chicha, vino

IF usuario = turista_extranjero
  THEN añadir contexto cultural e histórico en las explicaciones

IF historial_usuario contiene_lugar
  THEN reducir peso de ese lugar en futuras recomendaciones (no repetir)

IF horario = noche
  THEN filtrar solo lugares con actividad nocturna verificada

IF clima = lluvia (futuro)
  THEN priorizar lugares techados o con actividad interior
```

---

## 7. Ejemplos de Uso

**Consulta:** "Estoy con mi pareja, tenemos 3 horas y poco presupuesto. ¿Qué hacemos en Tarija?"

**Proceso:**

- `travel_party`: pareja
- `available_time`: 180 min
- `budget`: bajo
- Filtros: lugares románticos + gratuitos/económicos + cercanos

**Recomendaciones:**

1. **Plaza Luis de Fuentes** — Paseo gratuito, arquitectura colonial. "Punto de encuentro de la ciudad, perfecto para pasear."
2. **Mirador La Loma de San Juan** — Vista panorámica gratuita. "Ideal al atardecer para parejas."
3. **Mercado Central** — Gastronomía típica desde 10 BOB. "Prueba las empanadas tarijeñas."

**Itinerario sugerido:**

- 14:00 Plaza Luis de Fuentes (45 min)
- 15:00 Caminata al Mirador (30 min caminando)
- 16:00 Mirador + fotos (30 min)
- 16:30 Mercado Central (45 min)

---

## 8. Consideraciones Éticas

- Las recomendaciones deben ser diversas e incluir pequeños negocios y emprendimientos locales tarijeños, no solo establecimientos grandes.
- No deben favorecerse negocios con acuerdos comerciales sobre opciones más adecuadas para el usuario.
- Las recomendaciones para turistas extranjeros deben respetar las diferencias culturales.
- Los criterios de ranking deben ser transparentes y explicables al usuario cuando lo solicite.
- Incluir opciones accesibles para personas con movilidad reducida.

---

## 9. Consideraciones de Seguridad

- El historial del usuario debe cifrarse en reposo.
- Las preferencias y datos de perfil son de acceso exclusivo del usuario autenticado.
- El motor de ML no debe exponer datos de otros usuarios en las recomendaciones.
- Los datos de lugares turísticos deben provenir de fuentes verificadas (base de datos administrada).
- No exponer el identificador interno de lugares en respuestas públicas sin hash.

---

## 10. Casos Límite

| Caso                                                 | Comportamiento esperado                                             |
| ---------------------------------------------------- | ------------------------------------------------------------------- |
| No hay lugares disponibles con los filtros aplicados | Relajar filtros gradualmente e indicar qué se cambió                |
| Usuario no indica preferencias                       | Recomendar los 5 lugares mejor valorados en general                 |
| Todos los lugares cercanos están cerrados            | Indicar horarios de apertura y sugerir planificar para otro momento |
| Base de datos de lugares vacía o no disponible       | Informar al usuario y usar RAG como fallback                        |
| Usuario rechaza todas las recomendaciones            | Preguntar qué tipo de experiencia busca y regenerar                 |
| Lugar recomendado cierra permanentemente             | Sistema de moderación para actualizar/desactivar el lugar           |
