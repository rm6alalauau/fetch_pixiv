import os
import json
import requests
from pixivpy3 import AppPixivAPI
import time

# --- 從 GitHub Secrets 讀取秘密 ---
PIXIV_REFRESH_TOKEN = os.getenv('PIXIV_REFRESH_TOKEN')
APPS_SCRIPT_URL2 = os.getenv('APPS_SCRIPT_URL2')
APPS_SCRIPT_SECRET = os.getenv('APPS_SCRIPT_SECRET')

# --- 【新】抓取任務配置 ---
# 在這裡定義所有您想執行的搜尋任務。
# 程式會按照列表順序執行，並進行全局去重。
SEARCH_TASKS = [
    {
        "keyword": "ブラウンダスト2",
        "sort": "popular_desc",
        "target_count": 800  # 主要目標：抓取 800 篇熱門常規作品
    },
    {
        "keyword": "BrownDust2",
        "sort": "date_desc",  # 按最新排序
        "target_count": 200  # 補充目標：抓取最多 200 篇
    }
]

# --- 【新】輔助函式：執行單次抓取任務 ---
def fetch_and_add_illusts(api, task, all_illusts_map):
    """
    執行一個搜尋任務，並將不重複的作品添加到全局的 map 中。
    
    :param api: 已認證的 AppPixivAPI 物件
    :param task: 一個包含 keyword, sort, target_count 的字典
    :param all_illusts_map: 用於儲存所有獨一無二作品的字典 (ID -> illust 物件)
    """
    keyword = task["keyword"]
    sort_order = task["sort"]
    target_count = task["target_count"]
    
    print(f"\n--- 🚀 開始新任務: 搜尋關鍵字 '{keyword}' (排序: {sort_order}, 目標: {target_count}) ---")
    
    added_in_this_task = 0
    page_count = 1
    
    try:
        json_result = api.search_illust(keyword, search_target='partial_match_for_tags', sort=sort_order)
        
        while json_result and json_result.illusts:
            newly_added_this_page = 0
            for illust in json_result.illusts:
                # 核心去重邏輯：只有當 ID 不在全局 map 中時，才添加
                if illust.id not in all_illusts_map:
                    all_illusts_map[illust.id] = illust
                    newly_added_this_page += 1
            
            if newly_added_this_page > 0:
                added_in_this_task += newly_added_this_page
                print(f"✅ 第 {page_count} 頁: 新增 {newly_added_this_page} 篇不重複作品。此任務累計新增: {added_in_this_task}。全局總數: {len(all_illusts_map)}")

            # 如果此任務的目標已達成，或沒有下一頁了，就結束此任務
            if added_in_this_task >= target_count or not json_result.next_url:
                break
                
            page_count += 1
            time.sleep(1.5) # 稍微增加延遲，更加穩妥
            next_qs = api.parse_qs(json_result.next_url)
            json_result = api.search_illust(**next_qs)

    except Exception as e:
        print(f"⚠️ 執行任務 '{keyword}' 時發生錯誤: {e}")
        
    print(f"--- ✅ 任務 '{keyword}' 完成。此任務總共新增 {added_in_this_task} 篇作品。 ---")


# --- 主邏輯 (已重構) ---
def main():
    if not all([PIXIV_REFRESH_TOKEN, APPS_SCRIPT_URL2, APPS_SCRIPT_SECRET]):
        print("❌ Missing required environment variables. Aborting.")
        return

    try:
        # 1. 登入 Pixiv
        api = AppPixivAPI()
        api.auth(refresh_token=PIXIV_REFRESH_TOKEN)
        print("✅ Pixiv API authentication successful.")

        # 2. 【已升級】執行所有定義好的搜尋任務
        # 我們使用字典來儲存結果，鍵是 illust.id，值是 illust 物件本身。
        # 這使得去重操作非常高效 (O(1) 時間複雜度)。
        all_illusts_map = {}
        
        for task in SEARCH_TASKS:
            fetch_and_add_illusts(api, task, all_illusts_map)

        # 從字典中提取所有的 illust 物件，轉換為列表
        final_illusts = list(all_illusts_map.values())

        if not final_illusts:
            print("⚠️ 從所有任務中都未找到任何作品。")
            return

        print(f"\n✨ 所有任務執行完畢。總共獲取到 {len(final_illusts)} 篇獨一無二的作品。")
        
        # 3. 為所有作品添加 AI 判斷欄位
        print("Adding AI-generated flag to each illust object...")
        for illust in final_illusts:
            illust.is_ai = "true" if illust.illust_ai_type == 2 else "false"
        
        # 4. 將最終的、不重複的數據 POST 到 Apps Script
        payload = {
            "secret": APPS_SCRIPT_SECRET,
            "data": final_illusts
        }
        headers = { "Content-Type": "application/json" }
        
        print(f"Posting {len(final_illusts)} illusts to Apps Script...")
        response = requests.post(APPS_SCRIPT_URL2, data=json.dumps(payload, ensure_ascii=False), headers=headers)
        response.raise_for_status()
        
        print(f"✅ Successfully posted data to Apps Script. Response: {response.text}")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        raise e

if __name__ == "__main__":
    main()
