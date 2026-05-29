# ============================================================
# ai-service/rag/vector_store.py
# Gestión de la base vectorial con PostgreSQL + pgvector
# Genera embeddings y realiza búsqueda semántica
# ============================================================

import logging
from dataclasses import dataclass

import asyncpg
from openai import AsyncOpenAI

from config.settings import get_settings
from rag.loader import DocumentChunk

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RetrievedChunk:
    """Fragmento recuperado con su score de similitud."""
    content: str
    source: str
    category: str
    score: float
    metadata: dict


class VectorStore:
    """
    Gestiona embeddings y búsqueda vectorial sobre PostgreSQL + pgvector.
    Usa cosine similarity para recuperar fragmentos relevantes.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.EMBEDDING_MODEL
        self.dimension = settings.PGVECTOR_DIMENSION

    # ── Indexación ────────────────────────────────────────────

    async def index_chunks(self, chunks: list[DocumentChunk]) -> int:
        """
        Genera embeddings para una lista de chunks y los almacena.
        Retorna el número de chunks indexados exitosamente.
        """
        if not chunks:
            return 0

        indexed = 0
        # Procesar en lotes para no saturar la API de embeddings
        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            try:
                texts = [c.content for c in batch]
                embeddings = await self._generate_embeddings(texts)

                async with self.pool.acquire() as conn:
                    for chunk, embedding in zip(batch, embeddings):
                        await conn.execute(
                            """
                            INSERT INTO knowledge_chunks
                                (content, source, category, language, embedding, metadata)
                            VALUES ($1, $2, $3, $4, $5::vector, $6)
                            """,
                            chunk.content,
                            chunk.source,
                            chunk.category,
                            chunk.language,
                            str(embedding),           # pgvector acepta string '[0.1, 0.2, ...]'
                            chunk.metadata or {}
                        )
                        indexed += 1

                logger.info(f"Indexados {indexed}/{len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Error indexando lote {i}: {e}")

        return indexed

    # ── Recuperación ──────────────────────────────────────────

    async def search(
        self,
        query: str,
        top_k: int = None,
        min_score: float = None,
        category_filter: str | None = None,
        language: str = "es",
    ) -> list[RetrievedChunk]:
        """
        Recupera los chunks más similares a la query.
        Usa cosine similarity (1 - distancia coseno).
        """
        top_k = top_k or settings.RAG_TOP_K
        min_score = min_score or settings.RAG_MIN_SCORE

        try:
            query_embedding = await self._generate_embeddings([query])
            query_vec = str(query_embedding[0])

            async with self.pool.acquire() as conn:
                # Cosine similarity = 1 - cosine_distance (<=>)
                rows = await conn.fetch(
                    """
                    SELECT
                        content,
                        source,
                        category,
                        metadata,
                        1 - (embedding <=> $1::vector) AS score
                    FROM knowledge_chunks
                    WHERE
                        language = $2
                        AND ($3::text IS NULL OR category = $3)
                        AND 1 - (embedding <=> $1::vector) >= $4
                    ORDER BY score DESC
                    LIMIT $5
                    """,
                    query_vec,
                    language,
                    category_filter,
                    min_score,
                    top_k,
                )

            results = [
                RetrievedChunk(
                    content=row["content"],
                    source=row["source"],
                    category=row["category"],
                    score=float(row["score"]),
                    metadata=dict(row["metadata"]) if row["metadata"] else {},
                )
                for row in rows
            ]

            logger.info(f"RAG: {len(results)} chunks recuperados para query: '{query[:60]}...'")
            return results

        except Exception as e:
            logger.error(f"Error en búsqueda vectorial: {e}")
            return []

    # ── Construcción de Prompt Aumentado ─────────────────────

    def build_augmented_prompt(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        session_history: list[dict] | None = None,
    ) -> tuple[str, float]:
        """
        Construye el prompt enriquecido con el contexto recuperado.
        Retorna (prompt_aumentado, confianza_promedio).
        """
        if not chunks:
            # Sin contexto recuperado: el LLM responde con conocimiento general
            return query, 0.0

        # Construir bloque de contexto
        context_lines = []
        for i, chunk in enumerate(chunks, 1):
            context_lines.append(
                f"[Fuente {i} — {chunk.source}]\n{chunk.content}"
            )
        context_block = "\n\n".join(context_lines)

        # Historial de sesión resumido (últimos 4 turnos)
        history_block = ""
        if session_history:
            recent = session_history[-4:]
            history_lines = [
                f"{'Usuario' if m['role'] == 'user' else 'Asistente'}: {m['content']}"
                for m in recent
            ]
            history_block = "\nHistorial reciente:\n" + "\n".join(history_lines) + "\n"

        augmented = (
            f"Contexto turístico de Tarija:\n{context_block}\n"
            f"{history_block}\n"
            f"Consulta del usuario: {query}"
        )

        avg_confidence = sum(c.score for c in chunks) / len(chunks)
        return augmented, avg_confidence

    # ── Helpers ───────────────────────────────────────────────

    async def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings para una lista de textos usando la API de OpenAI."""
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def get_stats(self) -> dict:
        """Retorna estadísticas de la base vectorial."""
        async with self.pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM knowledge_chunks")
            by_category = await conn.fetch(
                "SELECT category, COUNT(*) as count FROM knowledge_chunks GROUP BY category"
            )
        return {
            "total_chunks": total,
            "by_category": {row["category"]: row["count"] for row in by_category},
        }