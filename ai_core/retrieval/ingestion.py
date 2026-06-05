import os
import re
import uuid
import shutil
import json 
from langchain_community.document_loaders import DirectoryLoader, PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
#from langchain_classic.storage import LocalFileStore
from vector_store import get_vector_store
from keyword_search import build_bm25_index
import sqlite3

class LocalFileStore:
    """High-Performance SQLite replacement. Writes thousands of chunks in milliseconds."""
    def __init__(self, path):
        self.path = path
        os.makedirs(self.path, exist_ok=True)
        self.db_path = os.path.join(self.path, "parents.db")

    def mget(self, keys):
        results = []
        with sqlite3.connect(self.db_path) as conn:
            # DEFENSIVE PROGRAMMING: Ensure table exists before reading
            conn.execute("CREATE TABLE IF NOT EXISTS store (id TEXT PRIMARY KEY, data BLOB)")
            cursor = conn.cursor()
            for key in keys:
                cursor.execute("SELECT data FROM store WHERE id=?", (key,))
                row = cursor.fetchone()
                results.append(row[0] if row else None)
        return results

    def mset(self, key_value_pairs):
        with sqlite3.connect(self.db_path) as conn:
            # DEFENSIVE PROGRAMMING: Ensure table exists right before saving!
            conn.execute("CREATE TABLE IF NOT EXISTS store (id TEXT PRIMARY KEY, data BLOB)")
            conn.executemany("INSERT OR REPLACE INTO store (id, data) VALUES (?, ?)", key_value_pairs)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "backend", "storage"))
PARENT_STORE_PATH = os.path.join(STORAGE_DIR, "parent_store")

os.makedirs(PARENT_STORE_PATH, exist_ok=True)
parent_docstore = LocalFileStore(PARENT_STORE_PATH)

def reset_database():
    print("🧹 Cleaning ALL databases for a fresh sync...")
    paths_to_delete = [
        os.path.join(STORAGE_DIR, "chroma_db"),
        PARENT_STORE_PATH,
        os.path.join(STORAGE_DIR, "bm25_index.pkl")
    ]
    for path in paths_to_delete:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    
    
    os.makedirs(PARENT_STORE_PATH, exist_ok=True)
    print("   - All databases reset.")

def clean_text(text: str) -> str:
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def ingest_documents_pipeline(raw_documents):
    vector_store = get_vector_store()
    
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

    parent_chunks, child_chunks, parent_keys_and_texts = [], [], []

    for doc in raw_documents:
        doc.page_content = clean_text(doc.page_content)
        parents = parent_splitter.split_documents([doc])
        
        for parent in parents:
            parent_id = str(uuid.uuid4())
            parent.metadata["doc_id"] = parent_id
            
            # --- HIS LOGIC: Extract Citation Data ---
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", 0)
            
            parent_chunks.append(parent)
            
            # --- THE MERGE: Pack the text AND his citations into JSON for easy retrieval ---
            parent_dict = {
                "text": parent.page_content,
                "source": source,
                "page": page
            }
            parent_keys_and_texts.append((parent_id, json.dumps(parent_dict).encode("utf-8")))
            
            children = child_splitter.split_documents([parent])
            
            # --- HIS LOGIC: Inject metadata into child chunks ---
            for child_index, child in enumerate(children):
                child.metadata["doc_id"] = parent_id
                child.metadata["source"] = source
                child.metadata["page"] = page
                child.metadata["chunk_index"] = child_index
                child_chunks.append(child)

    print(f"Saving {len(parent_chunks)} Parent contexts to disk...")
    parent_docstore.mset(parent_keys_and_texts)

    if child_chunks:
        print(f"Embedding {len(child_chunks)} chunks into ChromaDB...")
        batch_size = 1000  
        for i in range(0, len(child_chunks), batch_size):
            batch = child_chunks[i : i + batch_size]
            vector_store.add_documents(batch)
            print(f"Uploaded batch {i // batch_size + 1} to ChromaDB...")
        
    print("Indexing BM25...")
    build_bm25_index(child_chunks)
    print("✅ BM25 Keyword Index built successfully.")
    
    return parent_chunks, child_chunks

def load_directory_base_knowledge(data_directory: str):
    print(f"Loading base documents from directory: {data_directory}...")
    loader = DirectoryLoader(data_directory, glob="*.pdf", loader_cls=PDFPlumberLoader)
    raw_documents = loader.load()
    if not raw_documents:
        return [], []
    return ingest_documents_pipeline(raw_documents)

if __name__ == "__main__":
    reset_database() 
    
    DATA_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "../../data"))
    load_directory_base_knowledge(DATA_PATH)
    print("🚀 Pipeline complete!")