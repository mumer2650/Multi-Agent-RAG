def citation_builder(state):

    reranked_docs = state.get("reranked_docs",[])
    citations = []
    seen = set()

    for doc in reranked_docs:
        source = doc.get("source", "unknown")

        page = doc.get("page", 0)

        citation_key = (source, page)

        if citation_key in seen:
            continue

        seen.add(citation_key)

        citations.append({"source": source, "page": page})

    return {"citations": citations}