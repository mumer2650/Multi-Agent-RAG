import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from app.schemas.chat import ChatRequest, StreamResponse

router = APIRouter()

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat communication.
    
    This endpoint maintains an open connection with the client. It waits for a JSON
    payload matching the `ChatRequest` schema. Once received, it mocks the behavior 
    of a complex LangGraph multi-agent pipeline by sending status updates and streaming
    a text response word-by-word.
    
    Future LangGraph Integration:
        Instead of the mock loop, this endpoint will eventually:
        1. Parse the incoming request into a ChatRequest.
        2. Instantiate or retrieve the compiled LangGraph workflow.
        3. Iterate asynchronously over the graph's streaming output 
           (e.g., `async for event in app.astream_events(...)`).
        4. Map LangGraph events to `StreamResponse` payloads and send them to the client.
    """
    await websocket.accept()
    
    try:
        while True:
            # Wait to receive a JSON payload from the client
            data = await websocket.receive_text()
            
            try:
                # Validate the incoming data against our schema
                request_data = json.loads(data)
                chat_request = ChatRequest(**request_data)
            except (json.JSONDecodeError, ValidationError) as e:
                # Handle invalid formatting gracefully
                error_resp = StreamResponse(type="error", content=f"Invalid request format: {str(e)}")
                await websocket.send_json(error_resp.model_dump())
                continue

            # =================================================================
            # MOCK MULTI-AGENT PIPELINE
            # =================================================================
            # The following loop simulates the behavior of the LangGraph orchestrator
            # transitioning between different specialized agents.
            
            # Step 1: Simulate the Routing Agent deciding where to send the query
            status_routing = StreamResponse(type="status", content="Agent routing query...")
            await websocket.send_json(status_routing.model_dump())
            await asyncio.sleep(1.0)
            
            # Step 2: Simulate the Retrieval Agent querying the database
            status_querying = StreamResponse(type="status", content="Querying appliance database...")
            await websocket.send_json(status_querying.model_dump())
            await asyncio.sleep(1.0)
            
            # Step 3: Simulate the Generation Agent streaming the final answer token-by-token
            mock_response_string = "Based on the manual, the LG fridge requires a 2-inch clearance."
            words = mock_response_string.split(" ")
            
            for i, word in enumerate(words):
                # Add a space after the word, unless it's the very last word
                content = word + " " if i < len(words) - 1 else word
                token_resp = StreamResponse(type="token", content=content)
                await websocket.send_json(token_resp.model_dump())
                await asyncio.sleep(0.1)
                
            # Signal the end of the stream
            await websocket.send_json(StreamResponse(type="done", content="").model_dump())

    except WebSocketDisconnect:
        # Handle the client disconnecting gracefully
        print("Client disconnected from WebSocket.")
    except Exception as e:
        # Catch unexpected server-side errors
        print(f"WebSocket Error: {e}")
