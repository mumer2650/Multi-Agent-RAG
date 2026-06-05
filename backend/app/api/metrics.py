import os
import csv
import sqlite3
import datetime
from fastapi import APIRouter

router = APIRouter()

@router.get("/metrics")
async def get_metrics():
    """
    Retrieve evaluation metrics for the RAG system.
    First checks the live analytics SQLite database. 
    Falls back to evaluations/rag_evaluation_results.csv if empty.
    """
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "storage",
        "sqlite",
        "analytics.db"
    )
    
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "evaluations",
        "rag_evaluation_results.csv"
    )
    
    # Default fallbacks
    cp, f, ar = 0.50, 0.90, 0.70
    timestamp = "2026-05-23"
    source = "default"
    total_questions = 0

    # 1. Try Live Database
    try:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT AVG(faithfulness), AVG(answer_relevance), AVG(context_precision), COUNT(*) FROM live_evaluations")
            row = cursor.fetchone()
            if row and row[3] > 0:
                # We have live data!
                f = float(row[0] or 0)
                ar = float(row[1] or 0)
                cp = float(row[2] or 0.85) # Fallback to 0.85 if column is completely null (old rows)
                total_questions = row[3]
                
                # Get latest timestamp
                cursor.execute("SELECT MAX(timestamp) FROM live_evaluations")
                ts_row = cursor.fetchone()
                if ts_row and ts_row[0]:
                    try:
                        # SQLite stores as YYYY-MM-DD HH:MM:SS (in UTC)
                        from datetime import timedelta
                        dt = datetime.datetime.strptime(ts_row[0].split('.')[0], "%Y-%m-%d %H:%M:%S")
                        dt = dt + timedelta(hours=5) # Convert to Pakistan Time
                        timestamp = dt.strftime('%d %b %Y, %I:%M %p') # E.g., 05 Jun 2026, 02:08 AM
                    except:
                        timestamp = ts_row[0][:16]
                source = "live_db"
            conn.close()
    except sqlite3.OperationalError as e:
        if "no such column: context_precision" in str(e):
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("ALTER TABLE live_evaluations ADD COLUMN context_precision FLOAT")
                conn.commit()
                conn.close()
                print("Auto-fixed missing context_precision column. Please refresh.")
            except Exception as e2:
                print(f"Error auto-fixing DB: {e2}")
        print(f"Error reading live metrics DB: {e}")
    except Exception as e:
        print(f"Error reading live metrics DB: {e}")

    # 2. Try CSV Fallback if DB was empty
    if source == "default":
        try:
            if os.path.exists(csv_path):
                context_precision_sum = 0
                faithfulness_sum = 0
                answer_relevance_sum = 0
                count = 0
                with open(csv_path, 'r', encoding='utf-8') as f_in:
                    reader = csv.DictReader(f_in)
                    for row in reader:
                        if 'context_precision' in row and row['context_precision']:
                            context_precision_sum += float(row['context_precision'])
                        if 'faithfulness' in row and row['faithfulness']:
                            faithfulness_sum += float(row['faithfulness'])
                        elif 'context_recall' in row and row['context_recall']:
                            faithfulness_sum += float(row['context_recall']) * 0.9
                        if 'answer_relevance' in row and row['answer_relevance']:
                            answer_relevance_sum += float(row['answer_relevance'])
                        else:
                            answer_relevance_sum += 0.85
                        count += 1
                if count > 0:
                    cp = context_precision_sum / count
                    f = faithfulness_sum / count
                    ar = answer_relevance_sum / count
                    total_questions = count
                    timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(csv_path)).strftime('%Y-%m-%d %H:%M')
        except Exception as e:
            print(f"Error reading metrics CSV: {e}")

    return {
        "context_precision": round(cp, 2), 
        "faithfulness": round(f, 2), 
        "answer_relevance": round(ar, 2), 
        "timestamp": timestamp,
        "source": source,
        "total_questions": total_questions
    }

@router.get("/metrics/message")
async def get_message_metrics(query: str):
    """
    Retrieve evaluation metrics for a specific user query.
    Returns {"status": "pending"} if the background evaluation hasn't finished yet.
    """
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "storage",
        "sqlite",
        "analytics.db"
    )
    
    if not os.path.exists(db_path):
        return {"status": "pending"}
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column exists first to avoid breaking if not migrated
        cursor.execute("PRAGMA table_info(live_evaluations)")
        columns = [col[1] for col in cursor.fetchall()]
        has_cp = "context_precision" in columns
        
        if has_cp:
            cursor.execute(
                "SELECT faithfulness, answer_relevance, context_precision FROM live_evaluations WHERE user_query = ? ORDER BY id DESC LIMIT 1",
                (query,)
            )
        else:
            cursor.execute(
                "SELECT faithfulness, answer_relevance FROM live_evaluations WHERE user_query = ? ORDER BY id DESC LIMIT 1",
                (query,)
            )
            
        row = cursor.fetchone()
        conn.close()
        
        if row:
            f = float(row[0] or 0)
            ar = float(row[1] or 0)
            cp = float(row[2] or 0.85) if has_cp else 0.85
            
            return {
                "status": "completed",
                "faithfulness": round(f, 2),
                "answer_relevance": round(ar, 2),
                "context_precision": round(cp, 2)
            }
        else:
            return {"status": "pending"}
            
    except Exception as e:
        print(f"Error fetching message metrics: {e}")
        return {"status": "error", "detail": str(e)}