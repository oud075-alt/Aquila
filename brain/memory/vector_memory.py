"""Vector memory — semantic storage of past diagnoses and anomaly events.

Uses chromadb when available, with a deterministic NumPy-only fallback so
the system can still run in restricted environments. Embeddings are
provided by sentence-transformers when available, otherwise via a stable
hashing trick so semantic search still works (though with lower quality).
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from brain.logging_utils import get_logger
from config import get_settings


try:
    import chromadb  # type: ignore
    _HAS_CHROMA = True
except Exception:
    _HAS_CHROMA = False

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    _HAS_ST = True
except Exception:
    _HAS_ST = False


_EMBED_DIM = 384


def _hash_embed(text: str, dim: int = _EMBED_DIM) -> List[float]:
    """Deterministic, model-free fallback embedding."""
    rng = np.random.default_rng(int(hashlib.sha256(text.encode()).hexdigest()[:8], 16))
    raw = rng.standard_normal(dim)
    # L2 normalise so cosine similarity behaves
    norm = float(np.linalg.norm(raw)) or 1.0
    return list(raw / norm)


class _NumpyVectorStore:
    """File-backed brute-force vector store used when chromadb is missing."""

    def __init__(self, persist_dir: Path):
        self.dir = persist_dir / "numpy_vector"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.dir / "store.jsonl"

    def add(self, ids: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]], documents: List[str]) -> None:
        with self.data_file.open("a", encoding="utf-8") as f:
            for i, e, m, d in zip(ids, embeddings, metadatas, documents):
                f.write(json.dumps({"id": i, "embedding": e, "metadata": m, "document": d}) + "\n")

    def query(self, embedding: List[float], k: int) -> List[Dict[str, Any]]:
        if not self.data_file.exists():
            return []
        emb_q = np.asarray(embedding, dtype=np.float64)
        nq = float(np.linalg.norm(emb_q)) or 1.0
        results: List[tuple] = []
        with self.data_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                emb = np.asarray(obj["embedding"], dtype=np.float64)
                ne = float(np.linalg.norm(emb)) or 1.0
                sim = float(np.dot(emb, emb_q) / (nq * ne))
                results.append((sim, obj))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] | {"similarity": r[0]} for r in results[:k]]


class VectorMemory:
    """High-level vector memory interface."""

    def __init__(self, collection_name: str = "mspis_anomalies"):
        self.log = get_logger("mspis.memory.vector")
        self.settings = get_settings()
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._np_store: Optional[_NumpyVectorStore] = None
        self._embedder = None
        self._init_backend()

    # ------------------------------------------------------------------
    # Backend selection
    # ------------------------------------------------------------------
    def _init_backend(self) -> None:
        persist_dir = Path(self.settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        if _HAS_CHROMA:
            try:
                self._client = chromadb.PersistentClient(path=str(persist_dir))
                self._collection = self._client.get_or_create_collection(self.collection_name)
                self.log.info("Vector memory using chromadb at %s", persist_dir)
            except Exception as e:
                self.log.warning("chromadb init failed (%s); using numpy fallback", e)
                self._np_store = _NumpyVectorStore(persist_dir)
        else:
            self.log.info("chromadb missing; using deterministic numpy vector store")
            self._np_store = _NumpyVectorStore(persist_dir)

        if _HAS_ST:
            try:
                self._embedder = SentenceTransformer(self.settings.embedding_model)
                self.log.info("Embedding model loaded: %s", self.settings.embedding_model)
            except Exception as e:
                self.log.warning("Sentence transformer load failed (%s); using hash embed", e)
                self._embedder = None

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    def embed(self, text: str) -> List[float]:
        if self._embedder is not None:
            try:
                arr = self._embedder.encode(text, normalize_embeddings=True)
                return [float(v) for v in arr]
            except Exception:
                pass
        return _hash_embed(text)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def store(self, entry_id: str, text: str, metadata: Dict[str, Any]) -> None:
        emb = self.embed(text)
        metadata = {**metadata, "stored_at": time.time()}
        try:
            if self._collection is not None:
                self._collection.add(
                    ids=[entry_id],
                    documents=[text],
                    embeddings=[emb],
                    metadatas=[metadata],
                )
                return
            if self._np_store is not None:
                self._np_store.add([entry_id], [emb], [metadata], [text])
        except Exception as e:
            self.log.warning("vector store failed: %s", e)

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        emb = self.embed(query)
        try:
            if self._collection is not None:
                res = self._collection.query(query_embeddings=[emb], n_results=k)
                out = []
                if res and res.get("ids") and res["ids"][0]:
                    for i, doc, meta, dist in zip(
                        res["ids"][0],
                        res.get("documents", [[]])[0],
                        res.get("metadatas", [[]])[0],
                        res.get("distances", [[]])[0],
                    ):
                        out.append({"id": i, "document": doc, "metadata": meta, "distance": dist})
                return out
            if self._np_store is not None:
                return self._np_store.query(emb, k=k)
        except Exception as e:
            self.log.warning("vector search failed: %s", e)
        return []
