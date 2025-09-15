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

    for attempt in range(1, retries + 1):
        try:
            log(f"[INFO] Launch attempt {attempt}...")

            cleanup_chrome_processes()

            options = Options()
            options.add_argument(f"--remote-debugging-port={random.randint(9222, 9999)}")

            # 🚨 Force visible browser (no headless at all)
            log("[INFO] Forcing visible browser")
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

            # Screenshot checkpoint
            driver.save_screenshot("step1_loaded.png")
            log("📸 Screenshot saved: step1_loaded.png")

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
        WebDriverWait(driver, 60).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']") or
                     d.find_elements(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]")
        )

        qr_elements = driver.find_elements(By.CSS_SELECTOR, "canvas[aria-label='Scan me!']")
        if qr_elements:
            log("🔐 QR Code detected. Please scan with your mobile app.")
            try:
                WebDriverWait(driver, 60).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, "canvas[aria-label='Scan me!']"))
                )
                log("✅ QR Code scanned successfully!")
            except:
                log("⚠️ QR code not scanned within timeout. Continuing anyway...")

        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true'][data-tab]"))
        )
        log(f"✅ WhatsApp Web is ready! Page title: {driver.title}")

    except Exception as e:
        log(f"❌ Failed to load WhatsApp: {e}")
        try:
            driver.save_screenshot("whatsapp_error.png")
            log("📸 Screenshot saved as whatsapp_error.png")
        except:
            pass
        raise

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

        log("👉 Browser will stay open. Press ENTER here in terminal to continue...")
        input()  # Keep browser open until you press Enter

        # TODO: Add group processing logic once login works
        updated_rows = rows

    except Exception as e:
        log(f"❌ Fatal error: {e}")
    finally:
        # ⚠️ Do NOT quit driver immediately so you can debug visually
        if temp_profile and os.path.exists(temp_profile):
            try:
                shutil.rmtree(temp_profile, ignore_errors=True)
            except:
                pass
        # cleanup_chrome_processes()  # Disabled during debugging

    # Write updated CSV
    try:
        log("💾 Writing updated CSV...")
        with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ['groupName', 'Conversation']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        log("✅ CSV updated successfully!")
    except Exception as e:
        log(f"❌ Error writing CSV: {e}")

# --------------------- Main Execution ---------------------
if __name__ == "__main__":
    try:
        update_csv(CSV_PATH)
    except Exception as e:
        log(f"❌ Script failed: {e}")
        cleanup_chrome_processes()
