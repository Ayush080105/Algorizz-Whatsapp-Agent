import csv
import json
import time
import os
import platform
import tempfile
import subprocess
import random
import shutil
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

# --------------------- Logging ---------------------
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")

# --------------------- Cleanup Chrome Processes ---------------------
def cleanup_chrome_processes():
    """Kill all Chrome processes to ensure clean state"""
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/f", "/im", "chromedriver.exe"], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run("pkill -f chrome", shell=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run("pkill -f chromedriver", shell=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)  # Give time for processes to terminate
        log("✅ Chrome processes cleaned up")
    except Exception as e:
        log(f"⚠️ Cleanup warning: {e}")

# --------------------- Launch WhatsApp ---------------------
def launch_driver(retries=3, wait_time=5, headless=True):
    last_exception = None

    for attempt in range(1, retries + 1):
        try:
            log(f"[INFO] Launch attempt {attempt}...")
            
            # Clean up before each attempt
            cleanup_chrome_processes()
            
            options = webdriver.ChromeOptions()
            
            # Add random port to avoid conflicts
            options.add_argument(f"--remote-debugging-port={random.randint(9222, 9999)}")
            
            # Linux / EC2 safe flags
            if platform.system() != "Windows" and headless:
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--disable-software-rasterizer")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-background-networking")
            
            # Use unique temp profile for each attempt
            temp_profile = tempfile.mkdtemp(prefix=f"whatsapp_{attempt}_")
            options.add_argument(f"--user-data-dir={temp_profile}")
            
            # Additional stability options
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-web-security")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--no-first-run")
            
            # Set page load strategy to normal
            options.page_load_strategy = 'normal'
            
            # Initialize service with explicit path
            service = Service(ChromeDriverManager().install())
            
            # Set longer timeout for service
            service.start()
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(10)
            
            driver.get("https://web.whatsapp.com")
            log("[INFO] Chrome launched successfully!")
            return driver, temp_profile

        except Exception as e:
            last_exception = e
            log(f"[WARN] Launch attempt {attempt} failed: {e}")
            # Clean up temp directory if it was created
            if 'temp_profile' in locals():
                try:
                    shutil.rmtree(temp_profile, ignore_errors=True)
                except:
                    pass
            time.sleep(wait_time)

    raise Exception(f"🚨 Failed to launch Chrome after {retries} attempts. Last error: {last_exception}")

# --------------------- Wait for WhatsApp ---------------------
def wait_for_page_load(driver):
    log("Waiting for WhatsApp Web to load...")
    try:
        # Wait for either the QR code or the chat interface
        WebDriverWait(driver, 90).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']") or 
                     d.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]")
        )
        log("✅ WhatsApp Web loaded.")
    except Exception as e:
        log(f"❌ Page load failed: {e}")
        raise

# --------------------- Open Group ---------------------
def search_and_open_group(driver, group_name):
    log(f"🔍 Searching for group: {group_name}")
    try:
        driver.execute_script("window.scrollTo(0, 0);")
        search_box = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@role="textbox"][@contenteditable="true"][@data-tab="3"]'))
        )
        search_box.click()
        time.sleep(1)
        search_box.send_keys(Keys.CONTROL + 'a')
        time.sleep(0.5)
        search_box.send_keys(Keys.BACKSPACE)
        time.sleep(1)
        search_box.send_keys(group_name)
        time.sleep(3)
        
        # Try to click on the group from search results
        group_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//span[@title="{group_name}"]'))
        )
        group_element.click()
        time.sleep(3)
        
    except Exception as e:
        log(f"❌ Failed to find group {group_name}: {e}")
        # Fallback: press enter in search box
        try:
            search_box.send_keys(Keys.ENTER)
            time.sleep(3)
        except:
            raise

# --------------------- Read Today's Messages ---------------------
def read_todays_messages(driver, count=100):
    try:
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
                continue
        log(f"✅ Extracted {len(extracted)} messages")
        return extracted
    except Exception as e:
        log(f"❌ Error reading messages: {e}")
        return []

# --------------------- Update CSV ---------------------
def update_csv(csv_path):
    if not os.path.exists(csv_path):
        log(f"❌ CSV file not found: {csv_path}")
        return

    updated_rows = []
    log(f"📂 Loading CSV: {csv_path}")
    
    try:
        with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
        log(f"📊 Loaded {len(rows)} groups from CSV")
    except Exception as e:
        log(f"❌ Error reading CSV: {e}")
        return

    driver = None
    try:
        driver, temp_profile = launch_driver(headless=False)  # Set to False for debugging
        wait_for_page_load(driver)
        
        log("Please scan the QR code if needed, then press Enter to continue...")
        input()  # Wait for user to scan QR code

        for row in rows:
            group_name = row['groupName']
            log(f"\n📌 Fetching today's messages for group: {group_name}")

            todays_msgs = []
            try:
                search_and_open_group(driver, group_name)
                time.sleep(5)  # Wait longer for group to load
                todays_msgs = read_todays_messages(driver)
            except Exception as e:
                log(f"❌ Failed for group {group_name}: {e}")

            row['Conversation'] = json.dumps(todays_msgs, ensure_ascii=False)
            updated_rows.append(row)

    except Exception as e:
        log(f"❌ Fatal error: {e}")
    finally:
        if driver:
            driver.quit()
        cleanup_chrome_processes()

    # Write updated CSV
    try:
        log("💾 Writing updated CSV...")
        with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['groupName', 'Conversation']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        log("✅ CSV replaced with today's messages!")
    except Exception as e:
        log(f"❌ Error writing CSV: {e}")

# --------------------- Main Execution ---------------------
if __name__ == "__main__":
    try:
        update_csv(CSV_PATH)
    except Exception as e:
        log(f"❌ Script failed: {e}")
        cleanup_chrome_processes()