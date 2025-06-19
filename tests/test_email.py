import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def test_email():
    email = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD')
    to_email = os.getenv('TO_EMAIL')
    
    print(f"Testing email: {email}")
    print(f"Password length: {len(password) if password else 0}")
    print(f"To email: {to_email}")
    
    try:
        # Create a simple test message
        msg = MIMEText("This is a test email from your apartment tracker!")
        msg['Subject'] = "🧪 Test Email - Apartment Tracker"
        msg['From'] = email
        msg['To'] = to_email
        
        # Connect to Gmail
        print("Connecting to Gmail SMTP server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        print("Logging in...")
        server.login(email, password)
        
        print("Sending test email...")
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
        if "Username and Password not accepted" in str(e):
            print("\n🔧 Fix suggestions:")
            print("1. Make sure 2-Factor Authentication is enabled on your Gmail")
            print("2. Generate a new App Password:")
            print("   - Go to https://myaccount.google.com/security")
            print("   - Click '2-Step Verification' → 'App passwords'")
            print("   - Generate password for 'Mail'")
            print("   - Use the 16-character password (no spaces)")
            print("3. Update your .env file with the new app password")

if __name__ == "__main__":
    test_email() 