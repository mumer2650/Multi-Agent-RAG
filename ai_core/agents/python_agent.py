from typing import Dict, Any, List, Tuple
import statistics
import json
import math
import sqlite3
import os
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONSTANTS & LOOKUP TABLES
# =========================================================

# Database Configuration
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "backend",
    "storage",
    "sqlite",
    "sage_appliances.db"
)

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
  energy_rating FLOAT     ← SHORTCUT: use directly for star-rating filters
  features_text TEXT

TABLE: product_specifications
  id         INTEGER PRIMARY KEY
  product_id INTEGER  → FK to products.id
  spec_name  VARCHAR
  spec_value VARCHAR

TABLE: reviews
  id          INTEGER PRIMARY KEY
  product_id  INTEGER  → FK to products.id
  rating      INTEGER
  review_text TEXT
  sentiment   VARCHAR
"""

class SQLQueryOutput(BaseModel):
    sql_query: str = Field(description="The executable SQLite query")

# Schema cache
_schema_context_cache: str | None = None
LESCO_RATES = {
    "0_50": 9.18,
    "51_100": 12.42,
    "101_200": 15.03,
    "201_300": 18.54,
    "301_plus": 22.45
}

# Unit Conversions
BTU_PER_TON = 12000
AC_TON_TO_BTU = {
    0.5: 6000,
    0.75: 9000,
    1.0: 12000,
    1.5: 18000,
    2.0: 24000,
}

# Category Power Consumption Estimates (Watts - defaults if not in specs)
POWER_CONSUMPTION_DEFAULTS = {
    "air_conditioners": 1500,      # 1.5 ton AC ~1500W
    "refrigerators": 150,           # Avg fridge ~150W
    "washing_machines": 500,        # Avg washer ~500W
    "dishwasher": 1800,
    "leds": 50,
    "buds": 2,
    "dispenser": 300,
}

# CO2 Emission Factor (kg CO2 per kWh in Pakistan grid)
CO2_KG_PER_KWH = 0.79

# Daily Usage Hours by Category (defaults)
DAILY_USAGE_HOURS = {
    "air_conditioners": 8,
    "refrigerators": 24,
    "washing_machines": 1,
    "dishwasher": 1.5,
    "leds": 10,
    "buds": 4,
    "dispenser": 8,
}

# =========================================================
# STANDALONE SQL UTILITIES (Approach #6)
# =========================================================

def get_live_schema_context() -> str:
    """
    Get real database values for schema context.
    Caches result to avoid repeated DB queries.
    """
    global _schema_context_cache
    if _schema_context_cache is not None:
        return _schema_context_cache

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get real category names
        cursor.execute(
            "SELECT DISTINCT category_name FROM categories ORDER BY category_name"
        )
        categories = [row[0] for row in cursor.fetchall()]

        # Get spec names + sample values grouped by category
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
            "=== REAL DATABASE VALUES — use these strings EXACTLY ===\n",
            f"CATEGORY NAMES: {categories}\n",
            "SPEC NAMES per category with sample values:\n",
        ]
        for cat in sorted(cat_specs.keys()):
            lines.append(f"  [{cat}]")
            for spec_name, samples in sorted(cat_specs[cat].items()):
                lines.append(f'    "{spec_name}"  →  e.g. {samples}')
            lines.append("")

        _schema_context_cache = "\n".join(lines)
        print("[Schema] Live schema context loaded (cached)")
        return _schema_context_cache

    except Exception as e:
        print(f"[Schema Error] Could not load schema: {e}")
        return "(Schema context unavailable)"


def generate_sql_query(user_query: str, category: str) -> str:
    """
    Use Gemini to generate SQLite query based on user question.
    Returns raw SQL query string.
    """
    try:
        live_context = get_live_schema_context()

        prompt = f"""
You are a SQLite expert for a Samsung Appliances database.

SCHEMA:
{DB_SCHEMA}

{live_context}

═══════════════════════════════════════════════
STRICT RULES
═══════════════════════════════════════════════

RULE 1 — Use ONLY category_name and spec_name values listed above.
RULE 2 — Use shortcut columns: has_inverter (1=yes), energy_rating (1-5 stars).
RULE 3 — Boolean specs use 'Yes'/'No' exactly.
RULE 4 — String specs with units (BTU, kg, rpm, dB) use LIKE: ps.spec_value LIKE '%18,000%'
RULE 5 — ALWAYS alias primary column as model_name (or category_name AS model_name).
RULE 6 — Add DISTINCT when joining product_specifications.
RULE 7 — Always add LIMIT 100.
RULE 8 — Return ONLY raw SQL. No markdown, no explanation.

QUESTION: {user_query}
PRODUCT CATEGORY: {category}
"""

        sql_llm = ChatGoogleGenerativeAI(
            model="gemini-3.1-flash-lite",
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )

        structured_llm = sql_llm.with_structured_output(SQLQueryOutput)
        result = structured_llm.invoke([{"role": "user", "content": prompt}])

        sql_query = result.sql_query
        print(f"[SQL Generated] {sql_query[:100]}...")
        return sql_query

    except Exception as e:
        print(f"[SQL Generation Error] {str(e)}")
        return ""


def execute_sql_query(sql_query: str) -> List[Dict[str, Any]]:
    """
    Execute SQL query directly against database.
    Returns list of result dictionaries.
    """
    if not sql_query:
        print("[SQL Exec] No query provided")
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print(f"[SQL Exec] Executing query...")
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        conn.close()

        print(f"[SQL Exec] Returned {len(data)} rows")
        return data

    except sqlite3.Error as e:
        print(f"[SQL Error] {str(e)}")
        return []
    except Exception as e:
        print(f"[SQL Exec Error] {str(e)}")
        return []


def fetch_sql_data(user_query: str, category: str) -> List[Dict[str, Any]]:
    """
    Fetch products from database using Gemini-generated SQL.
    Standalone implementation (no state dependency).
    Returns: list of product records from database
    """
    try:
        print(f"[Python Agent] Fetching data for: {user_query[:60]}...")

        # Step 1: Generate SQL query using Gemini
        sql_query = generate_sql_query(user_query, category)
        if not sql_query:
            print("[Python Agent] Failed to generate SQL query")
            return []

        # Step 2: Execute query directly
        products = execute_sql_query(sql_query)

        if not products:
            print("[Python Agent] No products returned from query")
            return []

        print(f"[Python Agent] Successfully fetched {len(products)} products")
        return products

    except Exception as e:
        print(f"[Python Agent] Error fetching data: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


# =========================================================
# UTILITY FUNCTIONS - LESCO RATE CALCULATION
# =========================================================

def get_lesco_rate_for_usage(kwh_monthly: float) -> float:
    """
    Returns appropriate LESCO rate (Rs/kWh) based on monthly consumption slab.
    """
    if kwh_monthly <= 50:
        return LESCO_RATES["0_50"]
    elif kwh_monthly <= 100:
        return LESCO_RATES["51_100"]
    elif kwh_monthly <= 200:
        return LESCO_RATES["101_200"]
    elif kwh_monthly <= 300:
        return LESCO_RATES["201_300"]
    else:
        return LESCO_RATES["301_plus"]


def extract_power_watts(product: Dict[str, Any], category: str = None) -> float:
    """
    Extracts power consumption (watts) from product specs or returns default.
    Looks for spec_name patterns: "power", "watts", "wattage", "consumption"
    """
    if not product:
        return POWER_CONSUMPTION_DEFAULTS.get(category, 500)

    # Check if power_consumption_watts is already extracted by SQL
    if "power_consumption_watts" in product and product["power_consumption_watts"]:
        try:
            return float(product["power_consumption_watts"])
        except:
            pass

    # Look in features_text or specs
    features = product.get("features_text", "").lower()
    if "watt" in features:
        try:
            import re
            match = re.search(r'(\d+)\s*w(?:att)?s?', features)
            if match:
                return float(match.group(1))
        except:
            pass

    # Return category default
    return POWER_CONSUMPTION_DEFAULTS.get(category, 500)


def extract_capacity(product: Dict[str, Any], category: str = None) -> float:
    """
    Extracts capacity from product specs based on category.
    AC: BTU/Tons, Fridge: Liters, Washer: kg, Dishwasher: place settings
    """
    if not product:
        return 0

    if "capacity_value" in product and product["capacity_value"]:
        try:
            return float(product["capacity_value"])
        except:
            pass

    # Look in features_text for hints
    features = product.get("features_text", "").lower()

    if category == "air_conditioners":
        # Look for ton or BTU
        if "ton" in features:
            import re
            match = re.search(r'(\d+\.?\d*)\s*ton', features)
            if match:
                return float(match.group(1))
        if "btu" in features:
            import re
            match = re.search(r'(\d+,?\d*)\s*btu', features)
            if match:
                return float(match.group(1).replace(",", ""))

    elif category == "refrigerators":
        # Look for liters
        if "liter" in features or "l" in features:
            import re
            match = re.search(r'(\d+)\s*l(?:iter)?s?', features)
            if match:
                return float(match.group(1))

    elif category == "washing_machines":
        # Look for kg capacity
        if "kg" in features:
            import re
            match = re.search(r'(\d+)\s*kg', features)
            if match:
                return float(match.group(1))

    return 0


def extract_noise_level(product: Dict[str, Any]) -> float:
    """Extracts noise level in dB from product specs."""
    if "noise_level_db" in product and product["noise_level_db"]:
        try:
            return float(product["noise_level_db"])
        except:
            pass

    features = product.get("features_text", "").lower()
    if "db" in features:
        import re
        match = re.search(r'(\d+)\s*db', features)
        if match:
            return float(match.group(1))

    return None


# =========================================================
# CALCULATION UTILITIES
# =========================================================

def calculate_daily_electricity_cost(
    power_watts: float,
    daily_hours: float,
    lesco_rate: float
) -> float:
    """
    Calculate daily electricity cost.
    daily_hours: hours the appliance runs per day
    returns: cost in Rs
    """
    daily_kwh = (power_watts * daily_hours) / 1000
    return daily_kwh * lesco_rate


def calculate_monthly_electricity_cost(
    power_watts: float,
    daily_hours: float,
    days_per_month: float = 30
) -> Tuple[float, float]:
    """
    Calculate monthly electricity cost with appropriate LESCO slab.
    Returns: (monthly_kwh, monthly_cost_rs)
    """
    daily_kwh = (power_watts * daily_hours) / 1000
    monthly_kwh = daily_kwh * days_per_month
    lesco_rate = get_lesco_rate_for_usage(monthly_kwh)
    monthly_cost = monthly_kwh * lesco_rate
    return monthly_kwh, monthly_cost


def calculate_annual_electricity_cost(
    power_watts: float,
    daily_hours: float
) -> Tuple[float, float]:
    """
    Calculate annual electricity cost.
    Returns: (annual_kwh, annual_cost_rs)
    """
    daily_kwh = (power_watts * daily_hours) / 1000
    annual_kwh = daily_kwh * 365
    avg_lesco_rate = statistics.mean(LESCO_RATES.values())
    annual_cost = annual_kwh * avg_lesco_rate
    return annual_kwh, annual_cost


def calculate_5year_ownership_cost(
    purchase_price: float,
    power_watts: float,
    daily_hours: float,
    years: int = 5
) -> Tuple[float, float, float]:
    """
    Calculate total cost of ownership over N years (purchase + electricity).
    Returns: (total_electricity_cost, total_ownership_cost, avg_yearly_electricity)
    """
    daily_kwh = (power_watts * daily_hours) / 1000
    avg_lesco_rate = statistics.mean(LESCO_RATES.values())
    annual_electricity_cost = daily_kwh * 365 * avg_lesco_rate
    total_electricity = annual_electricity_cost * years
    total_ownership = purchase_price + total_electricity
    return total_electricity, total_ownership, annual_electricity_cost


def calculate_payback_period(
    premium_price: float,
    annual_savings: float
) -> float:
    """
    Calculate payback period in months.
    premium_price: extra cost of efficient model
    annual_savings: annual electricity savings in Rs
    returns: months to break even
    """
    if annual_savings <= 0:
        return float('inf')
    monthly_savings = annual_savings / 12
    months = premium_price / monthly_savings
    return months


def calculate_energy_efficiency_ratio(
    capacity_unit: float,
    power_watts: float
) -> float:
    """
    Calculate energy efficiency (capacity per watt).
    Higher is better. Interpretation varies by category.
    """
    if power_watts <= 0:
        return 0
    return capacity_unit / power_watts


def estimate_co2_savings(
    kwh_saved_annually: float,
    years: int = 5
) -> float:
    """
    Estimate CO2 emissions reduced over N years.
    Returns: kg CO2 saved
    """
    annual_co2_saved = kwh_saved_annually * CO2_KG_PER_KWH
    total_co2_saved = annual_co2_saved * years
    return total_co2_saved


def calculate_sentiment_ratio(
    reviews: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Calculate sentiment ratio from reviews.
    Assumes review has 'sentiment' field or infers from rating.
    Returns: {"positive_pct": X, "negative_pct": Y, "neutral_pct": Z}
    """
    if not reviews:
        return {"positive_pct": 0, "negative_pct": 0, "neutral_pct": 100}

    positive = 0
    negative = 0
    neutral = 0

    for review in reviews:
        sentiment = review.get("sentiment", "").lower()
        rating = review.get("rating", 3)

        if sentiment in ["positive", "good", "excellent"]:
            positive += 1
        elif sentiment in ["negative", "poor", "bad"]:
            negative += 1
        elif rating >= 4:
            positive += 1
        elif rating <= 2:
            negative += 1
        else:
            neutral += 1

    total = len(reviews)
    return {
        "positive_pct": round(100 * positive / total, 2),
        "negative_pct": round(100 * negative / total, 2),
        "neutral_pct": round(100 * neutral / total, 2)
    }


def score_products_by_criteria(
    products: List[Dict[str, Any]],
    criteria_weights: Dict[str, float],
    category: str = None
) -> List[Dict[str, float]]:
    """
    Score products on weighted multi-criteria basis.
    criteria_weights: {"price": 0.3, "efficiency": 0.4, "rating": 0.3}
    Normalizes each criterion to 0-100 scale first.
    Returns: list of {model_name, score}
    """
    if not products or not criteria_weights:
        return []

    scores = []

    for product in products:
        score = 0

        for criterion, weight in criteria_weights.items():
            if criterion == "price":
                # Lower price is better - invert scale
                prices = [p.get("price", 999999) for p in products if p.get("price")]
                if prices:
                    max_price = max(prices)
                    normalized = 100 * (1 - (product.get("price", max_price) / max_price))
                    score += normalized * weight

            elif criterion == "efficiency":
                # Higher efficiency is better
                power = extract_power_watts(product, category)
                capacity = extract_capacity(product, category)
                efficiency = calculate_energy_efficiency_ratio(capacity, power) if power > 0 else 0
                efficiencies = [
                    calculate_energy_efficiency_ratio(
                        extract_capacity(p, category),
                        extract_power_watts(p, category)
                    )
                    for p in products
                ]
                max_eff = max(efficiencies) if efficiencies else 1
                normalized = 100 * (efficiency / max_eff) if max_eff > 0 else 0
                score += normalized * weight

            elif criterion == "rating":
                # Higher rating is better (1-5 scale normalized to 0-100)
                rating = product.get("energy_rating", 3)
                normalized = 100 * (rating / 5)
                score += normalized * weight

        scores.append({
            "model_name": product.get("model_name", "Unknown"),
            "score": round(score, 2)
        })

    # Sort by score descending
    return sorted(scores, key=lambda x: x["score"], reverse=True)


def room_size_from_capacity(capacity_btu: float) -> float:
    """
    Estimate suitable room size (sq ft) for AC based on cooling capacity.
    Standard: 400-600 sq ft per 12,000 BTU (1 ton)
    Using middle estimate: 500 sq ft per ton
    """
    tons = capacity_btu / BTU_PER_TON
    return tons * 500


def calculate_earbud_charge_cycles(
    battery_mah: float,
    daily_usage_hours: float
) -> Tuple[float, float]:
    """
    Calculate earbud charge cycles per month.
    Assumes typical earbud gives 5-8 hours per charge (use 6 as default).
    Returns: (full_charges_needed_per_month, case_charge_frequency_days)
    """
    hours_per_charge = 6  # Typical earbud battery life
    monthly_usage = daily_usage_hours * 30
    full_charges = monthly_usage / hours_per_charge

    # Assuming case has 3-4 full charges capacity
    case_capacity = 3
    case_recharge_days = (case_capacity * hours_per_charge) / daily_usage_hours

    return round(full_charges, 2), round(case_recharge_days, 1)


def calculate_water_savings(
    dishwasher_place_settings: float,
    liters_per_setting_hand_wash: float = 25,
    liters_per_setting_machine: float = 10,
    cycles_per_year: float = 300
) -> Tuple[float, float]:
    """
    Calculate water savings when using dishwasher vs hand-washing.
    Returns: (annual_liters_saved, daily_average_liters_saved)
    """
    annual_hand_wash = dishwasher_place_settings * liters_per_setting_hand_wash * cycles_per_year
    annual_machine_wash = dishwasher_place_settings * liters_per_setting_machine * cycles_per_year
    annual_saved = annual_hand_wash - annual_machine_wash
    daily_saved = annual_saved / 365

    return annual_saved, daily_saved


# =========================================================
# VISUALIZATION BUILDERS
# =========================================================

def build_price_chart(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build bar chart for price comparison."""
    return {
        "chartType": "bar",
        "title": "Price Comparison",
        "xKey": "model",
        "yKey": "price",
        "data": [
            {
                "model": p.get("model_name", "Unknown"),
                "price": p.get("price", 0)
            }
            for p in products if p.get("price")
        ]
    }


def build_energy_chart(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build bar chart for energy ratings."""
    return {
        "chartType": "bar",
        "title": "Energy Efficiency Ratings",
        "xKey": "model",
        "yKey": "energy_rating",
        "data": [
            {
                "model": p.get("model_name", "Unknown"),
                "energy_rating": p.get("energy_rating", 0)
            }
            for p in products
        ]
    }


def build_scatter_chart(
    products: List[Dict[str, Any]],
    x_key: str,
    y_key: str,
    title: str
) -> Dict[str, Any]:
    """Build scatter chart for two-variable comparison."""
    return {
        "chartType": "scatter",
        "title": title,
        "xKey": x_key,
        "yKey": y_key,
        "data": [
            {
                "model": p.get("model_name", "Unknown"),
                x_key: p.get(x_key, 0),
                y_key: p.get(y_key, 0)
            }
            for p in products if p.get(x_key) and p.get(y_key)
        ]
    }


def build_noise_level_chart(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build bar chart for noise levels in dB."""
    data = []
    for p in products:
        noise = extract_noise_level(p)
        if noise:
            data.append({
                "model": p.get("model_name", "Unknown"),
                "noise_db": noise
            })

    return {
        "chartType": "bar",
        "title": "Noise Levels (dB)",
        "xKey": "model",
        "yKey": "noise_db",
        "data": data
    }


def build_cost_breakdown_chart(
    appliances: List[Dict[str, Any]],
    daily_hours: Dict[str, float]
) -> Dict[str, Any]:
    """
    Build stacked bar chart for monthly electricity cost breakdown.
    appliances: [{model_name, category, power_watts}, ...]
    daily_hours: {category: hours} e.g. {"refrigerators": 24, "air_conditioners": 8}
    """
    data = []
    for app in appliances:
        category = app.get("category", "unknown")
        power = extract_power_watts(app, category)
        hours = daily_hours.get(category, 0)
        _, monthly_cost = calculate_monthly_electricity_cost(power, hours)
        data.append({
            "appliance": app.get("model_name", "Unknown"),
            "monthly_cost": round(monthly_cost, 2)
        })

    return {
        "chartType": "bar",
        "title": "Monthly Electricity Cost Breakdown (Appliances)",
        "xKey": "appliance",
        "yKey": "monthly_cost",
        "data": data
    }


def build_sentiment_chart(
    categories: List[str],
    sentiments: List[Dict[str, float]]
) -> Dict[str, Any]:
    """
    Build sentiment visualization by product category.
    sentiments: [{"category": "AC", "positive": 70, "negative": 20, "neutral": 10}, ...]
    """
    return {
        "chartType": "bar",
        "title": "Sentiment Analysis by Product Category",
        "xKey": "category",
        "yKey": "positive_pct",
        "data": sentiments
    }


def build_cost_trend_chart(
    years: List[int],
    costs: List[float],
    title: str = "Total Cost of Ownership Over Time"
) -> Dict[str, Any]:
    """Build line chart for cost trends over years."""
    return {
        "chartType": "line",
        "title": title,
        "xKey": "year",
        "yKey": "cost",
        "data": [
            {"year": y, "cost": c}
            for y, c in zip(years, costs)
        ]
    }


# =========================================================
# QUERY DETECTION FUNCTIONS
# =========================================================

def detect_electricity_cost_query(query: str) -> bool:
    """Detects: monthly bill, annual cost, electricity cost calculations."""
    keywords = ["electricity bill", "monthly bill", "annual cost", "electricity", "cost",
                "monthly electricity", "electric bill", "power bill", "kwh cost"]
    return any(kw in query.lower() for kw in keywords)


def detect_efficiency_ratio_query(query: str) -> bool:
    """Detects: energy efficiency ratio, capacity per watt."""
    keywords = ["efficiency ratio", "energy efficient", "per watt", "capacity per",
                "efficient ratio", "energy efficiency"]
    return any(kw in query.lower() for kw in keywords)


def detect_payback_query(query: str) -> bool:
    """Detects: payback period, break-even, savings offset."""
    keywords = ["payback", "break even", "break-even", "savings offset", "offset", "months"]
    return any(kw in query.lower() for kw in keywords)


def detect_multi_criteria_query(query: str) -> bool:
    """Detects: ranking, scoring, budget optimization, best match."""
    keywords = ["ranking", "score", "best match", "budget", "priority",
                "combine", "combination", "fit within"]
    return any(kw in query.lower() for kw in keywords)


def detect_sentiment_query(query: str) -> bool:
    """Detects: sentiment analysis, review analysis, positive/negative ratio."""
    keywords = ["sentiment", "positive", "negative", "reviews", "feedback",
                "ratio", "review text"]
    return any(kw in query.lower() for kw in keywords)


def detect_visualization_query(query: str) -> bool:
    """Detects: chart, graph, plot, scatter, visualization requests."""
    keywords = ["chart", "graph", "plot", "scatter", "visualiz", "breakdown",
                "compare visually", "show chart"]
    return any(kw in query.lower() for kw in keywords)


def detect_ownership_cost_query(query: str) -> bool:
    """Detects: 5-year TCO, total cost of ownership, purchase + electricity."""
    keywords = ["total cost", "ownership", "5-year", "5 year", "purchase price",
                "tco", "cumulative cost"]
    return any(kw in query.lower() for kw in keywords)


def detect_co2_query(query: str) -> bool:
    """Detects: CO2 emissions, environmental impact, carbon."""
    keywords = ["co2", "carbon", "emission", "environmental", "carbon footprint",
                "kg co2", "emission reduction"]
    return any(kw in query.lower() for kw in keywords)


def detect_scenario_query(query: str) -> bool:
    """Detects: what-if, household scenarios, simultaneous usage."""
    keywords = ["scenario", "what if", "simultaneous", "running", "together",
                "household", "earbud", "earbuds", "hours per day"]
    return any(kw in query.lower() for kw in keywords)


def detect_room_size_query(query: str) -> bool:
    """Detects: room size, cooling capacity, suitable room."""
    keywords = ["room size", "room", "cooling", "suitable", "capacity", "ideal room"]
    return any(kw in query.lower() for kw in keywords)


def detect_water_savings_query(query: str) -> bool:
    """Detects: water savings, dishwasher, hand-washing comparison."""
    keywords = ["water", "liters", "hand-wash", "hand wash", "place setting",
                "dishwasher", "wash"]
    return any(kw in query.lower() for kw in keywords)


# =========================================================
# ANALYSIS FUNCTIONS
# =========================================================

def analyze_electricity_costs(query: str, products: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze electricity bills for selected products."""
    if not products:
        return {
            "tool_output": {
                "type": "python_result",
                "analysis": "No products found for electricity cost analysis.",
                "chart": None
            }
        }

    category = state.get("category", "unknown")
    daily_hours = DAILY_USAGE_HOURS.get(category, 6)
    analysis = []

    for product in products:
        power = extract_power_watts(product, category)
        price = product.get("price", 0)

        monthly_kwh, monthly_cost = calculate_monthly_electricity_cost(power, daily_hours)
        annual_kwh, annual_cost = calculate_annual_electricity_cost(power, daily_hours)

        analysis.append({
            "model": product.get("model_name"),
            "price": price,
            "power_watts": power,
            "monthly_kwh": round(monthly_kwh, 2),
            "monthly_cost_rs": round(monthly_cost, 2),
            "annual_kwh": round(annual_kwh, 2),
            "annual_cost_rs": round(annual_cost, 2)
        })

    return {
        "tool_output": {
            "type": "python_result",
            "analysis": analysis,
            "chart": None
        }
    }


def analyze_efficiency_ratios(query: str, products: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze energy efficiency ratios."""
    if not products:
        return {
            "tool_output": {
                "type": "python_result",
                "analysis": "No products found for efficiency analysis.",
                "chart": None
            }
        }

    category = state.get("category", "unknown")
    analysis = []

    for product in products:
        power = extract_power_watts(product, category)
        capacity = extract_capacity(product, category)
        ratio = calculate_energy_efficiency_ratio(capacity, power) if power > 0 else 0

        analysis.append({
            "model": product.get("model_name"),
            "capacity": capacity,
            "power_watts": power,
            "efficiency_ratio": round(ratio, 4)
        })

    # Sort by efficiency descending
    analysis = sorted(analysis, key=lambda x: x["efficiency_ratio"], reverse=True)

    return {
        "tool_output": {
            "type": "python_result",
            "analysis": analysis,
            "chart": None
        }
    }


def analyze_payback_period(query: str, products: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze payback period for efficient vs non-efficient models."""
    if len(products) < 2:
        return {
            "tool_output": {
                "type": "python_result",
                "analysis": "Need at least 2 products for payback comparison.",
                "chart": None
            }
        }

    category = state.get("category", "unknown")
    daily_hours = DAILY_USAGE_HOURS.get(category, 6)

    # Assume first product is standard, second is efficient
    standard = products[0]
    efficient = products[1]

    standard_power = extract_power_watts(standard, category)
    efficient_power = extract_power_watts(efficient, category)

    _, standard_annual_cost = calculate_annual_electricity_cost(standard_power, daily_hours)
    _, efficient_annual_cost = calculate_annual_electricity_cost(efficient_power, daily_hours)

    annual_savings = standard_annual_cost - efficient_annual_cost
    premium_price = efficient.get("price", 0) - standard.get("price", 0)

    payback_months = calculate_payback_period(premium_price, annual_savings)

    analysis = {
        "standard_model": standard.get("model_name"),
        "efficient_model": efficient.get("model_name"),
        "standard_annual_cost": round(standard_annual_cost, 2),
        "efficient_annual_cost": round(efficient_annual_cost, 2),
        "annual_savings": round(annual_savings, 2),
        "price_premium": round(premium_price, 2),
        "payback_months": round(payback_months, 1) if payback_months != float('inf') else "N/A"
    }

    return {
        "tool_output": {
            "type": "python_result",
            "analysis": analysis,
            "chart": None
        }
    }


def analyze_multi_criteria_ranking(query: str, products: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze and rank products on multiple criteria."""
    if not products:
        return {
            "tool_output": {
                "type": "python_result",
                "analysis": "No products found for ranking.",
                "chart": None
            }
        }

    category = state.get("category", "unknown")

    # Default weights: price (30%), efficiency (40%), rating (30%)
    weights = {"price": 0.3, "efficiency": 0.4, "rating": 0.3}

    scored = score_products_by_criteria(products, weights, category)

    return {
        "tool_output": {
            "type": "python_result",
            "analysis": scored,
            "chart": None
        }
    }


def analyze_co2_impact(query: str, products: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze CO2 emissions and savings."""
    if len(products) < 2:
        return {
            "tool_output": {
                "type": "python_result",
                "analysis": "Need at least 2 products for CO2 comparison.",
                "chart": None
            }
        }

    category = state.get("category", "unknown")
    daily_hours = DAILY_USAGE_HOURS.get(category, 6)

    standard = products[0]
    efficient = products[1]

    standard_power = extract_power_watts(standard, category)
    efficient_power = extract_power_watts(efficient, category)

    _, standard_annual = calculate_annual_electricity_cost(standard_power, daily_hours)
    _, efficient_annual = calculate_annual_electricity_cost(efficient_power, daily_hours)

    standard_kwh = (standard_power * daily_hours * 365) / 1000
    efficient_kwh = (efficient_power * daily_hours * 365) / 1000

    kwh_saved = standard_kwh - efficient_kwh
    co2_saved_5yr = estimate_co2_savings(kwh_saved, 5)

    analysis = {
        "standard_model": standard.get("model_name"),
        "efficient_model": efficient.get("model_name"),
        "annual_kwh_saved": round(kwh_saved, 2),
        "5_year_co2_saved_kg": round(co2_saved_5yr, 2),
        "equivalent_trees_planted": round(co2_saved_5yr / 20, 1)  # 1 tree absorbs ~20kg CO2/year
    }

    return {
        "tool_output": {
            "type": "python_result",
            "analysis": analysis,
            "chart": None
        }
    }


def analyze_room_size(query: str, products: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze ideal room size for AC models based on cooling capacity."""
    if not products:
        return {
            "tool_output": {
                "type": "python_result",
                "analysis": "No AC models found for room size calculation.",
                "chart": None
            }
        }

    analysis = []

    for product in products:
        capacity_btu = extract_capacity(product, "air_conditioners")

        if capacity_btu > 0:
            room_size_sqft = room_size_from_capacity(capacity_btu)
            tons = capacity_btu / BTU_PER_TON

            analysis.append({
                "model": product.get("model_name"),
                "capacity_btu": round(capacity_btu, 0),
                "capacity_tons": round(tons, 1),
                "ideal_room_size_sqft": round(room_size_sqft, 0)
            })

    return {
        "tool_output": {
            "type": "python_result",
            "analysis": analysis,
            "chart": None
        }
    }


def analyze_ownership_cost(query: str, products: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze 5-year total cost of ownership (purchase + electricity)."""
    if not products:
        return {
            "tool_output": {
                "type": "python_result",
                "analysis": "No products found for ownership cost analysis.",
                "chart": None
            }
        }

    category = state.get("category", "unknown")
    daily_hours = DAILY_USAGE_HOURS.get(category, 6)
    analysis = []

    for product in products:
        price = product.get("price", 0)
        power = extract_power_watts(product, category)

        total_electricity, total_ownership, avg_yearly = calculate_5year_ownership_cost(price, power, daily_hours, 5)

        analysis.append({
            "model": product.get("model_name"),
            "purchase_price": round(price, 2),
            "avg_yearly_electricity_cost": round(avg_yearly, 2),
            "5_year_total_electricity_cost": round(total_electricity, 2),
            "5_year_total_ownership_cost": round(total_ownership, 2)
        })

    # Sort by total ownership cost
    analysis = sorted(analysis, key=lambda x: x["5_year_total_ownership_cost"])

    return {
        "tool_output": {
            "type": "python_result",
            "analysis": analysis,
            "chart": None
        }
    }


# =========================================================
# MAIN PYTHON AGENT ROUTER
# =========================================================

def python_agent(state: Dict[str, Any]):
    """
    Main router for Python-based analysis.
    1. Fetches data from SQL agent using Gemini-generated queries
    2. Detects query intent
    3. Routes to appropriate analysis function
    4. Returns python_result with analysis + chart
    """
    user_query = state.get("user_query", "")
    category = state.get("category", "unknown")

    print(f"[Python Agent] Processing query: {user_query[:80]}...")
    print(f"[Python Agent] Category: {category}")

    try:
        # Step 1: Fetch data from SQL agent
        products = fetch_sql_data(user_query, category)

        if not products:
            print("[Python Agent] No products fetched from SQL agent")
            return {
                "tool_output": {
                    "type": "python_result",
                    "analysis": "No data available for analysis. Please try a different query.",
                    "chart": None
                }
            }

        print(f"[Python Agent] Fetched {len(products)} products. Analyzing query intent...")

        # Step 2: Route to appropriate analysis based on query type
        if detect_room_size_query(user_query):
            print("[Python Agent] -> Room Size Analysis")
            return analyze_room_size(user_query, products, state)

        elif detect_ownership_cost_query(user_query):
            print("[Python Agent] -> 5-Year Ownership Cost Analysis")
            return analyze_ownership_cost(user_query, products, state)

        elif detect_co2_query(user_query):
            print("[Python Agent] -> CO2 Impact Analysis")
            return analyze_co2_impact(user_query, products, state)

        elif detect_payback_query(user_query):
            print("[Python Agent] -> Payback Period Analysis")
            return analyze_payback_period(user_query, products, state)

        elif detect_efficiency_ratio_query(user_query):
            print("[Python Agent] -> Efficiency Ratio Analysis")
            return analyze_efficiency_ratios(user_query, products, state)

        elif detect_multi_criteria_query(user_query):
            print("[Python Agent] -> Multi-Criteria Ranking Analysis")
            return analyze_multi_criteria_ranking(user_query, products, state)

        elif detect_electricity_cost_query(user_query):
            print("[Python Agent] -> Electricity Cost Analysis")
            return analyze_electricity_costs(user_query, products, state)

        elif detect_sentiment_query(user_query):
            print("[Python Agent] -> Sentiment Analysis")
            # Collect reviews if available
            all_reviews = []
            for product in products:
                if "reviews" in product and product["reviews"]:
                    all_reviews.extend(product["reviews"])

            sentiment = calculate_sentiment_ratio(all_reviews)
            return {
                "tool_output": {
                    "type": "python_result",
                    "analysis": sentiment,
                    "chart": None
                }
            }

        else:
            print("[Python Agent] -> No specific intent detected, returning general analysis")
            return {
                "tool_output": {
                    "type": "python_result",
                    "analysis": "Query processed but no specific analysis type detected. Here are the products:",
                    "data": products,
                    "chart": None
                }
            }

    except Exception as error:
        print(f"[Python Agent Error] {str(error)}")
        import traceback
        traceback.print_exc()
        return {
            "tool_output": {
                "type": "python_result",
                "error": str(error),
                "chart": None
            }
        }
