import csv
import json
import time
import os
import platform
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --------------------- Launch WhatsApp ---------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # current project dir
PROFILE_PATH = os.path.join(BASE_DIR, "whatsapp_profile")
os.makedirs(PROFILE_PATH, exist_ok=True)  # ensure folder exists

# --------------------- Launch WhatsApp ---------------------
import os
import platform
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# WhatsApp profile folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(BASE_DIR, "whatsapp_profile")
os.makedirs(PROFILE_PATH, exist_ok=True)

def launch_driver():
    options = webdriver.ChromeOptions()

    # Use project-local profile
    options.add_argument(f"user-data-dir={PROFILE_PATH}")

    # Headless + Linux-safe flags (only on Linux)
    if platform.system() != "Windows":
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")

    # Auto-detect Chrome/Chromium binary
    chrome_path = shutil.which("google-chrome") or shutil.which("chromium-browser") or shutil.which("chromium")
    if chrome_path:
        options.binary_location = chrome_path
    elif platform.system() == "Windows":
        # Optional: default Windows Chrome path
        options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    else:
        raise Exception("No Chrome/Chromium binary found. Please install it on this machine.")

    # Use webdriver-manager for ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://web.whatsapp.com")
    return driver


def wait_for_page_load(driver):
    print("Waiting for WhatsApp Web to load...")
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )
    print("✅ WhatsApp Web loaded.")

# --------------------- Open Group ---------------------
def search_and_open_group(driver, group_name):
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, 0);")

    # Search bar (not footer input)
    search_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//div[@role="textbox"][@contenteditable="true"][@data-tab="3"]'))
    )
    search_box.click()
    time.sleep(0.5)

    search_box.send_keys(Keys.CONTROL, 'a')
    search_box.send_keys(Keys.BACKSPACE)
    time.sleep(0.5)

    search_box.send_keys(group_name)
    time.sleep(2)
    search_box.send_keys(Keys.ENTER)
    time.sleep(2)

# --------------------- Read Today's Messages ---------------------
def read_todays_messages(driver, count=100):
    messages = driver.find_elements(By.XPATH, '//div[contains(@class,"message-in") or contains(@class,"message-out")]')
    messages = messages[-count:]

    extracted = []

    # Detect platform-specific date format
    if platform.system() == "Windows":
        today = datetime.now().strftime("%#m/%#d/%Y")
    else:
        today = datetime.now().strftime("%-m/%-d/%Y")

    for msg in messages:
        try:
            # Sender info
            sender_elem = msg.find_element(By.XPATH, './/div[@data-pre-plain-text]')
            sender_text = sender_elem.get_attribute("data-pre-plain-text")

            # Extract date from prefix like: [12:34, 9/5/2025]
            if today not in sender_text:
                continue  # skip old messages

            sender = sender_text.split("] ")[-1].strip().rstrip(":")
            message_elem = msg.find_element(By.XPATH, './/span[contains(@class,"selectable-text")]')
            message = message_elem.text.strip()

            if message:
                extracted.append({"sender": sender, "message": message})

        except:
            continue

    return extracted

# --------------------- Update CSV ---------------------
# --------------------- Update CSV ---------------------
def update_csv(csv_path):
    updated_rows = []

    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    driver = launch_driver()
    wait_for_page_load(driver)

    for row in rows:
        group_name = row['groupName']
        print(f"\n📌 Fetching TODAY's messages from group: {group_name}")

        todays_msgs = []
        try:
            search_and_open_group(driver, group_name)
            time.sleep(2)

            todays_msgs = read_todays_messages(driver)

        except Exception as e:
            print(f"❌ Failed for group {group_name}: {e}")

        # ✅ Always overwrite conversation (even if empty)
        row['Conversation'] = json.dumps(todays_msgs, ensure_ascii=False)
        updated_rows.append(row)

    driver.quit()

    # ✅ Rewrite CSV completely (no append)
    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ['groupName', 'Conversation']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print("\n✅ CSV replaced with only today's messages!")

