"""
Aegis — Supabase pgvector Store for AST Vector Embeddings

Replaces local ephemeral ChromaDB with Supabase pgvector for persistent multi-tenant vector storage.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

import config
from database.db import SessionLocal
from database.models import DocumentEmbedding, HAS_PGVECTOR

logger = logging.getLogger(__name__)

_embedder = None

def get_embedding(text_content: str) -> List[float]:
    """Generate a 384-dimensional embedding vector for text using SentenceTransformer or ChromaDB default."""
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
            logger.info("pgvector_store: loaded BAAI/bge-small-en-v1.5 model")
        except Exception:
            try:
                from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
                _embedder = DefaultEmbeddingFunction()
                logger.info("pgvector_store: fallback to ChromaDB DefaultEmbeddingFunction")
            except Exception as e:
                logger.warning(f"pgvector_store: no embedding engine available ({e})")
                _embedder = False

    if _embedder and _embedder is not False:
        try:
            if hasattr(_embedder, "encode"):
                res = _embedder.encode([text_content])
                vec = res[0].tolist() if hasattr(res[0], "tolist") else list(res[0])
                return vec
            elif callable(_embedder):
                res = _embedder([text_content])
                return list(res[0])
        except Exception as e:
            logger.warning(f"Error computing embedding vector: {e}")

    # Fallback zero vector if embedder is unavailable
    return [0.0] * 384


def store_embeddings(repo_id: int, chunks: List[Dict[str, Any]]):
    """
    Store repository code AST chunks into Supabase pgvector table with real embeddings.
    """
    db: Session = SessionLocal()
    try:
        # Clear old embeddings for this repo before re-indexing
        db.query(DocumentEmbedding).filter(DocumentEmbedding.repo_id == repo_id).delete()
        db.commit()

        embeddings_to_add = []
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            vector = get_embedding(content)
            
            file_p = chunk.get("file_path") or chunk.get("file", "unknown")
            doc = DocumentEmbedding(
                repo_id=repo_id,
                file_path=file_p,
                chunk_id=chunk.get("id") or f"{repo_id}_{file_p}_{i}",
                content=content,
                meta_json=json.dumps(chunk.get("metadata") or chunk),
                embedding=vector if HAS_PGVECTOR else json.dumps(vector),
            )
            embeddings_to_add.append(doc)

        db.bulk_save_objects(embeddings_to_add)
        db.commit()
        logger.info(f"Stored {len(embeddings_to_add)} document embeddings in pgvector for repo_id={repo_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store pgvector embeddings: {e}")
    finally:
        db.close()


def query_similar_code(repo_id: int, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Perform cosine similarity vector search over repository AST chunks using pgvector <=> operator.
    """
    db: Session = SessionLocal()
    results = []
    try:
        query_vector = get_embedding(query_text)

        if HAS_PGVECTOR:
            # Format vector as string array format for Postgres pgvector query literal if needed
            vec_str = str(query_vector)
            stmt = text("""
                SELECT file_path, content, meta_json
                FROM document_embeddings
                WHERE repo_id = :repo_id
                ORDER BY embedding <=> :query_vec
                LIMIT :top_k
            """)
            rows = db.execute(stmt, {"repo_id": repo_id, "query_vec": vec_str, "top_k": top_k}).fetchall()
            for r in rows:
                results.append({
                    "file_path": r.file_path,
                    "content": r.content,
                    "metadata": json.loads(r.meta_json or "{}"),
                })
        else:
            rows = db.query(DocumentEmbedding).filter(
                DocumentEmbedding.repo_id == repo_id
            ).limit(top_k).all()
            
            for r in rows:
                results.append({
                    "file_path": r.file_path,
                    "content": r.content,
                    "metadata": json.loads(r.meta_json or "{}"),
                })
    except Exception as e:
        logger.error(f"pgvector search error: {e}")
    finally:
        db.close()

    return results

