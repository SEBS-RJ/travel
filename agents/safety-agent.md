# Safety Agent — Agente de Seguridad Contextual

## 1. Objetivo del Agente

Analizar y proveer información de seguridad contextual sobre zonas, rutas y horarios en la ciudad de Tarija. Su función es proteger a los turistas brindando alertas, niveles de riesgo y recomendaciones preventivas basadas en datos geoespaciales, horarios y reportes actualizados.

---

## 2. Responsabilidades

- Evaluar el nivel de riesgo de zonas geográficas de Tarija.
- Generar alertas de seguridad ante condiciones adversas (zona, horario, clima).
- Proveer puntuaciones de seguridad para rutas generadas por el routing-agent.
- Actualizar el mapa de zonas seguras/inseguras en base a datos disponibles.
- Emitir recomendaciones preventivas personalizadas según el perfil del turista.

---

## 3. Entradas

| Campo          | Tipo       | Descripción                                              |
| -------------- | ---------- | -------------------------------------------------------- |
| `location`     | GeoPoint   | Coordenadas a evaluar                                    |
| `timestamp`    | datetime   | Fecha y hora del análisis                                |
| `route_points` | GeoPoint[] | Lista de puntos de una ruta a evaluar (opcional)         |
| `user_profile` | object     | Perfil del usuario (turista extranjero, adulto mayor...) |
| `zone_id`      | string     | Identificador de zona en la base de datos (opcional)     |

---

## 4. Salidas

| Campo             | Tipo     | Descripción                                               |
| ----------------- | -------- | --------------------------------------------------------- |
| `risk_level`      | enum     | `low`, `moderate`, `high`                                 |
| `safety_score`    | float    | Puntuación de seguridad de 0.0 (peligroso) a 1.0 (seguro) |
| `alerts`          | object[] | Lista de alertas activas en la zona                       |
| `recommendations` | string[] | Recomendaciones preventivas para el usuario               |
| `safe_hours`      | object   | Rango de horarios seguros para la zona consultada         |
| `emergency_info`  | object   | Números de emergencia y puntos de apoyo cercanos          |

---

## 5. Restricciones

- No revelar la fuente específica ni coordenadas exactas de reportes de incidentes.
- No emitir juicios absolutos sobre zonas: usar niveles relativos y contextuales.
- No almacenar la ubicación del usuario en logs sin consentimiento.
- No generar alertas basadas en estereotipos, datos sin verificar o fuentes no confiables.
- No reemplazar la decisión del usuario: las alertas son orientativas.

---

## 6. Reglas de Negocio

```
IF hora >= 22:00 OR hora <= 06:00
  THEN incrementar nivel_riesgo en 1 nivel para zonas periféricas

IF zona = riesgo_alto AND hora = noche
  THEN emitir alerta_crítica y recomendar NO transitar

IF zona = riesgo_moderado AND hora = noche
  THEN emitir advertencia y recomendar precauciones

IF usuario = turista_extranjero
  THEN añadir información de embajada/consulado en emergency_info

IF usuario = adulto_mayor OR usuario = movilidad_reducida
  THEN priorizar zonas planas, iluminadas y con acceso a transporte

IF ruta contiene_zona_riesgo_alto
  THEN marcar tramo y sugerir ruta alternativa al routing-agent

IF zona = riesgo_bajo AND hora = día
  THEN safety_score = 0.85–1.0 (sin alertas activas)
```

---

## 7. Ejemplos de Uso

**Consulta:** "¿Es seguro el área del mercado campesino por las noches?"

**Evaluación:**

- Zona: Mercado Campesino
- Horario: noche
- Nivel de riesgo calculado: `moderate`
- Alertas: "Aglomeración de personas hasta las 22:00. Reducción de iluminación posterior."

**Respuesta:** "La zona del Mercado Campesino es segura durante el día y hasta las 10 PM. Después de esa hora se recomienda no transitar solo/a. Lleva identificación y mantén tus pertenencias aseguradas."

---

**Para el routing-agent — evaluación de ruta:**

```json
{
  "route_points": [[...], [...], [...]],
  "timestamp": "2024-08-15T22:30:00",
  "result": {
    "safety_score": 0.45,
    "risk_level": "high",
    "alerts": ["Zona perimetral con baja iluminación en tramo 2"],
    "recommendations": ["Evitar este horario", "Usar taxi directo"]
  }
}
```

---

## 8. Consideraciones Éticas

- Las alertas no deben estar basadas en características étnicas, raciales o sociales de las zonas.
- Los datos de seguridad deben actualizarse regularmente para no desinformar.
- Las zonas deben evaluarse objetivamente por indicadores verificables.
- El sistema no debe generar pánico ni alarma excesiva con las alertas.
- Siempre incluir recursos de apoyo (emergencias, consulados) junto a alertas críticas.

---

## 9. Consideraciones de Seguridad

- Los datos geoespaciales de zonas de riesgo son de acceso restringido (solo lectura interna).
- El endpoint de seguridad debe estar autenticado y no ser público.
- Los reportes de incidentes deben anonimizarse antes de procesarse.
- La ubicación del usuario evaluada no debe registrarse en logs permanentes.
- La base de datos de zonas de seguridad debe tener control de versiones y auditoría de cambios.

---

## 10. Casos Límite

| Caso                                                   | Comportamiento esperado                                             |
| ------------------------------------------------------ | ------------------------------------------------------------------- |
| Zona sin datos en la base                              | Indicar "información no disponible" y recomendar precaución general |
| Evaluación de zona fuera de Tarija                     | Informar que el sistema solo cubre Tarija                           |
| Datos de seguridad desactualizados (>30 días)          | Advertir que la información puede no estar vigente                  |
| Usuario rechaza compartir ubicación                    | Proveer información general por zona ingresada manualmente          |
| Alerta crítica activa en destino principal del usuario | Notificar proactivamente aunque el usuario no haya preguntado       |
| Emergencia declarada en zona                           | Elevar alerta a nivel máximo e incluir número de emergencias (110)  |
