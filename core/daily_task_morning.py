import csv
import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import tempfile

# ------------------ Paths ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "group_convo.csv")

# ------------------ Logging ------------------
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")

# ------------------ Driver Loader ------------------
def launch_driver():
    """Always launch Chrome visibly with a fresh temp profile (QR needed each run)."""
    log("🚀 Launching Chrome (fresh profile, visible mode)")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # create a unique temp profile directory every run
    temp_profile = tempfile.mkdtemp(prefix="whatsapp_profile_")
    chrome_options.add_argument(f"--user-data-dir={temp_profile}")

    service = Service()  # assumes chromedriver is in PATH
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://web.whatsapp.com")

    return driver, temp_profile

# ------------------ WhatsApp Helpers ------------------
def wait_for_whatsapp(driver):
    log("Waiting for WhatsApp Web to load...")
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
    )
    log("✅ WhatsApp Web loaded")

def search_and_open_group(driver, group_name):
    try:
        log(f"🔍 Searching for group: {group_name}")
        search_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        search_box.click()
        time.sleep(1)
        search_box.send_keys(Keys.CONTROL + 'a')
        search_box.send_keys(Keys.BACKSPACE)
        search_box.send_keys(group_name)
        time.sleep(3)

        group_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//span[@title="{group_name}"]'))
        )
        group_element.click()
        time.sleep(2)
    except Exception as e:
        log(f"❌ Failed to find group {group_name}: {e}")
        raise

def send_message(driver, message):
    log(f"✉️ Sending message: {message[:50]}{'...' if len(message)>50 else ''}")
    try:
        message_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )
        message_box.click()
        time.sleep(1)
        message_box.send_keys(message)
        time.sleep(1)
        message_box.send_keys(Keys.ENTER)
        log("✅ Message sent successfully")
        time.sleep(2)
    except Exception as e:
        log(f"❌ Failed to send message: {e}")
        raise

# ------------------ Main Task ------------------
def send_morning_message(csv_path=CSV_PATH):
    if not os.path.exists(csv_path):
        log(f"❌ CSV file not found: {csv_path}")
        return

    driver, temp_profile = None, None
    try:
        driver, temp_profile = launch_driver()

        # Wait for QR login
        log("👉 Please scan the QR code in the opened browser. Press Enter here once logged in.")
        input()
        wait_for_whatsapp(driver)

        # Load groups
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            groups = [row['groupName'] for row in reader]

        morning_message = "Good morning team! Please reply with what you plan to do today for your tasks."
        log(f"📤 Sending message to {len(groups)} groups")

        success_count = 0
        for group in groups:
            try:
                search_and_open_group(driver, group)
                send_message(driver, morning_message)
                success_count += 1
            except Exception:
                continue

        log(f"✅ Morning messages sent to {success_count}/{len(groups)} groups successfully!")

        log("⏸️ Browser will stay open for debugging. Press Enter to close it...")
        input()

    finally:
        if driver:
            driver.quit()
        if temp_profile and os.path.exists(temp_profile):
            shutil.rmtree(temp_profile, ignore_errors=True)

# ------------------ Run ------------------
if __name__ == "__main__":
    send_morning_message()
