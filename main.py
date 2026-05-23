from ai_core.graph.workflow import graph


def run_chat():

    state = {
        "messages": [],

        "user_query": "",

        "selected_agent": None,

        "tool_required": False,

        "retrieved_docs": [],

        "reranked_docs": [],

        "retrieval_attempts": 0,

        "max_retrieval_attempts": 3,

        "tool_output": None,

        "citations": [],

        "validation_passed": False,

        "final_answer": None,

        "error": None
    }

    print("Multi-Agent RAG Started")
    print("Type exit to quit\n")

    while True:

        query = input("You: ")

        if query.lower() == "exit":
            break

        state["user_query"] = query

        result = graph.invoke(state)

        state.update(result)

        print("\nAssistant:")
        print(state["final_answer"])

        if state["citations"]:

            print("\nSources:")

            for citation in state["citations"]:
                print(citation)

        print()


if __name__ == "__main__":
    run_chat()