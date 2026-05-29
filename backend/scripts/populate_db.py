import os
import re
from backend.app.db.database import SessionLocal, engine
from backend.app.db.models import Category, Product, ProductSpecification, Review, Base

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")

def parse_markdown(md_content):
    """Parses strictly formatted Markdown into a dictionary for the database."""
    
    # 1. Model Name
    model_name_match = re.search(r'^#\s+(.+)', md_content, re.MULTILINE)
    model_name = model_name_match.group(1).strip() if model_name_match else "Unknown Model"

    # 2. Price
    price = None
    price_match = re.search(r'\*\*Price:\*\*\s*Rs\.\s*([\d,]+)', md_content)
    if price_match:
        price = int(price_match.group(1).replace(',', ''))

    # 3. Inverter Status
    has_inverter = bool(re.search(r'inverter', md_content, re.IGNORECASE))

    # 4. Features Text
    features_text = ""
    features_match = re.search(r'### Features\n+(.*?)(?=### Specifications|### Reviews|$)', md_content, re.DOTALL)
    if features_match:
        features_text = features_match.group(1).strip()

    # 5. Specifications
    specs = []
    specs_section = re.search(r'### Specifications\n+(.*?)(?=### Reviews|$)', md_content, re.DOTALL)
    if specs_section:
        # UPDATED: Matches both '*' and '-' bullets
        spec_lines = re.findall(r'[-*]\s*\*\*(.*?):\*\*\s*(.*)', specs_section.group(1))
        for key, value in spec_lines:
            specs.append({"spec_name": key.strip(), "spec_value": value.strip()})

    # 6. Reviews (NEW)
    reviews = []
    reviews_section = re.search(r'### Reviews\n+(.*)', md_content, re.DOTALL)
    if reviews_section:
        # This regex looks for: "Number. Review Text (X stars"
        review_lines = re.findall(r'\d+\.\s*(.*?)\s*\((\d)\s*stars?,', reviews_section.group(1))
        for text, rating in review_lines:
            reviews.append({
                "rating": int(rating),
                "review_text": text.strip()
            })

    return {
        "model_name": model_name,
        "price": price,
        "has_inverter": has_inverter,
        "features_text": features_text,
        "specs": specs,
        "reviews": reviews
    }

def populate_database():
    print("Starting Markdown Database Ingestion...\n" + "="*40)
    
    # CREATE TABLES IF THEY DON'T EXIST
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()

    for category_name in os.listdir(DATASET_DIR):
        category_path = os.path.join(DATASET_DIR, category_name)

        if not os.path.isdir(category_path) or category_name == "evaluations":
            continue

        print(f"\n📂 CATEGORY: {category_name}")

        category = db.query(Category).filter_by(category_name=category_name).first()
        if not category:
            category = Category(category_name=category_name)
            db.add(category)
            db.commit()
            db.refresh(category)

        for filename in os.listdir(category_path):
            if not filename.endswith(".md"):
                continue

            md_path = os.path.join(category_path, filename)
            
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                data = parse_markdown(content)
                
                # Insert Product
                new_product = Product(
                    category_id=category.id,
                    model_name=data['model_name'],
                    price=data['price'],
                    has_inverter=data['has_inverter'],
                    features_text=data['features_text']
                )
                db.add(new_product)
                db.commit()
                db.refresh(new_product)

                # Insert Specs
                for spec in data['specs']:
                    new_spec = ProductSpecification(
                        product_id=new_product.id,
                        spec_name=spec['spec_name'],
                        spec_value=spec['spec_value']
                    )
                    db.add(new_spec)
                
                # Insert Reviews (NEW)
                for rev in data['reviews']:
                    new_review = Review(
                        product_id=new_product.id,
                        rating=rev['rating'],
                        review_text=rev['review_text'],
                        # Sentiment is left blank for now; you can use NLP on it later!
                    )
                    db.add(new_review)

                db.commit()

                print(f"  ✅ SAVED: {data['model_name']} (Rs. {data['price']} | {len(data['specs'])} specs | {len(data['reviews'])} reviews)")
                
            except Exception as e:
                print(f"  ❌ ERROR processing {filename}: {e}")

    db.close()
    print("\n" + "="*40 + "\nIngestion Complete!")

if __name__ == "__main__":
    populate_database()