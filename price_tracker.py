import os
import requests
from bs4 import BeautifulSoup
import logging
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def check_price(url):
    """
    Fetch Amazon product price using ScraperAPI (bypasses blocks & proxy issues).
    """
    api_key = os.getenv('SCRAPERAPI_KEY')
    if not api_key:
        logging.error("SCRAPERAPI_KEY not found")
        raise ValueError("ScraperAPI key is missing")

    scraper_url = "http://api.scraperapi.com"
    params = {
        'api_key': api_key,
        'url': url,
        'render': 'false',
        'premium': 'true',
    }

    try:
        logging.info(f"Scraping via ScraperAPI: {url}")
        response = requests.get(scraper_url, params=params, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        price_elem = soup.select_one('#corePrice_feature_div .a-offscreen') or \
                     soup.select_one('.a-price .a-offscreen') or \
                     soup.select_one('span.a-price-whole') or \
                     soup.select_one('#priceblock_ourprice') or \
                     soup.select_one('span.apexPriceToPay')

        if not price_elem:
            price_match = re.search(r'₹[\s]*?([\d,]+(?:\.\d{1,2})?)', response.text)
            if price_match:
                price_text = price_match.group(1).replace(',', '')
            else:
                logging.error("No price found even with regex")
                raise ValueError("Could not locate price")
        else:
            price_text = price_elem.get_text(strip=True).replace('₹', '').replace(',', '').strip()

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
#           Gmail SMTP Email Sending Functions
# ────────────────────────────────────────────────

def send_email(to_email, subject, body_text, body_html=None):
    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = os.getenv('GMAIL_USER')
    smtp_pass = os.getenv('GMAIL_APP_PASSWORD')
    from_email = smtp_user

    if not smtp_user or not smtp_pass:
        logging.error("Gmail SMTP credentials missing")
        raise ValueError("Gmail user or App Password not set")

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Amazon Price Tracker <{from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body_text, 'plain'))

        if body_html:
            msg.attach(MIMEText(body_html, 'html'))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()

        logging.info(f"Gmail email sent to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logging.error("Gmail authentication failed - check App Password")
        raise
    except Exception as e:
        logging.error(f"Gmail SMTP error: {str(e)}")
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
    <h2>Welcome to Amazon Price Tracker!</h2>
    <p>Product added: <a href="{product_url}">{product_url}</a></p>
    <p>You'll be notified on price changes.</p>
    <p>Best regards,<br>Amazon Price Tracker Team</p>
    """

    send_email(to_email, subject, body_text, body_html)


def send_price_alert(to_email, product_url, old_price, new_price, min_price=None, max_price=None):
    threshold_msg = ""
    if min_price is not None and new_price <= min_price:
        threshold_msg += f"\nDropped below min ₹{min_price:.2f}!"
    if max_price is not None and new_price >= max_price:
        threshold_msg += f"\nExceeded max ₹{max_price:.2f}!"

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