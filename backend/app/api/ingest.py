import os
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()

@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a new document into the RAG system.
    Saves the uploaded file to the 'dataset/raw_uploads' directory.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    dataset_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "dataset",
        "raw_uploads"
    )
    
    os.makedirs(dataset_dir, exist_ok=True)
    file_path = os.path.join(dataset_dir, file.filename)
    
    try:
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            
        # Run ingestion in a separate thread so we don't block the API
        import asyncio
        from langchain_community.document_loaders import PDFPlumberLoader
        import sys
        # Add the root directory to sys.path to resolve ai_core imports
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            
        from ai_core.retrieval.ingestion import ingest_documents_pipeline
        
        def run_ingestion():
            try:
                print(f"Loading {file_path} for ingestion...")
                loader = PDFPlumberLoader(file_path)
                raw_documents = loader.load()
                if raw_documents:
                    ingest_documents_pipeline(raw_documents)
                    print(f"Ingestion complete for {file.filename}")
            except Exception as e:
                print(f"Error during ingestion pipeline: {e}")
                
        # Fire and forget
        asyncio.create_task(asyncio.to_thread(run_ingestion))
        
    except Exception as e:
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    return {
        "status": "success", 
        "filename": file.filename, 
        "message": f"Document {file.filename} saved and is being ingested into ChromaDB."
    }
