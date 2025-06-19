"""
StreetEasy Apartment Tracker

A Python script that monitors StreetEasy apartment listings and sends email 
notifications when new apartments matching your criteria are found.

Author: Your Name
License: MIT (for educational and personal use)
"""

import os
import sqlite3
import time
import hashlib
import logging
import random
import smtplib
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import List, Dict

# Third-party libraries
import requests
from bs4 import BeautifulSoup
import schedule
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('apartment_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__);

class ApartmentTracker:
    def __init__(self):
        self.db_path = os.getenv('DB_PATH', 'apartments.db');
        self.url = os.getenv('SE_URL')
        # Note: You may have to switch headers as StreetEasy has request checks on web scrapers
        # Web scrapers are legal in the US

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        # Create a session for better connection handling
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Initalize database
        self.init_database()
    
    # Initalize SQLite database to store apartments seen
    def init_database(self):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS apartments (
                id TEXT PRIMARY KEY,
                title TEXT,
                price TEXT,
                address TEXT,
                url TEXT,
                bedrooms TEXT,
                bathrooms TEXT,
                sqft TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add image_url column if it doesn't exist
        try:
            cursor.execute('ALTER TABLE apartments ADD COLUMN image_url TEXT')
            logger.info('Added image_url column to existing database')
        except sqlite3.OperationalError:
            # In case where column already exists, which is fine
            pass

        connection.commit()
        connection.close()

    # Generate unique IDs for apartment lstings
    def generate_listing_id(self, title: str, address: str, price: str) -> str:
        unique_string = f"{title}_{address}_{price}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def get_page_with_retry(self, url: str, max_retries: int = 3) -> requests.Response:
        # Get page with retry logic and random delays
        for attempt in range(max_retries):
            try:
                # Random delays between requests to avoid rate limiting
                if attempt > 0:
                    delay = random.uniform(2,5)
                    logger.info(f"Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                logger.info(f"Attempting to fetch page (attempt {attempt+1}/{max_retries})...")
                response = self.session.get(url, timeout=30)

                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    logger.warning(f"403 Forbidden - attempt # {attempt + 1}")
                    if attempt < max_retries - 1:
                        # Switch user agents to get passed 403
                        user_agents = [
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
                            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        ]
                        self.session.headers['User-Agent'] = random.choice(user_agents)
                        continue
                    else:
                        logger.warning(f"HTTP {response.status_code} - attempt #{attempt + 1}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed on attempt {attempt + 1}: {e}")

        raise requests.exceptions.RequestException(f"Failed to fetch page after {max_retries} attempts")
    
    # Scrape apartment listings from website
    def scrape_listings(self) -> List[Dict]:
        try:
            logger.info("Starting to scrape listings...")

            # Get the page with retry logic
            response = self.get_page_with_retry(self.url)

            # Initialize Beautiful Soup
            soup = BeautifulSoup(response.content, 'html.parser')
            listings = []

            # Select HTML node by class data-testid, note if change to StreetEasy testing library we may experience downtime
            apartment_cards = soup.select('[data-testid="listing-card"]')

            if not apartment_cards:
                logger.warning("No apartment cards found with listing-card selector")
                return []
            
            logger.info(f"Found {len(apartment_cards)} apartment cards")

            for card in apartment_cards:
                try:
                    # Extract URL from the image container link 
                    link_elem = card.select_one('a.ImageContainer-module__listingLink___sYIL9')
                    if not link_elem:
                        # Try alternative selectors for the link
                        link_elem = card.select_one('a[href*="/rental/"]') or card.select_one('a[href*="/building/"]')
                        if not link_elem:
                            logger.debug("No link element found in card")
                            continue

                    full_url = link_elem.get('href', '')
                    if not full_url.startswith('http'):
                        full_url = f"https://streeteasy.com{full_url}"
                    
                    logger.debug(f"Found URL: {full_url}")
                    
                    # Extract title and image URL from image element
                    img_elem = card.select_one('img.CardImage-module__cardImage__cirIn')
                    if not img_elem:
                        # Try alternative selectors for images
                        img_elem = card.select_one('img') or card.select_one('[data-testid="listing-image"] img')
                    
                    title = 'N/A'
                    image_url = None

                    if img_elem:
                        alt_text = img_elem.get('alt', '')
                        if alt_text:
                            # Extract building name from alt text like "528 East 13th Street 1D image 1 of 23"
                            title = alt_text.split('image')[0].strip() if 'image' in alt_text else alt_text.strip()
                        
                        # Extract image URL
                        image_url = img_elem.get('src') or img_elem.get('data-src')
                        if image_url and not image_url.startswith('http'):
                            image_url = f"https://streeteasy.com{image_url}"
                    
                    # If we didn't get title from image, try to extract from other elements
                    if title == 'N/A':
                        # Try various selectors for title/address
                        title_selectors = [
                            '[data-testid="listing-title"]',
                            '.ListingCard-module__address__',
                            '.address',
                            'h3',
                            'h2',
                            '[class*="address"]',
                            '[class*="title"]'
                        ]
                        for selector in title_selectors:
                            title_elem = card.select_one(selector)
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                break
                    
                    logger.debug(f"Extracted title: {title}")
                    
                    # Extract price -- look for price elements
                    price = 'N/A'
                    price_selectors = [
                        '.PriceInfo-module__priceText___Ej9Ej',
                        '.price',
                        '[data-testid="price"]',
                        '.ListingDetails-module__price___',
                        '[class*="price"]',
                        '[class*="Price"]',
                        '.rent-price',
                        '.listing-price'
                    ]
                    
                    for selector in price_selectors:
                        price_elem = card.select_one(selector)
                        if price_elem:
                            raw_price = price_elem.get_text(strip=True)
                            # Clean up the price - extract only the dollar amount
                            price_match = re.search(r'\$[\d,]+', raw_price)
                            if price_match:
                                price = price_match.group(0)
                            else:
                                # Fallback: try to clean up manually
                                price = raw_price.split('base')[0].split('net')[0].split('rent')[0].strip()
                                if not price.startswith('$'):
                                    price = 'N/A'
                            break
                    
                    logger.debug(f"Extracted price: {price}")
                    
                    # Extract address
                    address = 'N/A'
                    if title != 'N/A' and any(word in title.lower() for word in ['street', 'avenue', 'road', 'place', 'drive']):
                        # Extract address from title
                        address_parts = title.split()
                        if len(address_parts) >= 3:
                            address = ' '.join(address_parts[:-1]) # Remove apartment number
                    
                    # Extract bedrooms, bathrooms, sqft
                    bedrooms = bathrooms = sqft = 'N/A'

                    # Look for beds/baths/sqft in the BedsBathsSqft module
                    beds_baths_container = card.select_one('.BedsBathsSqft-module__bedsBathsSqft___QFOK-')
                    if beds_baths_container:
                        bed_bath_items = beds_baths_container.select('.BedsBathsSqft-module__text___lnveO')
                        for item in bed_bath_items:
                            text = item.get_text(strip=True).lower()
                            if 'bed' in text:
                                bedrooms = item.get_text(strip=True)
                            elif 'bath' in text:
                                bathrooms = item.get_text(strip=True)
                            elif 'ft²' in text:
                                sqft = item.get_text(strip=True)
                    # Skip if we don't have essential information
                    logger.debug(f"Final check - Title: '{title}', URL: '{full_url}'")
                    if title == 'N/A' or not full_url:
                        logger.debug(f"Skipping listing - Title: '{title}', URL: '{full_url}'")
                        continue

                    # Listing object mapping to store in SQLite
                    listing = {
                        'id': self.generate_listing_id(title, address, price),
                        'title': title,
                        'price': price,
                        'address': address,
                        'url': full_url,
                        'bedrooms': bedrooms,
                        'bathrooms': bathrooms,
                        'sqft': sqft,
                        'image_url': image_url
                    }

                    listings.append(listing)

                except Exception as e:
                    logger.warning(f"Error parsing individual listing: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(listings)} listings")
            return listings
        except Exception as e:
            logger.error(f"Error scraping listings: {e}")
            return []
        
    def is_new_listing(self, listing_id: str) -> bool:
        # Check if listing is new (not in database)
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute('SELECT id FROM apartments WHERE id = ?', (listing_id,))
        result = cursor.fetchone()
        connection.close()
        return result is None
    
    def save_listing(self, listing: Dict):
        # Save new listing to database
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        # Use new schema with image_url
        cursor.execute('''
            INSERT OR IGNORE INTO apartments 
            (id, title, price, address, url, bedrooms, bathrooms, sqft, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing['id'], listing['title'], listing['price'], 
            listing['address'], listing['url'], listing['bedrooms'],
            listing['bathrooms'], listing['sqft'], listing.get('image_url')
        ))

        connection.commit()
        connection.close()
        
    # Download image from URL and return bytes
    def download_image(self, image_url: str) -> bytes:
        try:
            response = self.session.get(image_url, timeout=10)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.warning(f"Failed to download image from {image_url}: {e}")
        return None
    
    # Send email notifications if any new listings
    def send_email_notifications(self, new_listings: List[Dict]):
        try:
            email = os.getenv('EMAIL_ADDRESS')
            password = os.getenv('EMAIL_PASSWORD')
            to_email = os.getenv('TO_EMAIL') or email

            if not email or not password:
                logger.error("Email credentials not configured! Please set EMAIL_ADDRESS and EMAIL_PASSWORD in your .env file")
                return
            
            # Use 'related' for inline images
            msg = MIMEMultipart('related')
            msg['From'] = email
            msg['To'] = to_email
            msg['Subject'] = f"🏠 {len(new_listings)} New Apartment Listing(s) Found!"

            # Create HTML email body with table-based layout (better email client support)
            html_body = """
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #ffffff;">
            <div style="max-width: 1200px; margin: 0 auto;">
                <h2 style="color: #2c5aa0; text-align: center; margin-bottom: 10px;">🏠 New Apartment Listings Found!</h2>
                <p style="text-align: center; font-size: 1.1em; margin-bottom: 30px;">Here are the new apartments that match your criteria:</p>
                
                <!-- Start of listings table for better email compatibility -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td>
            """

            image_attachments = []
            
            for i, listing in enumerate(new_listings, 1):
                image_cid = f"image{i}"
                image_html = ""

                # Try to download and embed image
                if listing.get('image_url'):
                    image_data = self.download_image(listing['image_url'])
                    if image_data:
                        image_attachments.append((image_cid, image_data))
                        image_html = f'<img src="cid:{image_cid}" style="width: 100%; max-width: 300px; height: 200px; object-fit: cover; border-radius: 8px; margin-bottom: 15px;" alt="Apartment Image">'
                
                # Use table-based layout for better email client compatibility
                html_body += f"""
                <!-- Listing Card {i} -->
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 25px; border: 1px solid #ddd; border-radius: 12px; background-color: #f9f9f9;">
                    <tr>
                        <td style="padding: 20px;">
                            <h3 style="color: #2c5aa0; margin: 0 0 15px 0; font-size: 18px; font-weight: bold;">{listing['title']}</h3>
                            {image_html}
                            <div style="color: #e74c3c; font-size: 20px; font-weight: bold; margin: 15px 0;">💰 {listing['price']}</div>
                            <div style="margin: 15px 0; color: #555;">
                                <p style="margin: 8px 0; font-size: 14px;"><strong>📍 Address:</strong> {listing['address']}</p>
                                <p style="margin: 8px 0; font-size: 14px;"><strong>🏠 Details:</strong> {listing['bedrooms']} | {listing['bathrooms']} | {listing['sqft']}</p>
                            </div>
                            <table cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td style="background-color: #2c5aa0; border-radius: 6px; padding: 12px 24px;">
                                        <a href="{listing['url']}" style="color: #ffffff !important; text-decoration: none; font-weight: bold; font-size: 14px; display: block;">View Full Listing</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
                """
                
            html_body += """
                        </td>
                    </tr>
                </table>
                <!-- End of listings -->
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                <p style="color: #666; font-size: 14px; text-align: center; margin: 20px 0;">
                    This is an automated notification from your apartment tracker.<br>
                    Happy apartment hunting! 🏠
                </p>
            </div>
            </body>
            </html>
            """

            # Create plain text version (fallback)
            text_body = f"New apartment listings found ({len(new_listings)} total):\n\n"
            for i, listing in enumerate(new_listings, 1):
                text_body += f"#{i} {listing['title']}\n"
                text_body += f"💰 {listing['price']}\n"
                text_body += f"📍 {listing['address']}\n"
                text_body += f"🏠 {listing['bedrooms']} | {listing['bathrooms']} | {listing['sqft']}\n"
                text_body += f"🔗 {listing['url']}\n"
                if listing.get('image_url'):
                    text_body += f"🖼️ Image: {listing['image_url']}\n"
                text_body += "-" * 50 + "\n\n"
              
            # Create multipart alternative for HTML and text
            msg_alternative = MIMEMultipart('alternative')
            msg_alternative.attach(MIMEText(text_body, 'plain'))
            msg_alternative.attach(MIMEText(html_body, 'html'))
            msg.attach(msg_alternative)
            
            # Attach inline images
            for image_cid, image_data in image_attachments:
                img = MIMEImage(image_data)
                img.add_header('Content-ID', f'<{image_cid}>')
                img.add_header('Content-Disposition', 'inline')
                msg.attach(img)
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(email, password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Email notification sent successfully for {len(new_listings)} listings with {len(image_attachments)} images")
        except Exception as e:
            logger.error(f"❌ Error sending email: {e}")

    
    # Driver function for checking new listings and sending notifcations
    def check_for_new_listings(self):
        logger.info("Checking for new listings...")

        listings = self.scrape_listings()
        if not listings:
            logger.warning("No listings found - this might be temporary")
            return
        
        new_listings = []
        for listing in listings:
            if self.is_new_listing(listing['id']):
                new_listings.append(listing)
                self.save_listing(listing)
        
        if new_listings:
            logger.info(f"Found {len(new_listings)} new listings!")
            self.send_email_notifications(new_listings)
        else:
            logger.info("No new listings found")

    # Run the scheduler which checks every X minutes
    def run_scheduler(self):
        logger.info("Starting apartment rracker scheculer...")
        logger.info("Press Ctrl+C to stop")

        interval = int(os.getenv('TIME_INTERVAL', '5'))

        # Schedule the job every X minutes (default: 5)
        schedule.every(interval).minutes.do(self.check_for_new_listings)

        # Run once immediately
        self.check_for_new_listings()

        # Keep the script running, unless stopped by user
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Apartment tracker stopped by user")


if __name__ == "__main__":
    tracker = ApartmentTracker()
    tracker.run_scheduler()


