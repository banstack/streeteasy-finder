# StreetEasy Apartment Tracker (SET)

A Python script that monitors StreetEasy apartment listings and sends email notifications when new apartments matching your criteria are found.

<img width="1030" alt="image" src="https://github.com/user-attachments/assets/1c82b3e6-d36c-4b90-877d-7d448cb07566" />


## Features
- **Automated monitoring**: Runs every 5 minutes to check for new listings (configurable)
- **Email notifications**: Beautiful HTML emails with apartment images and details
- **Duplicate prevention**: Uses SQLite database to track seen listings
- **Price filtering**: Clean price extraction from StreetEasy listings
- **Robust scraping**: Handles rate limiting and website changes

## Requirements
- Python 3.7+
- Internet connection
- Gmail account (or other SMTP email provider)

## Setup Instructions

### Option 1: Docker Setup (Recommended) 🐳

The easiest way to run the apartment tracker with consistent environment:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit with your settings
nano .env

# 3. Build and run with Docker
./run.sh build
./run.sh run
```

**Docker Commands:**
```bash
./run.sh build    # Build the Docker image
./run.sh run      # Start the apartment tracker
./run.sh logs     # View logs
./run.sh stop     # Stop the tracker
./run.sh restart  # Restart the tracker
./run.sh clean    # Clean up containers
```

**Benefits:**
- ✅ No Python environment setup needed
- ✅ Consistent environment across all systems
- ✅ Persistent data storage (`./data/` and `./logs/`)
- ✅ Easy start/stop management

### Option 2: Local Python Setup

```bash
git clone <your-repo-url>
cd apartment-tracker
pip install -r requirements.txt
```

### Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual values
nano .env  # or use your preferred editor
```

### Gmail Setup (Recommended)

For Gmail, you need to set up an App Password:

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate App Password**:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Click "2-Step Verification" → "App passwords"
   - Select "Mail" and generate password
   - Copy the 16-character password (no spaces)
3. **Update .env file**:
   ```
   EMAIL_ADDRESS=your_email@gmail.com
   EMAIL_PASSWORD=your_16_character_app_password
   TO_EMAIL=your_email@gmail.com
   ```

### Customize Your Search

Update the `SE_URL` in your `.env` file with your StreetEasy search criteria:

```
# Example: Studio/1BR under $3000 in Manhattan
SE_URL=https://streeteasy.com/for-rent/nyc/price:-3000|beds%3C=1|area:106

# Example: 2BR under $4000 in Brooklyn
SE_URL=https://streeteasy.com/for-rent/brooklyn/price:-4000|beds:2
```

### Run the Tracker

**With Docker (Recommended):**
```bash
./run.sh run    # Starts in background
./run.sh logs   # View what's happening
```

**With Local Python:**
```bash
python apartment_tracker.py
```

The tracker will:
- Check for new listings immediately
- Continue checking every 5 minutes (configurable)
- Send email notifications for new apartments
- Store listings in database to prevent duplicates

**Docker**: Runs in background, use `./run.sh stop` to stop  
**Local**: Press `Ctrl+C` to stop

## Configuration Options

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SE_URL` | StreetEasy search URL | Yes | - |
| `EMAIL_ADDRESS` | Your email address | Yes | - |
| `EMAIL_PASSWORD` | Email app password | Yes | - |
| `TO_EMAIL` | Recipient email | No | Same as EMAIL_ADDRESS |
| `DB_PATH` | Database file path | No | `apartments.db` |
| `SMTP_SERVER` | SMTP server | No | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | No | `587` |

## Other Email Providers

### Outlook/Hotmail
```
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

### Yahoo Mail
```
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
```

## Database Queries

View stored apartments:
```bash
# All apartments
sqlite3 apartments.db "SELECT title, price, address FROM apartments;"

# Recent apartments (last 24 hours)
sqlite3 apartments.db "SELECT title, price, first_seen FROM apartments WHERE first_seen > datetime('now', '-1 day');"

# Count by price range
sqlite3 apartments.db "SELECT COUNT(*) as count, price FROM apartments GROUP BY price ORDER BY count DESC;"
```

## Troubleshooting

### Docker Issues
```bash
# View what's happening
./run.sh logs

# Restart if something goes wrong
./run.sh restart

# Clean slate (rebuild everything)
./run.sh stop
./run.sh clean
./run.sh build
./run.sh run
```

### Email Issues
- Ensure 2FA is enabled and App Password is generated
- Check email credentials in `.env` file
- Verify SMTP settings for your email provider

### No Listings Found
- Check if StreetEasy URL is accessible
- Website structure may have changed (selectors need updating)
- Rate limiting (script includes retry logic)

### Database Issues
**Docker:**
```bash
# Reset database (deletes all stored listings)
rm -rf data/
./run.sh restart
```

**Local Python:**
```bash
# Reset database (deletes all stored listings)
rm apartments.db
```

## Contributing

Feel free to submit issues and enhancement requests! 🤝

## License

This project is for educational and personal use only. Please respect StreetEasy's terms of service and use responsibly.

## Disclaimer

Web scraping should be done responsibly. This tool:
- Uses reasonable delays between requests
- Respects rate limiting
- Is intended for personal use only
- Should comply with website terms of service
