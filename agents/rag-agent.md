# RAG Agent — Agente de Recuperación y Generación Aumentada

## 1. Objetivo del Agente

Proveer respuestas contextualizadas y precisas sobre turismo en Tarija mediante la recuperación de información relevante de la base de conocimiento vectorial y su uso para enriquecer la generación de respuestas del LLM. Actúa como la memoria documental del sistema.

---

## 2. Responsabilidades

- Indexar y mantener la base de conocimiento turístico de Tarija en formato vectorial.
- Recuperar fragmentos de conocimiento relevantes dado una consulta del usuario.
- Proveer contexto enriquecido al LLM para generar respuestas precisas y fundamentadas.
- Responder FAQs turísticas sobre Tarija sin necesidad de llamar al LLM completo.
- Detectar cuando la base de conocimiento no tiene información suficiente y notificarlo.
- Mantener trazabilidad de las fuentes utilizadas en cada respuesta.

---

## 3. Entradas

| Campo             | Tipo   | Descripción                                                      |
| ----------------- | ------ | ---------------------------------------------------------------- |
| `query`           | string | Pregunta o consulta del usuario                                  |
| `top_k`           | int    | Número de fragmentos a recuperar (default: 5)                    |
| `filters`         | object | Filtros opcionales: categoría, zona, tipo_lugar, fecha           |
| `min_score`       | float  | Umbral mínimo de similitud para incluir fragmento (default: 0.7) |
| `session_context` | object | Contexto previo de la conversación para mejorar la búsqueda      |

---

## 4. Salidas

| Campo              | Tipo     | Descripción                                            |
| ------------------ | -------- | ------------------------------------------------------ |
| `retrieved_chunks` | object[] | Fragmentos recuperados con score de similitud y fuente |
| `augmented_prompt` | string   | Prompt enriquecido con el contexto recuperado          |
| `sources`          | string[] | Referencias de los documentos fuente utilizados        |
| `confidence`       | float    | Nivel de confianza de la respuesta (0.0 a 1.0)         |
| `fallback_needed`  | bool     | Indica si la base no tiene suficiente información      |

---

## 5. Restricciones

- No generar información que no esté respaldada por la base de conocimiento.
- No utilizar fragmentos con score de similitud menor al umbral configurado.
- No mezclar información de fuentes con fechas muy desactualizadas sin advertirlo.
- No incluir información personal de usuarios en los chunks indexados.
- La base de conocimiento debe actualizarse al menos mensualmente.

---

## 6. Fuentes de Conocimiento Indexadas

### Documentos Turísticos

- Guías turísticas oficiales de Tarija (Municipio, Gobernación).
- Catálogo de lugares turísticos con descripción, horarios, precios.
- Historia y cultura de Tarija.
- Gastronomía típica tarijeña.
- Festividades y eventos (Carnaval, Feria de la Uva, San Roque, etc.).

### Información Operativa

- FAQs frecuentes de turistas.
- Transporte urbano en Tarija (líneas de micro, taxis, terminales).
- Alojamientos disponibles por categoría y precio.
- Restaurantes y gastronomía local.
- Información de emergencias y contactos útiles.

### Formato de Chunks

```
Tipo: documento_turistico
Tamaño chunk: 300–500 tokens
Overlap: 50 tokens
Embedding model: text-embedding-3-small (OpenAI) o similar
Metadata: { fuente, fecha_actualizacion, categoria, zona, idioma }
```

---

## 7. Pipeline RAG

```
Consulta del usuario
       ↓
Preprocesamiento de la query (limpieza, normalización)
       ↓
Generación de embedding de la query
       ↓
Búsqueda por similitud en la base vectorial (PostgreSQL + pgvector)
       ↓
Recuperación de top-K chunks con score > umbral
       ↓
Reranking contextual (opcional)
       ↓
Construcción del prompt aumentado:
  [CONTEXTO RECUPERADO] + [HISTORIAL SESIÓN] + [CONSULTA USUARIO]
       ↓
Generación de respuesta por el LLM
       ↓
Post-procesamiento + cita de fuentes
       ↓
Respuesta al usuario
```

---

## 8. Ejemplos de Uso

**Consulta:** "¿En qué fecha es el Carnaval de Tarija?"

**Recuperación:**

- Chunk recuperado: "El Carnaval de Tarija se celebra 40 días antes de Semana Santa, generalmente en febrero o marzo. Es conocido por su fiesta de los 'ch'utas' y las comparsas típicas de la región."
- Score: 0.91
- Fuente: `guia_turistica_tarija_2023.pdf`

**Respuesta generada:** "El Carnaval de Tarija se celebra 40 días antes de la Semana Santa, usualmente en febrero o marzo. Es uno de los eventos más importantes de la ciudad, con comparsas y la tradicional fiesta de los ch'utas."

---

**Consulta sin información suficiente:** "¿Hay servicio de kayak en Tarija?"

**Recuperación:**

- No se encontraron chunks con score > 0.7
- `fallback_needed = true`

**Respuesta:** "No tengo información específica sobre kayak en Tarija. Te recomiendo consultar en la Secretaría de Turismo Municipal o preguntar en tu alojamiento. ¿Te puedo ayudar con otra actividad?"

---

## 9. Consideraciones Éticas

- Las fuentes deben ser verificadas y actualizadas periódicamente.
- No deben indexarse opiniones no verificadas o contenido de redes sociales sin curación.
- La atribución de fuentes debe ser transparente cuando el usuario la solicite.
- No deben indexarse datos personales de turistas o residentes.
- El contenido indexado debe respetar la diversidad cultural tarijeña sin estereotipos.

---

## 10. Consideraciones de Seguridad

- La base vectorial debe estar en una instancia protegida, no accesible públicamente.
- El endpoint de búsqueda vectorial debe estar autenticado (solo acceso interno entre agentes).
- Los embeddings no deben exponer el contenido original de los documentos a usuarios no autorizados.
- Los documentos fuente originales deben almacenarse cifrados.
- Auditoría de cambios en la base de conocimiento con logs inmutables.
- Rate limiting en el pipeline RAG para evitar abuso: máx. 50 consultas/min.

---

## 11. Casos Límite

| Caso                                            | Comportamiento esperado                                            |
| ----------------------------------------------- | ------------------------------------------------------------------ |
| Base vectorial vacía o no disponible            | Responder con conocimiento general del LLM e informar al usuario   |
| Todos los chunks tienen score bajo              | Activar `fallback_needed` y responder con incertidumbre explícita  |
| Consulta en inglés con base en español          | Traducir la query antes del embedding o usar modelo multilingüe    |
| Chunk recuperado con información desactualizada | Agregar advertencia de posible desactualización en la respuesta    |
| Múltiples fuentes contradictorias               | Presentar ambas versiones e indicar la contradicción               |
| Consulta ambigua (múltiples interpretaciones)   | Recuperar para la interpretación más probable y pedir confirmación |
