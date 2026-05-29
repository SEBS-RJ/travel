# ============================================================
# src/test_inferencia.py
# Sprint 2 — Pruebas de inferencia y métricas del sistema RAG
# Este archivo es el entregable parcial del Sprint 2
# ============================================================

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rag_engine import TurismoRAG

KNOWLEDGE_DIR = Path(__file__).parent.parent / "data" / "knowledge"


def separador(titulo: str = ""):
    print("\n" + "=" * 60)
    if titulo:
        print(f"  {titulo}")
        print("=" * 60)


def ejecutar_prueba(rag: TurismoRAG, numero: int, descripcion: str, **kwargs) -> dict:
    """Ejecuta una prueba y muestra el resultado formateado."""
    print(f"\n--- Prueba {numero}: {descripcion} ---")
    print(f"Query: \"{kwargs.get('query')}\"")

    t0 = time.time()
    result = rag.ask(**kwargs)
    elapsed = round((time.time() - t0) * 1000, 1)

    print(f"\nRespuesta:\n{result['answer']}")
    print(f"\nMétricas:")
    print(f"  Intent detectado : {result['intent']}")
    print(f"  Chunks usados    : {result['n_chunks_retrieved']}")
    print(f"  Confianza        : {result['confidence']:.4f}")
    print(f"  Tiempo respuesta : {elapsed} ms")
    print(f"  Fuentes          : {', '.join(result['sources']) if result['sources'] else 'ninguna'}")
    if result['flags']:
        print(f"  Flags activos    : {', '.join(result['flags'])}")

    return {**result, "elapsed_ms": elapsed}


def main():
    separador("SPRINT 2 — PRUEBAS DE INFERENCIA")
    print("Sistema RAG: Asistente Turístico Inteligente de Tarija")
    print("Paradigma: RAG + Reglas Simbólicas (IA Híbrida)")

    # Inicializar sistema
    rag = TurismoRAG(str(KNOWLEDGE_DIR))

    resultados = []

    # ── BLOQUE 1: Consultas turísticas básicas ────────────────
    separador("BLOQUE 1 — Consultas turísticas básicas")

    resultados.append(ejecutar_prueba(
        rag, 1, "Saludo inicial",
        query="Hola, buenos días"
    ))

    resultados.append(ejecutar_prueba(
        rag, 2, "Lugares para visitar",
        query="¿Qué lugares puedo visitar en Tarija?",
        hora=10
    ))

    resultados.append(ejecutar_prueba(
        rag, 3, "Gastronomía típica",
        query="¿Cuál es la comida típica de Tarija?",
        hora=13
    ))

    resultados.append(ejecutar_prueba(
        rag, 4, "Evento cultural",
        query="¿Cuándo es el Carnaval de Tarija?",
        hora=11
    ))

    # ── BLOQUE 2: Reglas simbólicas activas ───────────────────
    separador("BLOQUE 2 — Reglas simbólicas")

    resultados.append(ejecutar_prueba(
        rag, 5, "Regla: Presupuesto bajo",
        query="¿Qué puedo visitar con muy poco dinero?",
        hora=14,
        presupuesto_bob=30.0
    ))

    resultados.append(ejecutar_prueba(
        rag, 6, "Regla: Tiempo limitado",
        query="¿Qué puedo hacer en Tarija?",
        hora=15,
        tiempo_disponible_min=90
    ))

    resultados.append(ejecutar_prueba(
        rag, 7, "Regla: Seguridad nocturna",
        query="¿Cómo llego al centro de Tarija?",
        hora=23
    ))

    resultados.append(ejecutar_prueba(
        rag, 8, "Regla: Turista extranjero",
        query="¿Qué debo saber para visitar Tarija?",
        hora=10,
        extranjero=True
    ))

    resultados.append(ejecutar_prueba(
        rag, 9, "Regla: Emergencia",
        query="Me robaron la billetera, estoy perdido",
        hora=21
    ))

    # ── BLOQUE 3: Casos combinados ────────────────────────────
    separador("BLOQUE 3 — Casos combinados")

    resultados.append(ejecutar_prueba(
        rag, 10, "Pareja + bajo presupuesto + tarde",
        query="Estoy con mi pareja y tenemos 2 horas libres, ¿qué hacemos?",
        hora=16,
        presupuesto_bob=40.0,
        tiempo_disponible_min=120
    ))

    resultados.append(ejecutar_prueba(
        rag, 11, "Enoturismo",
        query="¿Dónde puedo hacer una degustación de vinos en Tarija?",
        hora=10
    ))

    resultados.append(ejecutar_prueba(
        rag, 12, "Transporte a bodega",
        query="¿Cómo llego a las bodegas de vino desde el centro?",
        hora=9
    ))

    # ── MÉTRICAS GLOBALES ─────────────────────────────────────
    separador("MÉTRICAS GLOBALES DEL SISTEMA")

    con_resultado = [r for r in resultados if r["n_chunks_retrieved"] > 0]
    sin_resultado = [r for r in resultados if r["n_chunks_retrieved"] == 0]
    confianza_prom = (
        sum(r["confidence"] for r in con_resultado) / len(con_resultado)
        if con_resultado else 0
    )
    tiempo_prom = sum(r["elapsed_ms"] for r in resultados) / len(resultados)

    total = len(resultados)
    cobertura = len(con_resultado) / total * 100

    print(f"\n  Total de pruebas          : {total}")
    print(f"  Con resultado (cobertura) : {len(con_resultado)} / {total} ({cobertura:.1f}%)")
    print(f"  Sin resultado             : {len(sin_resultado)}")
    print(f"  Confianza promedio        : {confianza_prom:.4f}")
    print(f"  Tiempo promedio respuesta : {tiempo_prom:.1f} ms")
    print(f"  Chunks en índice          : {rag.retriever.n_docs}")
    print(f"  Términos únicos indexados : {len(rag.retriever.idf)}")

    # Evaluación según rúbrica
    print("\n  Evaluación por rúbrica:")
    nivel = "Nivel Avanzado ✅" if cobertura >= 80 and confianza_prom >= 0.05 else \
            "Nivel Medio ⚠️"    if cobertura >= 60 else \
            "Nivel Inicial ❌"
    print(f"  Criterio Implementación: {nivel}")

    separador("FIN DE PRUEBAS SPRINT 2")
    print("Entregable parcial generado correctamente.")
    print("Siguiente paso: Sprint 3 → Interfaz Streamlit")


if __name__ == "__main__":
    main()