import sqlite3
import os
import json
import logging
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "storage",
    "sqlite",
    "analytics.db"
)

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS live_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_query TEXT,
            final_answer TEXT,
            faithfulness FLOAT,
            answer_relevance FLOAT
        )
    """)
    conn.commit()
    conn.close()

# Initialize db on module load
init_db()

def evaluate_interaction_background(query: str, answer: str, context: str):
    """
    Background task that evaluates the system's response using Gemini.
    Runs completely asynchronously without blocking the user.
    """
    try:
        logger.info(f"Background Eval Started for query: {query[:30]}...")
        
        # We use a fast Gemini model to grade the response
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite", 
            temperature=0.0
        )
        
        eval_prompt = PromptTemplate.from_template("""
        You are an impartial AI judge evaluating a RAG system.
        
        User Query: {query}
        System Answer: {answer}
        Retrieved Context: {context}
        
        Evaluate the System Answer on two metrics (from 0.0 to 1.0):
        1. faithfulness: Is the answer factually grounded in the Retrieved Context? (1.0 = completely grounded, 0.0 = completely hallucinated). If no context was provided but the answer gracefully handled it (e.g. "I don't know"), score 1.0.
        2. answer_relevance: Does the answer directly address the User Query? (1.0 = completely relevant, 0.0 = completely irrelevant/off-topic).
        
        Output ONLY valid JSON in this exact format:
        {{
            "faithfulness": 0.95,
            "answer_relevance": 0.90
        }}
        """)
        
        chain = eval_prompt | llm
        response = chain.invoke({
            "query": query, 
            "answer": answer, 
            "context": context if context else "No context retrieved."
        })
        
        raw_text = response.content.replace("```json", "").replace("```", "").strip()
        scores = json.loads(raw_text)
        
        f_score = float(scores.get("faithfulness", 0.0))
        ar_score = float(scores.get("answer_relevance", 0.0))
        
        # Save to SQLite
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO live_evaluations (user_query, final_answer, faithfulness, answer_relevance) VALUES (?, ?, ?, ?)",
            (query, answer, f_score, ar_score)
        )
        conn.commit()
        conn.close()
        
        logger.info(f"Background Eval Completed: F={f_score}, AR={ar_score}")
        
    except Exception as e:
        logger.error(f"Background Eval Failed: {e}")
