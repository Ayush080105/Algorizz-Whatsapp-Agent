import csv
import json
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import functions from group_reader.py
import groupReader


# --------------------- Azure OpenAI Config ---------------------
AZURE_OPENAI_ENDPOINT = "https://qrizz-us.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2025-01-01-preview"
AZURE_API_KEY = "b46942d9305c42d78df6078a465419ae"
HEADERS = {
    "Content-Type": "application/json",
    "api-key": AZURE_API_KEY
}


# --------------------- Use Azure LLM to Generate Evening Messages ---------------------
# --------------------- Use Azure LLM to Generate Evening Messages ---------------------
def generate_evening_updates_llm(conversation, group_name):
    if not conversation:
        return []

    # Load admin name from admin.txt
    try:
        with open("admin.txt", "r", encoding="utf-8") as f:
            admin_name = f.read().strip()
    except FileNotFoundError:
        admin_name = ""  # fallback if file missing

    convo_text = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in conversation])

    prompt = f"""
You are a polite assistant preparing evening follow-up messages in a WhatsApp group called '{group_name}'.

Here is today's group conversation:
{convo_text}

Rules:
- Identify what each non-admin person planned to do in the morning.
- Write a short, polite evening follow-up asking them for an update on their specific tasks.
- DO NOT generate a follow-up for the admin user: "{admin_name}".
- Keep it conversational and natural, as if written by a human group member.
- Format strictly as:
<name>: <evening message>
- Do not include commentary, explanations, or extra text outside the follow-up messages.
"""

    body = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that generates natural WhatsApp group follow-ups."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        response = requests.post(AZURE_OPENAI_ENDPOINT, headers=HEADERS, json=body)
        response.raise_for_status()
        data = response.json()

        raw_reply = data["choices"][0]["message"]["content"].strip()
        evening_msgs = [line for line in raw_reply.split("\n") if line.strip()]
        return evening_msgs

    except Exception as e:
        print(f"❌ LLM generation failed: {e}")
        return []


# --------------------- Send Evening Message ---------------------
def send_evening_message(driver, group_name, messages):
    try:
        groupReader.search_and_open_group(driver, group_name)
        time.sleep(2)

        for msg in messages:
            # Locate message input box (footer input, not search)
            input_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@role="textbox"][@contenteditable="true"][@data-tab="10"]')
                )
            )

            # Clear any drafts
            input_box.click()
            input_box.send_keys(Keys.CONTROL, 'a')
            input_box.send_keys(Keys.BACKSPACE)
            time.sleep(0.3)

            # Type and send the message
            input_box.send_keys(msg)
            time.sleep(0.5)
            input_box.send_keys(Keys.ENTER)
            time.sleep(1)

        print(f"✅ Evening messages sent to group: {group_name}")

    except Exception as e:
        print(f"❌ Failed to send evening message to {group_name}: {e}")



# --------------------- Main ---------------------
def main(csv_path="group_convo.csv"):
    # Step 1: Refresh today's conversations
    groupReader.update_csv(csv_path)

    # Step 2: Load updated CSV
    with open(csv_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    driver = groupReader.launch_driver()
    groupReader.wait_for_page_load(driver)

    # Step 3: For each group, create evening follow-up using LLM
    for row in rows:
        group_name = row["groupName"]

        try:
            conversation = json.loads(row["Conversation"]) if row["Conversation"].strip() else []
        except json.JSONDecodeError:
            conversation = []

        evening_msgs = generate_evening_updates_llm(conversation, group_name)

        if not evening_msgs:
            print(f"⚠️ No evening updates generated for group: {group_name}")
            continue

        send_evening_message(driver, group_name, evening_msgs)

    driver.quit()


if __name__ == "__main__":
    main()
