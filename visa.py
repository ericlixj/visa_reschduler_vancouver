# -*- coding: utf8 -*-

import os
import time
import json
import random
import platform
import logging
import configparser
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

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

def MY_CONDITION(month, day): return True

STEP_TIME = 1
RETRY_TIME = 1*10
EXCEPTION_TIME = 1*30
COOLDOWN_TIME = 1*60

DATE_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment"
EXIT = False


def send_notification(msg):
    logger.info(f"发送通知: {msg}")
    subject = "Visa Appointment Notification"
    send_email(subject, msg)


def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0")

    service = Service("/usr/local/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)


driver = get_driver()


def login():
    driver.get(f"https://ais.usvisa-info.com/en-ca/niv/users/sign_in")
    time.sleep(STEP_TIME)
    do_login_action()


def do_login_action():
    logger.info("输入邮箱")
    user = driver.find_element(By.ID, 'user_email')
    user.send_keys(USERNAME)
    time.sleep(random.randint(1, 3))

    logger.info("输入密码")
    pw = driver.find_element(By.ID, 'user_password')
    pw.send_keys(PASSWORD)
    time.sleep(random.randint(1, 3))

    logger.info("勾选隐私条款")
    box = driver.find_element(By.CLASS_NAME, 'icheckbox')
    box.click()
    time.sleep(random.randint(1, 3))

    logger.info("点击登录")
    btn = driver.find_element(By.NAME, 'commit')
    btn.click()
    time.sleep(random.randint(1, 3))

    Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))
    logger.info("登录成功")

    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie['name'] == '_yatri_session':
            yatri_session = cookie['value']
            logger.info(f"_yatri_session={yatri_session}")
            break


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
        logger.info(f"📡 请求可预约日期: {DATE_URL}")
        response = requests.get(DATE_URL, headers=headers, timeout=30)

        if response.status_code == 401 or "session expired" in response.text.lower():
            logger.warning("Session expired or unauthorized (401)，重新登录中...")
            send_notification("Session expired or unauthorized, re-login...")
            login()
            time.sleep(STEP_TIME)
            return get_date()

        response.raise_for_status()
        date_data = response.json()
        return date_data

    except requests.exceptions.RequestException as e:
        logger.warning(f"⚠️ 请求异常: {e}")
        time.sleep(STEP_TIME * 3)
        return get_date()


def get_time(date):
    time_url = TIME_URL % date
    driver.get(time_url)
    content = driver.find_element(By.TAG_NAME, 'pre').text
    data = json.loads(content)
    time_str = data.get("available_times")[-1]
    logger.info(f"获取时间成功: {date} {time_str}")
    return time_str


def reschedule(date):
    global EXIT
    logger.info(f"尝试重新预约: {date}")

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
        msg = f"🎉 预约修改成功: {date} {time_str}"
        send_notification(msg)
        EXIT = True
    else:
        msg = f"❌ 预约修改失败: {date} {time_str}"
        send_notification(msg)


def is_error():
    return "error" not in driver.page_source


last_seen = None


def get_available_date(dates):
    global last_seen

    def is_earlier(date):
        my_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
        new_date = datetime.strptime(date, "%Y-%m-%d")
        result = my_date > new_date
        logger.info(f"是否找到更早时间: {my_date} > {new_date} = {result}")
        return result

    logger.info("正在检查是否有更早日期")
    for d in dates:
        date = d.get('date')
        if is_earlier(date) and date != last_seen:
            _, month, day = date.split('-')
            if MY_CONDITION(month, day):
                last_seen = date
                return date


if __name__ == "__main__":
    logger.info("启动，模拟登录...")
    login()
    logger.info("登录成功！")
    send_notification("Login successful!")

    retry_count = 0
    while True:
        if retry_count > 6:
            break
        try:
            logger.info("--------开始检查--------")
            logger.info(f"当前时间：{datetime.today()}")
            logger.info(f"重试次数: {retry_count}")

            dates = get_date()[:5]
            logger.info(f"获取可用日期成功: {dates}")

            if dates:
                earliest = dates[0].get('date')
                logger.info(f"📆 当前查到的最早预约时间：{earliest}")
            else:
                logger.warning("⚠️ 暂无可预约日期，等待重试")
                time.sleep(COOLDOWN_TIME)
                continue

            date = get_available_date(dates)

            if date:
                logger.info(f"🎯 找到更早的预约时间: {date}")
                reschedule(date)
                time.sleep(COOLDOWN_TIME)
            else:
                logger.info("🔍 暂无更早的预约时间，等待重试")
                time.sleep(COOLDOWN_TIME)

            if EXIT:
                logger.info("✅ 已成功预约，退出脚本")
                break

        except Exception as e:
            logger.error(f"❌ 脚本异常: {e}")
            if "session" in str(e).lower():
                logger.warning("Session invalid，重新登录中...")
                send_notification("Session invalid, re-login...")
                login()
                time.sleep(STEP_TIME)
                retry_count = 0
                continue
            retry_count += 1
            time.sleep(EXCEPTION_TIME)

    if not EXIT:
        send_notification("HELP! Crashed.")
