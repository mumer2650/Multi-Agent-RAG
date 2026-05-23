from fastapi import APIRouter

router = APIRouter()

@router.get("/metrics")
async def get_metrics():
    """
    Retrieve evaluation metrics for the RAG system.

    This endpoint will eventually query the local SQLite database populated 
    by the automated evaluation pipeline to fetch the latest RAGAS scores 
    (context precision, faithfulness, etc.).
    """
    return {
        "context_precision": 0.50, 
        "faithfulness": 0.90, 
        "answer_relevance": 0.70, 
        "timestamp": "2026-05-23"
    }
