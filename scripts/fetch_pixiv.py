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
# 我們可以為不同排序方式設定不同的目標
TARGET_POPULAR_COUNT = 500 # 抓取 300 張熱門作品
TARGET_NEWEST_COUNT = 200  # 抓取 200 張最新作品

# --- 輔助函式：用於抓取特定排序的插圖 ---
def fetch_illusts(api, keyword, sort_order, target_count):
    """
    根據給定的排序方式抓取插圖。
    :param api: 已認證的 AppPixivAPI 物件
    :param keyword: 搜尋關鍵字
    :param sort_order: 'popular_desc' 或 'date_desc'
    :param target_count: 目標抓取數量
    :return: 插圖列表
    """
    illusts = []
    print(f"\n--- Starting fetch for sort_order: '{sort_order}' ---")
    
    try:
        json_result = api.search_illust(keyword, search_target='partial_match_for_tags', sort=sort_order)
        page_count = 1
        
        while json_result and json_result.illusts:
            # 使用集合來過濾已存在的ID，避免重複添加
            existing_ids = {illust.id for illust in illusts}
            new_illusts = [illust for illust in json_result.illusts if illust.id not in existing_ids]
            illusts.extend(new_illusts)
            
            print(f"✅ Fetched page {page_count} ({sort_order}), added {len(new_illusts)}. Total for this sort: {len(illusts)}")

            # 如果達到目標數量或沒有下一頁了，就停止
            if len(illusts) >= target_count or not json_result.next_url:
                break
            
            page_count += 1
            print(f"Fetching page {page_count}...")
            time.sleep(1.5) # 甚至可以稍微增加延遲，更加穩妥
            next_qs = api.parse_qs(json_result.next_url)
            json_result = api.search_illust(**next_qs)
            
    except Exception as e:
        print(f"⚠️ An error occurred during fetch for '{sort_order}': {e}")
        
    print(f"--- Finished fetch for '{sort_order}'. Found {len(illusts)} illusts. ---")
    return illusts


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

        # 2. 分別抓取熱門和最新的作品
        keyword = 'ブラウンダスト2'
        
        popular_illusts = fetch_illusts(api, keyword, 'popular_desc', TARGET_POPULAR_COUNT)
        newest_illusts = fetch_illusts(api, keyword, 'date_desc', TARGET_NEWEST_COUNT)

        # 3. 合併並去重
        # 將熱門作品放在前面，但確保ID唯一
        all_illusts_map = {illust.id: illust for illust in popular_illusts}
        for illust in newest_illusts:
            if illust.id not in all_illusts_map:
                all_illusts_map[illust.id] = illust
        
        final_illusts = list(all_illusts_map.values())

        if not final_illusts:
            print("⚠️ No illusts found from Pixiv.")
            return

        print(f"\n✅ Finished all fetching. Total unique illusts: {len(final_illusts)}")
        
        # 4. 將【所有】數據 POST 到您的 Apps Script Web App
        payload = {
            "secret": APPS_SCRIPT_SECRET,
            "data": final_illusts
        }
        headers = { "Content-Type": "application/json" }
        
        print(f"Posting {len(final_illusts)} illusts to Apps Script...")
        # 注意: PixivPy3返回的對象需要先轉換為可序列化的字典
        # AppPixivAPI的返回結果本身就是類字典結構，requests可以直接處理
        response = requests.post(APPS_SCRIPT_URL, data=json.dumps(payload, indent=2), headers=headers)
        response.raise_for_status() # 確保請求成功
        
        print(f"✅ Successfully posted data to Apps Script. Response: {response.text}")

    except Exception as e:
        print(f"❌ An error occurred in main function: {e}")
        raise e

if __name__ == "__main__":
    main()
