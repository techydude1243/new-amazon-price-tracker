import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from webdriver_manager.chrome import ChromeDriverManager
logging.basicConfig(level=logging.DEBUG)

# Function to check price using Selenium for dynamic content
def check_price(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    # service = Service('K:\\amazon-price-tracker\\chromedriver.exe')
    # driver = webdriver.Chrome(service=service, options=options)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)

        # Wait for the price element to load
        price_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.a-price-whole'))
        )

        price_text = price_element.text.replace(',', '').strip()
        price = float(price_text)

        logging.info(f"Price found: ₹{price}")
        return price

    except Exception as e:
        logging.error(f"Error checking price: {str(e)}")
        raise

    finally:
        driver.quit()

# ────────────────────────────────────────────────
#           Brevo API Email Sending Function
# ────────────────────────────────────────────────

def send_email(to_email, subject, body_text, body_html=None):
    """
    Send email using Brevo (Sendinblue) API
    """
    api_key = os.getenv('BREVO_API_KEY')
    from_email = os.getenv('BREVO_FROM_EMAIL')  # must be a verified sender in Brevo

    if not api_key:
        logging.error("BREVO_API_KEY not found in environment variables")
        raise ValueError("Brevo API key is missing")
    if not from_email:
        logging.error("BREVO_FROM_EMAIL not found in environment variables")
        raise ValueError("Brevo from email is missing")

    headers = {
        'accept': 'application/json',
        'api-key': api_key,
        'content-type': 'application/json'
    }

    payload = {
        "sender": {
            "name": "Amazon Price Tracker",
            "email": from_email
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body_text,
    }

    if body_html:
        payload["htmlContent"] = body_html

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers
        )

        if response.status_code in (200, 201, 202):
            logging.info(f"Email successfully sent to {to_email}")
            return True
        else:
            error_msg = f"Brevo API failed ({response.status_code}): {response.text}"
            logging.error(error_msg)
            raise Exception(error_msg)

    except requests.RequestException as e:
        logging.error(f"Network error sending email: {str(e)}")
        raise

# Function to send welcome email
def send_welcome_email(to_email, product_url):
    subject = "Product Tracking Confirmation"
    body_text = f"""
Thank you for using Amazon Price Tracker!

We have successfully added the following product to our tracking system:
{product_url}

You will receive email notifications when the price changes.

Best regards,
Amazon Price Tracker Team
    """
    body_html = f"""
    <h2>Welcome to Amazon Price Tracker!</h2>
    <p>Thank you for adding:</p>
    <p><a href="{product_url}">{product_url}</a></p>
    <p>You will be notified when the price changes.</p>
    <p>Best regards,<br>Amazon Price Tracker Team</p>
    """

    send_email(to_email, subject, body_text, body_html)

# Function to send price change alert
def send_price_alert(to_email, product_url, old_price, new_price, min_price=None, max_price=None):
    threshold_message = ""
    if min_price and new_price <= min_price:
        threshold_message += f"\nThe price has dropped below your minimum threshold of ₹{min_price:.2f}!"
    if max_price and new_price >= max_price:
        threshold_message += f"\nThe price has exceeded your maximum threshold of ₹{max_price:.2f}!"

    subject = "Amazon Price Alert!"
    body_text = f"""
Price changed for your tracked product!

Product URL: {product_url}
Old Price: ₹{old_price:.2f}
New Price: ₹{new_price:.2f}{threshold_message}

Check it out now!
    """
    body_html = f"""
    <h2>Price Alert!</h2>
    <p>Product: <a href="{product_url}">{product_url}</a></p>
    <p>Old Price: ₹{old_price:.2f}</p>
    <p><strong>New Price: ₹{new_price:.2f}</strong></p>
    {f'<p><strong>{threshold_message.strip()}</strong></p>' if threshold_message else ''}
    <p>Check it now!</p>
    """

    send_email(to_email, subject, body_text, body_html)