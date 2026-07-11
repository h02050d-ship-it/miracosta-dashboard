#!/usr/bin/env python3
"""ミラコスタ(楽天施設番号74733)の空室を楽天トラベルAPIで取得し availability.json を出力する。
- キーは環境変数 RAKUTEN_ACCESS_KEY（GitHub Secrets）から。コードに書かない。
- 楽天在庫ベースの目安（公式在庫と完全一致ではない）。
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import date, timedelta

APP_ID = "d324ea0a-e3b3-47f3-a8db-e9c581169b56"  # 公開前提のアプリID
KEY = os.environ.get("RAKUTEN_ACCESS_KEY", "").strip()
HOTEL_NO = "74733"
DAYS_AHEAD = 150          # 今日から何日先までチェックするか（解禁は約4ヶ月前）
# 本番は9月以降狙い → 開始日を指定して7・8月をスキップ（対象日を減らし頻度を上げる）
START_DATE = os.environ.get("START_DATE", "2026-09-01").strip()
SLEEP = 1.2               # リクエスト間隔（秒）礼儀
ORIGIN = "https://h02050d-ship-it.github.io"
REFERER = "https://h02050d-ship-it.github.io/miracosta-dashboard/"

if not KEY:
    print("ERROR: RAKUTEN_ACCESS_KEY not set"); sys.exit(1)

def fetch(day):
    ci = day.strftime("%Y-%m-%d")
    co = (day + timedelta(days=1)).strftime("%Y-%m-%d")
    url = ("https://openapi.rakuten.co.jp/engine/api/Travel/VacantHotelSearch/20170426"
           f"?applicationId={APP_ID}&hotelNo={HOTEL_NO}"
           f"&checkinDate={ci}&checkoutDate={co}&adultNum=2&format=json")
    req = urllib.request.Request(url, headers={
        "accessKey": KEY, "Origin": ORIGIN, "Referer": REFERER,
        "User-Agent": "miracosta-dashboard availability (personal use)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:  # Data Not Found = 空きなし
                return {"avail": False, "rooms": []}
            if e.code == 429:  # rate limit → 待って再試行
                time.sleep(10 * (attempt + 1)); continue
            try:
                d = json.loads(e.read().decode())
                break
            except Exception:
                return {"avail": None, "rooms": []}
        except Exception:
            time.sleep(5)
    else:
        return {"avail": None, "rooms": []}

    if "errors" in d or "error" in d:
        msg = (d.get("errors", {}) or {}).get("errorMessage", "") or d.get("error_description", "")
        if "Not Found" in msg or "not_found" in msg:
            return {"avail": False, "rooms": []}
        return {"avail": None, "rooms": []}  # 不明(エラー)

    rooms = []
    for h in d.get("hotels", []):
        for item in h.get("hotel", []):
            if "roomInfo" in item:
                rb = item["roomInfo"][0].get("roomBasicInfo", {})
                name = rb.get("roomName", "")
                if name and name not in rooms:
                    rooms.append(name)
    return {"avail": len(rooms) > 0, "rooms": rooms}

DOW = ["月", "火", "水", "木", "金", "土", "日"]

def official_url(ds):
    return ("https://reserve.tokyodisneyresort.jp/hotel/list/?roomsNum=1&adultNum=2&childNum=3"
            f"&stayingDays=1&useDate={ds}&childAgeBedInform=04_1%7C02_3%7C00_3%7C"
            "&searchHotelCD=DHM&hotelSearchDetail=true&detailOpenFlg=0&hotelChangeFlg=false"
            "&removeSessionFlg=true&returnFlg=false&displayType=data-hotel&reservationStatus=1")

def cancel_note(day):
    diff = (day - date.today()).days
    if diff >= 15:
        return f"✅ いま予約すれば無料キャンセル期間（宿泊{diff}日前）"
    fee = "1万円" if diff >= 8 else "2万円" if diff >= 2 else "3万円"
    return f"⚠️ **キャンセル料 {fee}/室 の時期**（宿泊{diff}日前・取消不可のつもりで判断を）"

def main():
    today = date.today()
    # 前回データ（差分検知＝新規HVだけメール通知するため）
    old = {}
    try:
        with open("availability.json", encoding="utf-8") as f:
            old = json.load(f).get("days", {})
    except Exception:
        pass

    try:
        start = date(int(START_DATE[:4]), int(START_DATE[5:7]), int(START_DATE[8:10]))
    except Exception:
        start = today
    if start < today:
        start = today
    out = {"updated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
           "source": "Rakuten Travel VacantHotelSearch (hotelNo=74733, adultNum=2)",
           "start": start.strftime("%Y%m%d"),
           "days": {}}
    for i in range(DAYS_AHEAD):
        day = today + timedelta(days=i)
        if day < start:      # 9月以降だけ対象（7・8月はスキップ）
            continue
        r = fetch(day)
        hv = any(("ハーバー" in nm) for nm in r["rooms"])
        out["days"][day.strftime("%Y%m%d")] = {
            "a": r["avail"],          # true=空きあり / false=なし / null=不明
            "hv": hv,                  # ハーバービュー系あり
            "r": r["rooms"][:6],
        }
        time.sleep(SLEEP)
    with open("availability.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    # 新規にHVが出た日を検出 → Issue本文を書き出し（GitHubがメール通知してくれる）
    new_hv = [k for k, v in out["days"].items()
              if v["hv"] and not (old.get(k) or {}).get("hv")]
    if new_hv:
        lines = ["@h02050d-ship-it ハーバービューに**新しい空き**が出ました（楽天トラベル在庫）。", ""]
        for ds in sorted(new_hv):
            d = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
            rooms = " / ".join(n for n in out["days"][ds]["r"] if "ハーバー" in n)
            lines.append(f"### {d.month}/{d.day}（{DOW[d.weekday()]}）")
            lines.append(f"- 部屋: {rooms}")
            lines.append(f"- {cancel_note(d)}")
            lines.append(f"- ▶ [公式で今すぐ予約]({official_url(ds)})")
            lines.append("")
        lines.append("[📊 ダッシュボードを開く](https://h02050d-ship-it.github.io/miracosta-dashboard/)")
        with open("new_hv_issue.md", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        # ntfy用の短いプッシュ本文（日付だけ列挙）
        labels = []
        for ds in sorted(new_hv):
            d = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
            labels.append(f"{d.month}/{d.day}({DOW[d.weekday()]})")
        with open("ntfy_msg.txt", "w", encoding="utf-8") as f:
            f.write("HV空き: " + " ".join(labels) + "\nタップで予約画面へ")
        # LINE用メッセージ（日付＋キャンセル料状況＋予約リンク）
        lmsg = ["🌟 ミラコスタ ハーバービュー空き！", ""]
        for ds in sorted(new_hv):
            d = date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
            note = "無料キャンセル期間" if (d - date.today()).days >= 15 else "キャンセル料あり期間"
            lmsg.append(f"■ {d.month}/{d.day}({DOW[d.weekday()]}) [{note}]")
            lmsg.append(official_url(ds))
        lmsg.append("")
        lmsg.append("📊 一覧 https://h02050d-ship-it.github.io/miracosta-dashboard/")
        with open("line_msg.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lmsg))
        print("NEW HV:", ",".join(sorted(new_hv)))

    n_avail = sum(1 for v in out["days"].values() if v["a"])
    n_hv = sum(1 for v in out["days"].values() if v["hv"])
    print(f"done: {len(out['days'])} days, avail={n_avail}, hv={n_hv}, new_hv={len(new_hv)}")

if __name__ == "__main__":
    main()
