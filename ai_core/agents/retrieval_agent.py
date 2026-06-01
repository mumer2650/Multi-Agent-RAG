from ai_core.retrieval.search_engine import (advanced_search)

def retrieval_agent(state):

    query = state["user_query"]

    retrieval_attempts = state.get("retrieval_attempts",0)

    try:

        retrieved_docs = advanced_search(query=query, k=5)
        
        print("Retrieved Docs:", len(retrieved_docs))

        return {

            "retrieved_docs": retrieved_docs,
            "retrieval_attempts":retrieval_attempts + 1
        }

    except Exception as error:

        return {

            "retrieved_docs": [],
            "retrieval_error": str(error),
            "retrieval_attempts": retrieval_attempts + 1
        }