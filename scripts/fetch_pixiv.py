import os
import json
import requests
from pixivpy3 import AppPixivAPI
import time

# --- 從 GitHub Secrets 讀取秘密 ---
PIXIV_REFRESH_TOKEN = os.getenv('PIXIV_REFRESH_TOKEN')
APPS_SCRIPT_URL = os.getenv('APPS_SCRIPT_URL')
APPS_SCRIPT_SECRET = os.getenv('APPS_SCRIPT_SECRET')

# --- 抓取配置 ---
TARGET_ILLUST_COUNT = 300
MAX_PAGES_TO_FETCH = 10

# --- 主邏輯 ---
def main():
    if not all([PIXIV_REFRESH_TOKEN, APPS_SCRIPT_URL, APPS_SCRIPT_SECRET]):
        print("❌ Missing required environment variables. Aborting.")
        return

    try:
        # 1. 登入 Pixiv
        api = AppPixivAPI()
        api.auth(refresh_token=PIXIV_REFRESH_TOKEN)
        print("✅ Pixiv API authentication successful.")

        # 2. 【升級】循環抓取多頁熱門作品
        all_illusts = []
        json_result = api.search_illust('ブラウンダスト2', search_target='partial_match_for_tags', sort='popular_desc')
        page_count = 1
        
        while json_result and json_result.illusts and page_count <= MAX_PAGES_TO_FETCH:
            existing_ids = {illust.id for illust in all_illusts}
            new_illusts = [illust for illust in json_result.illusts if illust.id not in existing_ids]
            all_illusts.extend(new_illusts)
            
            print(f"✅ Fetched page {page_count}, added {len(new_illusts)}. Total: {len(all_illusts)}")

            if len(all_illusts) >= TARGET_ILLUST_COUNT or not json_result.next_url:
                break
            
            page_count += 1
            print(f"Fetching page {page_count}...")
            time.sleep(1)
            next_qs = api.parse_qs(json_result.next_url)
            json_result = api.search_illust(**next_qs)

        if not all_illusts:
            print("⚠️ No illusts found from Pixiv.")
            return

        print(f"✅ Finished fetching. Total unique illusts: {len(all_illusts)}")
        
        # 3. 將【所有】數據 POST 到您的 Apps Script Web App
        payload = {
            "secret": APPS_SCRIPT_SECRET,
            "data": all_illusts 
        }
        headers = { "Content-Type": "application/json" }
        
        print(f"Posting {len(all_illusts)} illusts to Apps Script...")
        response = requests.post(APPS_SCRIPT_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status() # 確保請求成功
        
        print(f"✅ Successfully posted data to Apps Script. Response: {response.text}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        raise e

if __name__ == "__main__":
    main()
