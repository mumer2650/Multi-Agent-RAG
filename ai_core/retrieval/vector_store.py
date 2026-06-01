import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "backend", "storage"))
DB_DIR = os.path.join(STORAGE_DIR, "chroma_db")

embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

def get_vector_store():
    return Chroma(
        collection_name="rag_children",
        embedding_function=embedding_model,
        persist_directory=DB_DIR
    )