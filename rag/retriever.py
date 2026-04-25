import logging
from rag.indexer import get_or_create_collection
import config

logger = logging.getLogger(__name__)

def retrieve_relevant_context(
    repo_name: str,
    diff: dict,
    semgrep_findings: list,
    top_k: int = config.RAG_TOP_K
) -> str:
    """
    Given a commit diff, find the most relevant code chunks from the index.

    With function-level chunking, results now point to specific functions
    and classes rather than random file slices — giving agents much better
    context about where vulnerabilities live and how surrounding code works.
    """
    collection = get_or_create_collection(repo_name)

    if collection.count() == 0:
        return "No related context found (repository not yet indexed)."

    changed_files = [f["filename"] for f in diff["changed_files"]]
    changed_code = "\n".join([f.get("patch", "") for f in diff["changed_files"]])

    # Build a focused query from the diff + any Semgrep findings
    query_parts = [
        f"Files changed: {', '.join(changed_files)}",
        f"Code changed:\n{changed_code[:600]}",
    ]

    if semgrep_findings:
        # Include vuln type + message for targeted retrieval
        finding_strs = []
        for f in semgrep_findings[:3]:
            msg = f.get("message") or f.get("vuln_type") or ""
            finding_strs.append(msg)
        query_parts.append(f"Security issues: {', '.join(finding_strs)}")

    query = "\n".join(query_parts)

    try:
        n = min(top_k, collection.count())
        results = collection.query(
            query_texts=[query],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )

        if not results["distances"] or not results["distances"][0]:
            return "No related context found."

        context_parts = ["=== RELATED CODEBASE CONTEXT ===\n"]
        context_parts.append(
            "(Function/class-level chunks from the repo most relevant to the changed code)\n"
        )

        seen_files: set[str] = set()

        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            if distance >= config.RAG_DISTANCE_THRESHOLD:
                continue

            file_path = meta.get("file_path", "unknown")
            chunk_type = meta.get("chunk_type", "file")
            name = meta.get("name", file_path)
            start_line = meta.get("start_line", "?")
            end_line = meta.get("end_line", "?")
            content_preview = meta.get("content_preview", doc[:500])

            # Build a human-readable header for this chunk
            if chunk_type in ("function", "class"):
                header = f"{chunk_type} `{name}` in {file_path} (lines {start_line}–{end_line})"
            else:
                header = f"{file_path}"
                # Only show file-level chunks once per file
                if file_path in seen_files:
                    continue
                seen_files.add(file_path)

            context_parts.append(f"\n--- {header} ---\n{content_preview}\n")

        return "\n".join(context_parts)

    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")
        return "No related context found."
