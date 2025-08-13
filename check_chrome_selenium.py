# check_chrome_selenium_min.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import tempfile
import shutil
import sys

def test_chrome_selenium():
    print("=== Chrome + Selenium 环境检测 ===")

    # 查找 chromedriver 路径
    CHROMEDRIVER_PATH = shutil.which("chromedriver") or "/usr/bin/chromedriver"
    print(f"Chromedriver 路径: {CHROMEDRIVER_PATH}")

    # 使用临时目录作为用户数据目录，避免冲突
    temp_user_data_dir = tempfile.mkdtemp(prefix="chrome_profile_")
    print(f"临时 user-data-dir: {temp_user_data_dir}")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")      # 无头模式
    chrome_options.add_argument("--no-sandbox")        # root 下必须
    chrome_options.add_argument("--disable-dev-shm-usage")  # 避免 /dev/shm 太小问题
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,800")
    chrome_options.add_argument(f"--user-data-dir={temp_user_data_dir}")

    try:
        service = Service(CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://www.google.com")
        title = driver.title
        print(f"[SUCCESS] Chrome + Selenium 启动成功，访问 Google 页面标题：{title}")
        driver.quit()
    except Exception as e:
        print(f"[ERROR] Chrome/Selenium 启动失败：{e}")
        sys.exit(1)

if __name__ == "__main__":
    test_chrome_selenium()
