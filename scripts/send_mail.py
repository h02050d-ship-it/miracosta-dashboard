#!/usr/bin/env python3
"""HV空き検知メールを送る。
差出人を「自分(h02050d)」にすると受信トレイに入らないため（Gmailの自分宛仕様）、
会社用アカウント(hayazaimuku)から h02050d@gmail.com へ送る＝受信トレイに届く。
パスワードは環境変数(GitHub Secrets)から。コード/ファイルには書かない。
"""
import os, sys, smtplib, ssl, datetime
from email.mime.text import MIMEText
from email.header import Header
from email.utils import make_msgid

RECIPIENT = "h02050d@gmail.com"

# 優先: 会社用アカウントから送る（受信トレイに届く）
BIZ_PW = os.environ.get("BIZ_GMAIL_APP_PASSWORD", "").strip()
BIZ_USER = os.environ.get("BIZ_GMAIL_USER", "hayazaimuku@gmail.com").strip()
# 予備: 自分から自分（受信トレイには入らないが記録用）
SELF_PW = os.environ.get("GMAIL_APP_PASSWORD", "").strip()


def main():
    if BIZ_PW:
        auth_user, pw, sender = BIZ_USER, BIZ_PW, BIZ_USER
    elif SELF_PW:
        auth_user, pw, sender = RECIPIENT, SELF_PW, RECIPIENT
    else:
        print("no mail password set -> skip email")
        return 0

    body_file = sys.argv[1] if len(sys.argv) > 1 else "new_hv_issue.md"
    subject = sys.argv[2] if len(sys.argv) > 2 else "ミラコスタ ハーバービュー空き検知"
    subject = subject + " " + datetime.datetime.now().strftime("%-m/%-d %H:%M")

    try:
        with open(body_file, encoding="utf-8") as f:
            body = f.read()
    except Exception:
        body = "（本文なし）"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = str(Header("ミラコスタ空室通知", "utf-8")) + " <" + sender + ">"
    msg["To"] = RECIPIENT
    msg["Message-ID"] = make_msgid(domain="miracosta.local")

    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls(context=ctx)
        s.login(auth_user, pw)
        s.sendmail(sender, [RECIPIENT], msg.as_string())
    print("email sent: from", sender, "to", RECIPIENT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
