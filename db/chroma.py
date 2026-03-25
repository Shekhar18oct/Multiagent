"""
ChromaDB Cloud integration.
Tenant : shashishekhar618
Database: multiagent
Collection: source
Cloud URL: https://www.trychroma.com/shashishekhar618/aws-us-east-1/multiagent/source
"""

import os
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings

CHROMA_TENANT = "shashishekhar618"
CHROMA_DATABASE = "multiagent"
CHROMA_COLLECTION = "source"
CHROMA_API_KEY = os.getenv("CHROMA_API_KEY", "")


def _get_client():
    """Return a ChromaDB Cloud client."""
    return chromadb.CloudClient(
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE,
        api_key=CHROMA_API_KEY,
    )


def _get_collection(client):
    """Return (or create) the source collection."""
    return client.get_or_create_collection(name=CHROMA_COLLECTION)


# ── Project metadata ──────────────────────────────────────────────────────────

def store_project_metadata(project_id: str, metadata: Dict[str, str]) -> None:
    """Store project-level metadata as a document in ChromaDB."""
    client = _get_client()
    col = _get_collection(client)
    col.upsert(
        ids=[f"project:{project_id}"],
        documents=[f"Project {project_id}"],
        metadatas=[{**metadata, "type": "project"}],
    )


def get_project_metadata(project_id: str) -> Dict[str, Any]:
    """Retrieve project metadata from ChromaDB."""
    client = _get_client()
    col = _get_collection(client)
    result = col.get(ids=[f"project:{project_id}"])
    if result and result["metadatas"]:
        return dict(result["metadatas"][0])  # type: ignore[index]
    return {}


def list_all_projects() -> List[Dict[str, Any]]:
    """List all projects stored in ChromaDB."""
    client = _get_client()
    col = _get_collection(client)
    result = col.get(where={"type": "project"})
    projects = []
    if result and result["ids"]:
        for pid, meta in zip(result["ids"], result["metadatas"] or []):  # type: ignore[arg-type]
            projects.append({"project_id": pid.replace("project:", ""), **meta})
    return projects


# ── Code chunk embeddings ─────────────────────────────────────────────────────

def store_code_chunks(project_id: str, chunks: List[Dict]) -> None:
    """Store code chunks as embeddings-ready documents in ChromaDB."""
    if not chunks:
        return
    client = _get_client()
    col = _get_collection(client)
    ids = [f"{project_id}:chunk:{i}" for i in range(len(chunks))]
    documents = [
        f"{c.get('type', '')} {c.get('name', '')} in {c.get('file', '')}:\n{c.get('code', '')}"
        for c in chunks
    ]
    metadatas = [
        {
            "project_id": project_id,
            "type": c.get("type", ""),
            "name": c.get("name", ""),
            "file": c.get("file", ""),
            "lineno": str(c.get("lineno", "")),
            "chunk_type": "code_chunk",
        }
        for c in chunks
    ]
    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        col.upsert(
            ids=ids[i:i + batch_size],
            documents=documents[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size],  # type: ignore[arg-type]
        )


def query_code_chunks(project_id: str, query: str, top_k: int = 5) -> List[Dict]:
    """Query ChromaDB for code chunks semantically similar to the query."""
    client = _get_client()
    col = _get_collection(client)
    results = col.query(
        query_texts=[query],
        n_results=top_k,
        where={"project_id": project_id, "chunk_type": "code_chunk"},
    )
    chunks = []
    if results and results["ids"]:
        for meta, doc in zip((results["metadatas"] or [[]])[0], (results["documents"] or [[]])[0]):  # type: ignore[index]
            chunks.append({**meta, "snippet": doc[:300]})
    return chunks


# ── Legacy compatibility ───────────────────────────────────────────────────────

def store_embedding(collection: str, embedding, metadata: dict) -> None:
    """Legacy: store a raw embedding (kept for backwards compatibility)."""
    client = _get_client()
    col = client.get_or_create_collection(name=collection)
    col.upsert(ids=[metadata.get("id", "unknown")], embeddings=[embedding], metadatas=[metadata])


def query_embeddings(collection: str, query: str, top_k: int = 5):
    """Legacy: query by text (kept for backwards compatibility)."""
    client = _get_client()
    col = client.get_or_create_collection(name=collection)
    return col.query(query_texts=[query], n_results=top_k)
