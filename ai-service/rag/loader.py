# ============================================================
# ai-service/rag/loader.py
# Carga y procesamiento de documentos para la base vectorial
# Convierte documentos turísticos en chunks indexables
# ============================================================

import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Iterator

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Fragmento de documento listo para indexar."""
    content: str
    source: str
    category: str
    language: str = "es"
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DocumentLoader:
    """
    Carga documentos turísticos desde distintas fuentes
    y los divide en chunks optimizados para RAG.
    """

    SUPPORTED_EXTENSIONS = {".txt", ".md"}

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def load_directory(self, path: str, category: str = "general") -> list[DocumentChunk]:
        """Carga todos los documentos soportados de un directorio."""
        chunks: list[DocumentChunk] = []
        dir_path = Path(path)

        if not dir_path.exists():
            logger.warning(f"Directorio no encontrado: {path}")
            return chunks

        for file_path in dir_path.rglob("*"):
            if file_path.suffix in self.SUPPORTED_EXTENSIONS:
                file_chunks = self._load_file(file_path, category)
                chunks.extend(file_chunks)
                logger.info(f"Cargado: {file_path.name} → {len(file_chunks)} chunks")

        return chunks

    def load_from_dict(self, entries: list[dict]) -> list[DocumentChunk]:
        """
        Carga contenido directamente desde lista de dicts.
        Útil para cargar lugares turísticos desde la base de datos.

        Formato esperado:
        [{"content": "...", "source": "...", "category": "...", "language": "es"}]
        """
        chunks = []
        for entry in entries:
            text_chunks = list(self._split_text(entry["content"]))
            for i, chunk in enumerate(text_chunks):
                chunks.append(DocumentChunk(
                    content=chunk,
                    source=entry.get("source", "database"),
                    category=entry.get("category", "general"),
                    language=entry.get("language", "es"),
                    metadata={**entry.get("metadata", {}), "chunk_index": i}
                ))
        return chunks

    def _load_file(self, file_path: Path, category: str) -> list[DocumentChunk]:
        try:
            text = file_path.read_text(encoding="utf-8")
            source = file_path.name
            chunks = []
            for i, chunk in enumerate(self._split_text(text)):
                chunks.append(DocumentChunk(
                    content=chunk,
                    source=source,
                    category=category,
                    metadata={"chunk_index": i, "file_path": str(file_path)}
                ))
            return chunks
        except Exception as e:
            logger.error(f"Error cargando {file_path}: {e}")
            return []

    def _split_text(self, text: str) -> Iterator[str]:
        """
        Divide el texto en chunks con overlap.
        Respeta saltos de párrafo cuando es posible.
        """
        text = text.strip()
        if not text:
            return

        # Intentar dividir por párrafos primero
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        current_chunk = ""

        for paragraph in paragraphs:
            # Si el párrafo solo ya excede el tamaño, dividirlo por palabras
            if len(paragraph) > self.chunk_size:
                if current_chunk:
                    yield current_chunk.strip()
                    current_chunk = ""
                yield from self._split_by_words(paragraph)
                continue

            # Si agregar el párrafo excede el tamaño, emitir el chunk actual
            if len(current_chunk) + len(paragraph) + 2 > self.chunk_size:
                if current_chunk:
                    yield current_chunk.strip()
                    # Overlap: conservar últimas palabras del chunk anterior
                    words = current_chunk.split()
                    overlap_words = words[-self.chunk_overlap // 6:] if len(words) > 6 else []
                    current_chunk = " ".join(overlap_words) + " " + paragraph
                else:
                    current_chunk = paragraph
            else:
                current_chunk = (current_chunk + "\n\n" + paragraph).strip()

        if current_chunk:
            yield current_chunk.strip()

    def _split_by_words(self, text: str) -> Iterator[str]:
        words = text.split()
        i = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size // 6]
            yield " ".join(chunk_words)
            i += max(1, (self.chunk_size // 6) - (self.chunk_overlap // 6))