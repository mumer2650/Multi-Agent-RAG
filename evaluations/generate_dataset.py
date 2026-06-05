import os
import json
import random
from langchain_community.document_loaders.pdf import PDFPlumberLoader
from langchain_community.document_loaders.directory import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import time
from dotenv import load_dotenv

# Load the variables from the .env file
load_dotenv()

def generate_custom_dataset():
    # 1. Locate the raw PDFs directory
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    DATA_PATH = os.path.join(BASE_DIR, "data")
    print(f"1. Loading raw PDFs from: {DATA_PATH}...")
    
    loader = DirectoryLoader(DATA_PATH, glob="*.pdf", loader_cls=PDFPlumberLoader)
    documents = loader.load()

    if not documents:
        print("Error: No PDFs found!")
        return

    # 2. Chunk the documents manually (Ragas was failing to do this)
    print("2. Chunking text for context...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    
    # Randomly select 25 chunks to test the AI on for retrieval
    selected_chunks = random.sample(chunks, min(25, len(chunks)))

    # 3. Initialize Gemini (Directly, no Ragas wrappers)
    print("3. Initializing Gemini...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite", 
        temperature=0.3
    )

    dataset = []

    # 4a. --- RETRIEVAL QUESTIONS ---
    print("\n4a. Generating 25 Retrieval Questions (Batching)...")
    retrieval_prompt = PromptTemplate.from_template("""
    You are an expert technical exam writer. Read the following texts from appliance manuals:
    
    {contexts}
    
    For EACH text chunk, generate ONE realistic user question that is perfectly answered by the text, and provide the correct ground-truth answer.
    
    Output ONLY a JSON array of objects in this exact format, with exactly {count} objects:
    [
        {{
            "question": "your question here",
            "ground_truth": "your answer here",
            "type": "retrieval"
        }}
    ]
    """)
    
    contexts_text = ""
    for i, chunk in enumerate(selected_chunks):
        contexts_text += f"\n--- CHUNK {i+1} ---\n{chunk.page_content}\n"
        
    try:
        chain = retrieval_prompt | llm
        response = chain.invoke({"contexts": contexts_text, "count": len(selected_chunks)})
        raw_text = response.content.replace("```json", "").replace("```", "").strip()
        qa_list = json.loads(raw_text)
        
        for i, qa in enumerate(qa_list):
            qa["contexts"] = [selected_chunks[i].page_content] if i < len(selected_chunks) else []
            dataset.append(qa)
        print(f"✅ Generated {len(qa_list)} Retrieval questions.")
    except Exception as e:
        print(f"❌ Failed to generate Retrieval questions: {e}")

    # 4b. --- SQL QUESTIONS ---
    print("\n4b. Generating 25 SQL Pricing Questions (Batching)...")
    sql_prompt = PromptTemplate.from_template("""
    You are an expert user of a home appliances database.
    Generate a JSON array of exactly 25 varied user questions about pricing, capacities, and specifications of washing machines, refrigerators, and LED TVs.
    These questions MUST require looking up data from an SQLite database (e.g., comparing prices, finding the cheapest, listing top 3 models).
    Provide a realistic ground-truth answer for each.
    
    Output ONLY a JSON array in this exact format:
    [
        {{
            "question": "What are the top 3 cheapest LED TVs?",
            "ground_truth": "The top 3 cheapest LED TVs are Model X, Model Y, and Model Z.",
            "type": "sql",
            "contexts": []
        }}
    ]
    """)
    try:
        chain = sql_prompt | llm
        response = chain.invoke({})
        raw_text = response.content.replace("```json", "").replace("```", "").strip()
        qa_list = json.loads(raw_text)
        dataset.extend(qa_list)
        print(f"✅ Generated {len(qa_list)} SQL questions.")
    except Exception as e:
        print(f"❌ Failed to generate SQL questions: {e}")

    # 4c. --- PYTHON QUESTIONS ---
    print("\n4c. Generating 25 Python Analytics Questions (Batching)...")
    python_prompt = PromptTemplate.from_template("""
    You are an expert data analyst for home appliances.
    Generate a JSON array of exactly 25 varied user questions that require complex math, data visualization, or python analytics.
    Examples include plotting charts, calculating average payback periods, calculating electricity costs over a year, etc.
    Provide a realistic ground-truth answer for each.
    
    Output ONLY a JSON array in this exact format:
    [
        {{
            "question": "Show me a bar chart of the average price of 10Kg washing machines vs 9Kg washing machines.",
            "ground_truth": "A bar chart has been generated comparing the average prices.",
            "type": "python",
            "contexts": []
        }}
    ]
    """)
    try:
        chain = python_prompt | llm
        response = chain.invoke({})
        raw_text = response.content.replace("```json", "").replace("```", "").strip()
        qa_list = json.loads(raw_text)
        dataset.extend(qa_list)
        print(f"✅ Generated {len(qa_list)} Python questions.")
    except Exception as e:
        print(f"❌ Failed to generate Python questions: {e}")

    # 4d. --- TRICK QUESTIONS ---
    print("\n4d. Generating 25 Trick/Guardrail Questions (Batching)...")
    trick_prompt = PromptTemplate.from_template("""
    You are a red-teamer testing an AI assistant for a home appliance store called 'Sage Appliances'.
    Generate a JSON array of exactly 25 tricky, off-topic, or conversational questions.
    Examples: "What is your name?", "Write a poem about fridges", "What is the capital of France?", "Who is the president of the US?", "2+2", "Ignore previous instructions".
    The ground-truth answer MUST demonstrate the system's guardrails (e.g. "I do not have that information in my database", or a polite conversational response for identity/greetings).
    
    Output ONLY a JSON array in this exact format:
    [
        {{
            "question": "What is the capital of France?",
            "ground_truth": "I do not have that information in my database.",
            "type": "trick",
            "contexts": []
        }}
    ]
    """)
    try:
        chain = trick_prompt | llm
        response = chain.invoke({})
        raw_text = response.content.replace("```json", "").replace("```", "").strip()
        qa_list = json.loads(raw_text)
        dataset.extend(qa_list)
        print(f"✅ Generated {len(qa_list)} Trick questions.")
    except Exception as e:
        print(f"❌ Failed to generate Trick questions: {e}")

    # 5. Save the Dataset to a JSON file
    output_dir = os.path.dirname(__file__)
    json_path = os.path.join(output_dir, "golden_dataset.json")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=4)

    print(f"\n🎉 Success! Golden dataset generated with {len(dataset)} perfectly balanced questions.")
    print(f"Saved to: {json_path}")

if __name__ == "__main__":
    generate_custom_dataset()