import os
import ast
import logging
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

import config

logger = logging.getLogger(__name__)

chroma_client = chromadb.PersistentClient(path=config.VECTOR_DB_DIR)

# Use a single shared embedding function instance (loads model once)
_embedding_fn = DefaultEmbeddingFunction()

BATCH_SIZE = 50  # Upsert in batches for speed


def get_or_create_collection(repo_name: str):
    """
    Get or create a ChromaDB collection for the given repository.
    """
    safe_name = repo_name.replace("/", "_").replace("-", "_")
    return chroma_client.get_or_create_collection(
        name=safe_name,
        metadata={"hnsw:space": "cosine"},
        embedding_function=_embedding_fn,
    )


def extract_file_metadata(file_path: str, content: str) -> dict:
    """
    Extract useful facts about a code file.
    """
    metadata = {
        "file": file_path,
        "functions": [],
        "imports": [],
        "classes": [],
        "has_sql": "sql" in content.lower() or "SELECT" in content or "INSERT" in content,
        "has_auth": any(w in content.lower() for w in ["password", "token", "auth", "login", "jwt"]),
        "has_http": any(w in content.lower() for w in ["request", "response", "route", "endpoint"]),
    }
    
    if file_path.endswith(".py"):
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metadata["functions"].append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        metadata["imports"].append(alias.name)
                elif isinstance(node, ast.ClassDef):
                    metadata["classes"].append(node.name)
        except SyntaxError:
            pass
            
    return metadata


def index_repository(repo_path: str, repo_name: str, max_files: int = 200) -> int:
    """
    Walk through the repo and index code files into ChromaDB in batches.
    
    Optimizations over the original:
    - Batched upserts (BATCH_SIZE at a time) instead of one-by-one
    - Caps at max_files to prevent runaway indexing on huge repos
    - Skips files > 50KB (likely generated / vendored)
    - Collects all documents first, then upserts in bulk
    """
    collection = get_or_create_collection(repo_name)

    # Collect documents for batched upsert
    batch_ids: list[str] = []
    batch_docs: list[str] = []
    batch_metas: list[dict] = []
    indexed = 0

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in config.SKIP_DIRS]
        
        for filename in files:
            if indexed >= max_files:
                logger.info(f"Reached max_files cap ({max_files}), stopping indexing.")
                break

            _, ext = os.path.splitext(filename)
            if ext not in config.CODE_EXTENSIONS:
                continue
                
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, repo_path)
            
            try:
                file_size = os.path.getsize(file_path)
                if file_size > 50_000:  # Skip files > 50KB
                    continue

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                if len(content) < 10:
                    continue
                    
                metadata = extract_file_metadata(relative_path, content)
                
                text_to_embed = f"""\
File: {relative_path}
Functions: {', '.join(metadata['functions'][:10])}
Classes: {', '.join(metadata['classes'][:5])}
Imports: {', '.join(metadata['imports'][:10])}
SQL: {metadata['has_sql']} | Auth: {metadata['has_auth']} | HTTP: {metadata['has_http']}

{content[:1000]}"""

                batch_ids.append(relative_path)
                batch_docs.append(text_to_embed)
                batch_metas.append({
                    "file_path": relative_path,
                    "functions": str(metadata["functions"]),
                    "has_sql": metadata["has_sql"],
                    "has_auth": metadata["has_auth"],
                    "has_http": metadata["has_http"],
                    "content_preview": content[:500],
                })
                indexed += 1

                # Flush batch when full
                if len(batch_ids) >= BATCH_SIZE:
                    collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
                    logger.info(f"Batch upserted {len(batch_ids)} files ({indexed} total)")
                    batch_ids, batch_docs, batch_metas = [], [], []
                
            except Exception as e:
                logger.warning(f"Skipped {relative_path}: {e}")

        if indexed >= max_files:
            break

    # Flush remaining batch
    if batch_ids:
        collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
        logger.info(f"Final batch upserted {len(batch_ids)} files ({indexed} total)")

    logger.info(f"✅ Indexed {indexed} files for {repo_name}")
    return indexed
