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

    # Retrieval
    retrieved_docs: list
    reranked_docs: list

    # Retry Logic
    retrieval_attempts: int
    max_retrieval_attempts: int

    # Tool Outputs
    tool_output: Optional[str]

    # Citations
    citations: list

    # Validation
    validation_passed: bool

    # Final
    final_answer: Optional[str]

    # Errors
    error: Optional[str]