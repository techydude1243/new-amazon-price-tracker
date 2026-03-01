import time
import logging
import schedule
from datetime import datetime
from app import app, db
from models import Product
from price_tracker import check_price, send_price_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def check_all_products():
    """
    Check prices for all products in the database and send alerts if needed
    """
    with app.app_context():
        products = Product.query.all()
        if not products:
            logging.info("No products found to track")
            return
        
        logging.info(f"Checking prices for {len(products)} products")
        for product in products:
            try:
                current_price = check_price(product.url)
                old_price = product.last_price
                
                # Update the last checked time and price
                product.last_checked = datetime.utcnow()
                product.last_price = current_price
                db.session.commit()
                
                # Check if price has changed
                if current_price != old_price:
                    logging.info(f"Price changed for {product.url}: {old_price} -> {current_price}")
                    
                    # Check if price meets alert criteria
                    should_alert = False
                    
                    # Always alert on price change
                    should_alert = True
                    
                    # If min_price is set and price drops below it
                    if product.min_price and current_price <= product.min_price:
                        logging.info(f"Price dropped below minimum threshold of {product.min_price}")
                        should_alert = True
                    
                    # If max_price is set and price goes above it
                    if product.max_price and current_price >= product.max_price:
                        logging.info(f"Price exceeded maximum threshold of {product.max_price}")
                        should_alert = True
                    
                    if should_alert:
                        logging.info(f"Sending price alert to {product.email}")
                        send_price_alert(
                            product.email,
                            product.url,
                            old_price,
                            current_price,
                            product.min_price,
                            product.max_price
                        )
                else:
                    logging.info(f"No price change for {product.url}: {current_price}")
                    
            except Exception as e:
                logging.error(f"Error checking price for {product.url}: {str(e)}")

def run_scheduler():
    """
    Run the scheduler to check prices periodically
    """
    # Schedule the job to run every hour
    schedule.every(1).hours.do(check_all_products)
    
    # Run once immediately on startup
    check_all_products()
    
    # Keep the scheduler running
    logging.info("Price tracker scheduler started. Checking prices every hour.")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check for pending jobs every minute

if __name__ == "__main__":
    run_scheduler() 