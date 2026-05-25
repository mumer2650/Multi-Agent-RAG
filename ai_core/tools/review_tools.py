from backend.app.db.models import (Product,Review)

from ai_core.tools.db_session import (get_db_session)


def get_positive_reviews():

    db = get_db_session()

    try:

        reviews = (
            db.query(
                Product.model_name,
                Review.review_text,
                Review.rating
            )
            .join(Review)
            .filter(
                Review.sentiment == "positive"
            )
            .limit(10)
            .all()
        )

        results = []

        for review in reviews:

            results.append({

                "model_name":
                    review.model_name,

                "rating":
                    review.rating,

                "review":
                    review.review_text
            })

        return results

    finally:
        db.close()


def search_reviews(
    keyword: str
):

    db = get_db_session()

    try:

        reviews = (
            db.query(
                Product.model_name,
                Review.review_text
            )
            .join(Review)
            .filter(
                Review.review_text.ilike(
                    f"%{keyword}%"
                )
            )
            .limit(10)
            .all()
        )

        results = []

        for review in reviews:

            results.append({

                "model_name":
                    review.model_name,

                "review":
                    review.review_text
            })

        return results

    finally:
        db.close()