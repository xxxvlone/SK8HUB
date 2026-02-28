"""Sk8Top10 - 滑板资讯热榜主爬虫
整合所有数据源，抓取50条资讯，AI处理，排序，输出Top10
"""

import json
import re
import time
import random
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# ==========================================
# 配置区域
# ==========================================
DEEPSEEK_API_KEY = "sk-4bf1cec59ed641599a3457c7c4481fb6"
TARGET_ITEMS = 50
TOP_N = 10

# ==========================================
# 数据源配置
# ==========================================
DATA_SOURCES = {
    "kickerclub": {
        "name": "KickerClub",
        "url": "https://www.kickerclub.com/category/news/",
        "type": "web"
    },
    "thrasher": {
        "name": "Thrasher Magazine",
        "url": "https://www.thrashermagazine.com/events/",
        "type": "web"
    },
    "worldskate": {
        "name": "World Skate",
        "url": "https://www.worldskate.org/skateboarding.html",
        "type": "web"
    }
}

# 知名滑手列表（用于文化元素加权）
PRO_SKATERS = [
    "Nyjah Huston", "Ryan Sheckler", "Paul Rodriguez", "Andy Anderson",
    "Chris Cole", "Eric Koston", "Paul Rodriguez", "Shane O'Neill",
    "Luan Oliveira", "Ishod Wair", "Chris Joslin", "Tom Asta"
]

# 中国滑板相关关键词
CHINA_KEYWORDS = [
    "中国", "China", "上海", "北京", "深圳", "广州", "成都", "杭州",
    "大道之子", "Avenue & Son", "Hero", "Vagabond", "Justice", "沸点",
    "FLY Streetwear", "Stephen Khou", "Cyres Wong", "王汇丰", "Dan Z", "Vans"
]

# 热点关键词（用于基础加分）
HOT_KEYWORDS = [
    "奥运", "Olympic", "历史记录", "record", "冠军", "champion", "首发",
    "premiere", "冠军赛", "tournament", "世界锦标赛", "World Championship"
]

# 亚文化/嘻哈元素关键词
HIPHOP_KEYWORDS = [
    "hiphop", "hip hop", "rap", "trap", "DJ", "graffiti", "涂鸦",
    "街舞", "breakdance", "underground", "地下", "街头", "street"
]


def create_deepseek_client() -> OpenAI:
    """创建DeepSeek客户端"""
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")


def fetch_kickerclub(url: str, limit: int = 15) -> List[Dict]:
    """抓取KickerClub新闻"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        articles = []
        title_tags = soup.find_all(["h2", "h3"])
        
        for tag in title_tags:
            a_tag = tag.find("a")
            if a_tag and len(a_tag.text.strip()) > 2:
                articles.append({
                    "title": a_tag.text.strip(),
                    "link": a_tag.get("href"),
                    "source": "KickerClub"
                })
                if len(articles) >= limit:
                    break
        
        return articles
    except Exception as e:
        print(f"❌ KickerClub抓取失败: {e}")
        return []


def fetch_thrasher(url: str, limit: int = 15) -> List[Dict]:
    """抓取Thrasher活动"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        events = []
        for h4 in soup.find_all("h4"):
            title_raw = h4.get_text(strip=True)
            if len(title_raw) < 3:
                continue
            
            link = None
            a = h4.find("a") or h4.find_parent("a")
            if a and a.get("href"):
                link = a.get("href", "").strip()
                if link and not link.startswith("http"):
                    base = "https://www.thrashermagazine.com"
                    link = base + link if link.startswith("/") else (base + "/" + link)
            
            events.append({
                "title": title_raw,
                "link": link or url,
                "source": "Thrasher"
            })
            if len(events) >= limit:
                break
        
        return events
    except Exception as e:
        print(f"❌ Thrasher抓取失败: {e}")
        return []


def fetch_worldskate(url: str, limit: int = 15) -> List[Dict]:
    """抓取World Skate资讯"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        items = []
        for tag in soup.find_all(["h3", "h4"]):
            title_text = tag.get_text(strip=True)
            if len(title_text) < 4:
                continue
            
            link = None
            a = tag.find("a") or tag.find_parent("a")
            if a and a.get("href"):
                href = a.get("href", "").strip()
                if href:
                    base = "https://www.worldskate.org"
                    link = href if href.startswith("http") else (base + (href if href.startswith("/") else "/" + href))
            
            items.append({
                "title": title_text,
                "link": link or url,
                "source": "World Skate"
            })
            if len(items) >= limit:
                break
        
        return items
    except Exception as e:
        print(f"❌ World Skate抓取失败: {e}")
        return []


def calculate_keyword_score(title: str) -> int:
    """基于关键词计算基础分数"""
    score = 0
    title_lower = title.lower()
    
    # 热点关键词加分
    for keyword in HOT_KEYWORDS:
        if keyword.lower() in title_lower:
            score += 3
    
    # 中国元素加分
    for keyword in CHINA_KEYWORDS:
        if keyword.lower() in title_lower:
            score += 2
    
    # 知名滑手加分
    for skater in PRO_SKATERS:
        if skater.lower() in title_lower:
            score += 2
    
    # 亚文化元素加分
    for keyword in HIPHOP_KEYWORDS:
        if keyword.lower() in title_lower:
            score += 1
    
    return score


def get_ai_summary_and_score(client: OpenAI, title: str, source: str) -> tuple[int, str]:
    """使用DeepSeek AI获取分数和摘要"""
    prompt = f"""你是一个滑板资讯热榜编辑。请处理这条滑板资讯：

标题：{title}
来源：{source}

任务1：打分（0-20分）
- 包含"奥运"、"历史记录"、"冠军"、"首发"等词汇 +3分
- 涉及知名滑手 +2分
- 融合hiphop/街头文化元素 +2分
- 有中国元素 +2分
- 整体热度/重要性 0-11分

任务2：生成一句话摘要（必须12字以内，符合热点规律，有冲击力）

返回格式必须为：【分数】X分 | 【摘要】你的摘要
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        
        ai_text = (response.choices[0].message.content or "").strip()
        
        # 解析AI返回
        m = re.search(r"【分数】\s*(\d+)\s*分.*?【摘要】\s*(.+)", ai_text)
        if m:
            score = int(m.group(1))
            summary = m.group(2).strip()
            # 确保摘要不超过12字
            if len(summary) > 12:
                summary = summary[:12]
            return score, summary
        else:
            # 备用方案
            keyword_score = calculate_keyword_score(title)
            return keyword_score, "滑板资讯"
            
    except Exception as e:
        print(f"    ⚠️ AI调用失败，使用关键词评分: {e}")
        keyword_score = calculate_keyword_score(title)
        return keyword_score, "滑板资讯"


def fetch_all_sources() -> List[Dict]:
    """从所有数据源抓取资讯"""
    all_items = []
    
    print("📡 开始抓取数据源...")
    
    # KickerClub
    print("  - KickerClub...")
    kicker_items = fetch_kickerclub(DATA_SOURCES["kickerclub"]["url"], limit=20)
    all_items.extend(kicker_items)
    print(f"    ✅ 抓取到 {len(kicker_items)} 条")
    
    # Thrasher
    print("  - Thrasher...")
    thrasher_items = fetch_thrasher(DATA_SOURCES["thrasher"]["url"], limit=15)
    all_items.extend(thrasher_items)
    print(f"    ✅ 抓取到 {len(thrasher_items)} 条")
    
    # World Skate
    print("  - World Skate...")
    worldskate_items = fetch_worldskate(DATA_SOURCES["worldskate"]["url"], limit=15)
    all_items.extend(worldskate_items)
    print(f"    ✅ 抓取到 {len(worldskate_items)} 条")
    
    # 随机打乱并取前TARGET_ITEMS条
    random.shuffle(all_items)
    all_items = all_items[:TARGET_ITEMS]
    
    print(f"\n✅ 总共抓取到 {len(all_items)} 条资讯\n")
    return all_items


def process_items(items: List[Dict]) -> List[Dict]:
    """处理所有资讯：AI打分、生成摘要"""
    client = create_deepseek_client()
    processed = []
    
    print("🧠 开始AI处理...")
    
    for idx, item in enumerate(items, 1):
        title = item["title"]
        source = item.get("source", "Unknown")
        
        print(f"\n[{idx}/{len(items)}] 处理: {title[:40]}...")
        
        # 获取AI分数和摘要
        ai_score, ai_summary = get_ai_summary_and_score(client, title, source)
        
        # 计算关键词分数作为补充
        keyword_score = calculate_keyword_score(title)
        final_score = ai_score + keyword_score
        
        print(f"    分数: AI={ai_score}, 关键词={keyword_score}, 总计={final_score}")
        print(f"    摘要: {ai_summary}")
        
        processed.append({
            "title": title,
            "link": item["link"],
            "score": final_score,
            "summary": ai_summary,
            "source": source
        })
        
        # 避免API限流
        time.sleep(1.5)
    
    return processed


def write_data_js(items: List[Dict], path: str = "data.js"):
    """写入data.js供前端使用"""
    js_content = "const newsData = " + json.dumps(items, ensure_ascii=False, indent=2) + ";\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"\n💾 已生成 {path}")


def main():
    print("=" * 60)
    print("🚀 Sk8Top10 - 滑板资讯热榜")
    print("=" * 60)
    
    try:
        # 1. 抓取所有数据源
        items = fetch_all_sources()
        
        if not items:
            print("❌ 没有抓取到任何资讯")
            return
        
        # 2. AI处理
        processed = process_items(items)
        
        # 3. 按分数排序
        processed.sort(key=lambda x: x["score"], reverse=True)
        
        # 4. 取Top10
        top10 = processed[:TOP_N]
        
        print("\n" + "=" * 60)
        print("🏆 TOP 10 滑板资讯热榜")
        print("=" * 60)
        for idx, item in enumerate(top10, 1):
            print(f"\n[{idx}] 分数: {item['score']}")
            print(f"    标题: {item['title']}")
            print(f"    摘要: {item['summary']}")
            print(f"    来源: {item.get('source', 'Unknown')}")
        
        # 5. 写入data.js
        write_data_js(top10)
        
        print("\n" + "=" * 60)
        print("✅ 任务完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
