import csv
import json
import os
import time
import requests
import tempfile
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import groupReader
from dotenv import load_dotenv
from datetime import datetime

# ------------------ Load Environment ------------------
load_dotenv(override=True)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
HEADERS = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}

# ------------------ Logging ------------------
def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# ------------------ Read Admin Name ------------------
try:
    with open("admin.txt", "r", encoding="utf-8") as f:
        ADMIN_NAME = f.read().strip()
        if not ADMIN_NAME:
            raise ValueError("admin.txt is empty.")
except FileNotFoundError:
    log("❌ admin.txt not found. Please create the file and add the admin name.")
    exit(1)
except Exception as e:
    log(f"❌ Error reading admin.txt: {e}")
    exit(1)

# ------------------ WhatsApp Helpers ------------------
def search_and_open_chat(driver, contact_name):
    try:
        groupReader.search_and_open_group(driver, contact_name)
    except Exception as e:
        log(f"❌ Failed to open chat {contact_name}: {e}")

def send_message(driver, message):
    try:
        message_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )
        for line in message.split('\n'):
            message_box.send_keys(line)
            message_box.send_keys(Keys.SHIFT + Keys.ENTER)
        message_box.send_keys(Keys.ENTER)
        log("✅ Message sent.")
        time.sleep(2)
    except Exception as e:
        log(f"❌ Failed to send message: {e}")

# ------------------ Summarize & Send ------------------
def summarize_conversations_and_send(csv_path="group_convo.csv"):
    # Update CSV with today's messages
    log("📌 Updating CSV with today's messages...")
    groupReader.update_csv(csv_path)

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    log("🚀 Launching WhatsApp Web...")
    driver = groupReader.launch_driver()
    groupReader.wait_for_page_load(driver)

    for row in rows:
        group_name = row['groupName']
        try:
            chat = json.loads(row['Conversation']) if row['Conversation'].strip() else []
        except json.JSONDecodeError:
            log(f"⚠️ Invalid JSON for group {group_name}, skipping.")
            continue

        if not chat:
            log(f"ℹ️ No messages in {group_name}, skipping summary.")
            continue

        convo_text = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in chat])
        prompt_template = f"""
You are an executive assistant AI summarizing a WhatsApp group conversation for the admin.

Read the conversation from the group "{group_name}" and summarize it into short, actionable bullet points.

Your summary must include exactly three sections:
1. Key things done → Brief bullet points on completed work or progress updates.
2. Outstanding tasks & owners → Tasks that are pending, with the name of the person responsible.
3. Bottlenecks & actions you need to take → Current challenges/blockers and the specific actions you should take.

Keep it concise, factual, and easy to read. Do not add extra commentary or headings beyond these three sections.
Do not use bold or numbered points — keep it simple.

Here is the group conversation:

{convo_text}

Now write the summary.
"""
        payload = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt_template}
            ],
            "temperature": 0.7
        }

        try:
            response = requests.post(AZURE_OPENAI_ENDPOINT, headers=HEADERS, json=payload, timeout=30)
            response.raise_for_status()
            summary = response.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            log(f"❌ Failed to generate summary for {group_name}: {e}")
            continue

        log(f"\nSummary for group {group_name}:\n{'-'*50}\n{summary}")
        search_and_open_chat(driver, ADMIN_NAME)
        send_message(driver, f"*Update from group: {group_name}*\n\n{summary}")

    driver.quit()
    log("✅ Finished sending all group summaries.")

# ------------------ Run ------------------
if __name__ == "__main__":
    summarize_conversations_and_send()
