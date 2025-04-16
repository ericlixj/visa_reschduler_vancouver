# sendmail.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser

# 加载配置
config = configparser.ConfigParser()
config.read('config.ini')

def send_email(subject, html_content):
    sender_email = config['EMAIL']['SENDER_EMAIL']
    sender_password = config['EMAIL']['SENDER_PASSWORD']
    receiver_email = config['EMAIL']['RECEIVER_EMAIL']
    smtp_server = config['EMAIL'].get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(config['EMAIL'].get('SMTP_PORT', 587))

    # 构建邮件内容
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")


# 测试用例（可注释掉）
if __name__ == "__main__":
    send_email(
        subject="📬 测试邮件 - 来自 Python",
        html_content="""
        <html>
          <body>
            <h2>你好！</h2>
            <p>这是一封测试邮件，来自 <b>Python sendmail.py</b>。</p>
          </body>
        </html>
        """
    )
