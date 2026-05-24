from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from .database import Base

# 1. CATEGORIES
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String, unique=True, index=True, nullable=False)
    
    products = relationship("Product", back_populates="category")

# 2. PRODUCTS (The Core Table)
class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    model_name = Column(String, index=True, nullable=False)
    price = Column(Integer)
    has_inverter = Column(Boolean, default=False)
    energy_rating = Column(Float) 
    features_text = Column(Text)
    
    category = relationship("Category", back_populates="products")
    specifications = relationship("ProductSpecification", back_populates="product")
    embeddings = relationship("ProductEmbedding", back_populates="product")
    reviews = relationship("Review", back_populates="product")

# 3. PRODUCT SPECIFICATIONS (EAV Model for dynamic features)
class ProductSpecification(Base):
    __tablename__ = "product_specifications"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    spec_name = Column(String, index=True, nullable=False)
    spec_value = Column(String, nullable=False)
    
    product = relationship("Product", back_populates="specifications")

# 4. PRODUCT EMBEDDINGS (Bridge to ChromaDB)
class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding_id = Column(String, nullable=False)
    
    product = relationship("Product", back_populates="embeddings")

# 5. REVIEWS (Mock data for semantic search testing)
class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    rating = Column(Integer)
    review_text = Column(Text)
    sentiment = Column(String)
    
    product = relationship("Product", back_populates="reviews")