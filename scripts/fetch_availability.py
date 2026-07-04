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

def main():
    today = date.today()
    out = {"updated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
           "source": "Rakuten Travel VacantHotelSearch (hotelNo=74733, adultNum=2)",
           "days": {}}
    for i in range(DAYS_AHEAD):
        day = today + timedelta(days=i)
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
    n_avail = sum(1 for v in out["days"].values() if v["a"])
    n_hv = sum(1 for v in out["days"].values() if v["hv"])
    print(f"done: {len(out['days'])} days, avail={n_avail}, hv={n_hv}")

if __name__ == "__main__":
    main()
