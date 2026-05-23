import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_DIR = os.path.join(BASE_DIR, "backend", "storage", "chroma_db")

def get_vector_store():
    """Returns the ChromaDB instance with the embedding model attached."""
    return Chroma(
        collection_name="rag_children",
        embedding_function=embedding_model, # This is the "brain" that does the math
        persist_directory=DB_DIR
    )