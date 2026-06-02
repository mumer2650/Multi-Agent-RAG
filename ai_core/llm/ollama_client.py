from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

# =========================================================================
# EVALUATION DAY / PRODUCTION (Ollama 8B Local)
# To use this tomorrow on your teammate's gaming laptop, uncomment this:
# =========================================================================
# from langchain_ollama import ChatOllama
# llm = ChatOllama(
#     model="llama3.1",
#     temperature=0
# )

# =========================================================================
# DEVELOPMENT (Gemini Fast API)
# We are currently using this so your laptop doesn't lag! 
# When switching to Ollama tomorrow, just comment out the block below.
# =========================================================================
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY", "AIzaSyDZa0_iJitwS2lmkSunzwULcMN6IeDabRI")
)