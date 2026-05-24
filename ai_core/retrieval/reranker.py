from sentence_transformers import (CrossEncoder)

reranker_model = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

def rerank_documents(query: str, documents: list, top_k: int = 5):
    if not documents:
        return []

    try:
        pairs = [(query, doc["text"]) for doc in documents]

        scores = reranker_model.predict(pairs)

        scored_docs = []

        for doc, score in zip(documents,scores):
            doc["rerank_score"] = float(score)
            scored_docs.append(doc)

        scored_docs.sort(
            key=lambda x: x["rerank_score"],
            reverse=True
        )

        return scored_docs[:top_k]

    except Exception:
        return documents[:top_k]