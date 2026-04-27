"""
weather_notify.py
毎朝7時に天気予報を取得し、降水確率が高い場合にスマホへ通知を送るスクリプト。
使用API:
  - Open-Meteo (https://open-meteo.com/)  ※天気予報・無料・登録不要
  - ntfy.sh    (https://ntfy.sh/)         ※プッシュ通知・無料・登録不要
"""

import sys
from datetime import datetime, timezone, timedelta
import requests

JST = timezone(timedelta(hours=9))
from dotenv import load_dotenv
import os

load_dotenv()

# --- 設定（.envで上書き可能） ---
LATITUDE      = float(os.getenv("LATITUDE", "36.40"))
LONGITUDE     = float(os.getenv("LONGITUDE", "138.25"))
THRESHOLD     = int(os.getenv("THRESHOLD", "50"))    # 通知する降水確率の閾値（%）
LOCATION_NAME = os.getenv("LOCATION_NAME", "上田市上田原")
NTFY_TOPIC    = os.getenv("NTFY_TOPIC", "")          # ntfy.sh のトピック名（必須）


def get_max_precipitation_probability() -> int:
    """Open-Meteo APIから今日の最大降水確率（%）を取得する。"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "precipitation_probability",
        "timezone": "Asia/Tokyo",
        "forecast_days": 1,
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    times = data["hourly"]["time"]
    probs = data["hourly"]["precipitation_probability"]

    today_str = datetime.now(JST).date().isoformat()  # JSTで今日の日付を取得
    today_probs = [
        prob for t, prob in zip(times, probs)
        if t.startswith(today_str) and prob is not None
        and 8 <= int(t[11:13]) <= 16      # 8時〜16時のみ対象
    ]

    return max(today_probs) if today_probs else 0


def send_ntfy_notification(title: str, message: str) -> None:
    """ntfy.sh 経由でスマホにプッシュ通知を送る。"""
    if not NTFY_TOPIC:
        print("[警告] NTFY_TOPIC が未設定です。.env に NTFY_TOPIC=<トピック名> を追加してください。")
        return

    try:
        response = requests.post(
            "https://ntfy.sh/",
            json={
                "topic":    NTFY_TOPIC,
                "title":    title,
                "message":  message,
                "priority": 4,
                "tags":     ["umbrella", "rain"],
            },
            timeout=15,
        )
        response.raise_for_status()
        print(f"→ 通知を送信しました（ntfy.sh/{NTFY_TOPIC}）")
    except requests.RequestException as exc:
        print(f"[警告] 通知の送信に失敗しました: {exc}")


def main() -> None:
    today_jst = datetime.now(JST).date()
    print(f"[天気通知] {today_jst}（JST）の天気情報を取得中... ({LOCATION_NAME})")

    try:
        max_prob = get_max_precipitation_probability()
    except requests.RequestException as exc:
        print(f"[エラー] API通信に失敗しました: {exc}")
        sys.exit(1)

    print(f"8〜16時の最大降水確率: {max_prob}%（通知閾値: {THRESHOLD}%）")

    if max_prob >= THRESHOLD:
        title   = f"雨の可能性があります（{LOCATION_NAME}）"
        message = f"8〜16時の最大降水確率は {max_prob}% です。傘を忘れずに！"
        print(f"→ 閾値以上のため通知を送ります: {message}")
        send_ntfy_notification(title, message)
    else:
        print("→ 閾値未満のため通知しません。今日は傘不要の予報です。")


if __name__ == "__main__":
    main()
