import re

from ai_core.tools.sql_tools import (
    get_products_by_category,
    get_product_specifications,
    get_products_under_price
)

from ai_core.tools.analytics_tools import (
    get_top_rated_products,
    get_best_energy_products
)

from ai_core.tools.review_tools import (
    get_positive_reviews,
    search_reviews
)

from ai_core.tools.recommendation_tools import (
    recommend_energy_efficient_products,
    recommend_inverter_products
)

from ai_core.tools.energy_tools import (
    get_energy_efficient_products,
    get_category_statistics
)

CATEGORY_MAPPINGS = {

    "air_conditioner": "air_conditioners",
    "ac": "air_conditioners",

    "buds": "buds",

    "dishwasher": "dishwashers",

    "dispenser": "dispenser",

    "leds": "leds",
    "tv": "leds",
    "qled": "leds",

    "refrigerator": "refrigerators",
    "fridge": "refrigerators",

    "washing_machine": "washing_machines",
    "washer": "washing_machines"
}


def sql_agent(state):

    query = state.get("user_query", "").lower()
    category = state.get("extracted_category")

    try:

        # =====================================================
        # TOP RATED (check BEFORE category to catch "top rated [category]")
        # =====================================================

        if "top rated" in query:

            category = None

            for keyword, mapped_category in CATEGORY_MAPPINGS.items():

                if keyword in query:
                    category = mapped_category
                    break

            result = get_top_rated_products(category=category)

            return {
                "tool_output": {
                    "type": "sql_result",
                    "action": "top_rated",
                    "data": result
                }
            }

        # =====================================================
        # SPECIFICATIONS
        # =====================================================

        if any(x in query for x in ["specification", "specs", "features"]):

            result = get_product_specifications(query)

            return {
                "tool_output": {
                    "type": "sql_result",
                    "action": "specifications",
                    "data": result
                }
            }

        category = None

        for keyword, mapped_category in CATEGORY_MAPPINGS.items():

            if keyword in query:
                category = mapped_category
                break

        # =====================================================
        # CATEGORY + PRICE FILTER
        # =====================================================

        if category:

            data = get_products_by_category(category)

            # Price filtering
            price_keywords = ["under", "budget", "below", "max", "maximum", "cheaper"]
            if any(k in query for k in price_keywords) or re.search(r"\d+", query):
                
                # remove typical thousands separators to parse full numbers
                query_cleaned = query.replace(",", "")
                numbers = re.findall(r"\d+", query_cleaned)

                if numbers:
                    
                    # Sort or map properly, here we take the first matched number
                    # Some inputs might have "100000"
                    max_price = int(numbers[0])

                    filtered = []

                    for item in data:
                        price = item.get("price")
                        if price is not None and price <= max_price:
                            filtered.append(item)

                    data = filtered

            return {
                "tool_output": {
                    "type": "sql_result",
                    "action": "product_query",
                    "data": data
                }
            }

        # =====================================================
        # PRICE FILTER WITHOUT CATEGORY
        # =====================================================
        price_keywords = ["under", "budget", "below", "max", "maximum", "cheaper"]
        if any(k in query for k in price_keywords) and re.search(r"\d+", query):
            query_cleaned = query.replace(",", "")
            numbers = re.findall(r"\d+", query_cleaned)
            if numbers:
                max_price = int(numbers[0])
                data = get_products_under_price(max_price)
                return {
                    "tool_output": {
                        "type": "sql_result",
                        "action": "price_query",
                        "data": data
                    }
                }

        # =====================================================
        # ENERGY
        # =====================================================

        if "energy" in query:

            result = get_best_energy_products()

            return {
                "tool_output": {
                    "type": "sql_result",
                    "action": "energy",
                    "data": result
                }
            }

        # =====================================================
        # REVIEWS
        # =====================================================

        if "review" in query:

            if "positive" in query or "good" in query or "best" in query:
                result = get_positive_reviews()
            else:
                result = search_reviews(query)

            return {
                "tool_output": {
                    "type": "sql_result",
                    "action": "reviews",
                    "data": result
                }
            }

        # =====================================================
        # RECOMMENDATIONS
        # =====================================================

        if "recommend" in query:

            if "inverter" in query:
                result = recommend_inverter_products()

            else:
                result = recommend_energy_efficient_products()

            return {
                "tool_output": {
                    "type": "sql_result",
                    "action": "recommendation",
                    "data": result
                }
            }

        # =====================================================
        # ENERGY EFFICIENCY FILTER
        # =====================================================

        if "efficient" in query and "under" in query:

            query_cleaned = query.replace(",", "")
            numbers = re.findall(r"\d+", query_cleaned)
            max_price = int(numbers[0]) if numbers else None

            category = None
            for keyword, mapped_category in CATEGORY_MAPPINGS.items():
                if keyword in query:
                    category = mapped_category
                    break

            result = get_energy_efficient_products(
                min_rating=3.0,
                max_price=max_price,
                category=category
            )

            return {
                "tool_output": {
                    "type": "sql_result",
                    "action": "energy_filter",
                    "data": result
                }
            }

        # =====================================================
        # CATEGORY STATISTICS
        # =====================================================

        if any(x in query for x in ["statistics", "average", "total", "distribution", "summary"]):

            category = None
            for keyword, mapped_category in CATEGORY_MAPPINGS.items():
                if keyword in query:
                    category = mapped_category
                    break

            if category:
                result = get_category_statistics(category)

                return {
                    "tool_output": {
                        "type": "sql_result",
                        "action": "statistics",
                        "data": result
                    }
                }

        return {
            "tool_output": {
                "type": "sql_result",
                "action": "empty",
                "data": []
            }
        }

    except Exception as error:

        return {
            "tool_output": {
                "type": "sql_result",
                "error": str(error),
                "data": []
            }
        }