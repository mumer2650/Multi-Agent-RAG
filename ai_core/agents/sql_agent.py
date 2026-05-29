import sqlite3
import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# Gemini handles text-to-SQL highly accurately
sql_llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite", 
    temperature=0, 
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

class SQLQueryOutput(BaseModel):
    sql_query: str = Field(description="The executable SQLite query")

# Accurate schema derived from your SQLAlchemy models
DB_SCHEMA = """
TABLE: categories
COLUMNS: id (INTEGER PRIMARY KEY), category_name (VARCHAR)  
            here the category_name can consist these values ['air_conditioners','buds','dishwashers','dispenser','LEDs','refrigerators','washing_machines'] or 'unknown' if you are unable to identify the category

TABLE: products
COLUMNS: id (INTEGER PRIMARY KEY), category_id (INTEGER FOREIGN KEY to categories.id), model_name (VARCHAR), price (INTEGER), has_inverter (BOOLEAN), energy_rating (FLOAT), features_text (TEXT)

TABLE: product_specifications
COLUMNS: id (INTEGER PRIMARY KEY), product_id (INTEGER FOREIGN KEY to products.id), spec_name (VARCHAR), spec_value (VARCHAR)

TABLE: reviews
COLUMNS: id (INTEGER PRIMARY KEY), product_id (INTEGER FOREIGN KEY to products.id), rating (INTEGER), review_text (TEXT), sentiment (VARCHAR)

NOTE ON JOINS: To search for products by category (like 'air_conditioners'), you MUST use an INNER JOIN connecting products.category_id to categories.id.
"""

# Path to your database
#DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "sage_appliances.db")

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
    "backend", 
    "storage", 
    "sqlite", 
    "sage_appliances.db"
)

def sql_agent(state):
    query = state.get("user_query", "")
    last_error = state.get("last_sql_error")
    attempts = state.get("sql_attempts", 0)

    # 1. Ask Gemini to write the SQL
    prompt = f"""
    You are a SQLite expert for Samsung Appliances. Write a SQL query to answer the user's question based ONLY on the schema provided.
    
    CRITICAL RULES:
    1. NEVER select just one column. You MUST ALWAYS use 'SELECT *' (or 'SELECT T1.*, T2.*' if using JOINs) so the downstream agent can see prices, ratings, and features.
    2. If the user asks for prices 'under' or 'cheaper', use the < operator.
    3. Return ONLY the raw SQL query. Do not add markdown formatting.
    4.If filtering by specifications, use a JOIN with product_specifications.

    SCHEMA:
    {DB_SCHEMA}

    USER QUESTION: {query}
    """

    # Retry loop context: Feed the error back to Gemini so it fixes its mistake
    if last_error:
        prompt += f"\n\nWARNING: Your previous attempt failed with this error: {last_error}\nPlease fix the SQL syntax and try again."

    structured_llm = sql_llm.with_structured_output(SQLQueryOutput)
    
    try:
        print(f"🗃️ Requesting SQL from Gemini (Attempt {attempts + 1})...")
        result = structured_llm.invoke([{"role": "user", "content": prompt}])
        generated_sql = result.sql_query
        print(f"💻 Generated SQL: {generated_sql}")

        # 2. Execute the SQL directly against the database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        cursor.execute(generated_sql)
        rows = cursor.fetchall()
        
        data = [dict(row) for row in rows]
        conn.close()

        # If valid SQL is generated but the table returns 0 results
        if not data:
            return {
                "tool_output": {"type": "sql_result", "action": "empty", "data": []},
                "sql_attempts": attempts + 1,
                "generated_sql": generated_sql,
                "last_sql_error": None
            }

        # Success
        return {
            "tool_output": {"type": "sql_result", "action": "data_found", "data": data},
            "sql_attempts": attempts + 1,
            "generated_sql": generated_sql,
            "last_sql_error": None
        }

    except sqlite3.Error as e:
        error_msg = str(e)
        print(f"❌ SQLite Error: {error_msg}")
        return {
            "last_sql_error": error_msg,
            "sql_attempts": attempts + 1
        }
    except Exception as e:
        print(f"❌ Critical Error in SQL Agent: {e}")
        return {
            "last_sql_error": "Critical execution failure",
            "sql_attempts": attempts + 1
        }