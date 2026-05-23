# SAGE Frontend Architecture & Progress Documentation

## Overview

This document outlines the frontend architecture, UI/UX features, and API integration schemas for the **SAGE** (Multi-Agent RAG) system. The frontend is built to handle real-time streaming data from a FastAPI backend while maintaining a highly responsive, enterprise-grade user interface.

## 1. Tech Stack & Initialization

- **Framework:** React (Bootstrapped via Vite for fast HMR and optimized builds)
- **Styling:** Tailwind CSS (configured with `darkMode: 'class'` for manual theme toggling)
- **Icons:** `lucide-react`

## 2. UI/UX Implementations

### Layout & Animations

- **Dynamic Search Layout:** The interface starts with a centered landing greeting and a glowing search bar. Upon the first query submission, it seamlessly transitions the search bar to the bottom of the screen, revealing the chat history area.
- **Viewport Lock (`h-screen overflow-hidden`):** Prevents the global page from stretching and scrolling. This guarantees the search input remains securely anchored to the bottom of the viewport at all times.
- **Auto-Scroll Hook:** Utilizes `useRef` and `useEffect` to automatically scroll the chat container to the bottom whenever a new token or status update arrives, ensuring the user never has to scroll manually during generation.
- **UI Thread Unblocking:** Implemented a `setTimeout(..., 0)` hack inside the form submission handler. This forces React to flush the state clearing (`setQuery('')`) to the DOM instantly before executing the heavy layout transition and WebSocket initialization, preventing the text from "lingering" in the input box.
- **Custom Scrollbar:** Overrode default OS webkit scrollbars in `index.css` to feature a slim, transparent track with a rounded, theme-adaptive thumb, matching the ChatGPT aesthetic.

### Theme Management

- **Dark/Light Mode Toggle:** Implemented native Tailwind dark mode. The `Header` component toggles the `.dark` class directly on the `document.documentElement` (`<html>` tag).
- **Persistence:** The user's theme choice is saved to the browser's `localStorage` and falls back to the OS `prefers-color-scheme` if no local save is found.

## 3. Component Architecture

- **`App.jsx` / `main.jsx`:** The entry points wrapping the application in React Strict Mode.
- **`Header.jsx`:** Manages the branding and the Dark/Light mode toggle state logic.
- **`SearchBar.jsx`:** The primary input component. Manages its own local state (`query`) and conditionally renders its layout based on the `isActive` prop passed from the parent. Accepts an `isStreaming` prop to disable inputs while the AI is thinking.
- **`Home.jsx` (ChatLayout):** The main orchestrator. It manages the chat history array (`messages`), the AI's current state (`agentState`), the streaming lock (`isStreaming`), and the WebSocket connection lifecycle.

## 4. API Integration & Schemas

The frontend currently communicates with the FastAPI backend via a persistent WebSocket connection.

- **Endpoint:** `ws://127.0.0.1:8000/ws/chat` _(Note: Hardcoded to IPv4 loopback to bypass local Windows/Node IPv6 DNS resolution bugs)._

### Outgoing Payload (Client -> Server)

When the user submits a query, the frontend sends a JSON string matching the backend's `ChatRequest` Pydantic schema.

```json
{
  "query": "Find me an LG fridge under $1200"
}
```

### Incoming Payload (Server -> Client)

The `onmessage` listener parses incoming JSON strings matching the backend's `StreamResponse` schema. The frontend reacts differently based on the `type` field:

```json
{
  "type": "status" | "token" | "done" | "error",
  "content": "string"
}
```

**Frontend Handling Logic:**

1.  **`type: "status"`**: Updates the `agentState` UI (e.g., _"Querying database..."_) in small italic text above the search bar.
2.  **`type: "token"`**: Clears the status text and appends the `content` chunk to the final message bubble in the `messages` array, creating the real-time typing effect.
3.  **`type: "done"`**: Triggers `setIsStreaming(false)`, unlocking the input field and submit button for the next user query.
4.  **`type: "error"`**: Displays the error content in the status area, unlocks the input field, and safely closes the WebSocket connection.

# SAGE Backend Documentation: Current Progress & API Reference

## 1. What Has Been Done So Far (Backend Folder)

We have successfully scaffolded the foundational architecture for the FastAPI backend, setting up the necessary routing, CORS configurations, data validation schemas, and mock endpoints to allow the frontend to be developed independently of the core AI logic.

**Implemented File Structure:**

- `backend2/app/main.py`: The core application entry point. It initializes the FastAPI server, configures CORS to accept traffic from the Vite frontend, and registers all API routers.
- `backend2/app/api/chat.py`: Contains the WebSocket routing logic for real-time AI chat streaming. Currently runs a simulated async loop.
- `backend2/app/api/ingest.py`: Contains the REST routing logic for document uploads.
- `backend2/app/api/metrics.py`: Contains the REST routing logic for serving evaluation metrics.
- `backend2/app/schemas/chat.py`: Contains the Pydantic data models used to enforce strict JSON schemas for the chat endpoint.

_(Note: Folders for `db`, `core`, and `services` exist in the structure but are pending implementation by the database and AI orchestration engineers)._

---

## 2. API Endpoints Reference

Below is the complete list of all currently implemented APIs, their file locations, and their expected JSON request/response formats.

---

### 2.1. Health Check

- **Location:** `backend2/app/main.py`
- **Endpoint:** `GET /`
- **Protocol:** HTTP REST
- **Purpose:** A simple route to verify that the Uvicorn server is running.
- **Expected Input:** None

#### Produced Output (JSON)

```json
{
  "message": "Backend server is active"
}
```

---

### 2.2. Real-Time Chat Stream (WebSocket)

- **Location:** `backend2/app/api/chat.py`
- **Endpoint:** `ws://127.0.0.1:8000/ws/chat`
- **Protocol:** WebSocket
- **Purpose:** The core communication artery. Maintains a persistent connection to receive user queries and stream back simulated agent status updates and generated text.

---

#### Expected Incoming Data (Client -> Server)

Must conform to the `ChatRequest` Pydantic schema.

```json
{
  "query": "Find me an energy-efficient, No-Frost refrigerator under $1,200"
}
```

---

#### Produced Outgoing Data Stream (Server -> Client)

Streams multiple JSON packets over time, all conforming to the `StreamResponse` Pydantic schema.

The frontend parses the `type` field to know how to handle the content.

---

#### 1. Status Updates (Simulating LangGraph routing/querying)

```json
{
  "type": "status",
  "content": "Agent routing query..."
}
```

---

#### 2. Token Generation (Simulating real-time AI typing)

```json
{
  "type": "token",
  "content": "Based "
}
```

---

#### 3. Stream Termination (Tells the frontend to unlock the input field)

```json
{
  "type": "done",
  "content": ""
}
```

---

#### 4. Error Handling (If the incoming request JSON is invalid)

```json
{
  "type": "error",
  "content": "Invalid request format: [Error Details]"
}
```

---

### 2.3. Document Ingestion

- **Location:** `backend2/app/api/ingest.py`
- **Endpoint:** `POST /ingest`
- **Protocol:** HTTP REST
- **Purpose:** Handles the uploading of appliance manuals (PDFs) to eventually be chunked and indexed into ChromaDB. Currently simulates a 2-second processing delay.

---

#### Expected Incoming Data (Client -> Server)

- **Format:** `multipart/form-data`
- **Field Name:** `file` (An `UploadFile` object, typically a PDF)

---

#### Produced Output (JSON)

```json
{
  "status": "success",
  "filename": "uploaded_document_name.pdf",
  "message": "Document ingested and vector index updated."
}
```

---

### 2.4. MLOps Analytics Metrics

- **Location:** `backend2/app/api/metrics.py`
- **Endpoint:** `GET /metrics`
- **Protocol:** HTTP REST
- **Purpose:** Serves the latest automated benchmarking scores to populate the frontend admin dashboard. Eventually, this will query a local SQLite database.

---

#### Expected Incoming Data

None

---

#### Produced Output (JSON)

```json
{
  "context_precision": 0.85,
  "faithfulness": 0.92,
  "answer_relevance": 0.88,
  "timestamp": "2026-05-23"
}
```
