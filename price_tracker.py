import os
import requests
from bs4 import BeautifulSoup
import logging
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def check_price(url):
    """
    Fetch current price from Amazon.in product page using requests + BeautifulSoup.
    Works reliably on PythonAnywhere free tier (no Selenium/browser required).
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.amazon.in/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        logging.info(f"Fetching price from: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Comprehensive list of price selectors for Amazon.in (updated 2026)
        price_selectors = [
            '#corePrice_feature_div .a-offscreen',                # Primary modern price
            '#corePriceDisplay_feature_div .a-offscreen',         # Variant 1
            '.a-price .a-offscreen',                              # Common fallback
            '.a-price-whole',                                     # Whole part (combine with fraction)
            'span.a-price-whole + span.a-price-fraction',         # Whole + decimal
            '#priceblock_ourprice',                               # Older product pages
            '#priceblock_dealprice',                              # Deal price
            '.a-price-symbol + .a-price-whole',                   # Symbol + whole
            'span.apexPriceToPay',                                # Apex price block
        ]

        price_elem = None
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                logging.debug(f"Found price using selector: {selector}")
                break

        if not price_elem:
            # Last resort: search for any text that looks like ₹ followed by number
            price_match = re.search(r'₹[\d,]+(?:\.\d+)?', response.text)
            if price_match:
                price_text = price_match.group(0).replace('₹', '').replace(',', '')
                logging.warning("Used regex fallback to find price")
            else:
                logging.error("No price element or pattern found on page")
                logging.debug(f"Page title: {soup.title.string if soup.title else 'No title'}")
                logging.debug(f"First 300 chars: {response.text[:300]}...")
                raise ValueError("Could not locate price on Amazon page")
        else:
            price_text = price_elem.get_text(strip=True).replace('₹', '').replace(',', '').strip()

        # Handle cases where whole and fraction are separate
        fraction_elem = price_elem.find_next('span', class_='a-price-fraction') if price_elem else None
        if fraction_elem and '.' not in price_text:
            fraction = fraction_elem.get_text(strip=True)
            price_text += '.' + fraction.zfill(2)  # Ensure two decimal places

        # Final clean-up and conversion
        price_text = re.sub(r'[^\d.]', '', price_text)  # Remove any leftover non-numeric chars
        try:
            price = float(price_text)
            if price <= 0:
                raise ValueError("Price is zero or negative")
        except ValueError as ve:
            logging.error(f"Price conversion failed: '{price_text}' → {str(ve)}")
            raise ValueError(f"Invalid price format: {price_text}")

        logging.info(f"Successfully scraped price: ₹{price:.2f}")
        return price

    except requests.Timeout:
        logging.error(f"Timeout while fetching {url}")
        raise Exception("Request timed out while fetching Amazon page")
    except requests.RequestException as e:
        logging.error(f"Network/HTTP error for {url}: {str(e)}")
        raise Exception(f"Failed to fetch page: {str(e)}")
    except Exception as e:
        logging.exception(f"Unexpected error while checking price for {url}")
        raise


# ────────────────────────────────────────────────
#           Brevo API Email Sending Functions
# ────────────────────────────────────────────────

def send_email(to_email, subject, body_text, body_html=None):
    """
    Send email using Brevo (formerly Sendinblue) API
    """
    api_key = os.getenv('BREVO_API_KEY')
    from_email = os.getenv('BREVO_FROM_EMAIL')

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
            logging.info(f"Email successfully sent to {to_email}")
            return True
        else:
            error_msg = f"Brevo API error ({response.status_code}): {response.text}"
            logging.error(error_msg)
            raise Exception(error_msg)

    except requests.RequestException as e:
        logging.error(f"Network error sending email: {str(e)}")
        raise


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

    return send_email(to_email, subject, body_text, body_html)


def send_price_alert(to_email, product_url, old_price, new_price, min_price=None, max_price=None):
    threshold_message = ""
    if min_price is not None and new_price <= min_price:
        threshold_message += f"\nThe price has dropped below your minimum threshold of ₹{min_price:.2f}!"
    if max_price is not None and new_price >= max_price:
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

    return send_email(to_email, subject, body_text, body_html)