from ai_core.graph.workflow import graph

def run_chat():


    # GLOBAL CONVERSATION STATE

    state = {

        # Conversation Memory
        "messages": [],

        # User Query
        "user_query": "",

        # Routing
        "selected_agent": None,

        "tool_required": False,

        # Retrieval
        "retrieved_docs": [],

        "reranked_docs": [],

        "retrieval_attempts": 0,

        "max_retrieval_attempts": 3,

        # Tools
        "tool_output": None,

        # Citations
        "citations": [],

        # Validation
        "validation_passed": False,

        # Final Response
        "final_answer": None,

        # Errors
        "error": None
    }

    print("Multi-Agent RAG Started")

    print("Type exit to quit\n")

    while True:
        query = input("You: ")

        if query.lower() == "exit":
            break

        
        # SAVE USER MESSAGE TO MEMORY
    
        state["messages"].append({
            "role": "user",
            "content": query
        })

        
        # UPDATE CURRENT QUERY
        state["user_query"] = query

        
        # RESET REQUEST-SCOPED VARIABLES
        # IMPORTANT: Do NOT reset messages

        state["retrieval_attempts"] = 0

        state["retrieved_docs"] = []

        state["reranked_docs"] = []

        state["tool_output"] = None

        state["citations"] = []

        state["validation_passed"] = False

        state["final_answer"] = None

        state["error"] = None

        
        # RUN GRAPH
        result = graph.invoke(state)

        
        # UPDATE STATE
        state.update(result)


        # SAVE ASSISTANT RESPONSE TO MEMORY
        if state.get("final_answer"):
            state["messages"].append({
                "role": "assistant",
                "content": state["final_answer"]
            })

        
        # PRINT RESPONSE
        print("\nAssistant:")

        print(state["final_answer"])

        
        # PRINT SOURCES
        if state["citations"]:

            print("\nSources:")

            for citation in state["citations"]:

                print(citation)

        print()


if __name__ == "__main__":

    run_chat()