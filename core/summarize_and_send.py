import csv
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------ Config ------------------
AZURE_OPENAI_ENDPOINT = "https://qrizz-us.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2025-01-01-preview"
AZURE_API_KEY = "b46942d9305c42d78df6078a465419ae"
HEADERS = {
    "Content-Type": "application/json",
    "api-key": AZURE_API_KEY
}
PROFILE_PATH = "C:/Temp/WhatsAppProfile"

# ------------------ Read Admin Name ------------------
try:
    with open("admin.txt", "r", encoding="utf-8") as f:
        ADMIN_NAME = f.read().strip()
        if not ADMIN_NAME:
            raise ValueError("admin.txt is empty.")
except FileNotFoundError:
    print("❌ admin.txt not found. Please create the file and add the admin name.")
    exit(1)
except Exception as e:
    print(f"❌ Error reading admin.txt: {e}")
    exit(1)

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
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )
    print("✅ WhatsApp loaded.")

def clear_search_box(driver):
    search_box = driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]")
    search_box.click()
    search_box.send_keys(Keys.CONTROL + "a")
    search_box.send_keys(Keys.BACKSPACE)
    time.sleep(1)

def search_and_open_chat(driver, contact_name):
    clear_search_box(driver)
    search_box = driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]")
    search_box.send_keys(contact_name)
    time.sleep(2)
    search_box.send_keys(Keys.ENTER)
    time.sleep(2)

def send_message(driver, message):
    message_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
    )
    for line in message.split('\n'):
        message_box.send_keys(line)
        message_box.send_keys(Keys.SHIFT + Keys.ENTER)
    message_box.send_keys(Keys.ENTER)
    print("✅ Message sent.")
    time.sleep(5)

# ------------------ Summarize & Send ------------------
def summarize_conversations_and_send():
    driver = launch_driver()
    wait_for_whatsapp(driver)

    with open("group_convo.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            group_name = row['groupName']
            chat = row['Conversation']

            prompt_template = f"""
You are an executive assistant AI summarizing a WhatsApp group conversation for the admin.

Read the conversation from the group "{group_name}" and summarize it into short, actionable bullet points.

Your summary must include exactly three sections:
1. **Key things done** → Brief bullet points on completed work or progress updates.
2. **Outstanding tasks & owners** → Tasks that are pending, with the name of the person responsible.
3. **Bottlenecks & actions you need to take** → Current challenges/blockers and the specific actions you should take.

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
                search_and_open_chat(driver, ADMIN_NAME)
                send_message(driver, f"*Update from group: {group_name}*\n\n{summary}")
            else:
                print(f"\n❌ Failed to summarize {group_name}. Status code: {response.status_code}")
                print(response.text)

    driver.quit()

# ------------------ Run ------------------
if __name__ == "__main__":
    summarize_conversations_and_send()
