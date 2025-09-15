import csv
import json
import time
import os
import platform
import shutil
import tempfile
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

# --------------------- Launch WhatsApp ---------------------
def launch_driver(retries=3, wait_time=5):
    last_exception = None

    for attempt in range(1, retries + 1):
        try:
            options = webdriver.ChromeOptions()

            # Use a unique temporary profile folder per session (avoids profile-in-use errors)
            profile_dir = tempfile.mkdtemp(prefix="whatsapp_profile_")
            options.add_argument(f"user-data-dir={profile_dir}")

            # Linux-safe headless flags
            if platform.system() != "Windows":
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--remote-debugging-port=9222")
                options.add_argument("--disable-software-rasterizer")

            # Auto-detect Chrome/Chromium binary
            chrome_path = shutil.which("google-chrome") or shutil.which("chromium-browser") or shutil.which("chromium")
            if chrome_path:
                options.binary_location = chrome_path
            elif platform.system() == "Windows":
                options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            else:
                raise Exception("No Chrome/Chromium binary found. Install it on this machine.")

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.get("https://web.whatsapp.com")
            return driver

        except Exception as e:
            last_exception = e
            print(f"⚠️ Launch attempt {attempt} failed: {e}")
            time.sleep(wait_time)

    raise Exception(f"Failed to launch Chrome after {retries} attempts. Last error: {last_exception}")

# --------------------- Wait for WhatsApp ---------------------
def wait_for_page_load(driver):
    print("Waiting for WhatsApp Web to load...")
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )
    print("✅ WhatsApp Web loaded.")

# --------------------- Open Group ---------------------
def search_and_open_group(driver, group_name):
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
        except:
            continue
    return extracted

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

        row['Conversation'] = json.dumps(todays_msgs, ensure_ascii=False)
        updated_rows.append(row)

    driver.quit()

    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = ['groupName', 'Conversation']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print("\n✅ CSV replaced with only today's messages!")
