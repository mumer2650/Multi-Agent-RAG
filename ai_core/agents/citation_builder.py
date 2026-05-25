def citation_builder(state):

    retrieved_docs = state.get("retrieved_docs", [])
    tool_output = state.get("tool_output", {})

    citations = []
    seen = set()

    # =====================================================
    # RETRIEVAL-BASED CITATIONS
    # =====================================================

    for index, doc in enumerate(retrieved_docs):

        if not isinstance(doc, dict):
            continue

        source = doc.get("source", "unknown")
        page = doc.get("page", 0)
        text = doc.get("text", "")
        score = doc.get("score", None)
        key = (source, page)

        if key in seen:
            continue

        seen.add(key)

        # Build a short snippet for display
        snippet = text[:150].strip()
        if len(text) > 150:
            snippet += "..."

        citation_entry = {
            "type": "retrieval",
            "index": index + 1,
            "source": source,
            "page": page,
            "snippet": snippet,
        }

        if score is not None:
            citation_entry["relevance_score"] = round(score, 4)

        citations.append(citation_entry)

    # =====================================================
    # TOOL-BASED CITATIONS
    # =====================================================

    if isinstance(tool_output, dict) and tool_output.get("type"):

        tool_type = tool_output.get("type")
        action = tool_output.get("action", "unknown")

        # SQL query results
        if tool_type == "sql_result":

            data = tool_output.get("data", [])
            source = f"Database Query - {action}"
            key = (source, 0)

            if key not in seen:
                seen.add(key)
                citations.append({
                    "type": "database",
                    "source": source,
                    "page": 0,
                    "record_count": len(data) if isinstance(data, list) else 0,
                })

        # Python analysis results
        elif tool_type == "python_result":

            source = "Python Analysis"
            key = (source, 0)

            if key not in seen:
                seen.add(key)
                citations.append({
                    "type": "analysis",
                    "source": source,
                    "page": 0,
                })

    return {"citations": citations}
