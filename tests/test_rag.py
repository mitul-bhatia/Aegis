import pytest
import os
import json
import random
from rag.pgvector_store import get_embedding, store_embeddings, query_similar_code
from rag.indexer import chunk_file, chunk_python_file, chunk_js_ts_file
from rag.retriever import retrieve_relevant_context
from database.db import SessionLocal, Base, engine
from database.models import Repo, User

def test_rag_embedding_generation():
    vec = get_embedding("def calculate_sum(a, b): return a + b")
    assert isinstance(vec, list)
    assert len(vec) == 384

def test_python_chunker():
    content = '''
def hello_world():
    print("Hello, world!")
    return True

class Calculator:
    def add(self, a, b):
        return a + b
'''
    chunks = chunk_python_file(content, "test.py")
    assert len(chunks) >= 2
    func_chunk = next(c for c in chunks if c["type"] == "function")
    assert func_chunk["name"] == "hello_world"

def test_js_ts_chunker():
    content = '''
function processUser(user) {
    console.log(user.name);
    return user.id;
}

const formatData = (data) => {
    return JSON.stringify(data);
}
'''
    chunks = chunk_js_ts_file(content, "app.js")
    assert len(chunks) >= 2
    names = [c["name"] for c in chunks if c["type"] == "function"]
    assert "processUser" in names

def test_pgvector_store_and_retrieval():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        rand_id = random.randint(10000, 999999)
        user = User(github_id=rand_id, github_username=f"raguser_{rand_id}", github_token="tok")
        db.add(user)
        db.commit()
        repo = Repo(user_id=user.id, full_name=f"raguser_{rand_id}/ragrepo", is_indexed=True)
        db.add(repo)
        db.commit()
        db.refresh(repo)

        chunks = [
            {
                "id": "ragrepo::sql_query",
                "file_path": "db/query.py",
                "content": "def run_sql(query): db.execute(query)",
                "metadata": {"chunk_type": "function", "name": "run_sql", "start_line": 1, "end_line": 2}
            }
        ]
        store_embeddings(repo.id, chunks)

        context = retrieve_relevant_context(f"raguser_{rand_id}/ragrepo", {"changed_files": [{"filename": "db/query.py", "patch": "+run_sql"}]}, [])
        assert "run_sql" in context or "RELATED CODEBASE CONTEXT" in context

    finally:
        db.close()
