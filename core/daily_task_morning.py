import csv
import time
import os
import shutil
import uuid
import tempfile
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ------------------ Paths ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "group_convo.csv")


# ------------------ Logging ------------------
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")


# ------------------ Driver Helpers ------------------
def launch_driver():
    """Launch Chrome with a guaranteed unique profile each run."""
    log("🚀 Launching Chrome with fresh unique profile...")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Unique user data dir (prevents conflicts)
    temp_profile = os.path.join(tempfile.gettempdir(), f"whatsapp_profile_{uuid.uuid4().hex}")
    chrome_options.add_argument(f"--user-data-dir={temp_profile}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get("https://web.whatsapp.com")

    return driver, temp_profile


def cleanup_profile(profile_path):
    """Remove Chrome temp profile after run"""
    if profile_path and os.path.exists(profile_path):
        try:
            shutil.rmtree(profile_path, ignore_errors=True)
            log(f"🧹 Deleted temp profile: {profile_path}")
        except Exception as e:
            log(f"⚠️ Could not delete profile {profile_path}: {e}")


# ------------------ WhatsApp Helpers ------------------
def wait_for_whatsapp(driver):
    log("⌛ Waiting for WhatsApp Web to load (scan QR if needed)...")
    try:
        WebDriverWait(driver, 60).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']") or
                      d.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]")
        )
        log("✅ WhatsApp Web page loaded!")
    except Exception as e:
        log(f"❌ Failed to load WhatsApp: {e}")
        raise


def search_and_open_group(driver, group_name):
    try:
        log(f"🔍 Searching for group: {group_name}")

        # Find the search box
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

        # Click group from results
        group_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//span[@title="{group_name}"]'))
        )
        group_element.click()
        time.sleep(3)

        # Clear search again
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
        message_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )

        message_box.click()
        time.sleep(1)
        message_box.send_keys(Keys.CONTROL + 'a')
        time.sleep(0.5)
        message_box.send_keys(Keys.BACKSPACE)
        time.sleep(0.5)
        message_box.send_keys(message)
        time.sleep(1)
        message_box.send_keys(Keys.ENTER)
        time.sleep(3)

        log("✅ Message sent successfully")

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
        # Launch WhatsApp Web
        driver, temp_profile = launch_driver()
        wait_for_whatsapp(driver)

        log("📱 Please scan the QR code if prompted, then press Enter here...")
        input()

        time.sleep(5)  # Give time after QR scan

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
                time.sleep(3)
            except Exception as e:
                log(f"❌ Could not send to {group}: {e}")
                continue

        log(f"✅ Morning messages sent to {success_count}/{len(groups)} groups successfully!")

    except Exception as e:
        log(f"❌ Fatal error: {e}")

    finally:
        if driver:
            driver.quit()
        cleanup_profile(temp_profile)


# ------------------ Run ------------------
if __name__ == "__main__":
    send_morning_message()
