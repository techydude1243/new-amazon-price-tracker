import os
import logging
from flask import Flask, render_template, request, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
from price_tracker import check_price, send_email, send_welcome_email
import re

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Flask app
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Set secret key for session management
app.secret_key = os.getenv("SESSION_SECRET", "your-fallback-secret-key")

# Configure PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "postgresql://postgres:123456@localhost:5432/amazon_tracker"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Removed Gmail / old SMTP config - Brevo API is used in price_tracker.py
# No Flask-Mail configuration needed anymore

db.init_app(app)

# Import models after db initialization
from models import Product

with app.app_context():
    db.create_all()

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_amazon_url(url):
    return 'amazon' in url.lower() and url.startswith('http')

def validate_price(price):
    try:
        price = float(price)
        return price >= 0
    except (ValueError, TypeError):
        return False

@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/track', methods=['POST'])
def track_price():
    amazon_url = request.form.get('amazon_url')
    email = request.form.get('email')
    min_price = request.form.get('min_price')
    max_price = request.form.get('max_price')

    if not amazon_url or not email:
        flash('Please fill in all required fields', 'error')
        return jsonify({'success': False, 'message': 'Missing required fields'})

    if not validate_email(email):
        flash('Invalid email address', 'error')
        return jsonify({'success': False, 'message': 'Invalid email address'})

    if not validate_amazon_url(amazon_url):
        flash('Invalid Amazon URL', 'error')
        return jsonify({'success': False, 'message': 'Invalid Amazon URL'})

    # Validate and convert price thresholds
    min_price_float = float(min_price) if min_price and validate_price(min_price) else None
    max_price_float = float(max_price) if max_price and validate_price(max_price) else None

    if min_price_float and max_price_float and min_price_float >= max_price_float:
        flash('Minimum price must be less than maximum price', 'error')
        return jsonify({'success': False, 'message': 'Invalid price range'})

    try:
        initial_price = check_price(amazon_url)
        product = Product(
            url=amazon_url,
            email=email,
            last_price=initial_price,
            min_price=min_price_float,
            max_price=max_price_float
        )
        db.session.add(product)
        db.session.commit()

        # Send welcome email using Brevo API
        try:
            logging.info(f"Attempting to send welcome email to {email}")
            send_welcome_email(email, amazon_url)
            flash('Product added successfully! Welcome email sent.', 'success')
            logging.info(f"Welcome email sent successfully to {email}")
        except Exception as e:
            logging.error(f"Failed to send welcome email: {str(e)}")
            flash('Product added successfully, but failed to send welcome email.', 'warning')

        return jsonify({'success': True, 'message': 'Product added successfully'})
    except Exception as e:
        logging.error(f"Error tracking price: {str(e)}")
        flash('Error tracking price', 'error')
        return jsonify({'success': False, 'message': 'Error tracking price'})

@app.route('/clear', methods=['POST'])
def clear_all():
    try:
        Product.query.delete()
        db.session.commit()
        flash('All products cleared successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error clearing products: {str(e)}")
        flash('Error clearing products', 'error')
        return jsonify({'success': False})

# Optional: Keep test route (updated to use new send_email)
@app.route('/test-email')
def test_email():
    try:
        send_email(
            to_email="your-email@gmail.com",  # ← change to your test email
            subject="Test Email from Brevo API",
            body_text="This is a test email from your Amazon Price Tracker using Brevo API!"
        )
        logging.info("Test email sent successfully!")
        return "Test email sent successfully!"
    except Exception as e:
        logging.error(f"Failed to send test email: {str(e)}")
        return f"Failed to send email: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)