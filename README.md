# 🏔️ Asistente Turístico Inteligente de Tarija

Sistema híbrido de IA para turismo en Tarija, Bolivia. Combina búsqueda semántica (RAG) con Gemini 2.5 Flash, agente de rutas con mapas interactivos, alertas de seguridad y soporte multilingüe (español, inglés, portugués).

![Demo](https://via.placeholder.com/800x400?text=Captura+de+pantalla) <!-- Añade una captura real -->

## ✨ Características

- **🤖 RAG semántico:** Base de conocimiento local con embeddings (ChromaDB + sentence-transformers).
- **🧠 Gemini 2.5 Flash:** Respuestas inteligentes en múltiples idiomas con fallback a RAG local.
- **🗺️ Rutas y mapas:** Calcula rutas a pie y muestra el recorrido en un mapa interactivo.
- **🔒 Seguridad:** Alertas automáticas sobre zonas de precaución según hora del día.
- **🌍 Multilingüe:** Detecta el idioma de la consulta (español, inglés, portugués) y responde en el mismo.
- **📱 Responsive:** Interfaz adaptable a móviles con sidebar colapsable y botones flexibles.

## 🛠️ Tecnologías

- **Frontend/Backend:** Streamlit
- **LLM:** Google Gemini 2.5 Flash (con fallback local)
- **RAG:** ChromaDB, sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Mapas:** Folium, streamlit-folium
- **Seguridad:** Reglas simbólicas + base de conocimiento local
- **Idioma:** LangDetect

## 📦 Instalación local

### Requisitos

- Python 3.10 o superior
- Git

### Pasos

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/SEBS-RJ/travel.git
   cd travel
   ```

### Crear entorno virtual (opcional pero recomendado):

python -m venv venv

# Windows

venv\Scripts\activate

# Linux/Mac

source venv/bin/activate

### Instalar dependencias:

cd entregable
pip install -r requirements.txt

### (Opcional) Configurar API key de Gemini:

Crea el archivo .streamlit/secrets.toml (en la raíz del proyecto) con:
GEMINI_API_KEY = "tu_clave"

### Ejecutar la aplicación:

streamlit run src/app.py

### Abrir en el navegador: http://localhost:XXXX

### Despliegue en la nube

Puedes desplegar tu propia versión en Streamlit Cloud:
Sube el código a un repositorio de GitHub.
Ve a share.streamlit.io y selecciona "New app".
Indica el repositorio, rama (main) y ruta al archivo: entregable/src/app.py.
En "Settings → Secrets", añade la variable GEMINI_API_KEY con tu clave.
Haz clic en "Deploy". La app estará disponible públicamente en minutos.

## Estructura del proyecto

travel/
├── entregable/
│ ├── data/
│ │ ├── knowledge/ # Base de conocimiento (archivos .txt)
│ │ └── chroma_db/ # Índice vectorial (se genera automáticamente)
│ ├── src/
│ │ ├── app.py # Aplicación principal
│ │ ├── rag_engine_v2.py # Motor RAG con embeddings
│ │ ├── rag_engine_v2_wrapper.py
│ │ ├── routing_agent.py # Lógica de rutas y mapas
│ │ ├── safety_agent.py # Alertas de seguridad
│ │ └── ... (otros módulos)
│ └── requirements.txt
├── .streamlit/
│ └── secrets.toml # (no incluido en el repo) Claves API
├── .gitignore
└── README.md

## Uso

Contexto de viaje: En la barra lateral, ajusta la hora, presupuesto, tiempo disponible y si eres turista extranjero.

Consultas: Escribe en el chat o usa los botones rápidos.

Ejemplo en español: "¿Qué bodegas puedo visitar?"

En inglés: "What are the best wineries in Tarija?"

Rutas: "¿Cómo llegar de la plaza central a la bodega Campos de Solana?"

Mapa de ruta: Se mostrará automáticamente debajo del chat.

Alertas de seguridad: Aparecen en burbujas amarillas si la consulta menciona una zona con precaución.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request.

## Licencia

Este proyecto es de código abierto. Puedes usarlo y modificarlo libremente.

## Autor

SEBS-RJ - GitHub

## 📌 Paso 4: Últimas comprobaciones

- Asegúrate de que el archivo `entregable/requirements.txt` existe y contiene las dependencias. Si no, créalo con el contenido mínimo.
- Verifica que no haya errores de sintaxis o rutas absolutas en el código.
- Prueba localmente una última vez: `streamlit run src/app.py` desde `entregable`.

## 🎉 ¡Listo!

Una vez desplegado, tendrás un enlace público como `https://sebs-rj-travel.streamlit.app` (o similar). Compártelo con quien quieras.
