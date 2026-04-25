import os
import ast
import re
import logging
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

import config

logger = logging.getLogger(__name__)

chroma_client = chromadb.PersistentClient(path=config.VECTOR_DB_DIR)


def _build_embedding_fn():
    """
    Build the embedding function based on config.RAG_EMBEDDING_MODEL.
    Falls back to ChromaDB's default if sentence-transformers is not installed.
    """
    if config.RAG_EMBEDDING_MODEL == "bge":
        try:
            # Lazy import — only load if the package is installed
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            fn = SentenceTransformerEmbeddingFunction(
                model_name="BAAI/bge-small-en-v1.5"
            )
            logger.info("RAG: using BAAI/bge-small-en-v1.5 embedding model")
            return fn
        except (ImportError, Exception) as e:
            logger.warning(
                f"sentence-transformers not available ({e}) — "
                "falling back to default embeddings. "
                "Run: pip install sentence-transformers"
            )

    logger.info("RAG: using default ChromaDB embedding model (all-MiniLM-L6-v2)")
    return DefaultEmbeddingFunction()


# Build once at import time — shared across all collections
_embedding_fn = _build_embedding_fn()

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


def chunk_python_file(content: str, file_path: str) -> list[dict]:
    """
    Split a Python file into function/class-level chunks using the AST.

    Each function and class becomes its own chunk so the retriever can
    return the exact function that contains a vulnerability rather than
    a random 1000-char slice of the file.

    Always adds a file-level chunk too (first 2000 chars) for file-level queries.
    """
    chunks = []

    try:
        tree = ast.parse(content)
        lines = content.splitlines()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            start = node.lineno - 1          # 0-indexed
            end = getattr(node, "end_lineno", start + 1)
            chunk_content = "\n".join(lines[start:end])

            # Skip tiny stubs (< 3 lines)
            if end - start < 3:
                continue

            chunk_type = "class" if isinstance(node, ast.ClassDef) else "function"
            chunk_id = f"{file_path}::{node.name}"

            chunks.append({
                "id": chunk_id,
                "content": chunk_content,
                "type": chunk_type,
                "name": node.name,
                "start_line": start + 1,
                "end_line": end,
                "file": file_path,
            })

    except SyntaxError:
        # File has syntax errors — fall through to file-level chunk only
        pass

    # Always include a file-level chunk for broad queries
    chunks.append({
        "id": file_path,
        "content": content[:2000],
        "type": "file",
        "name": file_path,
        "start_line": 1,
        "end_line": content.count("\n") + 1,
        "file": file_path,
    })

    return chunks


def chunk_js_ts_file(content: str, file_path: str) -> list[dict]:
    """
    Split a JS/TS file into function/class-level chunks using regex.

    Handles:
    - function declarations: function foo() {
    - arrow functions assigned to const/let: const foo = () => {
    - class declarations: class Foo {
    - async variants of all the above
    """
    chunks = []
    lines = content.splitlines()

    # Patterns to detect function/class starts
    patterns = [
        # function foo() { / async function foo() {
        re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),
        # const foo = () => { / const foo = async () => {
        re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("),
        # class Foo {
        re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)"),
    ]

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        matched_name = None

        for pat in patterns:
            m = pat.match(line)
            if m:
                matched_name = m.group(1)
                break

        if matched_name:
            # Collect lines until brace depth returns to 0
            start = i
            depth = 0
            j = i
            while j < len(lines):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth > 0 or j == i:
                    j += 1
                    continue
                break

            end = min(j + 1, len(lines))
            chunk_content = "\n".join(lines[start:end])

            if end - start >= 3:
                chunks.append({
                    "id": f"{file_path}::{matched_name}",
                    "content": chunk_content,
                    "type": "function",
                    "name": matched_name,
                    "start_line": start + 1,
                    "end_line": end,
                    "file": file_path,
                })
            i = end
        else:
            i += 1

    # File-level chunk
    chunks.append({
        "id": file_path,
        "content": content[:2000],
        "type": "file",
        "name": file_path,
        "start_line": 1,
        "end_line": len(lines),
        "file": file_path,
    })

    return chunks


def chunk_file(content: str, file_path: str) -> list[dict]:
    """
    Dispatch to the right chunker based on file extension.
    Falls back to a single file-level chunk for unsupported types.
    """
    _, ext = os.path.splitext(file_path)

    if ext == ".py":
        return chunk_python_file(content, file_path)
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        return chunk_js_ts_file(content, file_path)
    else:
        # Generic: just index the first 2000 chars as one chunk
        return [{
            "id": file_path,
            "content": content[:2000],
            "type": "file",
            "name": file_path,
            "start_line": 1,
            "end_line": content.count("\n") + 1,
            "file": file_path,
        }]


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
    Walk through the repo and index code files into ChromaDB.

    Uses function/class-level chunking so the retriever can return
    the exact function containing a vulnerability rather than a random
    file slice.

    Each file produces multiple chunks (one per function/class + one file-level).
    """
    collection = get_or_create_collection(repo_name)

    batch_ids: list[str] = []
    batch_docs: list[str] = []
    batch_metas: list[dict] = []
    files_indexed = 0
    chunks_indexed = 0

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in config.SKIP_DIRS]

        for filename in files:
            if files_indexed >= max_files:
                logger.info(f"Reached max_files cap ({max_files}), stopping indexing.")
                break

            _, ext = os.path.splitext(filename)
            if ext not in config.CODE_EXTENSIONS:
                continue

            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, repo_path)

            try:
                file_size = os.path.getsize(file_path)
                if file_size > 50_000:  # Skip files > 50KB (generated/vendored)
                    continue

                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if len(content) < 10:
                    continue

                # Get function/class-level chunks for this file
                chunks = chunk_file(content, relative_path)
                file_meta = extract_file_metadata(relative_path, content)

                for chunk in chunks:
                    batch_ids.append(chunk["id"])
                    batch_docs.append(chunk["content"])
                    batch_metas.append({
                        "file_path": chunk["file"],
                        "chunk_type": chunk["type"],
                        "name": chunk["name"],
                        "start_line": chunk["start_line"],
                        "end_line": chunk["end_line"],
                        "has_sql": file_meta["has_sql"],
                        "has_auth": file_meta["has_auth"],
                        "has_http": file_meta["has_http"],
                        # Store the actual chunk content for retrieval
                        "content_preview": chunk["content"][:500],
                    })
                    chunks_indexed += 1

                    # Flush batch when full
                    if len(batch_ids) >= BATCH_SIZE:
                        collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
                        logger.debug(f"Batch upserted {len(batch_ids)} chunks")
                        batch_ids, batch_docs, batch_metas = [], [], []

                files_indexed += 1

            except Exception as e:
                logger.warning(f"Skipped {relative_path}: {e}")

        if files_indexed >= max_files:
            break

    # Flush remaining
    if batch_ids:
        collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
        logger.debug(f"Final batch upserted {len(batch_ids)} chunks")

    logger.info(f"Indexed {files_indexed} files → {chunks_indexed} chunks for {repo_name}")
    return files_indexed
