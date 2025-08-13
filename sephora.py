from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile

def scrape_sephora_product(url):
    options = Options()
    temp_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={temp_dir}")
    print(f"Using temp user data dir: {temp_dir}")

    # root 用户必须加 --no-sandbox
    options.add_argument("--no-sandbox")
    options.add_argument("--headless=new")  # 使用新 headless 模式
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.7258.127 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        print("页面标题:", driver.title)
    finally:
        driver.quit()
