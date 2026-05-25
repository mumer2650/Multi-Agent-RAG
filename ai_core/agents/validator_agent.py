def validator_agent(state):

    final_answer = state.get("final_answer", "")
    tool_output = state.get("tool_output")

    if not final_answer.strip():
        return {
            "validation_passed": False,
            "validation_reason": "Empty response"
        }

    # GRAPH / SQL queries can succeed without retrieval docs
    if tool_output:
        return {
            "validation_passed": True,
            "validation_reason": None
        }

    retrieved_docs = state.get("retrieved_docs", [])

    if not retrieved_docs:
        return {
            "validation_passed": False,
            "validation_reason": "No supporting documents"
        }

    return {
        "validation_passed": True,
        "validation_reason": None
    }