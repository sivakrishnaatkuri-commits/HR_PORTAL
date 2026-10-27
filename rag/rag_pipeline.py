"""Minimal persistent RAG pipeline using Sentence Transformers and ChromaDB.

This module indexes approved HR policy documents and retrieves semantically
relevant text chunks. Gemini generation is called by app.py after retrieval.
"""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parents[1]
VECTOR_DIR = BASE_DIR / "data" / "vector_db"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "talentsphere_hr_knowledge"
CHUNK_WORDS = 220
CHUNK_OVERLAP = 40


def _client():
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(VECTOR_DIR))


def _collection():
    return _client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    # First use downloads the model from Hugging Face. Subsequent runs reuse its cache.
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _chunks(text: str) -> list[str]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    step = max(1, CHUNK_WORDS - CHUNK_OVERLAP)
    result = []
    for start in range(0, len(words), step):
        part = " ".join(words[start:start + CHUNK_WORDS]).strip()
        if part:
            result.append(part)
        if start + CHUNK_WORDS >= len(words):
            break
    return result


def _document_id(filename: str, text: str, document_type: str) -> str:
    # Content hash makes re-indexing identical content idempotent while separating types.
    digest = hashlib.sha256((document_type + "\0" + filename + "\0" + text).encode("utf-8")).hexdigest()
    return digest[:32]


def index_document(filename: str, text: str, document_type: str = "hr_policy") -> dict[str, Any]:
    """Chunk, embed and persist a text document. Existing chunks for the same
    filename/type are removed before the latest version is inserted.
    """
    filename = Path(filename).name
    chunks = _chunks(text)
    if not chunks:
        raise ValueError("Document contains no indexable text.")

    collection = _collection()
    # Remove older versions of this filename/type so stale policy text isn't retrieved.
    collection.delete(where={"$and": [{"filename": filename}, {"document_type": document_type}]})

    model = _model()
    vectors = model.encode(chunks, normalize_embeddings=True).tolist()
    doc_id = _document_id(filename, text, document_type)
    ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "doc_id": doc_id,
            "filename": filename,
            "document_type": document_type,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]
    collection.add(ids=ids, documents=chunks, embeddings=vectors, metadatas=metadatas)
    return {"doc_id": doc_id, "filename": filename, "chunks": len(chunks)}


def retrieve_context(query: str, document_type: str = "hr_policy", top_k: int = 4) -> list[dict[str, Any]]:
    """Return the top semantically relevant chunks for a query."""
    if not query.strip():
        return []
    collection = _collection()
    count = collection.count()
    if count == 0:
        return []
    model = _model()
    query_vector = model.encode([query], normalize_embeddings=True).tolist()[0]
    result = collection.query(
        query_embeddings=[query_vector],
        n_results=min(max(1, int(top_k)), count),
        where={"document_type": document_type},
        include=["documents", "metadatas", "distances"],
    )
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    output = []
    for document, metadata, distance in zip(docs, metas, distances):
        metadata = metadata or {}
        output.append({
            "text": document,
            "filename": metadata.get("filename", "Unknown source"),
            "chunk_index": metadata.get("chunk_index", -1),
            "distance": float(distance) if distance is not None else None,
        })
    return output


def list_indexed_documents(document_type: str = "hr_policy") -> list[dict[str, Any]]:
    """Return document names and chunk counts for the selected document type."""
    collection = _collection()
    result = collection.get(where={"document_type": document_type}, include=["metadatas"])
    counts: dict[str, int] = {}
    for metadata in result.get("metadatas") or []:
        if metadata:
            name = metadata.get("filename", "Unknown source")
            counts[name] = counts.get(name, 0) + 1
    return [{"filename": name, "chunks": count} for name, count in sorted(counts.items())]
