# ============================================================
# 智绘锡承 - 邮件发送工具
# 位置: backend/app/utils/email.py
#
# 功能: 发送密码重置验证码邮件
# 策略:
#   - SMTP 配置完整 → 真实发送邮件
#   - SMTP 未配置（开发环境）→ 打印验证码到控制台（方便联调测试）
# ============================================================
import smtplib
import ssl
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate, make_msgid

from flask import current_app


def send_verification_email(to_email, code):
    """发送密码重置验证码邮件

    Args:
        to_email: 收件人邮箱
        code: 6位验证码

    Returns:
        bool: True=发送成功, False=发送失败
    """
    smtp_host = current_app.config.get('SMTP_HOST', '')
    smtp_port = current_app.config.get('SMTP_PORT', 465)
    smtp_user = current_app.config.get('SMTP_USER', '')
    smtp_password = current_app.config.get('SMTP_PASSWORD', '')
    sender_name = current_app.config.get('MAIL_SENDER_NAME', '智绘锡承')
    sender_name = escape(sender_name)

    # 构建邮件内容
    html = f"""
    <div style="max-width:480px;margin:0 auto;font-family:sans-serif;">
        <h2 style="color:#409EFF;">{sender_name}</h2>
        <p>您正在重置密码，验证码为：</p>
        <div style="font-size:32px;font-weight:bold;letter-spacing:8px;
                    color:#409EFF;text-align:center;padding:20px 0;">{code}</div>
        <p style="color:#999;font-size:12px;">
            验证码 10 分钟内有效，如非本人操作请忽略此邮件。
        </p>
    </div>
    """

    # 开发环境：SMTP 未配置 → 打印到控制台
    if not smtp_host or not smtp_user:
        if not current_app.debug and not current_app.testing:
            current_app.logger.error('生产环境未配置 SMTP，拒绝发送验证码')
            return False
        print(f'\n[DEV MODE] 密码重置验证码\n  收件人: {to_email}\n  验证码: {code}\n  （SMTP 未配置，请手动查看控制台）\n', flush=True)
        return True

    # 生产环境：真实发送邮件
    # 强制用 SMTP 登录账号作为发件人，加完整邮件头防拒收
    from_email = smtp_user
    if '@' not in from_email:
        current_app.logger.error('SMTP 发件账号缺少有效邮箱地址')
        return False
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'{sender_name} - 密码重置验证码'
    msg['From'] = formataddr((sender_name, from_email))
    msg['To'] = to_email
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid(domain=from_email.split('@')[1])
    msg['Reply-To'] = from_email
    msg.attach(MIMEText(html, 'html', 'utf-8'))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls(context=ssl.create_default_context())
        with server:
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception:
        current_app.logger.error('SMTP 邮件发送失败，请核对服务连接和授权')
        return False
