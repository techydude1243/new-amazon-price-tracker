from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app import db

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    last_price = db.Column(db.Float, nullable=False)
    min_price = db.Column(db.Float, nullable=True)
    max_price = db.Column(db.Float, nullable=True)
    last_checked = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Product {self.url}>'