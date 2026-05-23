def validator_agent(state):

    answer = state.get("final_answer")

    if not answer:
        return {
            "validation_passed": False,
            "error": "Empty response generated"
        }

    return {
        "validation_passed": True
    }