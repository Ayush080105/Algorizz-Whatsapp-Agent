import csv
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import your existing driver loader
import groupReader  # use launch_driver and helpers from here

# ------------------ Paths ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "group_convo.csv")

# ------------------ Logging ------------------
from datetime import datetime
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")

# ------------------ WhatsApp Helpers ------------------
def wait_for_whatsapp(driver):
    log("Waiting for WhatsApp Web to load...")
    groupReader.wait_for_page_load(driver)

def search_and_open_group(driver, group_name):
    groupReader.search_and_open_group(driver, group_name)

def send_message(driver, message):
    log(f"✉️ Sending message: {message[:50]}{'...' if len(message)>50 else ''}")
    try:
        message_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )
        message_box.click()
        time.sleep(1)
        
        # Clear any existing text
        message_box.send_keys(Keys.CONTROL + 'a')
        time.sleep(0.5)
        message_box.send_keys(Keys.BACKSPACE)
        time.sleep(0.5)
        
        # Send the message
        message_box.send_keys(message)
        time.sleep(1)
        message_box.send_keys(Keys.ENTER)
        time.sleep(2)  # Wait a bit longer to ensure message is sent
        
        log("✅ Message sent successfully")
        
    except Exception as e:
        log(f"❌ Failed to send message: {e}")
        raise

# ------------------ Main Task ------------------
def send_morning_message(csv_path=CSV_PATH):
    if not os.path.exists(csv_path):
        log(f"❌ CSV file not found: {csv_path}")
        return

    log("🚀 Launching WhatsApp Web...")
    driver, temp_profile = groupReader.launch_driver(headless=False)  # Use visible browser for sending messages
    
    try:
        wait_for_whatsapp(driver)
        
        # Wait for user to scan QR code if needed
        log("Please scan the QR code if needed, then press Enter to continue...")
        input()
        
        # Read groups from CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            groups = [row['groupName'] for row in reader]
        
        morning_message = "Good morning team! Please reply with what you plan to do today for your tasks."
        log(f"📤 Sending message to {len(groups)} groups")

        success_count = 0
        for i, group in enumerate(groups, 1):
            try:
                log(f"📋 Processing group {i}/{len(groups)}: {group}")
                search_and_open_group(driver, group)
                time.sleep(3)  # Wait for group to fully load
                send_message(driver, morning_message)
                success_count += 1
                time.sleep(2)  # Short pause between groups
                
            except Exception as e:
                log(f"❌ Failed to send message to group {group}: {e}")
                # Continue with next group even if one fails
                continue

        log(f"✅ Morning messages sent to {success_count}/{len(groups)} groups successfully!")

    except Exception as e:
        log(f"❌ Fatal error in send_morning_message: {e}")
    
    finally:
        # Clean up
        if 'driver' in locals():
            driver.quit()
        groupReader.cleanup_chrome_processes()
        # Clean up temp profile if needed
        if 'temp_profile' in locals():
            import shutil
            try:
                shutil.rmtree(temp_profile, ignore_errors=True)
            except:
                pass

# ------------------ Run ------------------
if __name__ == "__main__":
    send_morning_message()