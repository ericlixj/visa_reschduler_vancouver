import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# 临时 user data dir
tmp_user_data_dir = tempfile.mkdtemp()

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")  # root 必须加
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument(f"--user-data-dir={tmp_user_data_dir}")  # 解决目录占用问题
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

service = Service("/usr/local/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get("https://www.google.com")
print(driver.title)
driver.quit()
