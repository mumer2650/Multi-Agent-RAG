import sqlite3
import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

sql_llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

class SQLQueryOutput(BaseModel):
    sql_query: str = Field(description="The executable SQLite query")

# ── Static schema ──────────────────────────────────────────────────────────────
DB_SCHEMA = """
TABLE: categories
  id            INTEGER PRIMARY KEY
  category_name VARCHAR

TABLE: products
  id            INTEGER PRIMARY KEY
  category_id   INTEGER  → FK to categories.id
  model_name    VARCHAR
  price         INTEGER
  has_inverter  BOOLEAN   ← SHORTCUT: use directly (1 = inverter, 0 = non-inverter)
  energy_rating FLOAT     ← SHORTCUT: use directly for star-rating filters (e.g. = 5, >= 3)
  features_text TEXT

TABLE: product_specifications
  id         INTEGER PRIMARY KEY
  product_id INTEGER  → FK to products.id
  spec_name  VARCHAR
  spec_value VARCHAR   ← always VARCHAR; strip units before numeric comparison

TABLE: reviews
  id          INTEGER PRIMARY KEY
  product_id  INTEGER  → FK to products.id
  rating      INTEGER
  review_text TEXT
  sentiment   VARCHAR
"""

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "backend",
    "storage",
    "sqlite",
    "sage_appliances.db"
)

# ── Schema context cache ───────────────────────────────────────────────────────
_schema_context_cache: str | None = None


def get_live_schema_context() -> str:
    """
    Queries the DB once at startup. Builds a prompt block with:
      - All real category_name values
      - spec_names grouped by category (LLM knows which specs belong where)
      - Up to 3 sample spec_values per spec per category (shows exact format)
    """
    global _schema_context_cache
    if _schema_context_cache is not None:
        return _schema_context_cache

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Real category names
        cursor.execute(
            "SELECT DISTINCT category_name FROM categories ORDER BY category_name"
        )
        categories = [row[0] for row in cursor.fetchall()]

        # 2. Spec names + sample values grouped by category
        cursor.execute("""
            SELECT c.category_name, ps.spec_name, ps.spec_value
            FROM product_specifications ps
            JOIN products p ON ps.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            ORDER BY c.category_name, ps.spec_name, ps.spec_value
        """)

        cat_specs: dict[str, dict[str, list[str]]] = {}
        for cat_name, spec_name, spec_value in cursor.fetchall():
            cat_specs.setdefault(cat_name, {}).setdefault(spec_name, [])
            if len(cat_specs[cat_name][spec_name]) < 3:
                cat_specs[cat_name][spec_name].append(str(spec_value))

        conn.close()

        lines = [
            "=== REAL DATABASE VALUES — use these strings EXACTLY, never paraphrase ===\n",
            f"CATEGORY NAMES: {categories}\n",
            "SPEC NAMES per category with sample values",
            "(Only use spec_names listed under the relevant category. Never invent new ones.)\n",
        ]
        for cat in sorted(cat_specs.keys()):
            lines.append(f"  [{cat}]")
            for spec_name, samples in sorted(cat_specs[cat].items()):
                lines.append(f'    "{spec_name}"  →  e.g. {samples}')
            lines.append("")

        _schema_context_cache = "\n".join(lines)
        print("✅ Live schema context loaded into SQL agent.")
        return _schema_context_cache

    except Exception as e:
        print(f"⚠️  Could not load live schema context: {e}")
        return "(Live schema context unavailable — use best judgment.)"


# ── Aggregate query detector ───────────────────────────────────────────────────
def _is_aggregate_query(sql: str) -> bool:
    """
    Detects COUNT/AVG/SUM/MAX/MIN queries without GROUP BY.
    These return a single summary row, not a list of products.
    """
    upper = sql.upper()
    has_aggregate = any(fn in upper for fn in ("COUNT(", "AVG(", "SUM(", "MAX(", "MIN("))
    has_group_by  = "GROUP BY" in upper
    return has_aggregate and not has_group_by


# ── model_name safety net ──────────────────────────────────────────────────────
def _ensure_model_name(data: list[dict]) -> list[dict]:
    """
    Guarantees every row has a non-empty 'model_name' key so the
    answer_generator never shows 'Unknown model'.

    This is a safety net for two cases the answer_generator can't handle:

    Case 1 — COUNT / aggregate queries:
      SQL returns {'label': 'Samsung ACs with Wi-Fi', 'count': 3}
      → answer_generator can't find model_name → shows 'Unknown model'
      Fix: promote 'label' → 'model_name'

    Case 2 — GROUP BY category queries:
      SQL returns {'category_name': 'dishwashers', 'average_rating': 4.67}
      → answer_generator can't find model_name → shows 'Unknown model'
      Fix: promote 'category_name' → 'model_name'

    Priority order for promotion:
      model_name (already present) > label > category_name > category
      > first non-numeric string column > 'Result'
    """
    FALLBACK_KEYS = ["label", "category_name", "category", "name"]

    for row in data:
        # Already has a valid model_name — nothing to do
        if row.get("model_name"):
            continue

        promoted = False
        for key in FALLBACK_KEYS:
            if row.get(key):
                row["model_name"] = row[key]
                promoted = True
                break

        if not promoted:
            # Last resort: use the value of the first string column
            for value in row.values():
                if isinstance(value, str) and value.strip():
                    row["model_name"] = value
                    promoted = True
                    break

        if not promoted:
            row["model_name"] = "Result"

    return data


# ── Agent ──────────────────────────────────────────────────────────────────────

def sql_agent(state: dict) -> dict:
    query      = state.get("user_query", "")
    last_error = state.get("last_sql_error")
    attempts   = state.get("sql_attempts", 0)

    live_context = get_live_schema_context()

    prompt = f"""
You are a SQLite expert for a Samsung Appliances support system.

SCHEMA:
{DB_SCHEMA}

{live_context}

═══════════════════════════════════════════════
STRICT RULES — violating any rule causes empty or wrong results
═══════════════════════════════════════════════

RULE 1 — CATEGORY & SPEC NAMES:
  • Use ONLY category_name and spec_name values listed above.
  • ONLY use spec_names listed under the correct category — never borrow a
    spec_name from another category (e.g. 'Wi Fi' is a LED spec, not AC;
    AC Wi-Fi spec is listed under [air_conditioners] above).

RULE 2 — USE SHORTCUT COLUMNS FIRST:
  • For inverter questions → use products.has_inverter directly (1=yes, 0=no).
    ✓ Good: WHERE p.has_inverter = 1
    ✗ Bad:  WHERE ps.spec_name = 'Inverter' AND ps.spec_value = 'Yes'
  • For energy/star-rating questions → use products.energy_rating directly.
    ✓ Good: WHERE p.energy_rating = 5
    ✗ Bad:  WHERE ps.spec_name = 'Energy Rating' AND ps.spec_value = '5'

RULE 3 — SPEC VALUE MATCHING:
  • Boolean specs → use 'Yes' / 'No' exactly (never 'true'/'false'/'1'/'0').
  • String specs with units (BTU, kg, rpm, dB, kWh…) → ALWAYS use LIKE:
    ✓ Good: ps.spec_value LIKE '%18,000%'
    ✗ Bad:  ps.spec_value = '18000 Btu/hr'
  • Numeric comparisons on spec_value → strip unit first:
    CAST(REPLACE(REPLACE(ps.spec_value, ',', ''), ' BTU/Hr', '') AS FLOAT) > 12000

RULE 4 — TON-TO-BTU for AC capacity queries:
  • 1 ton   → LIKE '%12,000%'
  • 1.5 ton → LIKE '%18,000%'
  • 2 ton   → LIKE '%24,000%'
  Always use LIKE for BTU — the DB uses commas and mixed casing.

RULE 5 — ALWAYS alias the primary display column as model_name:
  The answer_generator reads the 'model_name' key from every row.
  If your query does NOT join products (e.g. category aggregates, counts),
  you MUST alias the main label column as model_name.

  ✓ Product queries (has p.model_name):
      SELECT p.model_name, p.price ...

  ✓ COUNT / single-number queries:
      SELECT 'Samsung ACs with Wi-Fi' AS model_name, COUNT(*) AS count ...

  ✓ GROUP BY category queries:
      SELECT c.category_name AS model_name, AVG(r.rating) AS average_rating ...

  ✓ Ranked / grouped product queries:
      SELECT p.model_name, COUNT(r.id) AS review_count ... GROUP BY p.id

  ✗ NEVER omit the display label:
      SELECT COUNT(DISTINCT p.id) ...   ← unreadable, no label

RULE 6 — DEDUPLICATION:
  Add DISTINCT when joining product_specifications to prevent duplicate rows.

RULE 7 — ALWAYS add LIMIT 100.

RULE 8 — Return ONLY the raw SQL. No markdown, no explanation.

USER QUESTION: {query}
"""

    if last_error:
        prompt += (
            f"\n\nYour previous attempt failed with this error:\n{last_error}\n"
            "Fix the error and try again."
        )

    structured_llm = sql_llm.with_structured_output(SQLQueryOutput)

    try:
        print(f"🗃️  Requesting SQL from Gemini (Attempt {attempts + 1})...")
        result        = structured_llm.invoke([{"role": "user", "content": prompt}])
        generated_sql = result.sql_query
        print(f"💻  Generated SQL: {generated_sql}")

        conn             = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor           = conn.cursor()
        cursor.execute(generated_sql)
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        conn.close()

        if not data:
            print("⚠️  SQL executed successfully but returned 0 results.")
            return {
                "tool_output"   : {"type": "sql_result", "action": "empty", "data": []},
                "sql_attempts"  : attempts + 1,
                "generated_sql" : generated_sql,
                "last_sql_error": None,
            }

        # Safety net: guarantee model_name exists in every row
        data = _ensure_model_name(data)

        action = "aggregate" if _is_aggregate_query(generated_sql) else "data_found"

        print(f"✅  SQL returned {len(data)} row(s). Action: {action}")
        return {
            "tool_output"   : {"type": "sql_result", "action": action, "data": data},
            "sql_attempts"  : attempts + 1,
            "generated_sql" : generated_sql,
            "last_sql_error": None,
        }

    except sqlite3.Error as e:
        print(f"❌  SQLite Error: {e}")
        return {
            "last_sql_error": str(e),
            "sql_attempts"  : attempts + 1,
        }

    except Exception as e:
        print(f"❌  Critical Error in SQL Agent: {e}")
        return {
            "last_sql_error": "Critical execution failure",
            "sql_attempts"  : attempts + 1,
        }
