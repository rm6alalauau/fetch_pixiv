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
TARGET_ILLUST_COUNT = 900
MAX_PAGES_TO_FETCH = 30

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

        # 2. 循環抓取多頁熱門作品 (維持不變)
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
        
        # 3. 【唯一修改處】直接在原始物件上新增 AI 判斷欄位
        print("Adding AI-generated flag to each illust object...")
        for illust in all_illusts:
            # 根據 illust.illust_ai_type 的值來決定新欄位的內容
            # illust_ai_type == 2 代表是 AI 生成作品
            if illust.illust_ai_type == 2:
                illust.is_ai = "true"
            else:
                illust.is_ai = "false"
        
        # 4. 將【已添加欄位的】原始數據 POST 到您的 Apps Script Web App (維持不變)
        payload = {
            "secret": APPS_SCRIPT_SECRET,
            "data": all_illusts # 直接使用被修改過的 all_illusts
        }
        headers = { "Content-Type": "application/json" }
        
        print(f"Posting {len(all_illusts)} illusts to Apps Script...")
        # 加上 ensure_ascii=False 確保中文字符正確傳輸
        response = requests.post(APPS_SCRIPT_URL, data=json.dumps(payload, ensure_ascii=False), headers=headers)
        response.raise_for_status() # 確保請求成功
        
        print(f"✅ Successfully posted data to Apps Script. Response: {response.text}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        raise e

if __name__ == "__main__":
    main()
