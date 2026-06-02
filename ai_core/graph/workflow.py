from langgraph.graph import StateGraph, START, END

from ai_core.graph.states import GraphState
from ai_core.graph.conditions import (
    route_agent,
    check_context,
    validation_condition
)

from ai_core.agents.supervisor_agent import supervisor_agent
from ai_core.agents.retrieval_agent import retrieval_agent
from ai_core.agents.sql_agent import sql_agent
from ai_core.agents.python_agent import python_agent
from ai_core.retrieval.query_rewriter import query_rewriter
from ai_core.agents.answer_generator import answer_generator
from ai_core.agents.citation_builder import citation_builder
from ai_core.agents.validator_agent import validator_agent

print("Workflow Started")

graph_builder = StateGraph(GraphState)

# =========================
# NODES (Python agent removed)
# =========================
graph_builder.add_node("supervisor", supervisor_agent)
graph_builder.add_node("retrieval_agent", retrieval_agent)
graph_builder.add_node("sql_agent", sql_agent)
graph_builder.add_node("python_agent", python_agent)
graph_builder.add_node("query_rewriter", query_rewriter)
graph_builder.add_node("answer_generator", answer_generator)
graph_builder.add_node("citation_builder", citation_builder)
graph_builder.add_node("validator", validator_agent)

# =========================
# ENTRY
# =========================
graph_builder.add_edge(START, "supervisor")

# =========================
# SUPERVISOR ROUTING
# =========================
graph_builder.add_conditional_edges(
    "supervisor",
    route_agent,
    {
        "retrieval": "retrieval_agent",
        "sql": "sql_agent",
        "python": "python_agent",
        "answer": "answer_generator"
    }
)

# =========================
# RETRIEVAL FLOW
# =========================
graph_builder.add_conditional_edges(
    "retrieval_agent",
    check_context,
    {
        "rewrite": "query_rewriter",
        "fail": END,
        "enough": "answer_generator"
    }
)

graph_builder.add_edge("query_rewriter", "retrieval_agent")

# =========================
# 🔥 SQL → SMART ROUTING & RETRY LOOP
# =========================
def sql_router(state):
    attempts = state.get("sql_attempts", 0)
    max_attempts = state.get("max_sql_attempts", 3)
    last_error = state.get("last_sql_error")
    tool_output = state.get("tool_output") or {}

    # SCENARIO 1: SQL Syntax Error -> Trigger Retry Loop
    if last_error:
        if attempts < max_attempts:
            print(f"🔄 Retrying SQL generation (Attempt {attempts + 1} of {max_attempts})...")
            return "retry_sql"
        else:
            print("⚠️ Max SQL retries reached. Falling back to Retrieval Agent...")
            return "retrieval"

    # SCENARIO 2: Valid SQL, but 0 products found -> Fallback to Retrieval
    if isinstance(tool_output, dict) and tool_output.get("action") == "empty":
        print("⚠️ SQL executed successfully but returned 0 results. Falling back to Retrieval Agent...")
        return "retrieval"

    # SCENARIO 3: Valid SQL and Data Found -> Move to Answer Generator
    return "answer"

graph_builder.add_conditional_edges(
    "sql_agent",
    sql_router,
    {
        "retry_sql": "sql_agent",        # Loops back to itself!
        "retrieval": "retrieval_agent",  # The Safety Net fallback
        "answer": "answer_generator"
    }
)

# =========================
# PYTHON AGENT → ANSWER GENERATOR
# =========================
graph_builder.add_edge("python_agent", "answer_generator")

# =========================
# FINAL PIPELINE
# =========================
graph_builder.add_edge("answer_generator", "citation_builder")
graph_builder.add_edge("citation_builder", "validator")

graph_builder.add_conditional_edges(
    "validator",
    validation_condition,
    {
        "pass": END,
        "fail": END
    }
)

# =========================
# COMPILE
# =========================
graph = graph_builder.compile()

print("Workflow Ended")