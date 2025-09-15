import csv
import time
import os
import shutil
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
    try:
        log(f"🔍 Searching for group: {group_name}")
        
        # Find and use the search box
        search_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        
        # Clear search box
        search_box.click()
        time.sleep(1)
        search_box.send_keys(Keys.CONTROL + 'a')
        time.sleep(0.5)
        search_box.send_keys(Keys.BACKSPACE)
        time.sleep(1)
        
        # Type group name
        search_box.send_keys(group_name)
        time.sleep(3)
        
        # Try to click on the group from search results
        try:
            group_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f'//span[@title="{group_name}"]'))
            )
            group_element.click()
            time.sleep(3)
        except:
            # Fallback: press enter in search box
            search_box.send_keys(Keys.ENTER)
            time.sleep(3)
            
        # Clear search to return to main view
        search_box.click()
        time.sleep(1)
        search_box.send_keys(Keys.CONTROL + 'a')
        time.sleep(0.5)
        search_box.send_keys(Keys.BACKSPACE)
        time.sleep(2)
            
    except Exception as e:
        log(f"❌ Failed to find group {group_name}: {e}")
        raise

def send_message(driver, message):
    log(f"✉️ Sending message: {message[:50]}{'...' if len(message)>50 else ''}")
    try:
        # Find the message input box
        message_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )
        
        # Click to focus
        message_box.click()
        time.sleep(1)
        
        # Clear any existing text
        message_box.send_keys(Keys.CONTROL + 'a')
        time.sleep(0.5)
        message_box.send_keys(Keys.BACKSPACE)
        time.sleep(0.5)
        
        # Type the message
        message_box.send_keys(message)
        time.sleep(1)
        
        # Send the message
        message_box.send_keys(Keys.ENTER)
        time.sleep(2)  # Shorter wait after send
        
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
    driver = None
    temp_profile = None
    
    try:
        # Force visible browser
        driver, temp_profile = groupReader.launch_driver(headless=False)
        
        # Wait for WhatsApp to load
        wait_for_whatsapp(driver)
        
        # Ask user to scan QR code if needed
        log("📱 Please scan the QR code if it appears, then press Enter to continue...")
        input()
        
        # Extra wait
        time.sleep(5)
        
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
                send_message(driver, morning_message)
                success_count += 1
                time.sleep(2)  # Pause between groups
                
            except Exception as e:
                log(f"❌ Failed to send message to group {group}: {e}")
                continue

        log(f"✅ Morning messages sent to {success_count}/{len(groups)} groups successfully!")

        log("✅ Task complete. Browser will stay open — close it manually when done.")
        input("Press Enter to close the browser...")

    except Exception as e:
        log(f"❌ Fatal error in send_morning_message: {e}")
    
    finally:
        if driver:
            driver.quit()
        groupReader.cleanup_chrome_processes()
        if temp_profile and os.path.exists(temp_profile):
            try:
                shutil.rmtree(temp_profile, ignore_errors=True)
            except:
                pass

# ------------------ Run ------------------
if __name__ == "__main__":
    send_morning_message()
