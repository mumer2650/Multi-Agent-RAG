from ai_core.llm.ollama_client import llm


def query_rewriter(state):

    query = state["user_query"]

#     system_prompt = """
    
# You are a search query optimizer. 
# Your task is to rewrite the user query to improve retrieval quality from a vector database or search engine.
# If the query is conversational or needs context from the chat history, resolve the context.
# If it's already a good search query (e.g., simple keywords, math equations, or short questions), you MUST keep it exactly as is.
# DO NOT answer the query. For example, if the query is "2+2", do not output "4", output "2+2". Return ONLY the rewritten search query and nothing else. No conversational filler, no explanations.
# """

    system_prompt = """
        You are a search query optimization engine. Your ONLY job is to extract the core keywords from the user's query to improve database retrieval.
        DO NOT answer the user. DO NOT add conversational text like 'Here is the query' or 'I cannot provide'.
        OUTPUT ONLY THE REWRITTEN QUERY STRING.
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