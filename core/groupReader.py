import os
import sys
import time
import csv
import json
import platform
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------- Paths ---------------------
BASE_PATH = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
PROFILE_PATH = os.path.join(BASE_PATH, "WhatsAppProfile")
CSV_PATH = os.path.join(BASE_PATH, "group_convo.csv")
os.makedirs(PROFILE_PATH, exist_ok=True)

# --------------------- Launch WhatsApp ---------------------
def launch_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={PROFILE_PATH}")  # persistent profile
    driver = webdriver.Chrome(options=options)
    driver.get("https://web.whatsapp.com")
    return driver

def wait_for_page_load(driver, timeout=60):
    print("Waiting for WhatsApp Web to load...")
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )
    print("✅ WhatsApp Web loaded.")

# --------------------- Open Group ---------------------
def search_and_open_group(driver, group_name):
    time.sleep(1)
    driver.execute_script("window.scrollTo(0, 0);")
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

    if platform.system() == "Windows":
        today = datetime.now().strftime("%#m/%#d/%Y")
    else:
        today = datetime.now().strftime("%-m/%-d/%Y")

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

# --------------------- Send Message ---------------------
def send_message(driver, group_name, messages):
    search_and_open_group(driver, group_name)
    input_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
    )
    input_box.click()
    for msg in messages:
        for line in msg.split('\n'):
            input_box.send_keys(line)
            input_box.send_keys(Keys.SHIFT + Keys.ENTER)
        input_box.send_keys(Keys.ENTER)
        time.sleep(1)
    print(f"✅ Message sent to {group_name}")

# --------------------- Update CSV ---------------------
def update_csv():
    updated_rows = []

    # Ensure CSV exists
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["groupName", "Conversation"])
            writer.writeheader()
        return

    # Read existing groups
    with open(CSV_PATH, mode='r', newline='', encoding='utf-8') as file:
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

    # Replace CSV completely
    with open(CSV_PATH, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['groupName', 'Conversation'])
        writer.writeheader()
        writer.writerows(updated_rows)

    print("\n✅ CSV replaced with only today's messages!")