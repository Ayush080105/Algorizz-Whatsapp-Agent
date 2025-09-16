import csv, json, time, requests, os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import groupReader
from dotenv import load_dotenv

# ------------------ Paths ------------------
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_PATH, "group_convo.csv")
ADMIN_FILE = os.path.join(BASE_PATH, "admin.txt")

# ------------------ Env ------------------
load_dotenv(override=True)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_API_KEY")
HEADERS = {"Content-Type": "application/json", "api-key": AZURE_API_KEY}


# --------------------- Use Azure LLM ---------------------
def generate_evening_updates_llm(conversation, group_name):
    if not conversation:
        return []

    try:
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
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
        response = requests.post(AZURE_OPENAI_ENDPOINT, headers=HEADERS, json=body)
        response.raise_for_status()
        raw_reply = response.json()["choices"][0]["message"]["content"].strip()
        return [line for line in raw_reply.split("\n") if line.strip()]
    except Exception as e:
        print(f"❌ LLM generation failed: {e}")
        return []


# --------------------- Send Evening Message ---------------------
def send_evening_message(driver, group_name, messages):
    try:
        # Open the group
        groupReader.search_and_open_group(driver, group_name)
        
        # Wait until input box is clickable (safer than presence)
        input_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )
        input_box.click()
        
        # Send all messages
        for msg in messages:
            for line in msg.split('\n'):
                input_box.send_keys(line)
                input_box.send_keys(Keys.SHIFT + Keys.ENTER)
            input_box.send_keys(Keys.ENTER)
            time.sleep(1)  # optional, avoid flooding
        
        print(f"✅ Evening messages sent to {group_name}")
    except Exception as e:
        print(f"❌ Failed to send evening message to {group_name}: {e}")




# --------------------- Main Wrapper ---------------------
def send_evening_messages(csv_path=CSV_PATH):
    groupReader.update_csv()

    if not os.path.exists(csv_path):
        print("⚠️ No group_convo.csv found, skipping evening messages.")
        return

    with open(csv_path, mode="r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    driver = groupReader.launch_driver()
    groupReader.wait_for_page_load(driver)

    for row in rows:
        group_name = row["groupName"]
        try:
            conversation = json.loads(row["Conversation"]) if row["Conversation"].strip() else []
        except json.JSONDecodeError:
            conversation = []

        evening_msgs = generate_evening_updates_llm(conversation, group_name)
        if evening_msgs:
            send_evening_message(driver, group_name, evening_msgs)

    driver.quit()
