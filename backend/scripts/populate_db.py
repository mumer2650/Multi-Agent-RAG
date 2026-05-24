import os
import re
from app.db.database import SessionLocal
from app.db.models import Category, Product, ProductSpecification

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")

def parse_markdown(md_content):
    """Parses strictly formatted Markdown into a dictionary for the database."""
    
    # 1. Model Name: Grabs whatever is on the first line after "# "
    model_name_match = re.search(r'^#\s+(.+)', md_content, re.MULTILINE)
    model_name = model_name_match.group(1).strip() if model_name_match else "Unknown Model"

    # 2. Price: Looks for "**Price:** Rs. " and grabs the numbers
    price = None
    price_match = re.search(r'\*\*Price:\*\*\s*Rs\.\s*([\d,]+)', md_content)
    if price_match:
        price = int(price_match.group(1).replace(',', ''))

    # 3. Inverter Status: Simple keyword check anywhere in the text
    has_inverter = bool(re.search(r'inverter', md_content, re.IGNORECASE))

    # 4. Features Text: Grabs everything between "### Features" and "### Specifications"
    features_text = ""
    features_match = re.search(r'### Features\n+(.*?)(?=### Specifications|### Reviews|$)', md_content, re.DOTALL)
    if features_match:
        features_text = features_match.group(1).strip()

    # 5. Specifications: Finds the section, then extracts all "* **Key:** Value" pairs
    specs = []
    specs_section = re.search(r'### Specifications\n+(.*?)(?=### Reviews|$)', md_content, re.DOTALL)
    if specs_section:
        spec_lines = re.findall(r'\*\s*\*\*(.*?):\*\*\s*(.*)', specs_section.group(1))
        for key, value in spec_lines:
            specs.append({"spec_name": key.strip(), "spec_value": value.strip()})

    return {
        "model_name": model_name,
        "price": price,
        "has_inverter": has_inverter,
        "features_text": features_text,
        "specs": specs
    }

def populate_database():
    print("Starting Markdown Database Ingestion...\n" + "="*40)
    db = SessionLocal()

    for category_name in os.listdir(DATASET_DIR):
        category_path = os.path.join(DATASET_DIR, category_name)

        # Skip files, evaluations folder, etc.
        if not os.path.isdir(category_path) or category_name == "evaluations":
            continue

        print(f"\n📂 CATEGORY: {category_name}")

        # Ensure category exists in DB
        category = db.query(Category).filter_by(category_name=category_name).first()
        if not category:
            category = Category(category_name=category_name)
            db.add(category)
            db.commit()
            db.refresh(category)

        # Process only .md files
        for filename in os.listdir(category_path):
            if not filename.endswith(".md"):
                continue

            md_path = os.path.join(category_path, filename)
            
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the Markdown
                data = parse_markdown(content)
                
                # Insert the Main Product
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

                # Insert the Specifications mapping to the new product ID
                for spec in data['specs']:
                    new_spec = ProductSpecification(
                        product_id=new_product.id,
                        spec_name=spec['spec_name'],
                        spec_value=spec['spec_value']
                    )
                    db.add(new_spec)
                db.commit()

                print(f"  ✅ SAVED: {data['model_name']} (Rs. {data['price']} | {len(data['specs'])} specs)")
                
            except Exception as e:
                print(f"  ❌ ERROR processing {filename}: {e}")

    db.close()
    print("\n" + "="*40 + "\nIngestion Complete!")

if __name__ == "__main__":
    populate_database()