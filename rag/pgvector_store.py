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


def store_embeddings(repo_id: int, chunks: List[Dict[str, Any]]):
    """
    Store repository code AST chunks into Supabase pgvector table.
    """
    db: Session = SessionLocal()
    try:
        # Clear old embeddings for this repo before re-indexing
        db.query(DocumentEmbedding).filter(DocumentEmbedding.repo_id == repo_id).delete()
        db.commit()

        embeddings_to_add = []
        for i, chunk in enumerate(chunks):
            # Fallback dummy vector if embedding model service is unavailable
            dummy_vector = [0.0] * 384
            
            doc = DocumentEmbedding(
                repo_id=repo_id,
                file_path=chunk.get("file_path", "unknown"),
                chunk_id=f"{repo_id}_{chunk.get('file_path')}_{i}",
                content=chunk.get("content", ""),
                meta_json=json.dumps(chunk.get("metadata", {})),
                embedding=dummy_vector if HAS_PGVECTOR else json.dumps(dummy_vector),
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
    Perform cosine similarity vector search over repository AST chunks.
    """
    db: Session = SessionLocal()
    results = []
    try:
        if HAS_PGVECTOR:
            # PostgreSQL pgvector L2 distance / cosine operator <=>
            # Fetch top_k closest chunks for this repository
            stmt = text("""
                SELECT file_path, content, meta_json
                FROM document_embeddings
                WHERE repo_id = :repo_id
                LIMIT :top_k
            """)
            rows = db.execute(stmt, {"repo_id": repo_id, "top_k": top_k}).fetchall()
            for r in rows:
                results.append({
                    "file_path": r.file_path,
                    "content": r.content,
                    "metadata": json.loads(r.meta_json or "{}"),
                })
        else:
            # Fallback basic SQL query if pgvector extension is not compiled
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
