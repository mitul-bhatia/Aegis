import os
import ast
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("aegis.rag.tree_indexer")

IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}

IGNORE_EXTENSIONS = {
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".zip",
    ".tar",
    ".gz",
    ".pdf",
    ".db",
    ".sqlite",
    ".lock",
}


def build_repo_tree(root_dir: str, max_depth: int = 5) -> str:
    """
    Generate a clean ASCII file tree representation of the codebase.
    """
    lines = []
    
    def _walk(current_dir: str, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return
            
        try:
            entries = sorted(os.listdir(current_dir))
        except Exception as e:
            logger.warning(f"Failed to read {current_dir}: {e}")
            return

        entries = [
            e for e in entries
            if e not in IGNORE_DIRS
            and not any(e.endswith(ext) for ext in IGNORE_EXTENSIONS)
            and not (e.startswith(".") and e not in {".env.example"})
        ]

        for i, entry in enumerate(entries):
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            full_path = os.path.join(current_dir, entry)
            lines.append(f"{prefix}{connector}{entry}")

            if os.path.isdir(full_path):
                extension = "    " if is_last else "│   "
                _walk(full_path, prefix + extension, depth + 1)

    _walk(root_dir)
    return "\n".join(lines)


def extract_python_ast_symbols(file_path: str) -> Dict[str, Any]:
    """
    Extract functions, classes, imports, and routes from a Python file using the built-in AST.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        logger.debug(f"AST parse failed for {file_path}: {e}")
        return {}

    classes = []
    functions = []
    routes = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = {
                "name": node.name,
                "line": node.lineno,
                "args": [a.arg for a in node.args.args],
            }
            functions.append(func_info)

            # Check for route decorators (e.g. @app.get, @router.post)
            for decorator in node.decorator_list:
                dec_str = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                if any(verb in dec_str.lower() for verb in ["get", "post", "put", "delete", "route", "api"]):
                    routes.append(f"{dec_str} -> {node.name}() [line {node.lineno}]")

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imports.append(f"{mod}.{alias.name}")

    return {
        "classes": classes,
        "functions": [f["name"] for f in functions],
        "routes": routes,
        "imports": imports[:20],
    }


def index_repository_structure(root_dir: str) -> Dict[str, Any]:
    """
    Index entire repository into a structured architectural map.
    Returns file tree, key API endpoints, classes, and language statistics.
    """
    tree_ascii = build_repo_tree(root_dir)
    file_map = {}
    languages = {}
    all_routes = []

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in IGNORE_EXTENSIONS or file.startswith("."):
                continue

            languages[ext] = languages.get(ext, 0) + 1
            rel_path = os.path.relpath(os.path.join(root, file), root_dir)
            full_path = os.path.join(root, file)

            if ext == ".py":
                symbols = extract_python_ast_symbols(full_path)
                if symbols:
                    file_map[rel_path] = symbols
                    if symbols.get("routes"):
                        all_routes.extend([f"{rel_path}: {r}" for r in symbols["routes"]])

    return {
        "tree": tree_ascii,
        "languages": languages,
        "routes": all_routes,
        "file_symbols": file_map,
    }
