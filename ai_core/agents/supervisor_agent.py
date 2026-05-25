from ai_core.llm.ollama_client import llm

# SUPERVISOR AGENT

def supervisor_agent(state):
    query = state["user_query"]

    system_prompt = """
    You are a supervisor agent.

    Your task is to decide which specialized
    agent should handle the user's query.

    Available agents:

    1. retrieval
       Use for:
       - product information
       - ecommerce product features
       - specifications
       - manuals
       - FAQs
       - knowledge retrieval
       - document question answering

    2. sql
       Use for:
       - inventory queries
       - shipment tracking
       - order analytics
       - database operations
       - structured business data

    3. python
       Use for:
       - calculations
       - mathematical analysis
       - comparisons
       - numerical reasoning
       - data analysis

    IMPORTANT:
    Return ONLY ONE WORD.

    Allowed outputs:
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

        selected_agent = (response.content.strip().lower())

        print("\n========== SUPERVISOR ==========")
        print("Query:", query)
        print("Selected Agent:", selected_agent)
        print("================================\n")

        # SAFETY VALIDATION

        allowed_agents = ["retrieval", "sql", "python"]

        if selected_agent not in allowed_agents:

            print("[SUPERVISOR WARNING] Invalid agent returned.")

            selected_agent = "retrieval"

        return {

            "selected_agent": selected_agent,
            "tool_required": (
                selected_agent != "retrieval"
            )
        }

    except Exception as error:
        print(
            "[SUPERVISOR ERROR]",str(error))

        # SAFE FALLBACK
        return {

            "selected_agent": "retrieval",

            "tool_required": False,

            "error": str(error)
        }