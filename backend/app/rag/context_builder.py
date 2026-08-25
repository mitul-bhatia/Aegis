import os
import logging
from typing import Dict, Any, Optional
from backend.app.rag.tree_indexer import index_repository_structure

logger = logging.getLogger("aegis.rag.context_builder")


def get_file_surrounding_context(
    file_path: str,
    line_start: int,
    line_end: Optional[int] = None,
    context_lines: int = 25,
) -> Dict[str, Any]:
    """
    Extract exact code snippet with surrounding context lines and line numbers.
    """
    if not os.path.exists(file_path):
        return {"code_snippet": "", "start_line": line_start, "end_line": line_start}

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception as e:
        logger.warning(f"Error reading file {file_path}: {e}")
        return {"code_snippet": "", "start_line": line_start, "end_line": line_start}

    total_lines = len(all_lines)
    actual_end = line_end or line_start
    
    start_idx = max(0, line_start - 1 - context_lines)
    end_idx = min(total_lines, actual_end + context_lines)

    numbered_snippet = []
    for idx in range(start_idx, end_idx):
        line_num = idx + 1
        marker = ">>" if line_start <= line_num <= actual_end else "  "
        numbered_snippet.append(f"{marker} {line_num:4d} | {all_lines[idx].rstrip()}")

    raw_exact_snippet = "".join(all_lines[max(0, line_start - 1) : min(total_lines, actual_end)])

    return {
        "numbered_context": "\n".join(numbered_snippet),
        "raw_exact_snippet": raw_exact_snippet,
        "full_file_content": "".join(all_lines),
        "start_line": start_idx + 1,
        "end_line": end_idx,
    }


def build_agent_context(
    repo_dir: str,
    vulnerable_file_rel_path: Optional[str] = None,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
) -> str:
    """
    Construct a clean Markdown context block combining repository structure
    and specific file context for LLM agents.
    """
    repo_structure = index_repository_structure(repo_dir)
    tree_text = repo_structure.get("tree", "")
    routes = repo_structure.get("routes", [])

    context_parts = [
        "## Repository Architecture & Structure",
        "```",
        tree_text[:3000] if len(tree_text) > 3000 else tree_text,
        "```",
    ]

    if routes:
        context_parts.extend([
            "### Detected API Endpoints / Routes",
            "\n".join(f"- `{r}`" for r in routes[:15]),
            "",
        ])

    if vulnerable_file_rel_path:
        full_file_path = os.path.join(repo_dir, vulnerable_file_rel_path)
        if os.path.exists(full_file_path) and line_start is not None:
            snippet_info = get_file_surrounding_context(full_file_path, line_start, line_end)
            context_parts.extend([
                f"## Vulnerable File: `{vulnerable_file_rel_path}` (Line {line_start})",
                "```python",
                snippet_info.get("numbered_context", ""),
                "```",
            ])

    return "\n\n".join(context_parts)
