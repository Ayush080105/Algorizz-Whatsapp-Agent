import csv
import json
import time
import os
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import groupReader
from dotenv import load_dotenv

# --------------------- Load Environment ---------------------
load_dotenv(override=True)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
HEADERS = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}

# --------------------- Logging ---------------------
from datetime import datetime
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")

# --------------------- Use Azure LLM ---------------------
def generate_evening_updates_llm(conversation, group_name):
    if not conversation:
        return []

    try:
        with open("admin.txt", "r", encoding="utf-8") as f:
            admin_name = f.read().strip()
    except FileNotFoundError:
        admin_name = ""

    convo_text = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in conversation])

    prompt = f"""
You are a polite assistant preparing evening follow-up messages in a WhatsApp group called '{group_name}'.

Here is today's group conversation:
{convo_text}

Rules:
- Identify what each non-admin person planned to do in the morning.
- Write a short, polite evening follow-up asking them for an update.
- Skip admin "{admin_name}".
- Format: <name>: <evening message>
"""

    body = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        response = requests.post(AZURE_OPENAI_ENDPOINT, headers=HEADERS, json=body, timeout=30)
        response.raise_for_status()
        raw_reply = response.json()["choices"][0]["message"]["content"].strip()
        return [line for line in raw_reply.split("\n") if line.strip()]
    except Exception as e:
        log(f"❌ LLM generation failed for group {group_name}: {e}")
        return []

# --------------------- Send Evening Messages ---------------------
def send_evening_message(driver, group_name, messages):
    try:
        groupReader.search_and_open_group(driver, group_name)
        time.sleep(2)

        for msg in messages:
            input_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@role="textbox"][@contenteditable="true"][@data-tab="10"]')
                )
            )
            input_box.click()
            input_box.send_keys(msg)
            input_box.send_keys(Keys.ENTER)
            time.sleep(1)

        log(f"✅ Evening messages sent to {group_name}")
    except Exception as e:
        log(f"❌ Failed to send evening messages to {group_name}: {e}")

# --------------------- Main Wrapper ---------------------
def send_evening_messages(csv_path="group_convo.csv"):
    log("📌 Updating CSV with today's messages...")
    groupReader.update_csv(csv_path)

    with open(csv_path, mode="r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    log("🚀 Launching WhatsApp Web with temporary profile...")
    # Use temporary profile to avoid session conflicts
    driver = groupReader.launch_driver(use_temp_profile=True)
    groupReader.wait_for_page_load(driver)

    for row in rows:
        group_name = row["groupName"]
        try:
            conversation = json.loads(row["Conversation"]) if row["Conversation"].strip() else []
        except json.JSONDecodeError:
            log(f"❌ JSON decode failed for group {group_name}, skipping conversation.")
            conversation = []

        evening_msgs = generate_evening_updates_llm(conversation, group_name)
        if evening_msgs:
            send_evening_message(driver, group_name, evening_msgs)
        else:
            log(f"ℹ️ No evening messages generated for {group_name}")

    driver.quit()
    log("✅ Finished sending evening messages to all groups.")

# --------------------- Run ---------------------
if __name__ == "__main__":
    send_evening_messages()
