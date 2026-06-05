# Multi-Agent RAG Backend Integration Guide

## System Architecture

Your Multi-Agent RAG system now has a complete backend-to-ai_core integration that allows:
- **Frontend** (React/WebSocket) → **Backend** (FastAPI) → **AI Core** (LangGraph) → **Response Streaming**

## How It Works

### 1. **Frontend Sends Query**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat');
ws.send(JSON.stringify({ query: "Show me products under 50000" }));
```

### 2. **Backend Receives & Routes (WebSocket Endpoint)**
- **File**: `backend/app/api/chat.py`
- **Function**: `websocket_chat_endpoint()`
- **Role**: 
  - Accepts WebSocket connections
  - Validates incoming `ChatRequest` (must have `query` field)
  - Maintains conversation history across multiple turns
  - Calls `run_pipeline()` from ai_bridge

### 3. **AI Bridge Initializes Graph & Streams (Service Layer)**
- **File**: `backend/app/services/ai_bridge.py`
- **Functions**:
  - `create_initial_state()` - Creates the initial graph state with all required fields
  - `run_pipeline()` - Main async generator that runs the LangGraph workflow

**Graph State Fields** (defined in `ai_core/graph/states.py`):
```python
{
    # Conversation
    "messages": [{"role": "user", "content": "..."}],
    
    # Query & Routing
    "user_query": "user question",
    "selected_agent": "retrieval|sql|python",  # Set by supervisor
    "tool_required": False,
    
    # Retrieval
    "retrieved_docs": [],
    "retrieval_error": None,
    "retrieval_attempts": 0,
    "max_retrieval_attempts": 3,
    
    # Tool Outputs
    "tool_output": None,  # {"type": "sql_result|python_result", ...}
    "chart": None,
    
    # Response Generation
    "citations": [],
    "final_answer": None,
    
    # Validation
    "validation_passed": False,
    "validation_reason": None,
    
    # Errors
    "error": None,
}
```

### 4. **LangGraph Pipeline Execution**
- **File**: `ai_core/graph/workflow.py`
- **Flow**:
  ```
  START
    ↓
  supervisor (routes to retrieval/sql/python)
    ↓
  [Branch based on selected_agent]
    ↓
  retrieval_agent (searches knowledge base)
    OR
  sql_agent (queries product database)
    OR
  python_agent (runs custom analysis/calculations)
    ↓
  answer_generator (generates response from context)
    ↓
  citation_builder (builds citations from sources)
    ↓
  validator (validates response quality)
    ↓
  END
  ```

### 5. **Response Streaming Back to Frontend**
Each step in the pipeline yields a `StreamResponse` with different types:

```python
class StreamResponse:
    type: str       # "status", "token", "citations", "chart", "done", "error"
    content: str    # The actual data
```

**Response Types**:
- **status** - Status update (e.g., "🧠 Routing your query...")
- **token** - Word-by-word streamed answer text
- **citations** - JSON array of citations (retrieval/database/analysis)
- **chart** - JSON chart data for visualization
- **done** - Signals end of response
- **error** - Any error messages

## Key Changes Made

### 1. **Created `__init__.py` Files** ✅
All Python packages now have `__init__.py` to be proper modules:
```
ai_core/
├── __init__.py ✅
├── graph/
│   ├── __init__.py ✅
│   └── workflow.py
├── agents/
│   ├── __init__.py ✅
│   └── *.py
├── retrieval/
│   ├── __init__.py ✅
│   └── *.py
├── tools/
│   ├── __init__.py ✅
│   └── *.py
└── llm/
    ├── __init__.py ✅
    └── *.py

backend/app/
├── __init__.py ✅
├── api/
│   ├── __init__.py ✅
│   └── chat.py
├── services/
│   ├── __init__.py ✅
│   └── ai_bridge.py [UPDATED]
├── db/
│   ├── __init__.py ✅
│   └── *.py
├── schemas/
│   ├── __init__.py ✅
│   └── *.py
└── core/
    ├── __init__.py ✅
    └── *.py
```

### 2. **Updated `ai_bridge.py`** ✅
**New Features**:
- ✅ `create_initial_state()` function for consistent state initialization
- ✅ Proper async event handling (supports both astream_events and astream)
- ✅ Comprehensive logging with `logging` module
- ✅ Better error handling and recovery
- ✅ Proper JSON serialization for citations and charts
- ✅ Token streaming with configurable delays

**Key Changes**:
```python
# BEFORE: Minimal state initialization
state = {
    "messages": [...],
    "user_query": query,
    ...
}

# AFTER: Complete state with all GraphState fields
state = create_initial_state(query, history)
# Returns state with retrieval_error, validation_reason, etc.
```

### 3. **Updated `chat.py` Endpoint** ✅
**New Features**:
- ✅ Proper conversation history management
- ✅ Token reconstruction to save assistant response
- ✅ Comprehensive error logging
- ✅ Better error messages
- ✅ Graceful handling of WebSocket disconnections

**Key Changes**:
```python
# BEFORE: Only saved user message
conversation_history.append({"role": "user", "content": query})

# AFTER: Saves both user and assistant messages
conversation_history.append({"role": "user", "content": query})
if reconstructed_answer.strip():
    conversation_history.append({
        "role": "assistant", 
        "content": reconstructed_answer.strip()
    })
```

## Running the System

### Option 1: Start Backend
```bash
# Windows
start_backend.bat

# Linux/Mac
bash start_backend.sh
```

This starts FastAPI on `http://localhost:8000` with WebSocket at `ws://localhost:8000/ws/chat`

### Option 2: Manual Backend Start
```bash
cd backend
python -m uvicorn app.main:app --reload
```

### Option 3: Console Testing (Still Works!)
```bash
python main.py
```

## Frontend Integration

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat');

ws.onopen = () => {
    console.log("Connected to backend");
    ws.send(JSON.stringify({ query: "What products have high efficiency?" }));
};

ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    
    if (response.type === "status") {
        updateStatus(response.content); // Show: "🧠 Routing..."
    } else if (response.type === "token") {
        appendToAnswer(response.content); // Build answer word-by-word
    } else if (response.type === "citations") {
        showCitations(JSON.parse(response.content));
    } else if (response.type === "chart") {
        renderChart(JSON.parse(response.content));
    } else if (response.type === "done") {
        console.log("Response complete");
    } else if (response.type === "error") {
        showError(response.content);
    }
};
```

## Data Flow Diagram

```
┌─────────────┐
│   Frontend  │ (React/WebSocket)
│  (Browser)  │
└──────┬──────┘
       │ WebSocket: { query: "..." }
       ↓
┌─────────────────────────┐
│  FastAPI Backend        │ (port 8000)
│  ├─ chat.py (endpoint)  │
│  └─ ai_bridge.py        │
└──────┬──────────────────┘
       │ Imports & invokes
       ↓
┌──────────────────────────┐
│  LangGraph Workflow      │
│  (ai_core/graph/)        │
│  ├─ supervisor          │
│  ├─ retrieval_agent     │
│  ├─ sql_agent           │
│  ├─ python_agent        │
│  ├─ answer_generator    │
│  ├─ citation_builder    │
│  └─ validator           │
└──────┬───────────────────┘
       │ Yields StreamResponse
       ↓
┌──────────────────────┐
│  WebSocket Streaming │
│  ├─ status updates   │
│  ├─ answer tokens    │
│  ├─ citations        │
│  ├─ chart data       │
│  └─ done signal      │
└──────┬───────────────┘
       │
       ↓
┌──────────────────┐
│  Frontend        │
│  Renders Result  │
└──────────────────┘
```

## Conversation History Management

The system now properly maintains multi-turn conversations:

**Turn 1**:
- User: "Show cheap products"
- Assistant: "Found 5 products under 30,000..."
- History: [user_msg_1, assistant_msg_1]

**Turn 2**:
- User: "What about TVs?"
- Graph receives: [user_msg_1, assistant_msg_1, user_msg_2]
- Can reference previous context!
- Assistant: "Here are 3 TVs..."
- History: [user_msg_1, assistant_msg_1, user_msg_2, assistant_msg_2]

## Error Handling

The system handles errors at multiple levels:

1. **WebSocket Level** - Chat endpoint catches connection errors
2. **Pipeline Level** - ai_bridge catches graph execution errors
3. **Node Level** - Individual agents have try-catch blocks
4. **Logging** - All errors logged with context (logger module)

## Testing the Integration

### Test 1: Basic Query
```javascript
ws.send(JSON.stringify({ query: "List TVs" }));
// Should route to SQL agent → python agent (for visualization)
```

### Test 2: Retrieval Query
```javascript
ws.send(JSON.stringify({ query: "How does this product compare?" }));
// Should route to retrieval agent
```

### Test 3: Math Query
```javascript
ws.send(JSON.stringify({ query: "Calculate EMI for 50000 at 12%" }));
// Should route to python agent
```

### Test 4: Multi-turn
```javascript
ws.send(JSON.stringify({ query: "Show products" }));
// Wait for response...
ws.send(JSON.stringify({ query: "Filter by energy efficient" }));
// Should reference previous context from turn 1
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'ai_core'"
**Solution**: Check that PROJECT_ROOT is set correctly in ai_bridge.py

### Issue: WebSocket connection refused
**Solution**: Make sure backend is running: `python -m uvicorn app.main:app --reload`

### Issue: No response received
**Solution**: Check logs for pipeline errors, verify all agents are returning dicts

### Issue: Async errors
**Solution**: Update to LangGraph 1.2.0+: `pip install --upgrade langgraph`

## Next Steps

1. ✅ Backend-to-AI_Core integration complete
2. 📝 Frontend WebSocket integration (in progress)
3. 🔒 Add authentication/authorization
4. 📊 Add metrics/analytics endpoints
5. 🚀 Deploy to production
