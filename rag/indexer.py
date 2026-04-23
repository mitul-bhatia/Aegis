import os
import ast
import logging
import chromadb

import config

logger = logging.getLogger(__name__)

chroma_client = chromadb.PersistentClient(path=config.VECTOR_DB_DIR)

def get_or_create_collection(repo_name: str):
    """
    Get or create a ChromaDB collection for the given repository.
    """
    safe_name = repo_name.replace("/", "_").replace("-", "_")
    return chroma_client.get_or_create_collection(
        name=safe_name,
        metadata={"hnsw:space": "cosine"}
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

def index_repository(repo_path: str, repo_name: str) -> int:
    """
    Walk through the entire repo and index every code file into ChromaDB.
    """
    collection = get_or_create_collection(repo_name)
    indexed = 0
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in config.SKIP_DIRS]
        
        for filename in files:
            _, ext = os.path.splitext(filename)
            if ext not in config.CODE_EXTENSIONS:
                continue
                
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, repo_path)
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                if len(content) < 10:
                    continue
                    
                metadata = extract_file_metadata(relative_path, content)
                
                text_to_embed = f"""
File: {relative_path}
Functions defined here: {', '.join(metadata['functions'][:10])}
Classes defined here: {', '.join(metadata['classes'][:5])}
Imports used: {', '.join(metadata['imports'][:10])}
Touches database (SQL): {metadata['has_sql']}
Handles authentication: {metadata['has_auth']}
Handles HTTP requests: {metadata['has_http']}

First 1000 chars of code:
{content[:1000]}
"""
                
                collection.upsert(
                    ids=[relative_path],
                    documents=[text_to_embed],
                    metadatas=[{
                        "file_path": relative_path,
                        "functions": str(metadata["functions"]),
                        "has_sql": metadata["has_sql"],
                        "has_auth": metadata["has_auth"],
                        "has_http": metadata["has_http"],
                        "content_preview": content[:500]
                    }]
                )
                
                indexed += 1
                logger.info(f"Indexed: {relative_path}")
                
            except Exception as e:
                logger.warning(f"Skipped {relative_path}: {e}")
                
    logger.info(f"Indexed {indexed} files for {repo_name}")
    return indexed
