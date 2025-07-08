import os
import json
import requests
from pixivpy3 import AppPixivAPI

# --- 從 GitHub Secrets 讀取秘密 ---
PIXIV_REFRESH_TOKEN = os.getenv('PIXIV_REFRESH_TOKEN')
APPS_SCRIPT_URL = os.getenv('APPS_SCRIPT_URL')
APPS_SCRIPT_SECRET = os.getenv('APPS_SCRIPT_SECRET')

# --- 主邏輯 ---
def main():
    try:
        # 1. 登入 Pixiv
        api = AppPixivAPI()
        api.auth(refresh_token=PIXIV_REFRESH_TOKEN)
        print("✅ Pixiv API authentication successful.")

        # 2. 搜尋熱門作品
        json_result = api.search_illust('ブラウンダスト', search_target='partial_match_for_tags', sort='popular_desc')
        illusts = json_result.illusts

        if not illusts:
            print("⚠️ No illusts found from Pixiv.")
            return

        print(f"✅ Fetched {len(illusts)} popular illusts from Pixiv.")
        
        # 3. 將數據 POST 到您的 Apps Script Web App
        payload = {
            "secret": APPS_SCRIPT_SECRET,
            "data": illusts 
        }
        headers = { "Content-Type": "application/json" }
        
        response = requests.post(APPS_SCRIPT_URL, data=json.dumps(payload), headers=headers)
        response.raise_for_status()
        
        print(f"✅ Successfully posted data to Apps Script. Response: {response.text}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        raise e

if __name__ == "__main__":
    main()
