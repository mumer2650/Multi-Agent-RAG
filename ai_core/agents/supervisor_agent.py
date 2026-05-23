from typing import Literal
from pydantic import BaseModel, Field

from ai_core.llm.ollama_client import llm


class SupervisorDecision(BaseModel):

    selected_agent: Literal[
        "retrieval",
        "sql",
        "python"
    ]

    tool_required: bool = Field(
        description="Whether external tool execution is required"
    )

supervisor_llm = llm.with_structured_output(SupervisorDecision)


def supervisor_agent(state):

    query = state["user_query"]

    system_prompt = """
    You are a supervisor agent.

    Decide which specialized agent
    should handle the query.

    Rules:
    1. retrieval
       - factual questions
       - document QA
       - knowledge retrieval

    2. sql
       - databases
       - logs
       - structured querying

    3. python
       - calculations
       - code execution
       - analysis
       - math

    Return structured output only.
    """

    result = supervisor_llm.invoke([
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": query
        }
    ])

    return {
        "selected_agent": result.selected_agent,
        "tool_required": result.tool_required
    }