import os
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.DEBUG)

def check_price(url):
    """
    Fetch Amazon product price using requests + BeautifulSoup
    No Selenium → works on PythonAnywhere free tier
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Try multiple common Amazon price selectors (2025–2026 layouts)
        selectors = [
            '.a-price-whole',                     # Main price whole part
            '#corePrice_feature_div .a-offscreen', # Modern price block
            '.a-price .a-offscreen',              # Alternative price
            '#priceblock_ourprice',               # Older layout
            '.a-price-symbol + .a-price-whole',   # Symbol + whole
            'span.a-price',                       # General price container
        ]

        price_element = None
        for sel in selectors:
            price_element = soup.select_one(sel)
            if price_element:
                break

        if not price_element:
            logging.error(f"No price element found on {url}")
            logging.debug(f"Page title: {soup.title.string if soup.title else 'No title'}")
            raise ValueError("Could not locate price on Amazon page")

        # Clean and parse price
        price_text = price_element.get_text(strip=True)
        price_text = price_text.replace('₹', '').replace(',', '').replace(' ', '').strip()

        # Sometimes price has decimal part in separate span
        if '.' not in price_text and price_element.find_next('span', class_='a-price-fraction'):
            fraction = price_element.find_next('span', class_='a-price-fraction').get_text(strip=True)
            price_text += '.' + fraction

        try:
            price = float(price_text)
        except ValueError:
            logging.error(f"Could not convert price text to float: '{price_text}'")
            raise ValueError("Invalid price format")

        logging.info(f"Price found for {url}: ₹{price}")
        return price

    except requests.RequestException as e:
        logging.error(f"Request failed for {url}: {str(e)}")
        raise
    except ValueError as e:
        logging.error(f"Price parsing error for {url}: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error checking price for {url}: {str(e)}")
        raise


# ────────────────────────────────────────────────
#           Brevo API Email Sending Function
# ────────────────────────────────────────────────

def send_email(to_email, subject, body_text, body_html=None):
    """
    Send email using Brevo (Sendinblue) API
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