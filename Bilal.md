Installed Modules 
pip install langchain
pip install langchain-ollama

Task1: Ollama Setup 
-> Download Ollama Setup from Ollama Website and Install
-> Open cmd and download model llama3.2:1.b 

Implemented Graph Workflow via Langgraph
                    START
                       ↓
               User Question
                       ↓
              Context Builder
                       ↓
               Supervisor Agent
                       ↓
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
   Retrieval Agent   SQL Agent   Python Agent
         │             │             │
         ▼             ▼             ▼
   Vector Search     DB Query     Code Execution
         │
         ▼
      Reranker
         │
         ▼
   Enough Context?
      ├── NO → Query Rewrite
      │            ↓
      │       Retry Retrieval
      │
      └── YES
               ↓
        Tool Needed?
               ↓
        Tool Router
               ↓
       Answer Generator
               ↓
       Citation Builder
               ↓
      Response Validator
               ↓
        Final Response
               ↓
              END