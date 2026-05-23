# Memory Vault: Data Ingestion Pipeline

This module handles the AI's "long-term memory." It transforms raw PDF documents into a structured, searchable format that the AI uses to provide accurate answers and avoid hallucinations.

## How it works (The 3-Step Process)

1.  **Cleaning:** PDF files often contain "messy" text (broken sentences, weird line breaks from columns, or extra spaces). My script uses regex to automatically detect these breaks and "glue" the text back together into proper, readable English sentences.
2.  **Parent-Child Chunking:** To provide high-quality context, we don't just feed the AI tiny, disconnected snippets. 
    * **Child Chunks (The Search Keys):** These are small pieces of text optimized for the AI to "find" quickly when a user asks a specific question.
    * **Parent Chunks (The Context):** Every Child chunk is linked to a larger Parent block of text. When a search matches a Child chunk, the AI is given the full Parent block, providing the necessary surrounding context for a smart answer.
3.  **Vector Embedding:** We use the `bge-small-en-v1.5` model to turn these chunks into mathematical coordinates (vectors). These are saved in `backend/storage/chroma_db/`, allowing the AI to understand the *meaning* of a user's question, not just keywords.



## How to use this

### Initial Setup
To process your base documents (like course manuals or technical specs):
1. Place your PDFs in the root `data/` folder. I haven't pushed this folder, you guyz are requested to create your own.
2. Run the ingestion script:
   ```bash
   python ai_core/retrieval/ingestion.py


# Active Search: The Retrieval Engine

This module is the "Search Brain" of our AI. It takes a natural language question from the user, dives into our Memory Vault, and pulls out the exact paragraphs the LLM needs to answer the question without hallucinating.

## How it works (The 3-Step Process)

1. **Semantic Understanding:** When a user asks a question, the engine uses the `bge-small-en-v1.5` embedding model to convert the question into a mathematical vector. It doesn't just look for exact keywords; it looks for the *meaning* behind the question.
2. **Child Matching (Speed):** It quickly scans the ChromaDB vector database to find the top `k` matching "Child Chunks" (our small, 300-character search keys).
3. **Parent Resolution (Context):** Once it finds the best matching children, it grabs their hidden `doc_id` tags. It then goes into our local `parent_store/` drive and pulls out the massive, original "Parent Paragraphs". 

This guarantees the AI gets the entire feature description or instruction set, rather than a chopped-up half-sentence.

## How to use this module

### For the AI Integration (Member 2 - Bilal)
You do not need to worry about connecting to databases or handling document IDs. All you need to do is import the main pipeline function into your LLM agent script: