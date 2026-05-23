def citation_builder(state):

    docs = state.get("reranked_docs", [])

    citations = []

    for idx, doc in enumerate(docs):

        citation = {
            "id": idx + 1,
            "source": "placeholder_source"
        }

        citations.append(citation)

    return {
        "citations": citations
    }