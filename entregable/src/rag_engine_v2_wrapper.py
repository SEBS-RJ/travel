# src/rag_engine_v2_wrapper.py
import json
from pathlib import Path
from datetime import datetime
from rag_engine_v2 import AdvancedRAGEngine


class TurismoRAG_v2:
    def __init__(self, knowledge_dir):
        self.engine = AdvancedRAGEngine(knowledge_dir)
        self.engine.load_documents()
        # Simular el atributo retriever que espera app.py (para mostrar métricas)
        class DummyRetriever:
            def __init__(self, n_docs):
                self.n_docs = n_docs
                self.idf = {}
        self.retriever = DummyRetriever(len(self.engine.collection.get()['ids']))

    def ask(self, query, hora=12, presupuesto_bob=None,
            tiempo_disponible_min=None, extranjero=False):
        intent = self.engine.classify_intent(query)

        # Aplicar reglas con contexto
        flags = self.engine.apply_rules(
            query, intent,
            hora=hora,
            presupuesto=presupuesto_bob,
            tiempo_min=tiempo_disponible_min,
            es_fin_de_semana=(datetime.now().weekday() >= 5)
        )

        # Sobrescribir flags con parámetros de la interfaz (compatibilidad)
        if presupuesto_bob is not None and presupuesto_bob < 100:
            flags["filtrar_gratuitos"] = True
        if tiempo_disponible_min is not None and tiempo_disponible_min < 60:
            flags["itinerario_corto"] = True
        if extranjero:
            flags["incluir_contexto_cultural"] = True
        if hora < 6 or hora > 20:
            flags["seguridad_nocturna"] = True

        # Búsqueda con caché (resultados en JSON)
        results_json = self.engine.search_with_cache(query, top_k=3)
        results = json.loads(results_json)

        answer = self.engine.generate_response(query, results, intent, flags)

        return {
            "answer": answer,
            "intent": intent,
            "confidence": results[0]["similarity"] if results else 0.0,
            "n_chunks_retrieved": len(results),
            "alerts": [w for w in flags if flags[w]],
            "sources": list(set(r["source"] for r in results)) if results else []
        }