from pathlib import Path
from rag_engine_v2 import AdvancedRAGEngine

class TurismoRAG_v2:
    """
    Wrapper para que app.py pueda usar AdvancedRAGEngine de forma compatible.
    Expone un atributo `retriever` con `n_docs` (número de fragmentos indexados).
    """

    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = knowledge_dir
        self.engine = AdvancedRAGEngine(knowledge_dir)
        # Cargar documentos (solo si no existen)
        n_docs = self.engine.load_documents()
        # Crear un objeto simulador de retriever para mantener compatibilidad con app.py
        class DummyRetriever:
            def __init__(self, n):
                self.n_docs = n
        self.retriever = DummyRetriever(n_docs)

    def ask(self, query: str, hora: int = 12, presupuesto_bob: float = None,
            tiempo_disponible_min: int = None, extranjero: bool = False) -> dict:
        """
        Interfaz unificada para responder consultas.
        """
        # 1. Recuperar fragmentos
        results = self.engine.search(query, top_k=3)
        # 2. Clasificar intención
        intent = self.engine.classify_intent(query)
        # 3. Aplicar reglas simbólicas
        flags = self.engine.apply_rules(
            query, intent, hora, presupuesto_bob, tiempo_disponible_min
        )
        # 4. Generar respuesta
        answer = self.engine.generate_response(query, results, intent, flags)

        return {
            "answer": answer,
            "intent": intent,
            "confidence": 0.8 if results else 0.3,
            "sources": list({r["source"] for r in results}),
            "n_chunks": len(results),
            "alerts": self._get_alerts_from_flags(flags),
        }

    def _get_alerts_from_flags(self, flags: dict) -> list:
        """Convierte flags en mensajes de alerta legibles."""
        alerts = []
        if flags.get("seguridad_nocturna"):
            alerts.append("⚠️ Horario nocturno: prefiere taxi de placa amarilla y evita zonas periféricas.")
        if flags.get("filtrar_gratuitos"):
            alerts.append("💰 Con presupuesto bajo: hay opciones gratuitas como plazas y miradores.")
        if flags.get("itinerario_corto"):
            alerts.append("⏱️ Poco tiempo: recomendamos lugares céntricos y cercanos.")
        if flags.get("incluir_contexto_cultural"):
            alerts.append("🌍 Para turistas extranjeros: recuerda llevar tu documento de identidad.")
        return alerts