from ai_core.graph.workflow import graph
import matplotlib.pyplot as plt


# ==========================================
# CHART RENDERER
# ==========================================
def render_chart(chart):

    if not chart:
        print("[CHART] No chart data found.")
        return

    chart_type = chart.get("chartType")
    data = chart.get("data", [])
    meta = chart.get("meta", {})

    if not data:
        print("[CHART] Empty chart data.")
        return

    plt.figure(figsize=(12, 6))

    # ==========================================
    # BAR CHART
    # ==========================================
    if chart_type == "bar":

        x = [d.get("model", "Unknown") for d in data]

        # AUTO DETECT VALUE KEY
        possible_keys = [
            "price",
            "efficiency_score",
            "emi_12m"
        ]

        value_key = None

        for key in possible_keys:
            if key in data[0]:
                value_key = key
                break

        if not value_key:
            print("[CHART ERROR] Could not detect y-axis key.")
            return

        y = [d.get(value_key, 0) for d in data]

        plt.bar(x, y)

        plt.ylabel(value_key.replace("_", " ").title())

        plt.xticks(rotation=25)

    # ==========================================
    # LINE CHART
    # ==========================================
    elif chart_type == "line":

        x = list(range(len(data)))

        value_key = list(data[0].keys())[-1]

        y = [d.get(value_key, 0) for d in data]

        plt.plot(x, y)

        plt.ylabel(value_key.replace("_", " ").title())

    else:
        print(f"[CHART ERROR] Unsupported chart type: {chart_type}")
        return

    # ==========================================
    # TITLES
    # ==========================================
    plt.title(meta.get("title", "Chart"))

    plt.xlabel("Products")

    plt.tight_layout()

    plt.show()


# ==========================================
# MAIN CHAT LOOP
# ==========================================
def run_chat():

    state = {

        # Conversation
        "messages": [],

        # User Query
        "user_query": "",

        # Routing
        "selected_agent": None,

        "tool_required": False,

        # Retrieval
        "retrieved_docs": [],

        "retrieval_attempts": 0,

        "max_retrieval_attempts": 3,

        # Tools
        "tool_output": None,

        # Visualization
        "chart": None,

        # Validation
        "validation_passed": False,

        # Output
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

        # ==========================================
        # SAVE USER MESSAGE
        # ==========================================
        state["messages"].append({
            "role": "user",
            "content": query
        })

        # ==========================================
        # UPDATE QUERY
        # ==========================================
        state["user_query"] = query

        # ==========================================
        # RESET REQUEST STATE
        # ==========================================
        state["retrieved_docs"] = []

        state["retrieval_attempts"] = 0

        state["tool_output"] = None

        state["chart"] = None

        state["citations"] = []

        state["validation_passed"] = False

        state["final_answer"] = None

        state["error"] = None

        # ==========================================
        # RUN WORKFLOW
        # ==========================================
        try:

            result = graph.invoke(state)

            state.update(result)

        except Exception as workflow_error:

            print("\n[WORKFLOW ERROR]")
            print(str(workflow_error))
            continue

        # ==========================================
        # DEBUGGING OUTPUT
        # ==========================================
        if state.get("tool_output"):

            print("\n[DEBUG TOOL OUTPUT]")
            print(state["tool_output"])

        if state.get("chart"):

            print("\n[DEBUG CHART FOUND]")
            print(state["chart"])

        # ==========================================
        # RENDER CHART
        # ==========================================
        if state.get("chart"):

            print("\n📊 Rendering Chart...")

            try:
                render_chart(state["chart"])

            except Exception as chart_error:

                print("\n[CHART RENDER ERROR]")
                print(str(chart_error))

        # ==========================================
        # SAVE ASSISTANT MESSAGE
        # ==========================================
        if state.get("final_answer"):

            state["messages"].append({
                "role": "assistant",
                "content": state["final_answer"]
            })

        # ==========================================
        # PRINT RESPONSE
        # ==========================================
        print("\nAssistant:")

        print(state.get("final_answer", "No response generated."))

        # ==========================================
        # PRINT CITATIONS
        # ==========================================
        citations = state.get("citations", [])

        if citations:

            print("\n" + "─" * 50)
            print("📚 Citations:")
            print("─" * 50)

            for cite in citations:

                cite_type = cite.get("type", "unknown")

                if cite_type == "retrieval":

                    source = cite.get("source", "unknown")
                    page = cite.get("page", "N/A")
                    snippet = cite.get("snippet", "")
                    score = cite.get("relevance_score")

                    print(f"\n  [{cite.get('index', '?')}] 📄 {source} (Page {page})")

                    if score is not None:
                        print(f"      Relevance: {score:.4f}")

                    if snippet:
                        print(f"      \"{snippet}\"")

                elif cite_type == "database":

                    source = cite.get("source", "unknown")
                    count = cite.get("record_count", 0)

                    print(f"\n  🗃️  {source} ({count} records)")

                elif cite_type == "analysis":

                    print(f"\n  📊 {cite.get('source', 'Python Analysis')}")

            print("\n" + "─" * 50)

        print()


if __name__ == "__main__":

    run_chat()