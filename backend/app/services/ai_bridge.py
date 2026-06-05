import sys
import os
import asyncio
import json
import logging
from ai_core.graph.workflow import graph
from backend.app.schemas.chat import StreamResponse


# ==========================================
# SETUP LOGGING
# ==========================================
logger = logging.getLogger(__name__)


# ==========================================
# PATH SETUP
# ==========================================
# The ai_core module lives at the project root, one level above backend/
# We need to add the project root to sys.path so Python can find it
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ==========================================
# FRIENDLY NODE LABELS
# ==========================================
NODE_LABELS = {
    "supervisor":       "🧠 Routing your query...",
    "retrieval_agent":  "📚 Searching knowledge base...",
    "sql_agent":        "🗃️ Querying product database...",
    "python_agent":     "🐍 Running analysis...",
    "query_rewriter":   "✏️ Refining search query...",
    "answer_generator": "💡 Generating answer...",
    "citation_builder": "📎 Building citations...",
    "validator":        "✅ Validating response...",
}


# ==========================================
# INITIALIZE GRAPH STATE TEMPLATE
# ==========================================
def create_initial_state(query: str, history: list = None):
    """Create the initial state for the LangGraph pipeline."""
    if history is None:
        history = []

    return {
        "messages":               history + [{"role": "user", "content": query}],
        "user_query":             query,
        "selected_agent":         None,
        "tool_required":          False,
        
        "retrieved_docs":         [],
        "retrieval_error":        None,
        "retrieval_attempts":     0,
        "max_retrieval_attempts": 3,
        
        "sql_attempts":           0,
        "max_sql_attempts":       3,
        "last_sql_error":         None,
        "generated_sql":          None,
        
        "tool_output":            None,
        "chart":                  None,
        "citations":              [],
        "validation_passed":      False,
        "validation_reason":      None,
        "final_answer":           None,
        "error":                  None,
    }


# ==========================================
# MAIN PIPELINE RUNNER
# ==========================================
async def run_pipeline(query: str, history: list = None):
    """
    Async generator that runs the LangGraph multi-agent pipeline
    and yields StreamResponse objects for each step.

    Args:
        query: User query string
        history: Previous conversation messages (list of dicts with "role" and "content")

    Yields:
        StreamResponse with type:
            - "status"    : Agent status updates (which node is running)
            - "token"     : Word-by-word streamed final answer
            - "citations" : Citation data (content = JSON string)
            - "chart"     : Chart data (content = JSON string)
            - "done"      : Signals end of response
            - "error"     : Any pipeline errors
    """
    if history is None:
        history = []

    logger.info(f"Starting pipeline for query: {query[:50]}...")

    # ==========================================
    # BUILD INITIAL STATE
    # ==========================================
    state = create_initial_state(query, history)
    final_state = {**state}

    # ==========================================
    # STREAM THROUGH GRAPH NODES
    # ==========================================
    try:
        # Use astream directly to match main.py's output exactly
        logger.debug("Using graph.astream()")
        async for event in graph.astream(state):
            try:
                for node_name, node_output in event.items():
                    # Send EXACT string from backend terminal
                    label = f"➔ [{node_name}] executed"
                    yield StreamResponse(type="status", content=label)

                    # Merge node output into our tracked final state
                    if isinstance(node_output, dict):
                        final_state.update(node_output)
            except Exception as e:
                logger.warning(f"Error processing node event: {e}")
                continue

        logger.info("Graph streaming completed successfully")

    except Exception as e:
        error_msg = f"Pipeline execution error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        yield StreamResponse(type="error", content=error_msg)
        return

    # ==========================================
    # STREAM FINAL ANSWER (word-by-word)
    # ==========================================
    answer = final_state.get("final_answer") or "No response generated."
    logger.debug(f"Final answer: {answer[:100]}...")

    words = answer.split(" ")
    for i, word in enumerate(words):
        try:
            content = word + " " if i < len(words) - 1 else word
            yield StreamResponse(type="token", content=content)
            await asyncio.sleep(0.02)
        except Exception as e:
            logger.warning(f"Error streaming token: {e}")
            continue

    # ==========================================
    # SEND CONTEXT FOR EVALUATOR
    # ==========================================
    collected_context = ""
    docs = final_state.get("retrieved_docs", [])
    if docs:
        # Docs could be dicts or Langchain Document objects
        collected_context += "\n".join([doc.get("page_content", "") if isinstance(doc, dict) else getattr(doc, "page_content", str(doc)) for doc in docs]) + "\n"
    
    sql_data = final_state.get("sql_data", [])
    if sql_data:
        collected_context += json.dumps(sql_data) + "\n"

    if collected_context:
        try:
            yield StreamResponse(type="context", content=collected_context)
            logger.debug("Sent context data for background evaluator")
        except Exception as e:
            logger.warning(f"Error streaming context: {e}")

    # ==========================================
    # SEND CITATIONS
    # ==========================================
    citations = final_state.get("citations", [])
    if citations:
        try:
            yield StreamResponse(
                type="citations",
                content=json.dumps(citations)
            )
            logger.debug(f"Sent {len(citations)} citations")
        except Exception as e:
            logger.warning(f"Error serializing citations: {e}")

    # ==========================================
    # SEND CHART DATA
    # ==========================================
    chart = final_state.get("chart")
    if chart:
        try:
            yield StreamResponse(
                type="chart",
                content=json.dumps(chart)
            )
            logger.debug("Sent chart data")
        except Exception as e:
            logger.warning(f"Error serializing chart: {e}")

    # ==========================================
    # SEND DONE SIGNAL
    # ==========================================
    yield StreamResponse(type="done", content="")
    logger.info("Pipeline completed and response streamed")
