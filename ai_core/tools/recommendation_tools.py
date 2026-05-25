from backend.app.db.models import (Product)

from ai_core.tools.db_session import (get_db_session)


def recommend_energy_efficient_products():

    db = get_db_session()

    try:

        products = (db.query(Product).filter(Product.energy_rating >= 4.0).filter(Product.energy_rating.isnot(None)).order_by(Product.energy_rating.desc()).limit(5).all())

        results = []

        for product in products:

            results.append({
                "model_name":product.model_name,
                "energy_rating":product.energy_rating,
                "price":product.price
            })

        return results

    finally:
        db.close()


def recommend_inverter_products():

    db = get_db_session()

    try:

        products = (db.query(Product).filter(Product.has_inverter == True).filter(Product.price.isnot(None)).limit(5).all())

        results = []

        for product in products:

            results.append({
                "model_name":product.model_name,
                "price":product.price
            })

        return results

    finally:
        db.close()