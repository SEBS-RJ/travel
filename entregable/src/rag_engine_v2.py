import os
import glob
import json
from functools import lru_cache
from typing import List, Dict, Any

import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings

class AdvancedRAGEngine:
    """
    Motor RAG con ChromaDB y persistencia en /tmp (para entornos de solo lectura como Streamlit Cloud).
    """

    def __init__(self, knowledge_dir: str, collection_name: str = "tarija_tourism"):
        self.knowledge_dir = knowledge_dir

        # ✅ Usar /tmp para persistencia (única ruta escribible en Streamlit Cloud)
        persist_dir = "/tmp/chroma_db"
        os.makedirs(persist_dir, exist_ok=True)

        self.chroma_client = chromadb.PersistentClient(path=persist_dir)


        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )

    def _chunk_text(self, text: str, filename: str, max_chars: int = 800) -> List[Dict]:
        """Divide el texto en fragmentos de aproximadamente max_chars palabras."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_chars):
            chunk = " ".join(words[i:i+max_chars])
            chunk_id = f"{filename}_{i}"
            chunks.append({
                "id": chunk_id,
                "text": chunk,
                "metadata": {"source": filename, "chunk_index": i}
            })
        return chunks

    def load_documents(self) -> int:
        """
        Carga los documentos solo si la colección está vacía.
        Retorna el número de fragmentos cargados.
        """
        # ✅ Evita recargar si ya hay datos
        if self.collection.count() > 0:
            print(f"Colección '{self.collection.name}' ya tiene {self.collection.count()} documentos. No se recargan.")
            return self.collection.count()

        txt_files = glob.glob(os.path.join(self.knowledge_dir, "*.txt"))
        all_chunks = []
        for filepath in txt_files:
            filename = os.path.basename(filepath)
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            all_chunks.extend(self._chunk_text(text, filename))

        # Insertar en lotes para mejor rendimiento
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i+batch_size]
            self.collection.upsert(
                ids=[chunk["id"] for chunk in batch],
                documents=[chunk["text"] for chunk in batch],
                metadatas=[chunk["metadata"] for chunk in batch]
            )
        print(f"Cargados {len(all_chunks)} fragmentos en ChromaDB.")
        return len(all_chunks)

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Busca los fragmentos más relevantes para la consulta."""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        formatted = []
        for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
            formatted.append({
                "text": doc,
                "source": meta.get("source", "desconocido"),
                "similarity": 1 - dist
            })
        return formatted

    @lru_cache(maxsize=128)
    def search_with_cache(self, query: str, top_k: int = 3) -> str:
        """Devuelve JSON con los resultados cacheados."""
        results = self.search(query, top_k)
        return json.dumps(results, ensure_ascii=False)

    def classify_intent(self, query: str) -> str:
        """Clasifica la intención de la consulta mediante palabras clave."""
        keywords = {
            "saludo": ["hola", "buenos días", "buenas tardes", "qué tal", "saludos", "hey", "buenas"],
            "lugares": ["lugar", "visitar", "turístico", "qué hacer", "sitio", "parque", "museo", "mirador", "plaza", "atractivo", "conocer", "excursión"],
            "gastronomia": ["comer", "restaurante", "comida", "vino", "singani", "chicha", "plato", "bebida", "almuerzo", "cena", "típico", "saice", "charquekan"],
            "eventos": ["evento", "feria", "carnaval", "festival", "concierto", "fiesta", "cultura", "vendimia", "calendario", "cuándo"],
            "ruta": ["llegar", "transporte", "bus", "taxi", "cómo ir", "dirección", "micro", "ruta", "distancia", "llegada"],
            "emergencia": ["robaron", "perdido", "policía", "ayuda", "emergencia", "accidente", "robo", "peligro", "ambulancia", "bomberos"],
            "alojamiento": ["hotel", "hostal", "dónde dormir", "alojamiento", "hospedaje", "residencial", "casa de huéspedes"],
            "clima": ["clima", "tiempo", "temperatura", "lluvia", "sol", "qué ropa llevar", "época", "estación", "frío", "calor"]
        }
        q = query.lower()
        for intent, words in keywords.items():
            if any(w in q for w in words):
                return intent
        return "general"

    def apply_rules(self, query: str, intent: str, hora: int = 12,
                    presupuesto: float = None, tiempo_min: int = None,
                    es_fin_de_semana: bool = None) -> Dict[str, bool]:
        """Aplica reglas simbólicas basadas en contexto y consulta."""
        flags = {}
        q = query.lower()

        # Reglas por palabras clave
        if any(k in q for k in ["poco dinero", "económico", "barato", "presupuesto bajo"]):
            flags["filtrar_gratuitos"] = True
        if any(k in q for k in ["poco tiempo", "2 horas", "rápido", "apuro"]):
            flags["itinerario_corto"] = True
        if "noche" in q or "nocturno" in q:
            flags["seguridad_nocturna"] = True
        if "extranjero" in q or "turista extranjero" in q:
            flags["incluir_contexto_cultural"] = True
        if intent == "emergencia":
            flags["emergencia"] = True
        if "con niños" in q or "familia" in q:
            flags["familiar"] = True

        # Reglas por parámetros
        if presupuesto is not None and presupuesto < 50:
            flags["filtrar_gratuitos"] = True
        if tiempo_min is not None and tiempo_min < 60:
            flags["itinerario_corto"] = True
        if hora is not None and (hora < 6 or hora > 20):
            flags["seguridad_nocturna"] = True
        if es_fin_de_semana:
            flags["es_fin_de_semana"] = True

        return flags

    def generate_response(self, query: str, results: List[Dict], intent: str, flags: Dict) -> str:
        """Genera la respuesta final combinando resultados y reglas."""
        if flags.get("emergencia"):
            return "🚨 EMERGENCIA: Policía 110 | Bomberos 119 | Médico 165. Diríjase a un lugar seguro y pida ayuda."

        if not results:
            return "No encontré información específica. Te recomiendo consultar la Secretaría de Turismo de Tarija."

        top_doc = results[0]["text"][:300]
        fuentes = set(r["source"] for r in results)

        prefijo = ""
        if intent == "saludo":
            prefijo = "¡Hola! Soy el asistente turístico de Tarija 🏔️\n"
        elif intent == "lugares":
            prefijo = "Estos son algunos lugares que podrías visitar:\n"
        elif intent == "gastronomia":
            prefijo = "Te recomiendo probar estas delicias tarijeñas:\n"
        elif intent == "eventos":
            prefijo = "Próximos eventos en Tarija:\n"
        elif intent == "ruta":
            prefijo = "Para moverte por la ciudad:\n"
        elif intent == "alojamiento":
            prefijo = "Opciones de hospedaje en Tarija:\n"

        if flags.get("filtrar_gratuitos"):
            prefijo += "💰 Con presupuesto bajo: "
        if flags.get("itinerario_corto"):
            prefijo += "⏱️ Poco tiempo: recomendaciones cercanas y rápidas.\n"
        if flags.get("familiar"):
            prefijo += "👨‍👩‍👧‍👦 Opciones para toda la familia: "
        if flags.get("es_fin_de_semana"):
            prefijo += "🎉 Durante el fin de semana hay más actividades. "

        return f"{prefijo}{top_doc}\n\n📚 Fuente: {', '.join(fuentes)}"