import os
import json
import gspread
from pixivpy3 import AppPixivAPI
import time

# --- 從 GitHub Secrets 讀取秘密 ---
PIXIV_REFRESH_TOKEN = os.getenv('PIXIV_REFRESH_TOKEN')
GCP_CREDS_JSON = os.getenv('GCP_SERVICE_ACCOUNT_CREDENTIALS')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

# --- 抓取配置 ---
TARGET_ILLUST_COUNT = 300  # 目標抓取 300 篇作品
MAX_PAGES_TO_FETCH = 10    # 最多抓 10 頁

# --- 主邏輯 ---
def main():
    try:
        # 1. 登入 Pixiv
        api = AppPixivAPI()
        api.auth(refresh_token=PIXIV_REFRESH_TOKEN)
        print("✅ Pixiv API authentication successful.")

        # 2. 循環抓取多頁熱門作品
        all_illusts = []
        # 先獲取第一頁
        print("Fetching page 1...")
        json_result = api.search_illust('ブラウンダスト2', search_target='partial_match_for_tags', sort='popular_desc')
        
        page_count = 1
        while json_result and json_result.illusts and page_count <= MAX_PAGES_TO_FETCH:
            # 去除重複的作品 (雖然不太可能，但保險起見)
            existing_ids = {illust.id for illust in all_illusts}
            new_illusts = [illust for illust in json_result.illusts if illust.id not in existing_ids]
            all_illusts.extend(new_illusts)
            
            print(f"✅ Fetched page {page_count}, added {len(new_illusts)} new illusts. Total: {len(all_illusts)}")

            # 如果達到目標數量或沒有下一頁了，就停止
            if len(all_illusts) >= TARGET_ILLUST_COUNT or not json_result.next_url:
                break
            
            # 獲取下一頁
            page_count += 1
            print(f"Fetching page {page_count}...")
            time.sleep(1) # 禮貌性延遲1秒
            next_qs = api.parse_qs(json_result.next_url)
            json_result = api.search_illust(**next_qs)

        if not all_illusts:
            print("⚠️ No illusts found from Pixiv.")
            return

        print(f"✅ Finished fetching. Total unique illusts: {len(all_illusts)}")
        
        # 3. 準備寫入 Sheet 的數據
        headers = ['id', 'user_id', 'title', 'total_bookmarks', 'sanity_level', 'image_url', 'author_name', 'author_avatar']
        sheet_data = [headers]
        for illust in all_illusts:
            # 對可能不存在的屬性做安全處理
            user_id = illust.user.id if illust.user else None
            author_name = illust.user.name if illust.user else None
            author_avatar = illust.user.profile_image_urls.medium if illust.user and illust.user.profile_image_urls else None

            sheet_data.append([
                illust.id,
                user_id,
                illust.title,
                illust.total_bookmarks,
                illust.sanity_level,
                illust.image_urls.square_medium,
                author_name,
                author_avatar
            ])

        # 4. 寫入 Google Sheet
        print("Connecting to Google Sheets...")
        gc = gspread.service_account_from_dict(json.loads(GCP_CREDS_JSON))
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        sheet_name = 'pixiv' # 指定要寫入的工作表名稱
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()
            print(f"✅ Cleared existing worksheet: '{sheet_name}'")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="500", cols="20")
            print(f"✅ Created new worksheet: '{sheet_name}'")

        worksheet.update('A1', sheet_data, value_input_option='USER_ENTERED')
        print(f"✅ Successfully wrote {len(all_illusts)} records to Google Sheet: '{sheet_name}'")
        
        print("\n🎉 Python script finished successfully!")

    except Exception as e:
        print(f"❌ An error occurred during Python script execution: {e}")
        raise e

if __name__ == "__main__":
    main()
