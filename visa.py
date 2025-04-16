# -*- coding: utf8 -*-

import time
import json
import random
import platform
import configparser
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from sendmail import send_email


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


# def MY_CONDITION(month, day): return int(month) == 11 and int(day) >= 5
def MY_CONDITION(month, day): return True # No custom condition wanted for the new scheduled date

STEP_TIME = 1  # time between steps (interactions with forms): 0.5 seconds
RETRY_TIME = 1*10  # wait time between retries/checks for available dates: 10 minutes
EXCEPTION_TIME = 1*30  # wait time when an exception occurs: 30 minutes
COOLDOWN_TIME = 1*60  # wait time when temporary banned (empty list): 60 minutes

DATE_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment"
EXIT = False


def send_notification(msg):
    print(f"Sending notification: {msg}")
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

    service = Service("/usr/local/bin/chromedriver")  # 这里填你实际的路径
    return webdriver.Chrome(service=service, options=chrome_options)

driver = get_driver()


def login():
    driver.get(f"https://ais.usvisa-info.com/en-ca/niv/users/sign_in")
    time.sleep(STEP_TIME)

    # print(driver.page_source) 


    # a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    # a.click()
    # time.sleep(STEP_TIME)

    # print("Login start...")
    # href = driver.find_element(By.XPATH, '//*[@id="header"]/nav/div[1]/div[1]/div[2]/div[1]/ul/li[3]/a')
   
    # href.click()
    # time.sleep(STEP_TIME)
    # Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))

    # print("\tclick bounce")
    # a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    # a.click()
    # time.sleep(STEP_TIME)

    do_login_action()


def do_login_action():
    print("\tinput email")
    user = driver.find_element(By.ID, 'user_email')
    user.send_keys(USERNAME)
    # print(f"\tUSERNAME: {USERNAME}")
    time.sleep(random.randint(1, 3))

    print("\tinput pwd")
    pw = driver.find_element(By.ID, 'user_password')
    pw.send_keys(PASSWORD)
    # print(f"\tPASSWORD: {PASSWORD}")
    time.sleep(random.randint(1, 3))

    print("\tclick privacy")
    box = driver.find_element(By.CLASS_NAME, 'icheckbox')
    box .click()
    time.sleep(random.randint(1, 3))

    print("\tcommit")
    btn = driver.find_element(By.NAME, 'commit')
    btn.click()
    time.sleep(random.randint(1, 3))

    Wait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))
    print("\tlogin successful!")

    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie['name'] == '_yatri_session':
            yatri_session = cookie['value']
            print(f"_yatri_session={yatri_session}")
            break


def get_date():
    # 从 selenium 获取当前 cookie 信息并转为请求头中的 Cookie 字符串
    cookie_dict = {c['name']: c['value'] for c in driver.get_cookies()}
    cookie_string = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": cookie_string
    }

    try:
        print(f"📡 请求可预约日期: {DATE_URL}")
        response = requests.get(DATE_URL, headers=headers, timeout=30)
        #if response contains("session expired"),login again
        if response.text.find("session expired") != -1:
            print("Session expired, re-login...")
            send_notification("Session expired, re-login...")
            login()
            time.sleep(STEP_TIME)
            return get_date()

        response.raise_for_status()  # 如果返回非 2xx 状态码，会抛出异常
        date_data = response.json()
        return date_data

    except requests.exceptions.RequestException as e:
        print(f"⚠️ 请求异常: {e}")
        time.sleep(STEP_TIME * 3)
        return get_date()  # 递归重试


def get_time(date):
    time_url = TIME_URL % date
    driver.get(time_url)
    content = driver.find_element(By.TAG_NAME, 'pre').text
    data = json.loads(content)
    time = data.get("available_times")[-1]
    print(f"Got time successfully! {date} {time}")
    return time


def reschedule(date):
    global EXIT
    print(f"Starting Reschedule ({date})")

    time = get_time(date)
    driver.get(APPOINTMENT_URL)

    data = {
        "utf8": driver.find_element(by=By.NAME, value='utf8').get_attribute('value'),
        "authenticity_token": driver.find_element(by=By.NAME, value='authenticity_token').get_attribute('value'),
        "confirmed_limit_message": driver.find_element(by=By.NAME, value='confirmed_limit_message').get_attribute('value'),
        "use_consulate_appointment_capacity": driver.find_element(by=By.NAME, value='use_consulate_appointment_capacity').get_attribute('value'),
        "appointments[consulate_appointment][facility_id]": FACILITY_ID,
        "appointments[consulate_appointment][date]": date,
        "appointments[consulate_appointment][time]": time,
    }

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": APPOINTMENT_URL,
        "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
    }

    r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
    if(r.text.find('Successfully Scheduled') != -1):
        msg = f"Rescheduled Successfully! {date} {time}"
        send_notification(msg)
        EXIT = True
    else:
        msg = f"Reschedule Failed. {date} {time}"
        send_notification(msg)


def is_error():
    content = driver.page_source
    if(content.find("error") != -1):
        return False
    return True


def print_dates(dates):
    print("Available dates:")
    for d in dates:
        print("%s \t business_day: %s" % (d.get('date'), d.get('business_day')))
    print()


last_seen = None


def get_available_date(dates):
    global last_seen

    def is_earlier(date):
        my_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
        new_date = datetime.strptime(date, "%Y-%m-%d")
        result = my_date > new_date
        print(f'Is {my_date} > {new_date}:\t{result}')
        return result

    print("Checking for an earlier date:")
    for d in dates:
        date = d.get('date')
        if is_earlier(date) and date != last_seen:
            _, month, day = date.split('-')
            if(MY_CONDITION(month, day)):
                last_seen = date
                return date


if __name__ == "__main__":
    print("启动，模拟登录...")
    login()
    print("登录成功！")
    send_notification("Login successful!")
    retry_count = 0
    while 1:
        if retry_count > 6:
            break
        try:
            print("--------启动----------")
            print(f"当前时间：{datetime.today()}")
            print(f"Retry count: {retry_count}")
            dates = get_date()[:5]
            print(f"获得有效日期successfully! {dates}")
            if dates:
                earliest = dates[0].get('date')
                print(f"📆 当前查到的最早预约时间：{earliest}")
            else:
                print("⚠️ 当前没有可用的预约日期，重试中...")
                time.sleep(COOLDOWN_TIME)
                continue
            date = get_available_date(dates)
            
            if date:
                print(f"🎯 恭喜！找到了更早的新日期: {date}")
                reschedule(date)
                time.sleep(COOLDOWN_TIME)
            else:
                print("🔍 没有比原计划更早的日期可用，重试中...")
                time.sleep(COOLDOWN_TIME)
                continue

            if(EXIT):
                print("------------------exit")
                break

        except:
            retry_count += 1
            time.sleep(EXCEPTION_TIME)

    if(not EXIT):
        send_notification("HELP! Crashed.")
