#!/usr/bin/env python3
"""HV空き検知メールを Gmail SMTP で h02050d@gmail.com に送る。
パスワードは環境変数 GMAIL_APP_PASSWORD（GitHub Secrets）から。コード/ファイルには書かない。
"""
import os, sys, smtplib, ssl
from email.mime.text import MIMEText
from email.header import Header

USER = "h02050d@gmail.com"
PW = os.environ.get("GMAIL_APP_PASSWORD", "").strip()


def main():
    if not PW:
        print("GMAIL_APP_PASSWORD not set -> skip email")
        return 0
    body_file = sys.argv[1] if len(sys.argv) > 1 else "new_hv_issue.md"
    subject = sys.argv[2] if len(sys.argv) > 2 else "ミラコスタ ハーバービュー空き検知"
    try:
        with open(body_file, encoding="utf-8") as f:
            body = f.read()
    except Exception:
        body = "（本文なし）"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = USER
    msg["To"] = USER
    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls(context=ctx)
        s.login(USER, PW)
        s.sendmail(USER, [USER], msg.as_string())
    print("email sent to", USER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
