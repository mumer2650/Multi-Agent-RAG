def validator_agent(state):
    final_answer = state.get("final_answer", "")

    reranked_docs = state.get("reranked_docs", [])

    if not final_answer.strip():
        return {
            "validation_passed": False,
            "validation_reason": "Empty response"
        }

    if not reranked_docs:
        return {
            "validation_passed": False,
            "validation_reason": "No supporting documents"
        }

    return {
        "validation_passed": True,
        "validation_reason": None
    }