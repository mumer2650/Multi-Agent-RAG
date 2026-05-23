import os
import re
import uuid
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_classic.storage import LocalFileStore
from vector_store import get_vector_store



# Set up storage path for Parent documents on your drive
STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../backend/storage"))
PARENT_STORE_PATH = os.path.join(STORAGE_DIR, "parent_store")

# Initialize an storage layer for parent text chunks
os.makedirs(PARENT_STORE_PATH, exist_ok=True)
parent_docstore = LocalFileStore(PARENT_STORE_PATH)

def clean_text(text: str) -> str:
    """Cleans up artificial line breaks and weird spacing found in PDFs."""
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r' +', ' ', text)
    return text.strip()

def ingest_documents_pipeline(raw_documents):
    """
    Core engine that takes a list of loaded LangChain documents,
    chunks them into Parent-Child pairs, and uploads them to the stores.
    """
    # 1. Connect to our initialized ChromaDB
    vector_store = get_vector_store()
    
    # 2. Configure Text Splitters
    parent_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", ". ", "? ", "! "],
        chunk_size=1500, 
        chunk_overlap=150
    )
    
    child_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", ". ", "? ", "! ", " "],
        chunk_size=300, 
        chunk_overlap=50
    )

    parent_chunks = []
    child_chunks = []
    parent_keys_and_texts = []

    # 3. Process Chunking Loop
    for doc in raw_documents:
        doc.page_content = clean_text(doc.page_content)
        parents = parent_splitter.split_documents([doc])
        
        for parent in parents:
            parent_id = str(uuid.uuid4())
            parent.metadata["doc_id"] = parent_id
            parent_chunks.append(parent)
            
            # Pack parent into format required for key-value document stores
            # Key: parent_id, Value: raw text content
            parent_keys_and_texts.append((parent_id, parent.page_content.encode("utf-8")))
            
            children = child_splitter.split_documents([parent])
            for child in children:
                child.metadata["doc_id"] = parent_id
                child_chunks.append(child)

    # 4. SAVE TO DATABASES (The missing link)
    if child_chunks:
        print(f"Embedding and adding {len(child_chunks)} child chunks to ChromaDB...")
        vector_store.add_documents(child_chunks)
        
        print(f"Saving {len(parent_chunks)} parent contexts to local file store...")
        parent_docstore.mset(parent_keys_and_texts)
        
        print("Success! Data completely saved into the Memory Vault.")
    
    return parent_chunks, child_chunks

def load_directory_base_knowledge(data_directory: str):
    """Loads all static base PDFs from the directory and triggers the pipeline."""
    print(f"Loading base documents from directory: {data_directory}...")
    loader = DirectoryLoader(data_directory, glob="*.pdf", loader_cls=PDFPlumberLoader)
    raw_documents = loader.load()
    
    if not raw_documents:
        print("Error: No documents found. Data directory might be empty.")
        return [], []
        
    return ingest_documents_pipeline(raw_documents)

def ingest_single_user_file(file_path: str):
    """
    EXPOSED WORKFLOW FUNCTION: This is what Member 1 (Saad) will call
    via FastAPI whenever a user uploads a dynamic file in the app!
    """
    print(f"Processing real-time user upload: {file_path}")
    loader = PDFPlumberLoader(file_path)
    raw_documents = loader.load()
    if raw_documents:
        ingest_documents_pipeline(raw_documents)
        return True
    return False

if __name__ == "__main__":
    # Test path setting
    DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data"))
    
    # Run pipeline on our base data directory
    parents, children = load_directory_base_knowledge(DATA_PATH)