import os
import json
import concurrent.futures
from ai_core.retrieval.vector_store import get_vector_store
#from langchain_classic.storage import LocalFileStore
from ai_core.retrieval.keyword_search import keyword_search
from sentence_transformers import CrossEncoder
import sqlite3
from langsmith import traceable

class LocalFileStore:
    """High-Performance SQLite replacement. Writes thousands of chunks in milliseconds."""
    def __init__(self, path):
        self.path = path
        os.makedirs(self.path, exist_ok=True)
        self.db_path = os.path.join(self.path, "parents.db")

    def mget(self, keys):
        results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS store (id TEXT PRIMARY KEY, data BLOB)")
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in keys])
            cursor.execute(f"SELECT id, data FROM store WHERE id IN ({placeholders})", keys)
            rows = cursor.fetchall()
            row_dict = {row[0]: row[1] for row in rows}
            for key in keys:
                results.append(row_dict.get(key))
        return results

    def mset(self, key_value_pairs):
        with sqlite3.connect(self.db_path) as conn:
            # DEFENSIVE PROGRAMMING: Ensure table exists right before saving!
            conn.execute("CREATE TABLE IF NOT EXISTS store (id TEXT PRIMARY KEY, data BLOB)")
            conn.executemany("INSERT OR REPLACE INTO store (id, data) VALUES (?, ?)", key_value_pairs)

# --- THE MASTER PATH FIX ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.abspath(os.path.join(CURRENT_DIR,"..", "..", "backend", "storage"))
PARENT_STORE_PATH = os.path.join(STORAGE_DIR, "parent_store")

parent_docstore = LocalFileStore(PARENT_STORE_PATH)

# Removed CrossEncoder initialization for massive latency reduction

@traceable(name="Dense Vector Search", run_type="retriever")
def _dense_vector_search(query: str, k: int):
    vector_store = get_vector_store()
    vector_results = vector_store.similarity_search(query, k=k)
    return [doc.metadata.get("doc_id") for doc in vector_results if doc.metadata.get("doc_id")]

@traceable(name="Sparse BM25 Search", run_type="retriever")
def _sparse_bm25_search(query: str, k: int):
    bm25_results = keyword_search(query, k=k)
    return [item["doc_id"] for item in bm25_results]

@traceable(name="Cross-Encoder Reranker", run_type="chain")
def _cross_encoder_rerank(query: str, candidate_parents_data: list, threshold: float = -100.0):
    print(f"⚖️  Reranking {len(candidate_parents_data)} candidate parent contexts...")
    cross_inp = [[query, data["text"]] for data in candidate_parents_data]
    rerank_scores = reranker.predict(cross_inp)
    for i, data in enumerate(candidate_parents_data):
        data["score"] = float(rerank_scores[i])
    
    # Filter out highly irrelevant documents based on the score threshold
    filtered_parents_data = [data for data in candidate_parents_data if data["score"] >= threshold]
    if not filtered_parents_data:
        print(f"⚠️ All retrieved contexts dropped. Top score was {max([data['score'] for data in candidate_parents_data], default='None')}")
        return []

    filtered_parents_data.sort(key=lambda x: x["score"], reverse=True)
    return filtered_parents_data[:3]

@traceable(name="advanced_search", run_type="retriever")
def advanced_search(query: str, k: int = 15):
    """
    1. Hybrid Search (Vector + BM25)
    2. Reciprocal Rank Fusion (RRF)
    3. Parent Context Resolution (with Clean Citations!)
    4. Cross-Encoder Reranking
    """
    print(f"\n🔍 Executing Advanced Hybrid Search for: '{query}'")
    
    # --- STEP 1 & 2: CONCURRENT VECTOR AND BM25 SEARCH ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        vector_future = executor.submit(_dense_vector_search, query, k)
        bm25_future = executor.submit(_sparse_bm25_search, query, k)
        
        vector_ids = vector_future.result()
        bm25_ids = bm25_future.result()

    # --- STEP 3: RRF (Reciprocal Rank Fusion) ---
    fused_scores = {}
    RRF_K = 60
    
    for rank, doc_id in enumerate(vector_ids):
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (rank + 1 + RRF_K)
    for rank, doc_id in enumerate(bm25_ids):
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (rank + 1 + RRF_K)
        
    sorted_fused_ids = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    top_candidate_ids = [doc_id for doc_id, score in sorted_fused_ids][:10]

    # --- STEP 3.5: EXACT KEYWORD SQLite FALLBACK ---
    # If BM25 missed an exact code (like "4C") due to punctuation, force it into the candidate list!
    import re
    keywords = re.findall(r'\b[a-zA-Z0-9]{2,}\b', query.lower())
    important_keywords = [kw for kw in keywords if re.search(r'\d', kw) and re.search(r'[a-z]', kw)]
    
    if important_keywords:
        import sqlite3
        with sqlite3.connect(parent_docstore.db_path) as conn:
            cursor = conn.cursor()
            for kw in important_keywords:
                # Use LIKE to find the keyword anywhere in the raw text JSON
                cursor.execute("SELECT id FROM store WHERE data LIKE ?", (f'%{kw}%',))
                rows = cursor.fetchall()
                for row in rows:
                    if row[0] not in top_candidate_ids:
                        top_candidate_ids.append(row[0])

    # --- STEP 4: RESOLVE PARENT CONTEXTS & CLEAN CITATIONS (BATCH FETCH) ---
    parent_bytes_list = parent_docstore.mget(top_candidate_ids)
    candidate_parents_data = []
    for doc_id, parent_bytes in zip(top_candidate_ids, parent_bytes_list):
        if parent_bytes:
            parent_data = json.loads(parent_bytes.decode("utf-8"))
            parent_data["doc_id"] = doc_id
            raw_source = parent_data.get("source", "unknown")
            parent_data["source"] = os.path.basename(raw_source)
            candidate_parents_data.append(parent_data)

    if not candidate_parents_data:
        return []

    # --- STEP 4.5: ZERO-LATENCY KEYWORD RERANKER ---
    # Since BM25 uses naive splitting, it misses codes attached to punctuation (e.g. "(4C)").
    # We extract alphanumeric codes from the query and boost matching parent contexts.
    import re
    keywords = re.findall(r'\b[a-zA-Z0-9]{2,}\b', query.lower())
    # Important keywords are alphanumeric combinations (e.g. "4c", "q70a")
    important_keywords = [kw for kw in keywords if re.search(r'\d', kw) and re.search(r'[a-z]', kw)]
    
    if important_keywords:
        for data in candidate_parents_data:
            text = data.get("text", "").lower()
            # Boost score based on how many important keywords are found in the text
            data["boost_score"] = sum(1 for kw in important_keywords if kw in text)
        
        # Sort by keyword boost first, falling back to original RRF order
        candidate_parents_data.sort(key=lambda x: x.get("boost_score", 0), reverse=True)

    # --- STEP 5: RETURN TOP RESULTS (Bypassing Cross-Encoder for speed) ---
    # Increased to top 4 to provide better context while avoiding total hallucination
    return candidate_parents_data[:4]


# --- TESTING MODULE ENGINE ---
if __name__ == "__main__":
    test_query = "What is the purpose of the Galaxy Wearable app when using Galaxy Buds FE?"
    
    contexts = advanced_search(test_query, k=15)
    
    print("\n=============================================")
    print("🏆 ADVANCED HYBRID RAG TEST RESULTS 🏆")
    print("=============================================\n")
    
    if not contexts:
        print("No contexts found. Check your database paths.")
    else:
        for idx, result in enumerate(contexts):
            print(f"📍 Rank #{idx + 1} | Source: {result['source']} | Page: {result['page']}")
            print(f"Score: {result['score']:.4f}")
            print(f"Text: {result['text'][:200]}...\n")
            print("-" * 60)