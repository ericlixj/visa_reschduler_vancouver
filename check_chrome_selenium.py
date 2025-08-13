# check_chrome_selenium_min.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import shutil
import sys

def test_chrome_selenium():
    print("=== Chrome + Selenium 环境检测 ===")

    CHROMEDRIVER_PATH = shutil.which("chromedriver") or "/usr/local/bin/chromedriver"
    print(f"Chromedriver 路径: {CHROMEDRIVER_PATH}")
    print(f"Google Chrome 路径: {shutil.which('google-chrome')}")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--window-size=1280,800")

    try:
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://www.google.com")
        print(f"[SUCCESS] 页面标题: {driver.title}")
        driver.quit()
    except Exception as e:
        print(f"[ERROR] Chrome/Selenium 启动失败：{e}")
        sys.exit(1)

if __name__ == "__main__":
    test_chrome_selenium()
