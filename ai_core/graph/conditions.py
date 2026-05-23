def route_agent(state):

    return state["selected_agent"]


def check_context(state):

    docs = state.get("reranked_docs", [])

    if len(docs) == 0:

        if (state["retrieval_attempts"] < state["max_retrieval_attempts"]
        ):
            return "rewrite"

        return "fail"

    return "enough"


def validation_condition(state):

    if state["validation_passed"]:
        return "pass"

    return "fail"