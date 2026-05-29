# Estructura del Proyecto — Sistema Inteligente de Turismo Tarija

```
/travel
│
├── /frontend                        # React Native (móvil) + React (web)
│   └── /src
│       ├── /components              # Componentes reutilizables de UI
│       ├── /screens                 # Pantallas principales
│       ├── /hooks                   # Custom hooks (useLocation, useChat...)
│       ├── /services                # Llamadas a la API backend
│       ├── /store                   # Estado global (Zustand / Redux)
│       ├── /utils                   # Funciones utilitarias
│       └── /types                   # TypeScript interfaces y tipos
│
├── /backend                         # ASP.NET Core Web API
│   └── /src
│       ├── /Controllers             # Endpoints REST
│       ├── /Services                # Lógica de negocio
│       ├── /Repositories            # Acceso a datos (patrón Repository)
│       ├── /Models                  # Entidades de dominio
│       ├── /DTOs                    # Objetos de transferencia de datos
│       ├── /Middleware              # Auth, logging, rate limiting
│       └── /Config                  # Configuración, variables de entorno
│
├── /ai-service                      # Microservicio Python + FastAPI
│   ├── /agents                      # Lógica de cada agente IA
│   ├── /rag                         # Pipeline RAG + base vectorial
│   ├── /inference                   # Motor de reglas simbólicas
│   ├── /models                      # Modelos de datos internos
│   ├── /prompts                     # Prompts organizados por agente
│   ├── /utils                       # Helpers, sanitización, logging
│   └── /config                      # Configuración del servicio IA
│
├── /agents                          # Documentación de agentes IA (.md)
│   ├── tourism-agent.md
│   ├── routing-agent.md
│   ├── safety-agent.md
│   ├── recommendation-agent.md
│   ├── rag-agent.md
│   └── communication-agent.md
│
├── /database                        # PostgreSQL + PostGIS
│   ├── /migrations                  # Migraciones de esquema
│   ├── /seeds                       # Datos iniciales (lugares, zonas...)
│   └── /schemas                     # Definición de tablas
│
├── /docs                            # Documentación técnica del proyecto
├── /docker                          # Docker Compose y Dockerfiles
└── /scripts                         # Scripts de setup, deploy, seed
```
