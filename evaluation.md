# SAGE AI - Evaluation System

SAGE AI employs a **Live Evaluation System (LLM-as-a-Judge)** to continuously monitor the performance of the Retrieval-Augmented Generation (RAG) pipeline in real-time. Instead of relying purely on pre-computed static datasets, every interaction between the user and SAGE is asynchronously evaluated by a strict Gemini-based judge agent.

## How it Works

1. **User Interaction**: The user asks a question, and SAGE orchestrates sub-agents to generate a response and retrieve context (PDF documents, SQL data).
2. **Background Evaluation**: The query, generated answer, and retrieved context are passed to a background process (`live_evaluator.py`).
3. **LLM as a Judge**: A Gemini 1.5 Flash-Lite agent analyzes the interaction and assigns scores between `0.0` and `1.0` based on strict RAG criteria.
4. **Analytics Storage**: The scores are saved to a live SQLite database (`analytics.db`). The Admin Dashboard queries this database to display the running average of the system's performance.

## Evaluation Metrics

The system tracks three core Ragas-inspired metrics to measure the health of the AI:

### 1. Context Precision
**What it means:** *Did the system retrieve the correct information from the database or manuals?*
- **Score 1.0:** The retrieved PDF chunks or SQL rows contained the exact, highly relevant information needed to answer the user's query perfectly.
- **Score 0.0:** The retrieval system fetched completely irrelevant information or nothing at all.
- *Note:* If the user asks a general greeting or an off-topic question where no appliance context is needed, the evaluator automatically grants a perfect score to prevent penalizing the system.

### 2. Faithfulness
**What it means:** *Did the AI stick to the facts, or did it hallucinate?*
- **Score 1.0:** Every claim made in the final answer is directly supported by the retrieved context. The AI did not invent any features, prices, or policies. 
- **Score 0.0:** The AI hallucinated information not present in the retrieved documents.
- *Note:* Because SAGE is powered by Gemini set to a strict `0.0` temperature alongside aggressive system prompts, Faithfulness generally remains consistently near 100%.

### 3. Answer Relevance
**What it means:** *Did the AI actually answer the user's prompt?*
- **Score 1.0:** The answer directly and concisely addresses the user's query without unnecessary tangents.
- **Score 0.0:** The answer is evasive, incomplete, or completely misses the point of the question.
- *Guardrail Enforcement:* If a user asks an off-topic question (e.g., "Give me a recipe for chocolate cake") and SAGE correctly refuses to answer by stating it is an appliance assistant, the evaluator correctly awards Answer Relevance a perfect `1.0` because the AI successfully enforced its enterprise guardrails.
