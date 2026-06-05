import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from backend.app.schemas.chat import ChatRequest, StreamResponse
from backend.app.services.ai_bridge import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat communication.

    This endpoint maintains an open connection with the client. It waits for a JSON
    payload matching the `ChatRequest` schema. Once received, it runs the real
    LangGraph multi-agent pipeline via ai_bridge and streams status updates,
    answer tokens, citations, and chart data back to the frontend.

    The endpoint:
    1. Maintains conversation history across multiple turns
    2. Streams all events from the LangGraph pipeline
    3. Reconstructs and saves the assistant message after the response is complete
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    conversation_history = []

    try:
        while True:
            # Wait to receive a JSON payload from the client
            data = await websocket.receive_text()
            logger.debug(f"Received message: {data[:100]}...")

            try:
                # Validate the incoming data against our schema
                request_data = json.loads(data)
                chat_request = ChatRequest(**request_data)
            except (json.JSONDecodeError, ValidationError) as e:
                # Handle invalid formatting gracefully
                error_resp = StreamResponse(
                    type="error",
                    content=f"Invalid request format: {str(e)}"
                )
                logger.warning(f"Validation error: {e}")
                await websocket.send_json(error_resp.model_dump())
                continue

            # =================================================================
            # REAL MULTI-AGENT PIPELINE
            # =================================================================
            # Run the LangGraph workflow through ai_bridge and stream every
            # event (status updates, tokens, citations, chart, done) to the client.

            logger.info(f"Processing query: {chat_request.query[:50]}...")
            reconstructed_answer = ""
            collected_context = ""
            pipeline_error = False

            try:
                async for response in run_pipeline(
                    query=chat_request.query,
                    history=conversation_history
                ):
                    await websocket.send_json(response.model_dump())

                    # Track streamed tokens to reconstruct the full answer
                    if response.type == "token":
                        reconstructed_answer += response.content
                        
                    # Track context for the background evaluator
                    if response.type == "context":
                        collected_context += response.content

                    # Log errors
                    if response.type == "error":
                        pipeline_error = True
                        logger.error(f"Pipeline error: {response.content}")

            except Exception as pipeline_error_detail:
                pipeline_error = True
                error_resp = StreamResponse(
                    type="error",
                    content=f"Pipeline error: {str(pipeline_error_detail)}"
                )
                logger.error(f"Pipeline failed: {pipeline_error_detail}", exc_info=True)
                await websocket.send_json(error_resp.model_dump())

            # =================================================================
            # SAVE CONVERSATION TURNS
            # =================================================================
            # Only save to history if the pipeline succeeded
            if not pipeline_error:
                conversation_history.append({
                    "role": "user",
                    "content": chat_request.query
                })

                # Save the reconstructed assistant response
                if reconstructed_answer.strip():
                    conversation_history.append({
                        "role": "assistant",
                        "content": reconstructed_answer.strip()
                    })
                    logger.debug(f"Saved assistant message to history: {reconstructed_answer[:50]}...")
                    
                    # TRIGGER LIVE EVALUATION IN BACKGROUND
                    import asyncio
                    from backend.app.services.live_evaluator import evaluate_interaction_background
                    
                    # Fire and forget
                    asyncio.create_task(
                        asyncio.to_thread(
                            evaluate_interaction_background,
                            chat_request.query,
                            reconstructed_answer.strip(),
                            collected_context if collected_context else "No context retrieved."
                        )
                    )

            logger.debug(f"Conversation history length: {len(conversation_history)}")

    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}", exc_info=True)
