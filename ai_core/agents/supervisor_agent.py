import os
import math
from typing import Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# --- Local Embeddings for the Guardrail ---
from langchain_ollama import OllamaEmbeddings
# --- Gemini for the Intelligent Router ---
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# ==========================================
# STRICT PYDANTIC SCHEMA
# ==========================================
class IntentClassification(BaseModel):
    # We can bring 'confidence' back because Gemini handles complex schemas perfectly!
    intent: Literal["sql", "retrieval", "answer"] = Field(
        description="Must be 'sql', 'retrieval', or 'answer'"
    )
    confidence: int = Field(description="Confidence integer from 1 to 10")

# Initialize Local Embeddings for semantic guardrail
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Initialize Gemini Router (Using 1.5 Flash for speed)
# We set temperature=0 to ensure deterministic, highly predictable routing
gemini_router = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite", 
    temperature=0,
    google_api_key="AIzaSyDZa0_iJitwS2lmkSunzwULcMN6IeDabRI"
)

def cosine_similarity(v1, v2):
    dot_product = sum(a*b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a*a for a in v1))
    mag2 = math.sqrt(sum(b*b for b in v2))
    if mag1 * mag2 == 0:
        return 0
    return dot_product / (mag1 * mag2)

def supervisor_agent(state):
    query = state.get("user_query", "").lower()

    # ==========================================
    # LAYER 1: THE GUARDRAIL (Deterministic & Local Embedding)
    # ==========================================
    # 1A. Deterministic Competitor Block
    competitors = ["lg", "sony", "haier", "dawlance", "pel"]
    if any(comp in query for comp in competitors):
        print("🛡️ Guardrail Triggered: Competitor detected.")
        return {
            "selected_agent": "answer",
            "tool_required": False,
            "competitor_detected": True,
            "off_topic": False
        }

    # 1B. Semantic Guardrail (Local check if query is completely off-topic)
    core_domain = "home appliances, electronics, refrigerators, washing machines, tvs, air conditioners, fixing appliances, warranties, troubleshooting"
    try:
        query_vec = embeddings.embed_query(query)
        domain_vec = embeddings.embed_query(core_domain)
        sim = cosine_similarity(query_vec, domain_vec)
        
        # If the query is completely unrelated (e.g. "What is the capital of France?")
        if sim < 0.20: 
            print("🛡️ Guardrail Triggered: Query is off-topic.")
            return {
                "selected_agent": "answer",
                "tool_required": False,
                "competitor_detected": False,
                "off_topic": True
            }
    except Exception as e:
        print(f"Embedding check skipped due to error: {e}")

    # ==========================================
    # LAYER 2: INTENT CLASSIFICATION (Powered by Gemini)
    # ==========================================
    system_prompt = """
    You are the intelligent routing system for Sage Appliances, an electronics ecommerce company.
    Analyze the user's query and categorize it into EXACTLY ONE of these intents:

    1. "sql": For product recommendations, prices, budgets, specifications, reviews, energy efficiency, and availability.
    2. "retrieval": For information from user manuals, troubleshooting guides, fixing appliances, warranty policies, and how-to descriptions.
    3. "answer": ONLY for general conversational pleasantries, simple greetings, or basic math.

    You must return a JSON object with 'intent' and 'confidence'.
    """

    # Bind the Pydantic schema to Gemini
    structured_llm = gemini_router.with_structured_output(IntentClassification)
    
    try:
        result = structured_llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ])
        
        intent = result.intent
        confidence = result.confidence
        print(f"🧠 Supervisor (Gemini) categorized intent as: {intent} (Confidence: {confidence}/10)")
        
        if intent == "sql":
            selected = "sql"
            tool_required = True
        elif intent == "retrieval":
            selected = "retrieval"
            tool_required = False
        else:
            selected = "answer"
            tool_required = False
            
        print("🎯 Tool Selected:", selected)
            
        return {
            "selected_agent": selected,
            "tool_required": tool_required,
            "competitor_detected": False,
            "off_topic": False
        }

    except Exception as error:
        print(f"⚠️ Gemini Classification failed: {error}")
        # Safest fallback if the API crashes is to send it to local retrieval
        return {
            "selected_agent": "retrieval",
            "tool_required": False,
            "competitor_detected": False,
            "off_topic": False
        }