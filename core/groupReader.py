import csv
import json
import time
import os
import platform
import shutil
import tempfile
import subprocess
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --------------------- Paths ---------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "group_convo.csv")

# --------------------- Logging helper ---------------------
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")

# --------------------- Launch WhatsApp ---------------------
def launch_driver(retries=3, wait_time=5):
    last_exception = None

    for attempt in range(1, retries + 1):
        try:
            print(f"[INFO] Launch attempt {attempt}...")

            # Kill any leftover Chrome processes
            subprocess.run("pkill -f chrome", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            options = webdriver.ChromeOptions()

            # Headless & Linux flags
            if platform.system() != "Windows":
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--remote-debugging-port=9222")

            # Always use unique temp profile
            temp_profile = tempfile.mkdtemp(prefix="whatsapp_")
            options.add_argument(f"--user-data-dir={temp_profile}")

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get("https://web.whatsapp.com")
            print("[INFO] Chrome launched successfully!")
            return driver

        except Exception as e:
            last_exception = e
            print(f"[WARN] Launch attempt {attempt} failed: {e}")
            time.sleep(wait_time)

    raise Exception(f"🚨 Failed to launch Chrome after {retries} attempts. Last error: {last_exception}")

# --------------------- Wait for WhatsApp ---------------------
def wait_for_page_load(driver):
    log("Waiting for WhatsApp Web to load...")
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )
    log("✅ WhatsApp Web loaded.")

# --------------------- Open Group ---------------------
def search_and_open_group(driver, group_name):
    log(f"🔍 Searching for group: {group_name}")
    driver.execute_script("window.scrollTo(0, 0);")
    search_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//div[@role="textbox"][@contenteditable="true"][@data-tab="3"]'))
    )
    search_box.click()
    time.sleep(0.5)
    search_box.send_keys(Keys.CONTROL, 'a', Keys.BACKSPACE)
    time.sleep(0.5)
    search_box.send_keys(group_name)
    time.sleep(2)
    search_box.send_keys(Keys.ENTER)
    time.sleep(2)

# --------------------- Read Today's Messages ---------------------
def read_todays_messages(driver, count=100):
    messages = driver.find_elements(By.XPATH, '//div[contains(@class,"message-in") or contains(@class,"message-out")]')[-count:]
    extracted = []

    today = datetime.now().strftime("%#m/%#d/%Y") if platform.system() == "Windows" else datetime.now().strftime("%-m/%-d/%Y")
    log(f"Reading messages for today: {today}")

    for msg in messages:
        try:
            sender_elem = msg.find_element(By.XPATH, './/div[@data-pre-plain-text]')
            sender_text = sender_elem.get_attribute("data-pre-plain-text")
            if today not in sender_text:
                continue
            sender = sender_text.split("] ")[-1].strip().rstrip(":")
            message_elem = msg.find_element(By.XPATH, './/span[contains(@class,"selectable-text")]')
            message = message_elem.text.strip()
            if message:
                extracted.append({"sender": sender, "message": message})
        except Exception as e:
            log(f"⚠️ Skipping a message due to error: {e}")
            continue
    log(f"✅ Extracted {len(extracted)} messages")
    return extracted

# --------------------- Update CSV ---------------------
def update_csv(csv_path):
    updated_rows = []

    log(f"📂 Loading CSV: {csv_path}")
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    log(f"📊 Loaded {len(rows)} groups from CSV")

    driver = launch_driver()
    wait_for_page_load(driver)

    for row in rows:
        group_name = row['groupName']
        log(f"\n📌 Fetching today's messages for group: {group_name}")

        todays_msgs = []
        try:
            search_and_open_group(driver, group_name)
            time.sleep(2)
            todays_msgs = read_todays_messages(driver)
        except Exception as e:
            log(f"❌ Failed for group {group_name}: {e}")

        row['Conversation'] = json.dumps(todays_msgs, ensure_ascii=False)
        updated_rows.append(row)

    driver.quit()
    log("💾 Writing updated CSV...")

    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ['groupName', 'Conversation']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    log("✅ CSV replaced with today's messages!")
