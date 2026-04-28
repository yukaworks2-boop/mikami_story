"""
三上ビジネス ストーリーをスプレッドシートに転記するスクリプト。
GitHub Actionsの「④ ビジネス スプシに転記」ワークフローから手動実行する。
みかみ本アカウントと同じスプレッドシートの別シートに転記する。
"""

import gspread
import os
import json
import re
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials

JST = timezone(timedelta(hours=9))
SPREADSHEET_ID = "12opzsgUNQhi9iQQJr8Ub1fkP4P9XBbpv51aEH4I6mWA"
SHEET_NAME = os.environ.get("SHEET_NAME", "ビジネス")


def parse_slides(content: str) -> list[str]:
    parts = re.split(r'━+\s*\n📱 ストーリー \d+枚目\s*\n━+', content)
    slides = [s.strip() for s in parts[1:] if s.strip()]
    return slides


def write_to_spreadsheet(date_str: str, slides: list[str]):
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        print("GOOGLE_SERVICE_ACCOUNT_JSON が未設定")
        return

    creds_data = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    try:
        sheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        print(f"シート「{SHEET_NAME}」が見つかりません。スプレッドシートに「{SHEET_NAME}」タブを作成してください。")
        return

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_short = f"{date_obj.month}/{date_obj.day}"

    a_col = sheet.col_values(1)
    target_row = None
    for i in range(9, len(a_col)):
        if a_col[i] == date_short:
            target_row = i + 1
            break

    if target_row is None:
        print(f"日付 {date_short} に一致する行が見つかりませんでした（シート: {SHEET_NAME}）")
        return

    for i, slide in enumerate(slides):
        sheet.update_cell(target_row, 7 + i, slide)

    print(f"✅ [{SHEET_NAME}] {target_row}行目 ({date_short}) のG列以降に {len(slides)}枚転記しました")


def main():
    target_date = os.environ.get("TARGET_DATE", "").strip()
    if not target_date:
        target_date = datetime.now(JST).strftime("%Y-%m-%d")

    print(f"転記対象日付: {target_date}（シート: {SHEET_NAME}）")

    story_file = f"stories_business/{target_date}.md"
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
