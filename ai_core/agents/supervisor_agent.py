from ai_core.llm.ollama_client import llm
import re


def supervisor_agent(state):

    query = state["user_query"].lower()

    # ==========================================
    # FALLBACK TO LLM FOR ROUTING
    # ==========================================

    system_prompt = """
    You are an intelligent supervisor routing system for an electronics ecommerce AI.
    Evaluate the user's query and decide the best agent to handle it.

    Routing logic:
    - Use 'sql' for any query asking for product recommendations, lists of products, querying by price/budget, technical specifications, reviews, energy efficiency, top rated items, or comparing products based on features. (e.g. "I want to buy an AC under 100000", "Top rated TVs", "Spec comparisons").
    - Use 'retrieval' ONLY for questions specifically asking for information from user manuals, troubleshooting guides, warranty policies, or how-to descriptions (e.g. "How do I clean the filter?", "What does error code E1 mean?").
    - Use 'python' for pure math calculations, generating graphs/plots/charts, or data visualizations (e.g. "Calculate EMI for 6 months", "Plot a graph of TV prices").
    - Use 'answer' for general conversational pleasantries, simple greetings, or basic inquiries that are general knowledge and clearly do not require company data (e.g. "Hello", "How are you?", "What is 2+2?").

    Return ONLY ONE WORD from the choices below, with no punctuation or extra text:
    retrieval
    sql
    python
    answer
    """

    try:

        response = llm.invoke([
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": str(state["user_query"])
            }
        ])

        raw = response.content.lower().strip()

        match = re.search(
            r"(retrieval|sql|python|answer)",
            raw
        )

        selected = (
            match.group(1)
            if match
            else "retrieval"
        )

        return {
            "selected_agent": selected,
            "tool_required": (
                selected not in ["retrieval", "answer"]
            )
        }

    except Exception as error:

        return {
            "selected_agent": "retrieval",
            "tool_required": False,
            "error": str(error)
        }
