from ai_core.llm.ollama_client import llm


def answer_generator(state):

    docs = state.get("retrieved_docs", [])

    tool_output = state.get("tool_output", {})

    user_query = state.get("user_query", "")

    messages = state.get("messages", [])[-6:]

    chart = None

    context = ""

    # =====================================================
    # TOOL OUTPUT
    # =====================================================

    if isinstance(tool_output, dict):

        tool_type = tool_output.get("type")

        # =========================================
        # PYTHON RESULT
        # =========================================
        if tool_type == "python_result":

            chart = tool_output.get("chart")

            analysis = tool_output.get("analysis", [])

            context += "\n\nPYTHON ANALYSIS:\n"

            context += str(analysis)

        # =========================================
        # SQL RESULT
        # =========================================
        elif tool_type == "sql_result":

            sql_data = tool_output.get("data", [])
            sql_action = tool_output.get("action", "")

            # Guard: empty SQL results should NOT go to LLM
            if not sql_data or (isinstance(sql_data, list) and len(sql_data) == 0):

                return {
                    "final_answer": (
                        "No matching products were found in the database "
                        "for your query. Please try a different search "
                        "term or category."
                    ),
                    "chart": None
                }

            context += "\n\nSQL RESULTS:\n"

            context += str(sql_data)

        # =========================================
        # GENERIC TOOL OUTPUT
        # =========================================
        else:

            context += "\n\nTOOL OUTPUT:\n"

            context += str(tool_output)

    else:

        context += "\n\nTOOL OUTPUT:\n"

        context += str(tool_output)

    # =====================================================
    # RETRIEVAL FLOW
    # =====================================================

    for index, doc in enumerate(docs[:3]):

        if not isinstance(doc, dict):
            continue

        source = doc.get('source', 'unknown')
        page = doc.get('page', 'N/A')

        context += (
            f"\n\nDocument {index + 1}"
            f" [Source: {source}, Page: {page}]"
            f"\nContent:\n{doc.get('text', '')}"
        )

    # =====================================================
    # EMPTY CHECK
    # =====================================================

    if not context.strip():

        return {
            "final_answer": (
                "The provided documents do not "
                "contain enough relevant information."
            ),
            "chart": None
        }

    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    system_prompt = """
You are an ecommerce AI assistant.

Answer ONLY from provided context.

If SQL results exist:
- summarize products clearly

If Python analysis exists:
- explain insights clearly

If retrieved documents exist:
- answer based on the document content
- cite sources by mentioning the document source name and page number
- format citations as [Source: filename, Page: N] at the end of relevant statements

Do not hallucinate. Do not invent information not present in the context.
If the context does not contain enough information, say so clearly.
"""

    user_prompt = f"""
Question:
{user_query}

Context:
{context}
"""

    # =====================================================
    # LLM CALL
    # =====================================================

    try:

        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            *messages,
            {"role": "user", "content": user_prompt}
        ])

        final_answer = response.content

    except Exception as error:

        return {
            "final_answer": "Error generating answer.",
            "chart": chart,
            "error": str(error)
        }

    # =====================================================
    # FINAL RETURN
    # =====================================================

    return {
        "final_answer": final_answer,
        "chart": chart
    }