from ai_core.llm.ollama_client import llm

def answer_generator(state):

    #Retrieved Context
    
    docs = state.get("reranked_docs", [])

    tool_output = state.get("tool_output")

    user_query = state.get("user_query", "")

    
    # CONVERSATION MEMORY
    messages = state.get("messages",[])

    context = ""

    
    # BUILD DOCUMENT CONTEXT

    for index, doc in enumerate(docs):

        doc_text = doc.get("text","")

        context += (f"\n\nDocument {index + 1}:\n {doc_text}")

    # TOOL OUTPUT
    if tool_output:
        context += (f"\n\nTool Output:\n {tool_output}")


    # EMPTY CONTEXT FALLBACK
    
    if not context.strip():
        return {
            "final_answer": (
                "I could not find enough "
                "information to answer "
                "the question accurately."
            )
        }

    
    # SYSTEM PROMPT
    
    system_prompt = """
    You are a highly accurate AI assistant.

    Your task is to answer the user's question
    using ONLY the provided retrieved context.

    You may use previous conversation history
    ONLY for conversational continuity.

    RULES:

    1. Do NOT hallucinate.

    2. Do NOT invent facts.

    3. If information is missing,
       clearly say:
       "The provided context does not contain enough information."

    4. Use concise and professional responses.

    5. Prefer factual grounded answers.

    6. If tool output is provided,
       prioritize it carefully.

    7. Never invent product specifications,
       prices, ratings, or features.

    8. NEVER answer from your own knowledge
       if retrieval context is missing.
    """

    # USER PROMPT
    user_prompt = f"""
    User Question:
    {user_query}

    Retrieved Context:
    {context}
    """


    # LLM INVOCATION
    try:

        response = llm.invoke([

            {
                "role": "system",

                "content": system_prompt
            },

            
            # CONVERSATION MEMORY
            *messages,

            # FINAL TASK
            {
                "role": "user",

                "content": user_prompt
            }
        ])

        generated_answer = response.content

    except Exception as error:

        return {

            "final_answer": ("An error occurred while generating the answer."),
            "generation_error": str(error)
        }

    # CITATIONS
    citations = state.get("citations",[])

    citation_text = ""

    if citations:
        citation_text += "\n\nSources:\n"
        for citation in citations:

            source = citation.get("source", "unknown")

            page = citation.get("page", 0)

            citation_text += (f"- {source} (Page {page})\n")

    
    # FINAL ANSWER

    final_answer = (
        generated_answer + citation_text
    )

    return {

        "final_answer": final_answer
    }