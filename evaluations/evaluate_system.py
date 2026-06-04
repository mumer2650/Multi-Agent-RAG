import os
import json
import sys
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.run_config import RunConfig
from ragas.metrics import answer_relevancy, faithfulness
from dotenv import load_dotenv

from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from ragas.llms import LangchainLLMWrapper
from langsmith import traceable
from langchain_core.tracers import LangChainTracer

load_dotenv()

OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))
RAGAS_TIMEOUT_SECONDS = int(os.getenv("RAGAS_TIMEOUT_SECONDS", "600"))

print("🧠 Connecting to Local Ollama Model (Llama 3.2:1B) for Evaluation...")
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

# Import the full Multi-Agent Graph
from ai_core.graph.workflow import graph

def create_initial_state(query):
    return {
        "messages": [{"role": "user", "content": query}],
        "user_query": query,
        "selected_agent": None,
        "tool_required": False,
        "retrieved_docs": [],
        "retrieval_error": None,
        "retrieval_attempts": 0,
        "max_retrieval_attempts": 3,
        "tool_output": None,
        "chart": None,
        "citations": [],
        "validation_passed": False,
        "validation_reason": None,
        "final_answer": None,
        "error": None,
    }

def run_evaluation():
    print("🚀 Starting Automated RAG Evaluation Pipeline (Full System)...")

    # 1. Load the Golden Dataset
    dataset_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "golden_dataset.json"))
    if not os.path.exists(dataset_path):
        print(f"❌ Golden dataset not found at {dataset_path}. Run generate_dataset.py first.")
        return

    with open(dataset_path, 'r', encoding='utf-8') as f:
        golden_data = json.load(f)

    # 2. Setup the Grader Embeddings
    grader_embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # 3. Prepare the Data Lists
    questions = []
    ground_truths = []
    contexts = []
    answers = []
    
    # Testing a small batch to keep local judge prompts manageable on CPU
    test_batch_size = int(os.getenv("EVAL_BATCH_SIZE", "5"))
    test_sample = golden_data[:test_batch_size]
    
    print(f"🔍 Running Multi-Agent System on {test_batch_size} sample questions...")
    
    for i, item in enumerate(test_sample):
        query = item["question"]
        print(f"\n[{i+1}/{test_batch_size}] Q: {query}")
        
        questions.append(query)
        ground_truths.append(item["ground_truth"]) 
        
        # Run the graph
        state = create_initial_state(query)
        try:
            for event in graph.stream(state):
                for node_name, node_state in event.items():
                    state.update(node_state)
                    
            final_ans = state.get("final_answer") or "No answer generated."
            
            # Combine retrieved docs and tool outputs into a single context string
            ctx_list = []
            if state.get("retrieved_docs"):
                ctx_list.extend([doc.page_content for doc in state["retrieved_docs"]])
            if state.get("tool_output"):
                ctx_list.append(str(state["tool_output"].get("data", "")))
                
            if not ctx_list:
                ctx_list = ["No context used."]
                
            answers.append(final_ans)
            contexts.append(ctx_list)
            
        except Exception as e:
            print(f"  ❌ Graph execution failed: {e}")
            answers.append("Error executing graph.")
            contexts.append(["Error"])

    # 4. Format for Ragas
    data = {
        "question": questions,
        "contexts": contexts,
        "answer": answers,
        "ground_truth": ground_truths
    }
    dataset = Dataset.from_dict(data)

    # 5. Run the Evaluation
    print("\n⚖️  Grading System Accuracy (Answer Relevancy & Faithfulness)...")
    print("⏳ Note: Local evaluation runs on your CPU/RAM, so this may take a minute.")
    
    tracer = LangChainTracer(project_name=os.getenv("LANGCHAIN_PROJECT", "multi-agent-rag-dev"))

    results = evaluate(
        dataset,
        metrics=[answer_relevancy, faithfulness],
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
    print(f"Answer Relevancy: {results.get('answer_relevancy', 0.0):.4f}")
    print(f"Faithfulness:     {results.get('faithfulness', 0.0):.4f}")
    
    # Save to CSV
    df = results.to_pandas()
    df.to_csv("rag_evaluation_results.csv", index=False)
    print("\n✅ Detailed results saved to rag_evaluation_results.csv")

if __name__ == "__main__":
    run_evaluation()