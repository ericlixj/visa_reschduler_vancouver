# check_chrome_selenium.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import tempfile

def test_chrome_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")           # 无头模式
    chrome_options.add_argument("--disable-dev-shm-usage")  # /dev/shm 太小时避免崩溃
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,800")

    # Chromedriver 路径
    service = Service("/usr/local/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("https://www.google.com")
        print("页面标题:", driver.title)
        html = driver.page_source
        print("前200字符HTML预览:", html[:200])
    finally:
        driver.quit()

if __name__ == "__main__":
    test_chrome_selenium()
