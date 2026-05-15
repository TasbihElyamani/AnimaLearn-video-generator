"""AnimaLearn — Qdrant Ingestion (sentence-transformers embeddings)"""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from src.settings import (QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION,
                           EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSION,
                           DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP, MOCK_MODE)

_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedder

def get_qdrant_client():
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantClient(url=QDRANT_URL)

def ensure_collection(client):
    names = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in names:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE))

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        c = " ".join(words[start:start + chunk_size]).strip()
        if c:
            chunks.append(c)
        start += chunk_size - overlap
    return chunks

def embed_texts(texts):
    if MOCK_MODE:
        import numpy as np
        return [np.random.randn(EMBEDDING_DIMENSION).tolist() for _ in texts]
    model = get_embedder()
    return model.encode(texts, show_progress_bar=False).tolist()

def text_to_id(text):
    return int(hashlib.md5(text.encode()).hexdigest()[:15], 16)

def ingest_text(client, text, source_name):
    chunks = chunk_text(text)
    if not chunks:
        return 0
    embeddings = embed_texts(chunks)
    points = [
        PointStruct(
            id=text_to_id(f"{source_name}_{i}"),
            vector=emb,
            payload={"text": ch, "source_file": source_name,
                     "source_id": f"REF-{source_name}", "chunk_index": i})
        for i, (ch, emb) in enumerate(zip(chunks, embeddings))
    ]
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return len(points)

def ingest_corpus(data_dir=None):
    data_dir = data_dir or DATA_DIR
    client = get_qdrant_client()
    ensure_collection(client)
    stats = {"files": 0, "vectors": 0}
    for fp in sorted(data_dir.glob("*.txt")):
        text = fp.read_text(encoding="utf-8")
        n = ingest_text(client, text, fp.stem)
        stats["files"] += 1
        stats["vectors"] += n
        print(f"  ✓ {fp.name}: {n} vectors")
    print(f"Done: {stats['files']} files, {stats['vectors']} vectors")
    return stats

def delete_collection():
    try:
        get_qdrant_client().delete_collection(QDRANT_COLLECTION)
        print(f"Deleted: {QDRANT_COLLECTION}")
    except Exception:
        print("Collection not found.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        delete_collection()
    else:
        ingest_corpus()
