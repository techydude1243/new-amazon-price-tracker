import os
import requests
from bs4 import BeautifulSoup
import logging
import re

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def check_price(url):
    """
    Fetch Amazon product price using ScraperAPI (bypasses blocks & proxy issues).
    """
    api_key = os.getenv('SCRAPERAPI_KEY')
    if not api_key:
        logging.error("SCRAPERAPI_KEY not found")
        raise ValueError("ScraperAPI key is missing")

    # ScraperAPI base URL
    scraper_url = "http://api.scraperapi.com"
    params = {
        'api_key': api_key,
        'url': url,
        'render': 'false',  # Set to 'true' if page needs JavaScript (costs 10 credits)
        'premium': 'true',  # Optional: better proxies for Amazon (costs more credits)
    }

    try:
        logging.info(f"Scraping via ScraperAPI: {url}")
        response = requests.get(scraper_url, params=params, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Current selectors for Amazon.in (2026 layouts)
        price_elem = soup.select_one('#corePrice_feature_div .a-offscreen') or \
                     soup.select_one('.a-price .a-offscreen') or \
                     soup.select_one('span.a-price-whole') or \
                     soup.select_one('#priceblock_ourprice') or \
                     soup.select_one('span.apexPriceToPay')

        if not price_elem:
            # Fallback regex if selectors fail
            price_match = re.search(r'₹[\s]*?([\d,]+(?:\.\d{1,2})?)', response.text)
            if price_match:
                price_text = price_match.group(1).replace(',', '')
            else:
                logging.error("No price found even with regex")
                raise ValueError("Could not locate price")
        else:
            price_text = price_elem.get_text(strip=True).replace('₹', '').replace(',', '').strip()

        # Handle decimal part if separate
        fraction = soup.select_one('span.a-price-fraction')
        if fraction and '.' not in price_text:
            price_text += '.' + fraction.get_text(strip=True).zfill(2)

        price = float(price_text)
        logging.info(f"Price via ScraperAPI: ₹{price}")
        return price

    except requests.RequestException as e:
        logging.error(f"ScraperAPI request failed: {str(e)}")
        raise
    except ValueError as e:
        logging.error(f"Price parsing failed: {str(e)}")
        raise
    except Exception as e:
        logging.exception(f"Unexpected ScraperAPI error")
        raise

# ────────────────────────────────────────────────
#           Brevo API Email Sending Functions
# ────────────────────────────────────────────────

def send_email(to_email, subject, body_text, body_html=None):
    api_key = os.getenv('BREVO_API_KEY')
    from_email = os.getenv('BREVO_FROM_EMAIL')

    if not api_key:
        logging.error("BREVO_API_KEY missing")
        raise ValueError("Brevo API key is missing")
    if not from_email:
        logging.error("BREVO_FROM_EMAIL missing")
        raise ValueError("Brevo from email is missing")

    headers = {
        'accept': 'application/json',
        'api-key': api_key,
        'content-type': 'application/json'
    }

    payload = {
        "sender": {"name": "Amazon Price Tracker", "email": from_email},
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
            headers=headers,
            timeout=15
        )

        if response.status_code in (200, 201, 202):
            logging.info(f"Email sent to {to_email}")
            return True
        else:
            error_msg = f"Brevo error ({response.status_code}): {response.text}"
            logging.error(error_msg)
            raise Exception(error_msg)

    except requests.RequestException as e:
        logging.error(f"Email network error: {str(e)}")
        raise


def send_welcome_email(to_email, product_url):
    subject = "Product Tracking Confirmation"
    body_text = f"""
Thank you for using Amazon Price Tracker!

Product added: {product_url}

You'll get alerts when the price changes.

Best regards,
Amazon Price Tracker Team
    """
    body_html = f"""
    <h2>Welcome!</h2>
    <p>Product added: <a href="{product_url}">{product_url}</a></p>
    <p>Price change alerts coming your way.</p>
    <p>Best regards,<br>Amazon Price Tracker Team</p>
    """

    send_email(to_email, subject, body_text, body_html)


def send_price_alert(to_email, product_url, old_price, new_price, min_price=None, max_price=None):
    threshold_msg = ""
    if min_price is not None and new_price <= min_price:
        threshold_msg += f"\nDropped below your min: ₹{min_price:.2f}!"
    if max_price is not None and new_price >= max_price:
        threshold_msg += f"\nExceeded your max: ₹{max_price:.2f}!"

    subject = "Amazon Price Alert!"
    body_text = f"""
Price changed!

URL: {product_url}
Old: ₹{old_price:.2f}
New: ₹{new_price:.2f}{threshold_msg}

Check now!
    """
    body_html = f"""
    <h2>Price Alert!</h2>
    <p><a href="{product_url}">{product_url}</a></p>
    <p>Old: ₹{old_price:.2f}</p>
    <p><strong>New: ₹{new_price:.2f}</strong></p>
    {f'<p><strong>{threshold_msg.strip()}</strong></p>' if threshold_msg else ''}
    <p>Check now!</p>
    """

    send_email(to_email, subject, body_text, body_html)