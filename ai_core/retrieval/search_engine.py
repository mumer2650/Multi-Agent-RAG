import os
import json
from vector_store import get_vector_store
from langchain_classic.storage import LocalFileStore
from keyword_search import keyword_search
from sentence_transformers import CrossEncoder

# --- THE MASTER PATH FIX ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "backend", "storage"))
PARENT_STORE_PATH = os.path.join(STORAGE_DIR, "parent_store")

parent_docstore = LocalFileStore(PARENT_STORE_PATH)

print("Loading Final Judge (Cross-Encoder)...")
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def advanced_search(query: str, k: int = 15):
    """
    1. Hybrid Search (Vector + BM25)
    2. Reciprocal Rank Fusion (RRF)
    3. Parent Context Resolution (with Clean Citations!)
    4. Cross-Encoder Reranking
    """
    print(f"\n🔍 Executing Advanced Hybrid Search for: '{query}'")
    
    # --- STEP 1: VECTOR SEARCH ---
    vector_store = get_vector_store()
    vector_results = vector_store.similarity_search(query, k=k)
    vector_ids = [doc.metadata.get("doc_id") for doc in vector_results if doc.metadata.get("doc_id")]
    
    # --- STEP 2: BM25 KEYWORD SEARCH ---
    bm25_results = keyword_search(query, k=k)
    bm25_ids = [item["doc_id"] for item in bm25_results]

    # --- STEP 3: RRF (Reciprocal Rank Fusion) ---
    fused_scores = {}
    RRF_K = 60
    
    for rank, doc_id in enumerate(vector_ids):
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (rank + 1 + RRF_K)
    for rank, doc_id in enumerate(bm25_ids):
        fused_scores[doc_id] = fused_scores.get(doc_id, 0) + 1 / (rank + 1 + RRF_K)
        
    sorted_fused_ids = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    top_candidate_ids = [doc_id for doc_id, score in sorted_fused_ids][:10]

    # --- STEP 4: RESOLVE PARENT CONTEXTS & CLEAN CITATIONS ---
    candidate_parents_data = []
    for doc_id in top_candidate_ids:
        parent_bytes = parent_docstore.mget([doc_id])[0]
        if parent_bytes:
            # Decode the JSON we saved in ingestion.py
            parent_data = json.loads(parent_bytes.decode("utf-8"))
            parent_data["doc_id"] = doc_id  # Attach the ID for reference
            
            raw_source = parent_data.get("source", "unknown")
            parent_data["source"] = os.path.basename(raw_source)
            
            candidate_parents_data.append(parent_data)

    if not candidate_parents_data:
        return []

    # --- STEP 5: CROSS-ENCODER RERANKING ---
    print(f"⚖️  Reranking {len(candidate_parents_data)} candidate parent contexts...")
    
    # Extract just the text to show the Reranker model
    cross_inp = [[query, data["text"]] for data in candidate_parents_data]
    rerank_scores = reranker.predict(cross_inp)
    
    # Re-attach the scores to the dictionary format
    for i, data in enumerate(candidate_parents_data):
        data["score"] = float(rerank_scores[i])
        
    # Sort by the final Cross-Encoder score
    candidate_parents_data.sort(key=lambda x: x["score"], reverse=True)
    
    # Return the exact requested dictionary format (Top 3)
    return candidate_parents_data[:3]


# --- TESTING MODULE ENGINE ---
if __name__ == "__main__":
    test_query = "What is AI Energy Mode?"
    
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