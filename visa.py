# -*- coding: utf8 -*-

import os
import time
import json
import random
import platform
import logging
import configparser
from datetime import datetime
import random

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import tempfile
from sendmail import send_email

# 日志配置
log_dir = '/root/deploy/logs'
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, 'visa.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_path, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

USERNAME = config['USVISA']['USERNAME']
PASSWORD = config['USVISA']['PASSWORD']
SCHEDULE_ID = config['USVISA']['SCHEDULE_ID']
MY_SCHEDULE_DATE = config['USVISA']['MY_SCHEDULE_DATE']
COUNTRY_CODE = config['USVISA']['COUNTRY_CODE']
FACILITY_ID = config['USVISA']['FACILITY_ID']

SENDGRID_API_KEY = config['SENDGRID']['SENDGRID_API_KEY']
PUSH_TOKEN = config['PUSHOVER']['PUSH_TOKEN']
PUSH_USER = config['PUSHOVER']['PUSH_USER']

LOCAL_USE = config['CHROMEDRIVER'].getboolean('LOCAL_USE')
HUB_ADDRESS = config['CHROMEDRIVER']['HUB_ADDRESS']

REGEX_CONTINUE = "//a[contains(text(),'Continue')]"

# 活跃刷 slot 的时间段，按小时（24小时制）
# 示例为：(起始小时, 结束小时)，表示每天在这些时间段内刷 slot

ACTIVE_TIME_SLOTS = [
    (0, 24),    # 凌晨 slot 重置
    (5, 7),    # 清晨系统处理
    (8, 10),   # 上午使馆工作时间开始
    (11, 13),  # 中午可能释放 slot
    (15, 18),  # 下午美国办公时间段
    (20, 22),  # 晚上高峰期
]


def MY_CONDITION(month, day): return True

def get_cooldown():
    return random.randint(2, 6)

STEP_TIME = 0.3
RETRY_TIME = 2
EXCEPTION_TIME = 5

DATE_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment"
EXIT = False
last_seen = None

def send_notification(msg):
    logger.info(f"发送通知: {msg}")
    subject = "Visa Appointment Notification"
    send_email(subject, msg)

import tempfile
def get_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    chrome_options.binary_location = "/opt/chrome/chrome"
    tmp_profile_dir = tempfile.mkdtemp(prefix="chrome-profile-")
    chrome_options.add_argument(f"--user-data-dir={tmp_profile_dir}")
    chrome_options.add_argument("--headless=new")  # 更稳定
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--mute-audio")

    service = Service("/usr/local/bin/chromedriver")

    return webdriver.Chrome(service=service, options=chrome_options)

driver = None

def login():
    global driver
    driver = get_driver()

    driver.get(f"https://ais.usvisa-info.com/en-ca/niv/users/sign_in")
    time.sleep(STEP_TIME)
    do_login_action()

def do_login_action():
    logger = logging.getLogger(__name__)
    try:
        logger.info("等待邮箱输入框出现")
        Wait(driver, 30).until(EC.presence_of_element_located((By.ID, 'user_email')))
        user = driver.find_element(By.ID, 'user_email')
        user.clear()
        user.send_keys(USERNAME)
        time.sleep(random.uniform(1, 3))

        logger.info("等待密码输入框出现")
        Wait(driver, 30).until(EC.presence_of_element_located((By.ID, 'user_password')))
        pw = driver.find_element(By.ID, 'user_password')
        pw.clear()
        pw.send_keys(PASSWORD)
        time.sleep(random.uniform(1, 3))

        logger.info("等待隐私条款勾选框出现")
        Wait(driver, 30).until(EC.element_to_be_clickable((By.CLASS_NAME, 'icheckbox')))
        box = driver.find_element(By.CLASS_NAME, 'icheckbox')
        box.click()
        time.sleep(random.uniform(1, 3))

        logger.info("等待登录按钮出现")
        Wait(driver, 30).until(EC.element_to_be_clickable((By.NAME, 'commit')))
        btn = driver.find_element(By.NAME, 'commit')
        btn.click()
        time.sleep(random.uniform(1, 3))

        logger.info("等待登录后页面元素出现（Continue按钮）")
        Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))

        logger.info("登录成功")

    except Exception as e:
        logger.error(f"登录过程中出错: {e}", exc_info=True)
        screenshot_path = f"/tmp/login_error_{int(time.time())}.png"
        driver.save_screenshot(screenshot_path)
        logger.info(f"登录失败时截图已保存: {screenshot_path}")
        raise

def get_date():
    cookie_dict = {c['name']: c['value'] for c in driver.get_cookies()}
    cookie_string = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie_string
    }

    try:
        logger.info(f"请求可预约日期: {DATE_URL}")
        response = requests.get(DATE_URL, headers=headers, timeout=30)

        if response.status_code == 401 or "session expired" in response.text.lower():
            logger.warning("Session expired or unauthorized (401)，重新登录中...")
            # send_notification("Session expired or unauthorized, re-login...")
            login()
            time.sleep(STEP_TIME)
            return get_date()

        response.raise_for_status()
        date_data = response.json()
        return date_data

    except requests.exceptions.RequestException as e:
        logger.warning(f"请求异常: {e}")
        time.sleep(STEP_TIME * 3)
        return get_date()

def get_time(date):
    cookie_dict = {c['name']: c['value'] for c in driver.get_cookies()}
    cookie_string = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie_string
    }

    time_url = TIME_URL % date
    try:
        logger.info(f"请求预约时间: {time_url}")
        response = requests.get(time_url, headers=headers, timeout=30)
        logger.info(f"预约时间响应状态码: {response.status_code}")
        logger.debug(f"预约时间响应内容: {response.text[:500]}")
        response.raise_for_status()
        data = response.json()
        time_str = data.get("available_times")[-1]
        logger.info(f"获取时间成功: {date} {time_str}")
        return time_str
    except Exception as e:
        logger.error(f"⚠️ 获取预约时间失败: {e}")
        raise

def reschedule(date):
    global EXIT
    logger.info(f"尝试重新预约: {date}")

    trying_msg = f"TRY to reschedule visa appointment：{date}"
    send_notification(trying_msg)

    time_str = get_time(date)
    driver.get(APPOINTMENT_URL)

    data = {
        "utf8": driver.find_element(by=By.NAME, value='utf8').get_attribute('value'),
        "authenticity_token": driver.find_element(by=By.NAME, value='authenticity_token').get_attribute('value'),
        "confirmed_limit_message": driver.find_element(by=By.NAME, value='confirmed_limit_message').get_attribute('value'),
        "use_consulate_appointment_capacity": driver.find_element(by=By.NAME, value='use_consulate_appointment_capacity').get_attribute('value'),
        "appointments[consulate_appointment][facility_id]": FACILITY_ID,
        "appointments[consulate_appointment][date]": date,
        "appointments[consulate_appointment][time]": time_str,
    }

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": APPOINTMENT_URL,
        "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
    }

    r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
    if "Successfully Scheduled" in r.text:
        msg = f"预约修改成功: {date} {time_str}"
        send_notification(msg)
        EXIT = True
    else:
        msg = f"预约修改失败: {date} {time_str}"
        send_notification(msg)

def is_earlier(date_str):
    my_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
    new_date = datetime.strptime(date_str, "%Y-%m-%d")
    result = my_date > new_date
    logger.info(f"是否找到更早时间: {my_date} > {new_date} = {result}")
    return result

def within_active_time():
    now_hour = datetime.now().hour
    for start, end in ACTIVE_TIME_SLOTS:
        if start < end:
            if start <= now_hour < end:
                return True
        else:
            if now_hour >= start or now_hour < end:
                return True
    return False

if __name__ == "__main__":
    logger.info("启动，等待进入刷号时间段...")

    # 登录前先等到活跃时间段
    while not within_active_time():
        logger.info("⏳ 当前时间不在刷号时段内，等待下次...")
        time.sleep(RETRY_TIME)

    logger.info("当前时间在刷号时段内，启动模拟登录...")
    login()
    retry_count = 0
    while True:
        if retry_count > 6:
            break
        try:
            if not within_active_time():
                logger.info("⏳ 当前时间不在刷号时段内，等待下次...")
                time.sleep(RETRY_TIME)
                continue

            logger.info("--------开始检查--------")
            logger.info(f"当前时间：{datetime.today()}")
            logger.info(f"重试次数: {retry_count}")

            dates = get_date()[:5]
            logger.info(f"获取可用日期成功: {dates}")

            if dates:
                earliest = dates[0].get('date')
                logger.info(f"当前查到的最早预约时间：{earliest}")

                if is_earlier(earliest):
                    logger.info(f"找到比预期更早的预约时间: {earliest}")
                    reschedule(earliest)
                    time.sleep(get_cooldown())
                else:
                    logger.info("暂无更早的预约时间，等待重试")
                    time.sleep(get_cooldown())
            else:
                logger.warning("暂无可预约日期，等待重试")
                time.sleep(get_cooldown())

            if EXIT:
                logger.info("已成功预约，退出脚本")
                break

        except Exception as e:
            logger.error(f"脚本异常: {e}")
            if "session" in str(e).lower():
                logger.warning("Session invalid，重新登录中...")
                # send_notification("Session invalid, re-login...")
                login()
                time.sleep(STEP_TIME)
                retry_count = 0
                continue
            retry_count += 1
            time.sleep(EXCEPTION_TIME)

    if not EXIT:
        send_notification("HELP! Crashed.")
