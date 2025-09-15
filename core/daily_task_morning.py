import csv
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import your existing driver loader
from groupReader import launch_driver  # <- use this instead of redefining

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
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )
    log("✅ WhatsApp Web loaded.")

def search_and_open_group(driver, group_name):
    log(f"🔍 Searching for group: {group_name}")
    driver.execute_script("window.scrollTo(0, 0);")
    search_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )
    search_box.click()
    time.sleep(0.5)
    search_box.send_keys(Keys.CONTROL + "a")
    search_box.send_keys(Keys.BACKSPACE)
    time.sleep(0.5)
    search_box.send_keys(group_name)
    time.sleep(2)
    search_box.send_keys(Keys.ENTER)
    time.sleep(2)

def send_message(driver, message):
    log(f"✉️ Sending message: {message[:50]}{'...' if len(message)>50 else ''}")
    message_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
    )
    message_box.click()
    message_box.send_keys(message)
    message_box.send_keys(Keys.ENTER)
    time.sleep(1)

# ------------------ Main Task ------------------
def send_morning_message():
    driver = launch_driver()  # <-- reuse from groupReader.py
    wait_for_whatsapp(driver)

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        groups = [row['groupName'] for row in reader]

    morning_message = "Good morning team! Please reply with what you plan to do today for your tasks."

    for group in groups:
        try:
            search_and_open_group(driver, group)
            send_message(driver, morning_message)
        except Exception as e:
            log(f"❌ Failed to send message to group {group}: {e}")

    driver.quit()
    log("✅ Morning messages sent to all groups!")

if __name__ == "__main__":
    send_morning_message()
