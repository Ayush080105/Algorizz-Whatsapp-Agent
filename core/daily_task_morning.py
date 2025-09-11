import time, csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROFILE_PATH = "C:/Temp/WhatsAppProfile"

# ------------------ WhatsApp Helpers ------------------
def launch_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={PROFILE_PATH}")
    driver = webdriver.Chrome(options=options)
    driver.get("https://web.whatsapp.com")
    return driver

def wait_for_whatsapp(driver):
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )

def search_and_open_group(driver, group_name):
    search_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
    )
    search_box.click()
    time.sleep(0.5)
    search_box.send_keys(Keys.CONTROL + "a")
    search_box.send_keys(Keys.BACKSPACE)
    time.sleep(0.5)
    search_box.send_keys(group_name)
    time.sleep(2)
    search_box.send_keys(Keys.ENTER)
    time.sleep(2)

def send_message(driver, message):
    message_box = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
    )
    message_box.click()
    message_box.send_keys(message)
    message_box.send_keys(Keys.ENTER)
    time.sleep(1)

# ------------------ Main ------------------
if __name__ == "__main__":
    driver = launch_driver()
    wait_for_whatsapp(driver)

    # Load groups from CSV
    with open("group_convo.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        groups = [row['groupName'] for row in reader]

    morning_message = "Good morning team! Please reply with what you plan to do today for your tasks."

    for group in groups:
        search_and_open_group(driver, group)
        send_message(driver, morning_message)

    driver.quit()
