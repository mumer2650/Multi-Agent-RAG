import os
import json
import sys
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig
from ragas.metrics import context_precision, context_recall
from dotenv import load_dotenv

from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from ragas.llms import LangchainLLMWrapper
from langsmith import traceable
from langchain_core.tracers import LangChainTracer

load_dotenv()

OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))
RAGAS_TIMEOUT_SECONDS = int(os.getenv("RAGAS_TIMEOUT_SECONDS", "600"))

print("🧠 Connecting to Local Ollama Model (Llama 3.2:1B)...")
base_evaluator = ChatOllama(
    model="llama3.2:1b",
    temperature=0,
    system="You are a strict evaluator. You MUST respond ONLY in valid JSON format. Do not include conversational filler."
)

ragas_llm = LangchainLLMWrapper(base_evaluator)
ragas_run_config = RunConfig(timeout=RAGAS_TIMEOUT_SECONDS, max_retries=2, max_wait=30, max_workers=1)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Import YOUR search engine function
from ai_core.retrieval.search_engine import advanced_search

@traceable(name="advanced_search", run_type="retriever")
def traced_advanced_search(query: str, k: int):
    return advanced_search(query, k=k)

def run_evaluation():
    print("🚀 Starting Automated RAG Evaluation Pipeline (Local Mode)...")

    # 1. Load the Golden Dataset
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "golden_dataset.json"))
    with open(dataset_path, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)

    # 2. Setup the Grader Embeddings (100% Local Nomic Embeddings!)
    grader_embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # 3. Prepare the Data Lists
    questions = []
    ground_truths = []
    contexts = []
    
    # Testing a small batch to keep local judge prompts manageable on CPU
    test_batch_size = int(os.getenv("EVAL_BATCH_SIZE", "5"))
    test_sample = golden_data[:test_batch_size]
    
    print(f"🔍 Running Retrieval on {test_batch_size} sample questions...")
    
    for item in test_sample:
        query = item["question"]
        questions.append(query)
        ground_truths.append(item["ground_truth"]) 
        
        # Run YOUR engine!
        search_results = traced_advanced_search(query, k=int(os.getenv("EVAL_TOP_K", "5")))
        retrieved_texts = [res["text"] for res in search_results]
        
        # Fallback if search fails
        if not retrieved_texts:
            retrieved_texts = ["No context retrieved."]
            
        contexts.append(retrieved_texts)

    # 4. Format for Ragas (HuggingFace Dataset format)
    data = {
        "question": questions,
        "contexts": contexts,
        "ground_truth": ground_truths
    }
    dataset = Dataset.from_dict(data)

    # 5. Run the Evaluation
    print("⚖️  Grading Retrieval Accuracy (Context Precision & Recall)...")
    print("⏳ Note: Local evaluation runs on your CPU/RAM, so this may take a minute. No rate limits!")
    
    tracer = LangChainTracer(project_name=os.getenv("LANGCHAIN_PROJECT", "multi-agent-rag-dev"))

    results = evaluate(
        dataset,
        metrics=[context_precision, context_recall],
        llm=ragas_llm,
        embeddings=grader_embeddings,
        raise_exceptions=False,
        run_config=ragas_run_config,
        callbacks=[tracer]
    )

    # 6. Output the Scorecard
    print("\n=============================================")
    print("🏆 FINAL EVALUATION SCORECARD 🏆")
    print("=============================================")
    print(f"Context Precision: {results['context_precision']:.4f}")
    print(f"Context Recall:    {results['context_recall']:.4f}")
    
    # Save to a CSV for your team dashboard
    df = results.to_pandas()

    if df[["context_precision", "context_recall"]].isna().any().any():
        print("\nWARNING: One or more metric values are NaN.")
        print("This usually means the local judge timed out or failed to produce a valid JSON response.")
        print("Try a larger Ollama timeout, fewer retrieved contexts, or a stronger local model.")

    df.to_csv("rag_evaluation_results.csv", index=False)
    print("\n✅ Detailed results saved to rag_evaluation_results.csv")

if __name__ == "__main__":
    run_evaluation()