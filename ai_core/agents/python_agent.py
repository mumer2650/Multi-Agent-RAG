from typing import Dict, Any, List


# =========================================================
# UTILITIES
# =========================================================

def calculate_emi(price, rate=12, months=12):

    monthly_rate = rate / (12 * 100)

    emi = (
        price * monthly_rate * (1 + monthly_rate) ** months
    ) / ((1 + monthly_rate) ** months - 1)

    return round(emi, 2)


def build_price_chart(products):

    return {
        "chartType": "bar",
        "title": "Price Comparison",
        "xKey": "model",
        "yKey": "price",
        "data": [
            {
                "model": p.get("model_name"),
                "price": p.get("price", 0)
            }
            for p in products
        ]
    }


def build_energy_chart(products):

    return {
        "chartType": "bar",
        "title": "Energy Ratings",
        "xKey": "model",
        "yKey": "energy_rating",
        "data": [
            {
                "model": p.get("model_name"),
                "energy_rating": p.get("energy_rating", 0)
            }
            for p in products
        ]
    }


# =========================================================
# PYTHON AGENT
# =========================================================

def python_agent(state: Dict[str, Any]):

    query = state.get("user_query", "").lower()

    tool_output = state.get("tool_output", {})

    products = []

    if (
        isinstance(tool_output, dict)
        and tool_output.get("type") == "sql_result"
    ):

        products = tool_output.get("data", [])

    try:

        # =====================================================
        # PRICE GRAPH
        # =====================================================

        if any(x in query for x in ["price", "compare", "graph", "chart"]):

            products_with_price = [p for p in products if p.get("price") is not None]

            if not products_with_price:
                return {
                    "tool_output": {
                        "type": "python_result",
                        "analysis": "No products with valid pricing data available.",
                        "chart": None
                    }
                }

            analysis = []

            for p in products_with_price:

                price = p.get("price")

                analysis.append({

                    "model": p.get("model_name"),

                    "price": price,

                    "emi": calculate_emi(price)
                })

            return {
                "tool_output": {
                    "type": "python_result",
                    "analysis": analysis,
                    "chart": build_price_chart(products_with_price)
                }
            }

        # =====================================================
        # ENERGY GRAPH
        # =====================================================

        if any(x in query for x in ["energy", "efficient", "inverter"]):

            return {
                "tool_output": {
                    "type": "python_result",
                    "analysis": products,
                    "chart": build_energy_chart(products)
                }
            }

        return {
            "tool_output": {
                "type": "python_result",
                "analysis": "No mathematical analysis needed.",
                "chart": None
            }
        }

    except Exception as error:

        return {
            "tool_output": {
                "type": "python_result",
                "error": str(error),
                "chart": None
            }
        }