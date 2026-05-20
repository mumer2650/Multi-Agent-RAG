## 📂 Repository Structure

This monorepo is distinctly compartmentalized. [cite_start]This structure ensures that development on the frontend, API, and multi-agent logic remains decoupled, allowing the team to work in parallel without blocking one another[cite: 172].

* [cite_start]**`frontend/`**: Contains the React application and real-time UX components[cite: 162]. [cite_start]This includes the Chat Interface, the Agent State Viewer (listening to WebSockets), and the MLOps Analytics dashboard[cite: 167, 168, 170]. All `package.json` dependencies live here.
* [cite_start]**`backend/`**: Houses the FastAPI orchestrator[cite: 145]. [cite_start]This layer acts as the event-driven shell, handling `POST /ingest` for document uploads, WebSocket connections for streaming tokens, and `GET /metrics` for the SQLite dashboard data[cite: 147, 149, 150, 152].
* **`ai_core/`**: The operational brain of the application.
  * **`agents/`**: Defines the LangGraph state machine, including the Supervisor, Researcher, and Analyst sub-agents[cite: 85, 89, 90, 91].
  * [cite_start]**`retrieval/`**: Contains scripts for Data Ingestion (Parent-Child chunking), Dense retrieval (ChromaDB), Sparse retrieval (BM25), and Cross-Encoder reranking[cite: 35, 38, 50, 54, 64].
  * [cite_start]**`tools/`**: The defined local Python and SQL functions that the local LLM is instructed to call[cite: 76, 77, 82, 83].
* **`evaluations/`**: Dedicated to the Automated MLOps Evaluation Pipeline[cite: 27]. This folder holds the RAGAS or DeepEval automated testing scripts, the Golden Dataset (JSON/CSV) of benchmark questions, and the local SQLite metrics database[cite: 119, 126, 129, 138].