import csv
import json
import time
import os
import platform
import tempfile
import subprocess
import random
import shutil
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# --------------------- Paths ---------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "group_convo.csv")

# --------------------- Logging ---------------------
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")

# --------------------- Display Detection ---------------------
def has_display():
    """Check if the system has a display available"""
    try:
        if platform.system() == "Linux":
            return os.environ.get('DISPLAY') is not None or os.environ.get('WAYLAND_DISPLAY') is not None
        elif platform.system() == "Darwin":  # macOS
            return True
        elif platform.system() == "Windows":
            return True
        return False
    except:
        return False

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
        time.sleep(2)
        log("✅ Chrome processes cleaned up")
    except Exception as e:
        log(f"⚠️ Cleanup warning: {e}")

# --------------------- Launch WhatsApp ---------------------
def launch_driver(retries=3, wait_time=5):
    last_exception = None
    has_display_env = has_display()

    for attempt in range(1, retries + 1):
        try:
            log(f"[INFO] Launch attempt {attempt}...")
            log(f"[INFO] Display available: {has_display_env}")
            
            cleanup_chrome_processes()
            
            options = Options()
            options.add_argument(f"--remote-debugging-port={random.randint(9222, 9999)}")
            
            if not has_display_env:
                log("[INFO] Running in headless mode")
                options.add_argument("--headless=new")
            else:
                log("[INFO] Running with visible browser")
                options.add_argument("--window-size=1200,800")
                options.add_argument("--start-maximized")
            
            # Common options
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-background-networking")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-web-security")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--no-first-run")
            
            # Use unique temp profile
            temp_profile = tempfile.mkdtemp(prefix=f"whatsapp_{attempt}_")
            options.add_argument(f"--user-data-dir={temp_profile}")
            
            options.page_load_strategy = 'normal'
            
            service = Service(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(10)
            
            driver.get("https://web.whatsapp.com")
            log("[INFO] Chrome launched successfully!")
            return driver, temp_profile

        except Exception as e:
            last_exception = e
            log(f"[WARN] Launch attempt {attempt} failed: {e}")
            if 'temp_profile' in locals():
                try:
                    shutil.rmtree(temp_profile, ignore_errors=True)
                except:
                    pass
            time.sleep(wait_time)

    raise Exception(f"🚨 Failed to launch Chrome after {retries} attempts. Last error: {last_exception}")

# --------------------- Wait for WhatsApp & QR Code ---------------------
def wait_for_whatsapp_ready(driver):
    log("Waiting for WhatsApp Web to load...")
    
    try:
        WebDriverWait(driver, 30).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']") or 
                     d.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]")
        )
        
        qr_elements = driver.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']")
        if qr_elements:
            log("🔐 QR Code detected.")
            
            if has_display():
                log("Please scan the QR code with your WhatsApp mobile app.")
                log("You have 60 seconds to scan the QR code...")
            else:
                log("Running in headless mode. Please ensure you've logged in previously.")
            
            try:
                WebDriverWait(driver, 60).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "canvas[aria-label='Scan me!']"))
                )
                log("✅ QR Code scanned successfully!")
            except:
                log("⚠️ QR code not scanned within timeout. Continuing anyway...")
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
        )
        log("✅ WhatsApp Web is ready!")
        
    except Exception as e:
        log(f"❌ Failed to load WhatsApp: {e}")
        try:
            driver.save_screenshot("whatsapp_error.png")
            log("📸 Screenshot saved as whatsapp_error.png")
        except:
            pass
        raise

# --------------------- Open Group Without Losing Visibility ---------------------
def open_group_persistent(driver, group_name):
    """Open a group while maintaining the group list visibility"""
    log(f"🔍 Opening group: {group_name}")
    
    try:
        # First, try to find the group in the left pane (group list)
        group_selector = f"span[title='{group_name}']"
        group_elements = driver.find_elements(By.CSS_SELECTOR, group_selector)
        
        if group_elements:
            log(f"✅ Found group in list: {group_name}")
            # Click the group in the left pane
            group_elements[0].click()
            time.sleep(3)
            return True
        
        # If not found in the visible list, use search
        log("Group not immediately visible, using search...")
        search_box = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']"))
        )
        
        # Clear search box carefully
        search_box.click()
        time.sleep(1)
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
        time.sleep(0.5)
        actions.send_keys(Keys.BACKSPACE).perform()
        time.sleep(1)
        
        # Type group name
        search_box.send_keys(group_name)
        time.sleep(2)
        
        # Look for the group in search results
        search_results = driver.find_elements(By.CSS_SELECTOR, f"span[title='{group_name}']")
        if search_results:
            log(f"✅ Found group in search: {group_name}")
            search_results[0].click()
            time.sleep(3)
            
            # Clear search to return to main view
            actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            time.sleep(0.5)
            actions.send_keys(Keys.BACKSPACE).perform()
            time.sleep(2)
            
            return True
        else:
            log(f"❌ Group not found: {group_name}")
            return False
            
    except Exception as e:
        log(f"❌ Error opening group {group_name}: {e}")
        return False

# --------------------- Read Today's Messages ---------------------
def read_todays_messages(driver):
    try:
        # Find all message elements
        message_elements = driver.find_elements(By.CSS_SELECTOR, "div.message-in, div.message-out")
        extracted = []

        today = datetime.now().strftime("%#m/%#d/%Y") if platform.system() == "Windows" else datetime.now().strftime("%-m/%-d/%Y")
        log(f"Reading messages for today: {today}")

        for msg in message_elements:
            try:
                # Check if message has the date attribute
                if msg.find_elements(By.CSS_SELECTOR, "div[data-pre-plain-text]"):
                    sender_elem = msg.find_element(By.CSS_SELECTOR, "div[data-pre-plain-text]")
                    sender_text = sender_elem.get_attribute("data-pre-plain-text")
                    
                    if today in sender_text:
                        sender = sender_text.split("] ")[-1].strip().rstrip(":")
                        
                        # Try to find message text
                        message_text = ""
                        if msg.find_elements(By.CSS_SELECTOR, "span.selectable-text"):
                            message_elem = msg.find_element(By.CSS_SELECTOR, "span.selectable-text")
                            message_text = message_elem.text.strip()
                        
                        if message_text:
                            extracted.append({"sender": sender, "message": message_text})
            except Exception as e:
                continue
                
        log(f"✅ Extracted {len(extracted)} messages from today")
        return extracted
        
    except Exception as e:
        log(f"❌ Error reading messages: {e}")
        return []

# --------------------- Update CSV ---------------------
def update_csv(csv_path):
    if not os.path.exists(csv_path):
        log(f"❌ CSV file not found: {csv_path}")
        with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=['groupName', 'Conversation'])
            writer.writeheader()
            writer.writerow({'groupName': 'Example Group', 'Conversation': '[]'})
        log(f"📝 Created sample CSV file: {csv_path}")

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
    temp_profile = None
    try:
        driver, temp_profile = launch_driver()
        wait_for_whatsapp_ready(driver)
        time.sleep(5)  # Additional wait for complete loading

        for row in rows:
            group_name = row['groupName']
            log(f"\n📌 Processing group: {group_name}")

            todays_msgs = []
            try:
                # Open the group while maintaining the interface
                if open_group_persistent(driver, group_name):
                    time.sleep(3)  # Wait for group to load
                    todays_msgs = read_todays_messages(driver)
                else:
                    log(f"❌ Could not open group: {group_name}")
            except Exception as e:
                log(f"❌ Error processing group {group_name}: {e}")

            row['Conversation'] = json.dumps(todays_msgs, ensure_ascii=False)
            updated_rows.append(row)

    except Exception as e:
        log(f"❌ Fatal error: {e}")
    finally:
        if driver:
            driver.quit()
        if temp_profile and os.path.exists(temp_profile):
            try:
                shutil.rmtree(temp_profile, ignore_errors=True)
            except:
                pass
        cleanup_chrome_processes()

    # Write updated CSV
    try:
        log("💾 Writing updated CSV...")
        with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['groupName', 'Conversation']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        log("✅ CSV updated successfully with today's messages!")
    except Exception as e:
        log(f"❌ Error writing CSV: {e}")

# --------------------- Main Execution ---------------------
if __name__ == "__main__":
    try:
        update_csv(CSV_PATH)
    except Exception as e:
        log(f"❌ Script failed: {e}")
        cleanup_chrome_processes()