import csv
import json
import os
import sys
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv(override=True)

# ------------------ Config ------------------
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
HEADERS = {
    "Content-Type": "application/json",
    "api-key": AZURE_API_KEY
}
BASE_PATH = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
PROFILE_PATH = os.path.join(BASE_PATH, "WhatsAppProfile")
CSV_PATH = os.path.join(BASE_PATH, "group_convo.csv")

# ------------------ Resource Path Helper ------------------
def resource_path(relative_path):
    base_path = os.path.join(os.environ.get("USERPROFILE", os.getcwd()), "WhatsAppProfileApp")
    os.makedirs(base_path, exist_ok=True)
    return os.path.join(base_path, relative_path)

# ------------------ Read Admin Name ------------------
ADMIN_FILE = os.path.join(BASE_PATH, "admin.txt")

try:
    with open(ADMIN_FILE, "r", encoding="utf-8") as f:
        ADMIN_NAME = f.read().strip()
        if not ADMIN_NAME:
            raise ValueError("admin.txt is empty.")
except FileNotFoundError:
    print("❌ admin.txt not found. Please create the file and add the admin name.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error reading admin.txt: {e}")
    sys.exit(1)

# ------------------ Selenium Setup ------------------
def launch_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={PROFILE_PATH}")
    driver = webdriver.Chrome(options=options)
    driver.get("https://web.whatsapp.com")
    return driver

def wait_for_whatsapp(driver):
    print("Waiting for WhatsApp Web to load...")
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
    )
    print("✅ WhatsApp loaded.")

# ------------------ Chat Helpers ------------------
def search_and_open_chat(driver, contact_name):
    # Wait for search box to be clickable
    search_box = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
    )
    search_box.click()
    time.sleep(0.5)
    
    # Clear existing text
    search_box.send_keys(Keys.CONTROL + "a")
    search_box.send_keys(Keys.BACKSPACE)
    time.sleep(0.3)
    
    # Type contact/admin name and open chat
    search_box.send_keys(contact_name)
    time.sleep(2)
    search_box.send_keys(Keys.ENTER)
    time.sleep(2)

def send_message(driver, message):
    message_box = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
    )
    message_box.click()
    time.sleep(0.3)
    
    # Type message line by line
    for line in message.split('\n'):
        message_box.send_keys(line)
        message_box.send_keys(Keys.SHIFT + Keys.ENTER)
    message_box.send_keys(Keys.ENTER)
    print("✅ Message sent.")
    time.sleep(2)

# ------------------ Summarize & Send ------------------
def summarize_conversations_and_send():
    driver = launch_driver()
    wait_for_whatsapp(driver)

    csv_file = CSV_PATH
    if not os.path.exists(csv_file):
        print("⚠️ group_convo.csv not found. Exiting.")
        driver.quit()
        return

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_name = row['groupName']
            chat = row['Conversation']

            prompt_template = f"""
You are an executive assistant AI summarizing a WhatsApp group conversation for the admin.

Read the conversation from the group "{group_name}" and summarize it into short, actionable bullet points.

Your summary must include exactly three sections:
1. Key things done → Brief bullet points on completed work or progress updates.
2. Outstanding tasks & owners → Tasks that are pending, with the name of the person responsible.
3. Bottlenecks & actions you need to take → Current challenges/blockers and the specific actions you should take.

Keep it concise, factual, and easy to read. Do not add extra commentary or headings beyond these three sections. Don't use bold points and don't add numeric bullet points keep it simple.

Here is the group conversation:

{chat}

Now write the summary.
"""

            payload = {
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt_template}
                ],
                "temperature": 0.7
            }

            response = requests.post(AZURE_OPENAI_ENDPOINT, headers=HEADERS, json=payload)

            if response.status_code == 200:
                summary = response.json()['choices'][0]['message']['content']
                print(f"\nSummary for group: {group_name}\n{'-'*50}")
                print(summary)

                # Send summary to admin
                search_and_open_chat(driver, ADMIN_NAME)
                send_message(driver, f"*Update from group: {group_name}*\n\n{summary}")
            else:
                print(f"\n❌ Failed to summarize {group_name}. Status code: {response.status_code}")
                print(response.text)

    driver.quit()
