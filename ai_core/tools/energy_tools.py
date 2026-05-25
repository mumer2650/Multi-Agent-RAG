from sqlalchemy import func

from backend.app.db.models import Product, Category

from ai_core.tools.db_session import get_db_session


def get_energy_efficient_products(min_rating=3.0, max_price=None, category=None):
    """
    Filter products by energy efficiency with optional price and category filters.

    Args:
        min_rating: Minimum energy rating threshold (default 3.0)
        max_price: Maximum price (optional, for "under X" queries)
        category: Category name to filter (optional)

    Returns:
        List of products sorted by energy_rating descending
        Each product has: model_name, energy_rating, price, has_inverter
    """

    db = get_db_session()

    try:

        query = (db.query(Product)
            .filter(Product.energy_rating.isnot(None))
            .filter(Product.energy_rating >= min_rating))

        if max_price is not None:
            query = query.filter(Product.price.isnot(None))
            query = query.filter(Product.price <= max_price)

        if category is not None:
            query = query.join(Category).filter(
                func.lower(Category.category_name) == category.lower()
            )

        products = query.order_by(Product.energy_rating.desc()).limit(10).all()

        results = []

        for p in products:

            results.append({
                "model_name": p.model_name,
                "energy_rating": p.energy_rating,
                "price": p.price,
                "has_inverter": p.has_inverter
            })

        return results

    finally:
        db.close()


def get_category_statistics(category_name):
    """
    Get statistical summary for products in a category.

    Args:
        category_name: Name of category to analyze (e.g., "air_conditioners")

    Returns:
        Dict with statistics about the category
    """

    db = get_db_session()

    try:

        products = (db.query(Product)
            .join(Category)
            .filter(func.lower(Category.category_name) == category_name.lower())
            .all())

        prices = [p.price for p in products if p.price is not None]
        energy_ratings = [p.energy_rating for p in products if p.energy_rating is not None]

        avg_price = round(sum(prices) / len(prices), 2) if prices else None
        avg_energy_rating = round(sum(energy_ratings) / len(energy_ratings), 2) if energy_ratings else None
        inverter_percentage = round(100 * sum(1 for p in products if p.has_inverter) / len(products), 1) if products else 0

        return {
            "category": category_name,
            "total_products": len(products),
            "products_with_price": len(prices),
            "products_with_energy_rating": len(energy_ratings),
            "avg_price": avg_price,
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
            "avg_energy_rating": avg_energy_rating,
            "min_energy_rating": min(energy_ratings) if energy_ratings else None,
            "max_energy_rating": max(energy_ratings) if energy_ratings else None,
            "inverter_count": sum(1 for p in products if p.has_inverter),
            "inverter_percentage": inverter_percentage
        }

    finally:
        db.close()
