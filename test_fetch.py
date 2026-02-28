"""测试数据源抓取功能（不调用AI）"""

import json
import random
from typing import List, Dict

import requests
from bs4 import BeautifulSoup


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
                    "source": "KickerClub",
                    "score": random.randint(5, 15),
                    "summary": "滑板资讯热闻"
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
                "source": "Thrasher",
                "score": random.randint(5, 15),
                "summary": "滑板活动盛事"
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
                "source": "World Skate",
                "score": random.randint(5, 15),
                "summary": "滑板官方资讯"
            })
            if len(items) >= limit:
                break
        
        return items
    except Exception as e:
        print(f"❌ World Skate抓取失败: {e}")
        return []


def main():
    print("=" * 60)
    print("🧪 Sk8Top10 - 数据源抓取测试")
    print("=" * 60)
    
    all_items = []
    
    print("\n📡 开始抓取数据源...")
    
    # KickerClub
    print("\n  1. KickerClub...")
    kicker_items = fetch_kickerclub("https://www.kickerclub.com/category/news/", limit=10)
    all_items.extend(kicker_items)
    print(f"    ✅ 抓取到 {len(kicker_items)} 条")
    
    # Thrasher
    print("\n  2. Thrasher...")
    thrasher_items = fetch_thrasher("https://www.thrashermagazine.com/events/", limit=10)
    all_items.extend(thrasher_items)
    print(f"    ✅ 抓取到 {len(thrasher_items)} 条")
    
    # World Skate
    print("\n  3. World Skate...")
    worldskate_items = fetch_worldskate("https://www.worldskate.org/skateboarding.html", limit=10)
    all_items.extend(worldskate_items)
    print(f"    ✅ 抓取到 {len(worldskate_items)} 条")
    
    # 排序并取Top10
    all_items.sort(key=lambda x: x["score"], reverse=True)
    top10 = all_items[:10]
    
    print("\n" + "=" * 60)
    print("🏆 测试结果 - TOP 10")
    print("=" * 60)
    for idx, item in enumerate(top10, 1):
        print(f"\n[{idx}] 来源: {item['source']}")
        print(f"    标题: {item['title']}")
        print(f"    摘要: {item['summary']}")
    
    # 写入data.js
    js_content = "const newsData = " + json.dumps(top10, ensure_ascii=False, indent=2) + ";\n"
    with open("data.js", "w", encoding="utf-8") as f:
        f.write(js_content)
    
    print("\n" + "=" * 60)
    print(f"💾 已生成 data.js，包含 {len(top10)} 条资讯")
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
