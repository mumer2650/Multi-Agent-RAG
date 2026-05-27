from sqlalchemy import func

from backend.app.db.models import (Product, Category, ProductSpecification)

from ai_core.tools.db_session import (get_db_session)


def get_products_by_category(category_name: str):
    if not isinstance(category_name, str) or not category_name.strip():
        raise ValueError("category_name must be a non-empty string.")

    db = get_db_session()

    try:

        products = (db.query(Product).join(Category).filter(func.lower(Category.category_name) == category_name.lower()).all())

        results = []

        for product in products:

            results.append({

                "model_name":
                    product.model_name,

                "price":
                    product.price,

                "energy_rating":
                    product.energy_rating,

                "has_inverter":
                    product.has_inverter
            })

        return results

    finally:
        db.close()


def get_product_specifications(model_name: str):
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be a non-empty string.")

    db = get_db_session()

    try:

        product = (
            db.query(Product).filter(Product.model_name.ilike(f"%{model_name}%")).first())

        if not product:
            return None

        specs = []

        for spec in product.specifications:

            specs.append({
                "spec_name":
                    spec.spec_name,

                "spec_value":
                    spec.spec_value
            })

        return {
            "model_name":
                product.model_name,

            "specifications":
                specs
        }

    finally:
        db.close()

def get_products_under_price(max_price: int):
    if not isinstance(max_price, (int, float)):
        raise ValueError("max_price must be a numeric value.")
    if max_price < 0:
        raise ValueError("max_price cannot be negative.")

    db = get_db_session()

    try:

        products = (db.query(Product).filter(Product.price.isnot(None)).filter(Product.price <= max_price).all())

        results = []

        for product in products:

            results.append({
                "model_name":
                    product.model_name,

                "price":
                    product.price
            })

        return results

    finally:
        db.close()