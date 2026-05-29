-- ============================================================
-- ESQUEMA DE BASE DE DATOS
-- Sistema Inteligente de Turismo Tarija
-- PostgreSQL 15 + PostGIS
-- ============================================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector para embeddings RAG

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE user_role AS ENUM ('tourist', 'admin', 'business_owner');
CREATE TYPE transport_mode AS ENUM ('walking', 'taxi', 'public_transport', 'car');
CREATE TYPE risk_level AS ENUM ('low', 'moderate', 'high');
CREATE TYPE place_category AS ENUM (
  'tourist_spot', 'restaurant', 'hotel', 'museum',
  'market', 'winery', 'park', 'transport_hub', 'other'
);
CREATE TYPE itinerary_status AS ENUM ('draft', 'active', 'completed');
CREATE TYPE conversation_role AS ENUM ('user', 'assistant');

-- ============================================================
-- TABLA: users
-- ============================================================

CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email           VARCHAR(255) UNIQUE NOT NULL,
  password_hash   TEXT NOT NULL,
  full_name       VARCHAR(150),
  role            user_role NOT NULL DEFAULT 'tourist',
  language        VARCHAR(5) DEFAULT 'es',        -- 'es' | 'en'
  is_foreign      BOOLEAN DEFAULT FALSE,
  is_senior       BOOLEAN DEFAULT FALSE,
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: user_preferences
-- Preferencias turísticas del usuario autenticado
-- ============================================================

CREATE TABLE user_preferences (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id           UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  preferred_transport  transport_mode DEFAULT 'walking',
  max_budget        NUMERIC(10,2),                -- en BOB
  prefers_walking   BOOLEAN DEFAULT FALSE,
  accessibility_needed BOOLEAN DEFAULT FALSE,
  dietary_restrictions TEXT[],                    -- ['vegetarian', 'vegan'...]
  interests         TEXT[],                       -- ['gastronomia', 'historia'...]
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);

-- ============================================================
-- TABLA: tourist_places
-- Lugares turísticos, restaurantes, hoteles, etc.
-- ============================================================

CREATE TABLE tourist_places (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name            VARCHAR(200) NOT NULL,
  slug            VARCHAR(200) UNIQUE NOT NULL,
  description     TEXT,
  category        place_category NOT NULL,
  address         VARCHAR(300),
  location        GEOGRAPHY(POINT, 4326) NOT NULL,  -- PostGIS geolocalización
  zone_id         UUID REFERENCES safety_zones(id),
  phone           VARCHAR(20),
  website         VARCHAR(300),
  opening_hours   JSONB,   -- {"mon": "09:00-18:00", "sat": "09:00-13:00", ...}
  price_range     VARCHAR(10),   -- 'free' | 'low' | 'mid' | 'high'
  avg_price_bob   NUMERIC(8,2),
  rating          NUMERIC(3,2) DEFAULT 0.0 CHECK (rating >= 0 AND rating <= 5),
  rating_count    INTEGER DEFAULT 0,
  images          TEXT[],
  tags            TEXT[],
  is_accessible   BOOLEAN DEFAULT FALSE,
  is_active       BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índice espacial para búsquedas por proximidad
CREATE INDEX idx_tourist_places_location ON tourist_places USING GIST(location);
CREATE INDEX idx_tourist_places_category ON tourist_places(category);

-- ============================================================
-- TABLA: safety_zones
-- Zonas geográficas con nivel de riesgo
-- Nota: referenciada por tourist_places, definida aquí primero
-- ============================================================

CREATE TABLE safety_zones (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name            VARCHAR(150) NOT NULL,
  description     TEXT,
  boundary        GEOGRAPHY(POLYGON, 4326) NOT NULL,  -- Polígono de la zona
  risk_level      risk_level NOT NULL DEFAULT 'low',
  risk_score      NUMERIC(3,2) DEFAULT 0.0 CHECK (risk_score >= 0 AND risk_score <= 1),
  safe_hours_from TIME DEFAULT '06:00',
  safe_hours_to   TIME DEFAULT '22:00',
  notes           TEXT,
  last_updated    TIMESTAMPTZ DEFAULT NOW(),
  updated_by      UUID REFERENCES users(id)
);

-- Índice espacial para zonas
CREATE INDEX idx_safety_zones_boundary ON safety_zones USING GIST(boundary);

-- ============================================================
-- TABLA: routes
-- Rutas generadas por el sistema
-- ============================================================

CREATE TABLE routes (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
  origin          GEOGRAPHY(POINT, 4326) NOT NULL,
  destination     GEOGRAPHY(POINT, 4326) NOT NULL,
  destination_name VARCHAR(200),
  transport_mode  transport_mode NOT NULL,
  path            GEOGRAPHY(LINESTRING, 4326),   -- Trayecto completo
  distance_km     NUMERIC(8,3),
  duration_min    INTEGER,
  safety_score    NUMERIC(3,2),
  cost_bob        NUMERIC(8,2),
  waypoints       JSONB,    -- Puntos de interés en el camino
  warnings        TEXT[],
  generated_at    TIMESTAMPTZ DEFAULT NOW(),
  expires_at      TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

CREATE INDEX idx_routes_user_id ON routes(user_id);

-- ============================================================
-- TABLA: itineraries
-- Itinerarios personalizados
-- ============================================================

CREATE TABLE itineraries (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
  title           VARCHAR(200),
  total_duration_min INTEGER,
  total_budget_bob   NUMERIC(10,2),
  status          itinerary_status DEFAULT 'draft',
  notes           TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: itinerary_items
-- Lugares que componen un itinerario
-- ============================================================

CREATE TABLE itinerary_items (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  itinerary_id    UUID NOT NULL REFERENCES itineraries(id) ON DELETE CASCADE,
  place_id        UUID NOT NULL REFERENCES tourist_places(id),
  visit_order     INTEGER NOT NULL,
  arrival_time    TIME,
  duration_min    INTEGER,
  notes           TEXT
);

-- ============================================================
-- TABLA: recommendations
-- Registro de recomendaciones generadas por la IA
-- ============================================================

CREATE TABLE recommendations (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
  session_id      VARCHAR(100),
  place_id        UUID REFERENCES tourist_places(id),
  score           NUMERIC(5,4),           -- Score de relevancia
  reason          TEXT,                   -- Explicación de la recomendación
  filters_used    JSONB,                  -- Filtros aplicados
  was_accepted    BOOLEAN,                -- El usuario la aceptó o rechazó
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: conversations
-- Historial de conversaciones del chatbot
-- ============================================================

CREATE TABLE conversations (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
  session_id      VARCHAR(100) NOT NULL,
  channel         VARCHAR(30) DEFAULT 'mobile_app',  -- mobile_app | web | chatbot
  started_at      TIMESTAMPTZ DEFAULT NOW(),
  ended_at        TIMESTAMPTZ,
  message_count   INTEGER DEFAULT 0,
  language        VARCHAR(5) DEFAULT 'es'
);

-- ============================================================
-- TABLA: conversation_messages
-- Mensajes individuales de cada conversación
-- ============================================================

CREATE TABLE conversation_messages (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role            conversation_role NOT NULL,
  content         TEXT NOT NULL,
  intent_detected VARCHAR(80),
  agents_used     TEXT[],
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conv_messages_conv_id ON conversation_messages(conversation_id);

-- ============================================================
-- TABLA: knowledge_chunks
-- Base vectorial RAG para recuperación de información turística
-- ============================================================

CREATE TABLE knowledge_chunks (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  content         TEXT NOT NULL,
  source          VARCHAR(300),           -- Nombre del documento fuente
  category        VARCHAR(100),           -- 'gastronomia' | 'historia' | 'transporte'...
  language        VARCHAR(5) DEFAULT 'es',
  embedding       vector(1536),           -- pgvector: dimensión según modelo usado
  metadata        JSONB,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índice vectorial para búsqueda semántica
CREATE INDEX idx_knowledge_chunks_embedding
  ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- ============================================================
-- TABLA: safety_alerts
-- Alertas de seguridad activas
-- ============================================================

CREATE TABLE safety_alerts (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  zone_id         UUID REFERENCES safety_zones(id),
  title           VARCHAR(200) NOT NULL,
  description     TEXT,
  severity        risk_level NOT NULL,
  is_active       BOOLEAN DEFAULT TRUE,
  valid_from      TIMESTAMPTZ DEFAULT NOW(),
  valid_until     TIMESTAMPTZ,
  created_by      UUID REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLA: place_reviews
-- Valoraciones de lugares por usuarios
-- ============================================================

CREATE TABLE place_reviews (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  place_id        UUID NOT NULL REFERENCES tourist_places(id) ON DELETE CASCADE,
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  rating          INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
  comment         TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(place_id, user_id)
);

-- ============================================================
-- FUNCIÓN: Actualizar rating promedio de un lugar
-- ============================================================

CREATE OR REPLACE FUNCTION update_place_rating()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE tourist_places
  SET
    rating = (SELECT AVG(rating) FROM place_reviews WHERE place_id = NEW.place_id),
    rating_count = (SELECT COUNT(*) FROM place_reviews WHERE place_id = NEW.place_id),
    updated_at = NOW()
  WHERE id = NEW.place_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_place_rating
AFTER INSERT OR UPDATE ON place_reviews
FOR EACH ROW EXECUTE FUNCTION update_place_rating();

-- ============================================================
-- FUNCIÓN: Evaluar seguridad de punto geográfico
-- Retorna risk_level dado coordenadas y hora
-- ============================================================

CREATE OR REPLACE FUNCTION get_location_risk(
  p_lat FLOAT,
  p_lng FLOAT,
  p_hour INTEGER DEFAULT EXTRACT(HOUR FROM NOW())::INTEGER
)
RETURNS TABLE(zone_name TEXT, risk risk_level, score NUMERIC) AS $$
BEGIN
  RETURN QUERY
  SELECT
    sz.name::TEXT,
    CASE
      WHEN p_hour < sz.safe_hours_from::INTEGER OR p_hour >= sz.safe_hours_to::INTEGER
      THEN CASE sz.risk_level
             WHEN 'low' THEN 'moderate'::risk_level
             WHEN 'moderate' THEN 'high'::risk_level
             ELSE 'high'::risk_level
           END
      ELSE sz.risk_level
    END AS risk,
    sz.risk_score
  FROM safety_zones sz
  WHERE ST_Contains(
    sz.boundary::geometry,
    ST_SetSRID(ST_MakePoint(p_lng, p_lat), 4326)
  )
  ORDER BY sz.risk_score DESC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;