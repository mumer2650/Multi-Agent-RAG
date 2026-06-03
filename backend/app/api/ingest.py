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
    except Exception as e:
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    return {
        "status": "success", 
        "filename": file.filename, 
        "message": f"Document {file.filename} saved to dataset/raw_uploads."
    }
