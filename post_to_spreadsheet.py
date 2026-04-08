"""
確認済みのストーリーをスプレッドシートに転記するスクリプト。
GitHub Actionsの「② スプシに転記」ワークフローから手動実行する。
"""

import gspread
import os
import json
import re
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

JST = timezone(timedelta(hours=9))
SPREADSHEET_ID = "12opzsgUNQhi9iQQJr8Ub1fkP4P9XBbpv51aEH4I6mWA"


def parse_slides(content: str) -> list[str]:
    """ストーリーテキストをスライド単位に分割する"""
    parts = re.split(r'━+\s*\n📱 ストーリー \d+枚目\s*\n━+', content)
    slides = [s.strip() for s in parts if s.strip()]
    return slides


def write_to_spreadsheet(date_str: str, slides: list[str]):
    """A列の日付に一致する行のG列以降にスライドを書き込む"""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        print("GOOGLE_SERVICE_ACCOUNT_JSON が未設定")
        return

    creds_data = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.sheet1

    # 日付を M/D 形式に変換
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_short = f"{date_obj.month}/{date_obj.day}"

    # A列を取得して10行目以降で日付が一致する行を探す
    a_col = sheet.col_values(1)
    target_row = None
    for i in range(9, len(a_col)):
        if a_col[i] == date_short:
            target_row = i + 1  # 1-indexed
            break

    if target_row is None:
        print(f"日付 {date_short} に一致する行が見つかりませんでした")
        return

    # G列(7列目)以降にスライドを書き込む
    for i, slide in enumerate(slides):
        sheet.update_cell(target_row, 7 + i, slide)

    print(f"✅ {target_row}行目 ({date_short}) のG列以降に {len(slides)}枚転記しました")


def main():
    # TARGET_DATE環境変数があればそちら、なければ今日
    target_date = os.environ.get("TARGET_DATE", "").strip()
    if not target_date:
        target_date = datetime.now(JST).strftime("%Y-%m-%d")

    print(f"転記対象日付: {target_date}")

    # stories/YYYY-MM-DD.md を読み込む
    story_file = f"stories/{target_date}.md"
    if not os.path.exists(story_file):
        print(f"ストーリーファイルが見つかりません: {story_file}")
        return

    with open(story_file, "r", encoding="utf-8") as f:
        content = f.read()

    slides = parse_slides(content)
    print(f"スライド数: {len(slides)}枚")

    if not slides:
        print("スライドが見つかりませんでした")
        return

    write_to_spreadsheet(target_date, slides)


if __name__ == "__main__":
    main()
