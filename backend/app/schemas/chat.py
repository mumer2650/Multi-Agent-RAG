from pydantic import BaseModel

class ChatRequest(BaseModel):
    """
    Schema for incoming chat requests from the frontend.
    
    Integration Note: In the final LangGraph pipeline, the `query` string received 
    here will be injected into the initial state of the graph (e.g., as the 'messages' 
    list or a dedicated 'user_input' state field) to kick off the multi-agent orchestration.
    """
    query: str

class StreamResponse(BaseModel):
    """
    Schema for streaming responses back to the frontend over WebSockets.
    
    Fields:
        type (str): Categorizes the payload. Examples:
                    - 'status': Used to broadcast which LangGraph node or agent is currently active.
                    - 'token': A chunk of the final generated text being streamed to the user.
                    - 'error': Any exception caught during the graph execution.
        content (str): The actual message, token, or error detail.
        
    Integration Note: As LangGraph processes the query and transitions between nodes 
    (e.g., from the router agent to the retrieval agent), we will yield 
    `StreamResponse(type="status", content="...")`. When the final generation node 
    starts producing output via an LLM, we will stream the text chunks by yielding 
    `StreamResponse(type="token", content="chunk")`.
    """
    type: str
    content: str
