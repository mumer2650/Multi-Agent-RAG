"""
Test script to run the first 5 questions from questions.txt
through the LangGraph pipeline and print the results.
"""
import sys
import os
import io

# Fix Windows encoding — emoji in print() statements crash charmap codec
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv()

from ai_core.graph.workflow import graph

questions = [
    "What is the cheapest refrigerator available, and what is its net total capacity?",
    "How do I clean the lint filter of a front-loading washing machine?",
    "Calculate the monthly electricity bill if I run the Top Mounted Freezer SpaceMax 304L for 24 hours a day, assuming the standard tariff rate.",
    "Recommend a Samsung LED TV that costs under Rs 300,000.",
    "Does the Side-by-Side Refrigerator Twist Ice Maker 655L support Wi-Fi or SmartThings?",
]

for i, q in enumerate(questions, 1):
    print(f"\n{'='*80}")
    print(f"QUESTION {i}: {q}")
    print(f"{'='*80}")
    try:
        result = graph.invoke({"user_query": q})
        print(f"\n--- SELECTED AGENT: {result.get('selected_agent')} ---")
        print(f"--- FINAL ANSWER ---")
        print(result.get("final_answer", "NO ANSWER"))
        if result.get("error"):
            print(f"--- ERROR: {result.get('error')} ---")
    except Exception as e:
        print(f"EXCEPTION: {e}")
    print()
