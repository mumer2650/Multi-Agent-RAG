def route_agent(state):

    return state["selected_agent"]


def check_context(state):
    docs = state.get("retrieved_docs",[])

    attempts = state.get("retrieval_attempts", 0)

    max_attempts = state.get("max_retrieval_attempts", 3)

    print(f"Docs: {len(docs)} | Attempts: {attempts}/{max_attempts}")

    if len(docs) == 0:

        if attempts >= max_attempts:

            return "enough"

        return "rewrite"

    return "enough"

def validation_condition(state):

    if state["validation_passed"]:
        return "pass"

    return "fail"