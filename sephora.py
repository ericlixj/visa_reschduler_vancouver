# check_chrome_env.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import shutil
import sys

CHROMEDRIVER_PATH = shutil.which("chromedriver") or "/usr/bin/chromedriver"
TEST_URL = "https://www.google.com"

def check_chrome_env():
    print("=== Chrome + Selenium 环境检测 ===")
    print(f"Chromedriver 路径: {CHROMEDRIVER_PATH}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")      # 无头模式
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--window-size=1280,800")
    chrome_options.add_argument("--user-data-dir=/tmp/chrome-profile-test")  # 防止 profile 冲突
    
    try:
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(TEST_URL)
        title = driver.title
        print(f"[SUCCESS] 访问 {TEST_URL} 成功，页面标题：{title}")
        driver.quit()
    except Exception as e:
        print(f"[ERROR] Chrome/Selenium 启动失败：{e}")
        sys.exit(1)

if __name__ == "__main__":
    check_chrome_env()
