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
    
    # Randomly select 30 chunks to test the AI on
    selected_chunks = random.sample(chunks, min(100, len(chunks)))

    # 3. Initialize Gemini (Directly, no Ragas wrappers)
    print("3. Initializing Gemini 1.5 Flash...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite", 
        #google_api_key="AIzaSyDZa0_iJitwS2lmkSunzwULcMN6IeDabRI", 
        temperature=0.3
    )

    # 4. Create the prompt instructing Gemini to write the exam
    prompt = PromptTemplate.from_template("""
    You are an expert technical exam writer. Read the following text from a manual:
    
    {context}
    
    Generate ONE realistic question a user might ask that is perfectly answered by this text.
    Then, write the correct ground-truth answer.
    
    Output ONLY valid JSON in this exact format:
    {{
        "question": "your question here",
        "ground_truth": "your answer here"
    }}
    """)
    
    # Combine the prompt and the LLM
    chain = prompt | llm

    # 5. Generate the Dataset
    dataset = []
    print("\n4. Generating Golden Dataset (100 questions)...")
    
    for i, chunk in enumerate(selected_chunks):
        try:
            # Ask Gemini to generate the Q&A pair
            response = chain.invoke({"context": chunk.page_content})
            
            # Clean up the output to ensure it is pure JSON
            raw_text = response.content.replace("```json", "").replace("```", "").strip()
            qa_pair = json.loads(raw_text)
            
            # Save the context so we can grade it later
            qa_pair["contexts"] = [chunk.page_content]
            
            dataset.append(qa_pair)
            print(f"[{i+1}/100] Success: {qa_pair['question'][:60]}...")
            time.sleep(5)
        except Exception as e:
            print(f"[{i+1}/100] Failed to generate or parse JSON. Skipping.")
            time.sleep(5)

    # 6. Save the Dataset to a JSON file
    output_dir = os.path.dirname(__file__)
    json_path = os.path.join(output_dir, "golden_dataset.json")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=4)

    print(f"\n🎉 Success! Golden dataset generated without Ragas.")
    print(f"Saved {len(dataset)} structured evaluation samples to: {json_path}")

if __name__ == "__main__":
    generate_custom_dataset()