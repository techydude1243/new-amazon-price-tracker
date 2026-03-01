import os
import requests
from bs4 import BeautifulSoup
import logging
import re

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def check_price(url):
    """
    Fetch current price from Amazon.in using requests + BeautifulSoup.
    Updated selectors for 2026 layouts + fallback regex.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': 'https://www.amazon.in/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    try:
        logging.info(f"Scraping price from: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # 2026-updated selectors for Amazon.in (tested on real pages)
        selectors = [
            'span.a-price-whole',                              # Whole rupees
            'span.a-price-fraction',                           # Paise (decimal)
            '#corePrice_feature_div span.a-offscreen',         # Primary modern price
            '#corePriceDisplay_feature_div span.a-offscreen',  # Variant
            '.a-price span.a-offscreen',                       # Common fallback
            '#priceblock_ourprice',                            # Older pages
            '#priceblock_dealprice',                           # Deal price
            'span.apexPriceToPay',                             # Apex block
            '.a-price-symbol + span.a-price-whole',            # Symbol + whole
        ]

        price_whole = None
        price_fraction = None

        # First try structured selectors
        for sel in selectors:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(strip=True)
                if 'whole' in sel or 'whole' in elem.get('class', []):
                    price_whole = text
                elif 'fraction' in sel or 'fraction' in elem.get('class', []):
                    price_fraction = text
                else:
                    # Full price in one element
                    full_text = text.replace('₹', '').replace(',', '').strip()
                    if full_text.replace('.', '').isdigit():
                        price = float(full_text)
                        logging.info(f"Found full price: ₹{price}")
                        return price

        # Combine whole + fraction if found separately
        if price_whole and price_fraction:
            price_text = f"{price_whole}.{price_fraction.zfill(2)}"
            price = float(price_text)
            logging.info(f"Combined price: ₹{price}")
            return price

        # Fallback: regex search in entire page (very reliable)
        price_match = re.search(r'₹[\s]*?([\d,]+(?:\.\d{1,2})?)', response.text)
        if price_match:
            price_text = price_match.group(1).replace(',', '')
            price = float(price_text)
            logging.info(f"Regex fallback found price: ₹{price}")
            return price

        # If nothing works
        logging.error(f"No price found on {url}")
        logging.debug(f"Page title: {soup.title.string if soup.title else 'No title'}")
        raise ValueError("Could not locate price on Amazon page")

    except requests.Timeout:
        logging.error(f"Timeout fetching {url}")
        raise Exception("Request timed out")
    except requests.RequestException as e:
        logging.error(f"Request failed for {url}: {str(e)}")
        raise Exception(f"Failed to load page: {str(e)}")
    except ValueError as e:
        logging.error(f"Price parsing error: {str(e)}")
        raise
    except Exception as e:
        logging.exception(f"Unexpected error for {url}")
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