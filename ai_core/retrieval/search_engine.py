import os
from vector_store import get_vector_store
from langchain_classic.storage import LocalFileStore

# 1. Locate and lock onto our persistent Parent Storage directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
STORAGE_DIR = os.path.join(BASE_DIR, "..", "backend", "storage")
PARENT_STORE_PATH = os.path.join(STORAGE_DIR, "parent_store")

parent_docstore = LocalFileStore(PARENT_STORE_PATH)

def retrieve_context_pipeline(query: str, k: int = 3):

    vector_store = get_vector_store()
    
    # 2. Search ChromaDB for the top 'k' most relevant Child Chunks
    print(f"Searching vector database for: '{query}'...")
    child_matches = vector_store.similarity_search(query, k=k)
    
    retrieved_parents = []
    seen_parent_ids = set() # Avoid sending duplicate parents if two children match
    
    # 3. Resolve parent texts from the local byte store using metadata tags
    for child in child_matches:
        parent_id = child.metadata.get("doc_id")
        
        if parent_id and parent_id not in seen_parent_ids:
            seen_parent_ids.add(parent_id)
            
            # Fetch the encrypted bytes from our disk store
            parent_bytes = parent_docstore.mget([parent_id])[0]
            
            if parent_bytes:
                # Decode bytes back to an English string
                parent_text = parent_bytes.decode("utf-8")
                retrieved_parents.append(parent_text)
                
    return retrieved_parents

# --- TESTING MODULE ENGINE ---
if __name__ == "__main__":
    # Let's test your engine with a natural language query!
    test_query = "What is AI Energy Mode?"
    
    contexts = retrieve_context_pipeline(test_query, k=2)
    
    print("\n=============================================")
    print("🏆 PIPELINE RETRIEVAL TEST RESULTS 🏆")
    print("=============================================\n")
    
    if not contexts:
        print("No contexts found. Did you initialize your ingestion directory cleanly?")
    else:
        for idx, paragraph in enumerate(contexts):
            print(f"📍 Resolved Parent Context #{idx + 1}:")
            print(f"{paragraph}\n")
            print("-" * 45)