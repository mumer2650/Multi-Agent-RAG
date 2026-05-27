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
            if tool_output:
                context += "\n\nTOOL OUTPUT:\n"
                context += str(tool_output)

    else:
        if tool_output:
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
        system_prompt = """
You are an expert, helpful AI assistant.
The user has asked a question, but no relevant information was found in the retrieved company documents or internal database.

INSTRUCTIONS:
1. First, explicitly state that you could not find the answer in the provided documents/database.
2. Then, if the question pertains to general knowledge (e.g., general programming, history, math, or publicly known facts), attempt to answer it directly to the best of your ability.
3. If the question is specific to internal company data, proprietary products, or cannot be answered without the specific context that is missing, politely inform the user that you do not have access to that information.
4. Do NOT hallucinate or invent features, prices, policies, or internal data. When guessing or making general statements, make it clear that you are speaking generally.
5. IMPORTANT: You must ONLY answer in English, regardless of the language the user's question is written in.

Be extremely careful to clearly separate what is general knowledge from what might be a hallucination about the specific company context. Answer clearly and concisely.
"""
        user_prompt = f"Question:\n{user_query}"
        
        try:
            # We already have the original user query in messages, or user_query is the fallback
            prompt_messages = [{"role": "system", "content": system_prompt}]
            
            if messages:
                prompt_messages.extend(messages)
            else:
                prompt_messages.append({"role": "user", "content": f"Question:\n{user_query}"})

            response = llm.invoke(prompt_messages)
            return {
                "final_answer": response.content,
                "chart": None
            }
        except Exception as error:
            return {
                "final_answer": "Error generating answer.",
                "chart": None,
                "error": str(error)
            }

    # =====================================================
    # SYSTEM PROMPT
    # =====================================================

    system_prompt = """
You are an ecommerce AI assistant.

Answer ONLY from provided context.

If SQL results exist:
- summarize products clearly

If retrieved documents exist:
- answer based on the document content
- cite sources by mentioning the document source name and page number
- format citations as [Source: filename, Page: N] at the end of relevant statements

Do not hallucinate. Do not invent information not present in the context.
If the context does not contain enough information, say so clearly.

You are Sage AI, the official assistant for Sage Appliances. 
You will be provided with context from our database or manuals. 
You MUST base your entire answer ONLY on the provided context. 
If the context is empty or does not contain the answer, you must say 'I do not have that information in my database.' 
DO NOT invent product names, prices, or car models.

IMPORTANT: You must ONLY answer in English, regardless of the language the user's question is written in.
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