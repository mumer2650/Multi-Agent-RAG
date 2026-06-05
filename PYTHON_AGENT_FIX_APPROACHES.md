# Python Agent Database Integration - Approaches Analysis

## Problem
Python agent is not fetching real database data. Responses are generic/hallucinated instead of using actual product data.

**Current Behavior:**
- Query: "5-year TCO for top 3 Samsung ACs"
- Expected: Real AC models from DB with calculated costs
- Actual: Generic response "I do not have that information"

**Root Cause:** 
- `fetch_sql_data()` calls `sql_agent()` which requires full GraphState
- Minimal state creation is insufficient
- SQL agent may fail silently or return empty results
- Python agent falls back gracefully, leading to LLM-generated generic responses

---

## Approach 1: Call SQL Agent with Complete State
**Implementation:** Build complete GraphState before calling sql_agent

```python
def fetch_sql_data(user_query: str, category: str):
    complete_state = {
        "user_query": user_query,
        "category": category,
        "selected_agent": "sql",
        "messages": [],
        "retrieved_docs": [],
        "tool_output": None,
        # ... all 20+ GraphState fields
    }
    result = sql_agent(complete_state)
    return result.get("tool_output", {}).get("data", [])
```

**Pros:**
- Uses existing, tested sql_agent
- No code duplication
- Follows established patterns

**Cons:**
- Requires maintaining 20+ state fields
- Still state-dependent, error-prone
- Complex state setup for simple query
- May fail if state initialization is incomplete

---

## Approach 2: Extract SQL Generation Logic into Python Agent
**Implementation:** Replicate Gemini SQL generation directly in python_agent

```python
def _generate_sql_with_schema(user_query: str, category: str):
    # 1. Get live schema like sql_agent does
    schema = get_live_schema_context()
    
    # 2. Build Gemini prompt with same rules as sql_agent
    prompt = f"""
    Use these EXACT schema values...
    RULES:
    - Use shortcut columns (has_inverter, energy_rating)
    - Use LIKE for units (BTU, kg, etc)
    - Alias primary column as model_name
    ...
    QUERY: {user_query}
    """
    
    # 3. Call Gemini
    structured_llm = ChatGoogleGenerativeAI(...).with_structured_output(SQLQueryOutput)
    result = structured_llm.invoke([{"role": "user", "content": prompt}])
    
    # 4. Execute and return
    sql = result.sql_query
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]
```

**Pros:**
- Self-contained in python_agent
- No state dependencies
- Direct DB access (fast)
- Follows proven sql_agent pattern
- Easy to debug and improve

**Cons:**
- Code duplication with sql_agent
- Need to maintain schema logic separately
- Error handling is local (may differ from sql_agent)

---

## Approach 3: Direct SQLite Queries (Simple Intent Matching)
**Implementation:** Build SQL queries directly based on query pattern matching

```python
def _fetch_products_by_intent(user_query: str, category: str):
    if "efficiency ratio" in user_query:
        # Direct SQL for efficiency analysis
        sql = """
        SELECT p.model_name, p.price, ps.spec_value as capacity
        FROM products p
        WHERE category = ?
        """
    elif "5-year" in user_query or "total cost" in user_query:
        sql = """
        SELECT p.model_name, p.price, p.energy_rating
        FROM products p
        WHERE category = ? AND price > 0
        ORDER BY p.price DESC LIMIT 3
        """
    # ... more patterns
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql, (category,))
    return [dict(zip([col[0] for col in cursor.description], row)) 
            for row in cursor.fetchall()]
```

**Pros:**
- Very fast, no Gemini overhead
- Reliable for known patterns
- Minimal code

**Cons:**
- Not flexible for varied user questions
- Hard to maintain as queries grow
- Limited to predefined patterns
- Cannot handle complex or creative queries

---

## Approach 4: Hybrid - Try Gemini-Generated SQL, Fall Back to Direct Queries
**Implementation:** Attempt intelligent SQL generation, fall back to pattern-based

```python
def fetch_sql_data(user_query: str, category: str):
    # Try Gemini approach (Approach 2)
    try:
        products = _generate_sql_with_schema(user_query, category)
        if products and len(products) > 0:
            return products
    except Exception as e:
        print(f"Gemini SQL generation failed: {e}")
    
    # Fall back to pattern matching (Approach 3)
    try:
        products = _fetch_products_by_intent(user_query, category)
        if products:
            return products
    except Exception as e:
        print(f"Pattern matching failed: {e}")
    
    # Final fallback: return empty
    return []
```

**Pros:**
- Best of both worlds
- Handles edge cases gracefully
- Fallback ensures some data is returned

**Cons:**
- More complex code
- Multiple failure points
- Harder to debug

---

## Approach 5: Create Wrapper Around SQL Agent with Proper State Builder
**Implementation:** Build a dedicated state initializer for sql_agent calls

```python
def _build_complete_graph_state(user_query: str, category: str) -> Dict[str, Any]:
    """Initialize complete GraphState for sql_agent"""
    return {
        "messages": [{"role": "user", "content": user_query}],
        "user_query": user_query,
        "selected_agent": "sql",
        "tool_required": True,
        "competitor_detected": False,
        "off_topic": False,
        "category": category,
        "retrieved_docs": [],
        "retrieval_error": None,
        "retrieval_attempts": 0,
        "max_retrieval_attempts": 3,
        "sql_attempts": 0,
        "max_sql_attempts": 3,
        "last_sql_error": None,
        "generated_sql": None,
        "tool_output": None,
        "citations": [],
        "validation_passed": False,
        "validation_reason": None,
        "chart": None,
        "final_answer": None,
        "error": None
    }

def fetch_sql_data(user_query: str, category: str):
    state = _build_complete_graph_state(user_query, category)
    result = sql_agent(state)
    return result.get("tool_output", {}).get("data", [])
```

**Pros:**
- Uses proven sql_agent
- Explicit state contract
- Easy to update if GraphState changes

**Cons:**
- Still state-dependent
- Duplicates state structure
- Fragile - breaks if GraphState changes
- More boilerplate than needed

---

## Approach 6: SQL Agent Query Function (NO State Required) ⭐ RECOMMENDED
**Implementation:** Extract just the query generation logic as standalone utility

```python
def get_live_schema_context() -> str:
    """Get real DB values - same as sql_agent uses"""
    # ... existing code from sql_agent ...

def generate_sql_query(user_query: str, category: str) -> str:
    """Generate SQL using Gemini - NO state needed"""
    schema = get_live_schema_context()
    
    prompt = f"""
    {schema}
    
    RULES:
    1. Use ONLY category_name and spec_name values listed above
    2. Use shortcut columns: has_inverter, energy_rating
    3. Boolean specs use 'Yes'/'No'
    4. String specs with units use LIKE
    5. Always alias primary column as model_name
    6. Add LIMIT 100
    7. Return ONLY raw SQL
    
    QUERY: {user_query}
    """
    
    structured_llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite",
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    ).with_structured_output(SQLQueryOutput)
    
    result = structured_llm.invoke([{"role": "user", "content": prompt}])
    return result.sql_query

def execute_sql_query(sql_query: str) -> List[Dict[str, Any]]:
    """Execute SQL and return results - reusable utility"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"SQL Error: {e}")
        return []

def fetch_sql_data(user_query: str, category: str) -> List[Dict[str, Any]]:
    """Fetch products matching query - uses Gemini + DB directly"""
    try:
        sql = generate_sql_query(user_query, category)
        print(f"Generated SQL: {sql}")
        products = execute_sql_query(sql)
        print(f"Fetched {len(products)} products")
        return products
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return []
```

**Pros:**
- ✅ Completely standalone, no state needed
- ✅ Reuses proven schema & rule system
- ✅ Clear separation of concerns
- ✅ Easy to test independently
- ✅ Fast, direct DB access
- ✅ Easy to debug Gemini prompts
- ✅ Maintains consistency with sql_agent
- ✅ No duplication of state initialization logic

**Cons:**
- Duplicates schema context logic (but this is stable)
- Doesn't integrate with workflow (doesn't need to)

---

## Approach 7: Create Shared SQL Module (Future Cleanup)
**Implementation:** Extract common SQL utilities to shared module

```
ai_core/
├── agents/
│   ├── sql_agent.py
│   └── python_agent.py
├── utils/
│   └── sql_utils.py  ← NEW: Shared SQL utilities
```

```python
# ai_core/utils/sql_utils.py
from langchain_google_genai import ChatGoogleGenerativeAI
import sqlite3
import os

class SQLExecutor:
    def __init__(self):
        self.db_path = ...
        self.llm = ChatGoogleGenerativeAI(...)
    
    def get_schema_context(self) -> str: ...
    def generate_query(self, question: str) -> str: ...
    def execute_query(self, sql: str) -> List[Dict]: ...
    def fetch_data(self, question: str) -> List[Dict]: ...

# Both sql_agent and python_agent import and use SQLExecutor
```

**Pros:**
- ✅ Eliminates code duplication
- ✅ Single source of truth for SQL logic
- ✅ Both agents stay in sync

**Cons:**
- Requires refactoring sql_agent
- More complex structure
- Delayed benefit (useful later, not immediate fix)

---

## Comparison Table

| Approach | Effort | Speed | Reliability | Maintainability | State-Free | Score |
|----------|--------|-------|-------------|-----------------|-----------|-------|
| 1. Complete State | Medium | Slow | Medium | Medium | ❌ | 5/10 |
| 2. Replicate Logic | High | Fast | High | Low | ✅ | 6/10 |
| 3. Direct Pattern SQL | Low | Fast | Low | Low | ✅ | 4/10 |
| 4. Hybrid | High | Medium | Medium | Low | ✅ | 5/10 |
| 5. State Wrapper | Low | Slow | Low | Medium | ❌ | 4/10 |
| **6. Standalone Utilities** | **Medium** | **Fast** | **High** | **High** | **✅** | **8/10** |
| 7. Shared Module | High | Fast | High | High | ✅ | 9/10 |

---

## 🎯 RECOMMENDED APPROACH: #6 (Standalone SQL Utilities)

### Why?
1. **No State Dependencies** - Works in isolation
2. **Proven Pattern** - Copies working sql_agent logic
3. **Fast Execution** - Direct DB access
4. **Easy Debugging** - Standalone functions
5. **Quick Implementation** - 50 lines of focused code
6. **Future Path** - Can upgrade to Approach 7 later

### Implementation Steps:
1. ✅ Copy `get_live_schema_context()` into python_agent
2. ✅ Create `generate_sql_query()` using same Gemini + schema pattern
3. ✅ Create `execute_sql_query()` for direct SQLite execution
4. ✅ Wrap with `fetch_sql_data()` for clean interface
5. ✅ Update analysis functions to use fetched data
6. ✅ Add error handling and logging

### Expected Results:
- ✅ Queries return REAL product data
- ✅ Calculations use ACTUAL prices/specs
- ✅ No more generic responses
- ✅ Full traceability via logs

---

## After Initial Fix (Future Enhancement)
Once #6 is working and stable, refactor to Approach 7:
- Extract to `ai_core/utils/sql_utils.py`
- Both sql_agent and python_agent use shared SQLExecutor
- Eliminates duplication
- Single configuration point for DB queries
