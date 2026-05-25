from sqlalchemy import func

from backend.app.db.models import (Product, Review, Category)

from ai_core.tools.db_session import (get_db_session)


def get_top_rated_products(limit: int = 5, category: str = None):

    db = get_db_session()

    try:

        query = (
            db.query(
                Product.model_name,

                func.avg(
                    Review.rating
                ).label("avg_rating")
            )
            .join(Review)
        )

        if category:
            query = query.join(Category).filter(
                func.lower(Category.category_name) == category.lower()
            )

        products = (
            query
            .group_by(Product.id)
            .order_by(
                func.avg(
                    Review.rating
                ).desc()
            )
            .limit(limit)
            .all()
        )

        results = []

        for product in products:

            results.append({

                "model_name":
                    product.model_name,

                "average_rating":
                    round(product.avg_rating, 2)
            })

        return results

    finally:
        db.close()


def get_best_energy_products():

    db = get_db_session()

    try:

        products = (db.query(Product).filter(Product.energy_rating.isnot(None)).order_by(Product.energy_rating.desc()).limit(5).all())

        results = []

        for product in products:

            results.append({

                "model_name":
                    product.model_name,

                "energy_rating":
                    product.energy_rating
            })

        return results

    finally:
        db.close()