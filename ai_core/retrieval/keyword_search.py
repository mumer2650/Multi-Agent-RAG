import pickle
import os
from rank_bm25 import BM25Okapi

# Set storage path
STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend", "storage"))
INDEX_PATH = os.path.join(STORAGE_DIR, "bm25_index.pkl")

def build_bm25_index(all_chunks):
    """
    1. Tokenize all text.
    2. Extract doc_ids in the exact same order.
    3. Build BM25 Index.
    4. Save BOTH to disk.
    """
    tokenized_corpus = [doc.page_content.lower().split(" ") for doc in all_chunks]
    
    doc_ids = [doc.metadata.get("doc_id") for doc in all_chunks]
    
    bm25 = BM25Okapi(tokenized_corpus)
    
    os.makedirs(STORAGE_DIR, exist_ok=True)
    
    with open(INDEX_PATH, 'wb') as f:
        pickle.dump({'bm25': bm25, 'doc_ids': doc_ids}, f)
        
    print(f"BM25 Index and ID mappings saved to {INDEX_PATH}")
    return bm25

def load_bm25_index():
    with open(INDEX_PATH, 'rb') as f:
        return pickle.load(f)

def keyword_search(query, k=5):
    """
    Returns a list of dictionaries containing the doc_id and BM25 score.
    """
    data = load_bm25_index()
    bm25 = data['bm25']
    doc_ids = data['doc_ids']
    
    tokenized_query = query.lower().split(" ")
    
    scores = bm25.get_scores(tokenized_query)
    
    id_score_pairs = list(zip(doc_ids, scores))
    
    sorted_pairs = sorted(id_score_pairs, key=lambda x: x[1], reverse=True)
    
    top_results = [{"doc_id": doc_id, "score": score} for doc_id, score in sorted_pairs if score > 0][:k]
    
    return top_results