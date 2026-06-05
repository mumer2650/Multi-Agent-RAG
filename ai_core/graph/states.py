from typing import Annotated, TypedDict, Optional
from langgraph.graph import add_messages


class GraphState(TypedDict):

    # Conversation
    messages: Annotated[list, add_messages]

    # Query
    user_query: str

    # Routing
    selected_agent: Optional[str]
    tool_required: bool
    competitor_detected: bool
    off_topic: bool
    sql_failed_try_retrieval: bool
    category: Optional[str]  # Product category extracted by supervisor (air_conditioners, etc)

    # Retrieval
    retrieved_docs: list
    retrieval_error: str | None

    # Retry Logic (Retrieval)
    retrieval_attempts: int
    max_retrieval_attempts: int

    # Retry Logic (SQL) - NEW FIELDS
    sql_attempts: int
    max_sql_attempts: int
    last_sql_error: str | None
    generated_sql: str | None

    # Tool Outputs
    tool_output: Optional[dict]  # Changed to dict since we output {"type": "sql_result", "action": "...", "data": []}

    # Citations
    citations: list

    # Validation
    validation_passed: bool
    validation_reason: str | None

    # Visualization
    chart: Optional[dict]

    # Final
    final_answer: Optional[str]

    # Errors
    error: Optional[str]