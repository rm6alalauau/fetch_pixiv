import os
import json
import requests
import gspread
from pixivpy3 import AppPixivAPI

# --- 從環境變數讀取秘密 ---
# 這些值將由 GitHub Actions 傳入
PIXIV_REFRESH_TOKEN = os.getenv('PIXIV_REFRESH_TOKEN')
GCP_CREDS_JSON = os.getenv('GCP_SERVICE_ACCOUNT_CREDENTIALS')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
WORKER_UPDATE_URL = os.getenv('WORKER_UPDATE_URL')
WORKER_SECRET = os.getenv('WORKER_SECRET')

# --- 主邏輯 ---
def main():
    try:
        # 1. 登入 Pixiv
        api = AppPixivAPI()
        api.auth(refresh_token=PIXIV_REFRESH_TOKEN)
        print("✅ Pixiv API authentication successful.")

        # 2. 搜尋熱門作品
        json_result = api.search_illust('ブラウンダスト2', search_target='partial_match_for_tags', sort='popular_desc')
        illusts = json_result.illusts

        if not illusts:
            print("⚠️ No illusts found from Pixiv.")
            return

        print(f"✅ Fetched {len(illusts)} popular illusts from Pixiv.")
        
        # 3. 準備寫入 Sheet 的數據
        # 我們只保留最關鍵的欄位
        sheet_data = [['id', 'user_id', 'title', 'total_bookmarks', 'sanity_level', 'image_url', 'author_name', 'author_avatar']]
        for illust in illusts:
            sheet_data.append([
                illust.id,
                illust.user.id,
                illust.title,
                illust.total_bookmarks,
                illust.sanity_level,
                illust.image_urls.square_medium, # 儲存原始 URL
                illust.user.name,
                illust.user.profile_image_urls.medium
            ])

        # 4. 寫入 Google Sheet
        gc = gspread.service_account_from_dict(json.loads(GCP_CREDS_JSON))
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        sheet_name = 'pixiv'
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()
            print(f"✅ Cleared existing worksheet: {sheet_name}")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="20")
            print(f"✅ Created new worksheet: {sheet_name}")

        worksheet.update('A1', sheet_data)
        print(f"✅ Wrote {len(sheet_data) - 1} rows to Google Sheet: {sheet_name}")
        
        # 5. 將數據 POST 到 Cloudflare Worker 更新 KV
        # 我們直接傳遞 illusts 這個原始 JSON 數據
        payload = {"key": "pixiv", "value": illusts}
        headers = {"Content-Type": "application/json", "X-Auth-Secret": WORKER_SECRET}
        
        response = requests.post(WORKER_UPDATE_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status() # 如果狀態碼不是 2xx，會拋出錯誤
        
        print(f"✅ Successfully updated Cloudflare KV for key 'pixiv'. Response: {response.text}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        raise e

if __name__ == "__main__":
    main()
