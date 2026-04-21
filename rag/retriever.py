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
    Given a commit diff, find the most relevant files from our index.
    """
    collection = get_or_create_collection(repo_name)
    
    changed_files = [f["filename"] for f in diff["changed_files"]]
    changed_code = "\n".join([f["patch"] for f in diff["changed_files"]])
    
    query_parts = [
        f"Files that were changed: {', '.join(changed_files)}",
        f"Code that was changed: {changed_code[:500]}",
    ]
    
    if semgrep_findings:
        issues = [f["message"] for f in semgrep_findings[:3]]
        query_parts.append(f"Security issues found: {', '.join(issues)}")
        
    query = "\n".join(query_parts)
    
    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"]
        )
        
        context_parts = ["=== RELATED CODEBASE CONTEXT ===\n"]
        context_parts.append("(These are files from the repo that are related to the changed code)\n")
        
        if not results["distances"] or not results["distances"][0]:
            return "No related context found."
            
        for i, (doc, meta, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            if distance < config.RAG_DISTANCE_THRESHOLD:
                context_parts.append(f"""
--- Related File {i+1}: {meta['file_path']} ---
{meta.get('content_preview', 'No preview available')}
""")
                
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error during RAG retrieval: {e}")
        return "No related context found."
