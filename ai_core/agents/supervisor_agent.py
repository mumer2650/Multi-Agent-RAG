from ai_core.llm.ollama_client import llm
import re


def supervisor_agent(state):

    query = state["user_query"].lower()

    # ==========================================
    # FORCE RULES (MOST IMPORTANT)
    # ==========================================

    graph_keywords = [
        "graph",
        "plot",
        "chart",
        "visualize",
        "comparison",
        "compare"
    ]

    math_keywords = [
        "calculate",
        "emi",
        "interest",
        "formula",
        "equation",
        "percentage",
        "discount math"
    ]

    sql_keywords = [
        "list",
        "show",
        "display",
        "top rated",
        "under",
        "price",
        "products",
        "tv",
        "air conditioner",
        "refrigerator",
        "washing machine",
        "buds"
    ]

    # ==========================================
    # GRAPH QUERIES
    # MUST GO SQL → PYTHON
    # ==========================================

    if any(word in query for word in graph_keywords):

        return {
            "selected_agent": "sql",
            "tool_required": True
        }

    # ==========================================
    # PURE MATH QUERIES
    # ==========================================

    if any(word in query for word in math_keywords):

        return {
            "selected_agent": "python",
            "tool_required": True
        }

    # ==========================================
    # SQL QUERIES
    # ==========================================

    if any(word in query for word in sql_keywords):

        return {
            "selected_agent": "sql",
            "tool_required": True
        }

    # ==========================================
    # FALLBACK TO LLM
    # ==========================================

    system_prompt = """
    You are a routing system.

    Return ONLY one word:
    retrieval
    sql
    python
    """

    try:

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

        raw = response.content.lower()

        match = re.search(
            r"(retrieval|sql|python)",
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
                selected != "retrieval"
            )
        }

    except Exception as error:

        return {
            "selected_agent": "retrieval",
            "tool_required": False,
            "error": str(error)
        }