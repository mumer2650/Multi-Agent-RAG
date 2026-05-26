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
# NODES
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
# 🔥 SQL → SMART ROUTING
# =========================
def sql_router(state):
    query = state.get("user_query", "").lower()

    # GRAPH / VISUALIZATION CASE
    if any(word in query for word in ["graph", "plot", "chart", "visualize", "compare"]):
        return "python"

    return "answer"

graph_builder.add_conditional_edges(
    "sql_agent",
    sql_router,
    {
        "python": "python_agent",
        "answer": "answer_generator"
    }
)


# =========================
# PYTHON FLOW
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