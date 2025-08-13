from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

# Chrome 启动参数
chrome_options = Options()
chrome_options.add_argument("--headless")  # 无界面模式
chrome_options.add_argument("--no-sandbox")  # root 用户必须加
chrome_options.add_argument("--disable-dev-shm-usage")  # 避免 /dev/shm 空间不足
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

# ChromeDriver 路径（如果已在 PATH 中可以不写）
service = Service("/usr/local/bin/chromedriver")

# 创建 driver
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # 打开 google.com
    driver.get("https://www.google.com")

    # 等待页面加载
    time.sleep(2)

    # 输出页面 HTML
    print(driver.page_source)
finally:
    driver.quit()
