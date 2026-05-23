from ai_core.llm.ollama_client import llm


def query_rewriter(state):

    query = state["user_query"]

    system_prompt = """
    Rewrite the user query
    to improve retrieval quality.
    """

    response = llm.invoke([
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": query
        }
    ])

    return {
        "user_query": response.content,
        "retrieval_attempts":
            state["retrieval_attempts"] + 1
    }