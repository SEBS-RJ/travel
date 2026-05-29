# ============================================================
# src/rag_engine.py
# Sprint 2 — Motor RAG para el asistente turístico de Tarija
#
# Paradigma: RAG (Retrieval-Augmented Generation)
# Por qué RAG y no solo un LLM:
#   - Un LLM puro no conoce datos locales de Tarija (horarios,
#     precios, zonas de riesgo, eventos específicos).
#   - RAG recupera información verificada antes de generar,
#     evitando alucinaciones sobre datos turísticos locales.
#   - La base de conocimiento es actualizable sin reentrenar.
# ============================================================

import os
import re
import math
from pathlib import Path
from dataclasses import dataclass, field
from collections import Counter


# ── Modelos de datos ──────────────────────────────────────────

@dataclass
class Chunk:
    """Fragmento de documento indexado."""
    id: int
    content: str
    source: str
    tokens: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.tokens = tokenize(self.content)


@dataclass
class SearchResult:
    """Resultado de búsqueda con score de relevancia."""
    chunk: Chunk
    score: float


# ── Tokenización y preprocesamiento ──────────────────────────

STOPWORDS_ES = {
    "de", "la", "el", "en", "y", "a", "los", "las", "con", "por",
    "para", "es", "se", "del", "que", "un", "una", "su", "son",
    "al", "lo", "más", "o", "pero", "si", "como", "este", "esta",
    "no", "hay", "tiene", "hay", "también", "entre", "desde",
}

def tokenize(text: str) -> list[str]:
    """Convierte texto en tokens normalizados."""
    text = text.lower()
    text = re.sub(r"[^\w\sáéíóúüñ]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in STOPWORDS_ES and len(t) > 2]


# ── Cargador de documentos ────────────────────────────────────

class DocumentLoader:
    """
    Carga archivos .txt desde un directorio y los divide en chunks.
    Cada sección separada por '===' es un chunk independiente.
    """

    def __init__(self, chunk_size: int = 300, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def load_directory(self, path: str) -> list[Chunk]:
        chunks = []
        chunk_id = 0
        dir_path = Path(path)

        for file_path in sorted(dir_path.glob("*.txt")):
            text = file_path.read_text(encoding="utf-8")
            source = file_path.name
            file_chunks = self._split_by_sections(text, source)

            for content in file_chunks:
                if len(content.strip()) > 50:
                    chunks.append(Chunk(id=chunk_id, content=content.strip(), source=source))
                    chunk_id += 1

            print(f"  [{source}] → {len(file_chunks)} chunks cargados")

        return chunks

    def _split_by_sections(self, text: str, source: str) -> list[str]:
        """Divide el texto en secciones usando '===' como delimitador."""
        sections = re.split(r"===.*?===", text)
        raw_sections = re.findall(r"===.*?===(.*?)(?====|\Z)", text, re.DOTALL)

        # Si hay secciones delimitadas, usarlas
        if raw_sections:
            result = []
            headers = re.findall(r"=== (.*?) ===", text)
            for i, (header, content) in enumerate(zip(headers, raw_sections)):
                result.append(f"{header}\n{content.strip()}")
            return result

        # Si no, dividir por párrafos
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return paragraphs


# ── Motor de búsqueda TF-IDF ─────────────────────────────────

class TFIDFRetriever:
    """
    Recuperación de chunks usando TF-IDF sin dependencias externas.

    TF  = frecuencia del término en el chunk
    IDF = log(N / df) donde N=total chunks, df=chunks con el término
    Score = suma de TF-IDF de los términos de la query en el chunk
    """

    def __init__(self):
        self.chunks: list[Chunk] = []
        self.idf: dict[str, float] = {}
        self.n_docs: int = 0

    def index(self, chunks: list[Chunk]) -> None:
        """Construye el índice TF-IDF sobre todos los chunks."""
        self.chunks = chunks
        self.n_docs = len(chunks)

        # Calcular document frequency (df) por término
        df: Counter = Counter()
        for chunk in chunks:
            unique_tokens = set(chunk.tokens)
            df.update(unique_tokens)

        # Calcular IDF
        self.idf = {
            term: math.log((self.n_docs + 1) / (freq + 1)) + 1
            for term, freq in df.items()
        }

        print(f"\n  Índice construido: {self.n_docs} chunks, {len(self.idf)} términos únicos")

    def search(self, query: str, top_k: int = 3, min_score: float = 0.1) -> list[SearchResult]:
        """Busca los chunks más relevantes para la query."""
        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        results = []
        for chunk in self.chunks:
            score = self._score(query_tokens, chunk)
            if score >= min_score:
                results.append(SearchResult(chunk=chunk, score=score))

        # Ordenar por score descendente
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def _score(self, query_tokens: list[str], chunk: Chunk) -> float:
        """Calcula el score TF-IDF para un chunk dado los tokens de la query."""
        if not chunk.tokens:
            return 0.0

        tf_map = Counter(chunk.tokens)
        n_tokens = len(chunk.tokens)
        score = 0.0

        for token in query_tokens:
            if token in tf_map:
                tf = tf_map[token] / n_tokens
                idf = self.idf.get(token, 0.0)
                score += tf * idf

        return score


# ── Motor de reglas simbólicas ────────────────────────────────

class SymbolicRules:
    """
    Reglas IF-THEN del dominio turístico.
    Complementa el RAG con razonamiento explícito.
    """

    @staticmethod
    def apply(query: str, context: dict) -> dict:
        """
        Evalúa reglas simbólicas sobre la consulta y el contexto.
        Retorna advertencias y ajustes al resultado.
        """
        query_lower = query.lower()
        alerts = []
        flags = []

        hora = context.get("hora", 12)
        presupuesto = context.get("presupuesto_bob")
        tiempo_min = context.get("tiempo_disponible_min")

        # Regla 1: Seguridad nocturna
        if hora >= 22 or hora < 6:
            if any(w in query_lower for w in ["ruta", "caminar", "ir", "llegar", "zona"]):
                alerts.append("⚠️ Horario nocturno: prefiere taxi de placa amarilla y evita zonas periféricas.")
                flags.append("ruta_nocturna")

        # Regla 2: Presupuesto bajo
        if presupuesto is not None and presupuesto < 50:
            flags.append("filtrar_gratuitos")
            alerts.append("💰 Con presupuesto bajo: Plaza Luis de Fuentes, Loma San Juan y Mercado Central son gratuitos.")

        # Regla 3: Tiempo limitado
        if tiempo_min is not None and tiempo_min < 120:
            flags.append("itinerario_corto")
            alerts.append("⏱️ Poco tiempo: recomiendo lugares céntricos a menos de 15 minutos caminando.")

        # Regla 4: Turista extranjero
        if context.get("extranjero", False):
            flags.append("incluir_contexto_cultural")
            alerts.append("🌍 Para turistas extranjeros: el documento de identidad es requerido en alojamientos y bodegas.")

        # Regla 5: Consulta de emergencia
        emergencia_keywords = [
            "perdido", "robo", "robaron", "robó", "accidente",
            "herido", "emergencia", "peligro", "auxilio", "ayuda",
            "asaltaron", "asalto", "perdí", "perdi"
        ]
        if any(k in query_lower for k in emergencia_keywords):
            alerts.insert(0, "🚨 EMERGENCIA: Policía 110 | Bomberos 119 | Médico 165")
            flags.append("emergencia")

        return {"alerts": alerts, "flags": flags}


# ── Generador de respuestas ───────────────────────────────────

class ResponseGenerator:
    """
    Genera respuestas en lenguaje natural combinando:
    1. Contexto recuperado por el RAG (chunks relevantes)
    2. Reglas simbólicas aplicadas
    3. Plantillas de respuesta por intención
    """

    INTENT_PATTERNS = {
        "lugares":     [r"visitar", r"qu[eé] lugar", r"lugares", r"qu[eé] hay", r"conocer", r"ver en tarija", r"turístic", r"sitios", r"atracci"],
        "ruta":        [r"c[oó]mo llego", r"ruta", r"camino", r"llegar", r"direcci"],
        "gastronomia": [r"comer", r"restaur", r"comida", r"plato", r"gastronom", r"típic", r"bebida"],
        "seguridad":   [r"segur", r"riesgo", r"peligro", r"zona", r"noche"],
        "transporte":  [r"taxi", r"micro", r"bus", r"transport", r"terminal"],
        "eventos":     [r"carnaval", r"feria", r"festival", r"evento", r"fiesta", r"celebraci"],
        "saludo":      [r"^hola", r"^buenos", r"^hi", r"^buenas"],
        "emergencia":  [r"robar", r"robaron", r"robó", r"accidente", r"perdido", r"auxilio", r"ayuda"],
    }

    def detect_intent(self, query: str) -> str:
        q = query.lower()
        for intent, patterns in self.INTENT_PATTERNS.items():
            if any(re.search(p, q) for p in patterns):
                return intent
        return "general"

    def generate(
        self,
        query: str,
        results: list[SearchResult],
        rules_output: dict,
    ) -> str:
        """Construye la respuesta final."""
        intent = self.detect_intent(query)
        alerts = rules_output.get("alerts", [])

        # Respuesta de saludo
        if intent == "saludo":
            return (
                "¡Hola! Soy el asistente turístico de Tarija 🏔️\n"
                "Puedo ayudarte con lugares para visitar, gastronomía típica, "
                "transporte, rutas seguras y eventos culturales.\n"
                "¿Qué te gustaría saber sobre Tarija?"
            )

        # Sin resultados relevantes
        if not results:
            base = (
                "No encontré información específica sobre eso en mi base de conocimiento. "
                "Te recomiendo consultar la Secretaría de Turismo de Tarija o preguntar en tu alojamiento."
            )
            if alerts:
                return "\n".join(alerts) + "\n\n" + base
            return base

        # Construir respuesta con el contexto recuperado
        lines = []

        # Alertas primero (si las hay)
        if alerts:
            lines.extend(alerts)
            lines.append("")

        # Respuesta basada en el chunk más relevante
        top = results[0]
        lines.append(self._summarize_chunk(top.chunk.content, intent))

        # Chunks adicionales como sugerencias complementarias
        if len(results) > 1:
            lines.append("\nInformación relacionada:")
            for r in results[1:]:
                title = r.chunk.content.split("\n")[0][:60]
                lines.append(f"  • {title}...")

        # Fuente
        sources = list({r.chunk.source for r in results})
        lines.append(f"\n📚 Fuente: {', '.join(sources)}")

        return "\n".join(lines)

    def _summarize_chunk(self, content: str, intent: str) -> str:
        """Extrae la parte más relevante del chunk según la intención."""
        lines = [l.strip() for l in content.split("\n") if l.strip()]

        # Para lugares y gastronomía, mostrar descripción y datos clave
        if intent in ("lugares", "gastronomia", "eventos"):
            result = []
            for line in lines[:8]:
                result.append(line)
            return "\n".join(result)

        # Para rutas y transporte, priorizar costos y horarios
        if intent in ("ruta", "transporte"):
            result = []
            for line in lines:
                if any(k in line.lower() for k in ["costo", "horario", "precio", "bob", "línea", "ruta", "terminal"]):
                    result.append(line)
            return "\n".join(result[:6]) if result else "\n".join(lines[:6])

        # Caso general: primeras líneas del chunk
        return "\n".join(lines[:6])


# ── Clase principal RAG ───────────────────────────────────────

class TurismoRAG:
    """
    Sistema RAG completo para asistencia turística en Tarija.
    Combina recuperación TF-IDF + reglas simbólicas + generación de respuesta.
    """

    def __init__(self, knowledge_dir: str):
        print("Inicializando sistema RAG para Tarija...\n")
        print("Cargando base de conocimiento:")

        loader = DocumentLoader()
        chunks = loader.load_directory(knowledge_dir)

        self.retriever = TFIDFRetriever()
        self.retriever.index(chunks)

        self.rules = SymbolicRules()
        self.generator = ResponseGenerator()

        print(f"\n✅ Sistema listo. {len(chunks)} fragmentos de conocimiento indexados.")
        print("=" * 60)

    def ask(
        self,
        query: str,
        hora: int = 12,
        presupuesto_bob: float = None,
        tiempo_disponible_min: int = None,
        extranjero: bool = False,
    ) -> dict:
        """
        Procesa una consulta y retorna la respuesta completa.

        Args:
            query: Pregunta del usuario
            hora: Hora del día (0-23) para reglas de seguridad
            presupuesto_bob: Presupuesto en bolivianos
            tiempo_disponible_min: Tiempo disponible en minutos
            extranjero: Si el usuario es turista extranjero

        Returns:
            dict con answer, intent, sources, alerts, confidence
        """
        # 1. Recuperar chunks relevantes
        results = self.retriever.search(query, top_k=3)

        # 2. Aplicar reglas simbólicas
        context = {
            "hora": hora,
            "presupuesto_bob": presupuesto_bob,
            "tiempo_disponible_min": tiempo_disponible_min,
            "extranjero": extranjero,
        }
        rules_output = self.rules.apply(query, context)

        # 3. Generar respuesta
        answer = self.generator.generate(query, results, rules_output)
        intent = self.generator.detect_intent(query)

        # 4. Calcular confianza (score promedio de los resultados)
        confidence = (
            round(sum(r.score for r in results) / len(results), 4)
            if results else 0.0
        )

        return {
            "query": query,
            "answer": answer,
            "intent": intent,
            "sources": list({r.chunk.source for r in results}),
            "confidence": confidence,
            "n_chunks_retrieved": len(results),
            "alerts": rules_output.get("alerts", []),
            "flags": rules_output.get("flags", []),
        }