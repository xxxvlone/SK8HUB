"""Thrasher Magazine 活动页爬虫 + DeepSeek 打分，并导出 events_data.js"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup
from openai import OpenAI


# ==========================================
# DeepSeek API Key（与 spider / worldskate_news 共用）
API_KEY = "sk-4bf1cec59ed641599a3457c7c4481fb6"
# ==========================================


EVENTS_URL = "https://www.thrashermagazine.com/events/"


def create_deepseek_client() -> OpenAI:
    """创建并返回已配置 API Key 的 DeepSeek 客户端（OpenAI 兼容接口）"""
    if not API_KEY or API_KEY == "YOUR_DEEPSEEK_API_KEY_HERE":
        raise ValueError("请先在 thrasher_events.py 中配置 DeepSeek API Key 再运行。")
    return OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")


def fetch_events(limit: int = 5):
    """抓取 Thrasher 活动页，返回最新若干条活动的标题、日期、链接、描述"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(EVENTS_URL, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # 页面结构：活动标题在 h4 中，日期和活动名连在一起，下方有描述段落
    events = []
    for h4 in soup.find_all("h4"):
        title_raw = h4.get_text(strip=True)
        if len(title_raw) < 3:
            continue

        # 尝试取链接：h4 可能在 <a> 内，或父级容器内有 <a>
        link = None
        a = h4.find("a") or h4.find_parent("a")
        if a and a.get("href"):
            link = a.get("href", "").strip()
            if link and not link.startswith("http"):
                base = "https://www.thrashermagazine.com"
                link = base + link if link.startswith("/") else (base + "/" + link)

        # 描述：取 h4 下一个兄弟节点或父级内后续文本
        desc = ""
        next_el = h4.find_next_sibling()
        if next_el:
            desc = next_el.get_text(strip=True)
        if not desc and h4.parent:
            # 父节点内除 h4 外的第一段文字
            for node in h4.parent.children:
                if node != h4 and getattr(node, "get_text", None):
                    desc = node.get_text(strip=True)
                    if len(desc) > 10:
                        break

        events.append({
            "title": title_raw,
            "date": "",  # 若需可从 title_raw 里用正则拆出日期
            "link": link or EVENTS_URL,
            "description": desc[:200] if desc else "",
        })

    return events[:limit]


def parse_ai_text(ai_text: str):
    """从 DeepSeek 返回文本解析出分数和摘要"""
    if not ai_text:
        return 0, "模型未返回内容"
    m = re.search(r"【分数】\s*(\d+)\s*分.*?【摘要】\s*(.+)", ai_text)
    if not m:
        return 0, ai_text.strip()
    score = int(m.group(1))
    summary = m.group(2).strip()
    return score, summary


def write_events_js(items, path: str = "events_data.js"):
    """将结果写入 events_data.js"""
    payload = []
    for item in items:
        payload.append({
            "title": item["title"],
            "link": item["link"],
            "score": item["score"],
            "summary": item["summary"],
            "date": item.get("date", ""),
            "description": item.get("description", ""),
        })
    js_content = "const eventsData = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(js_content)


def main():
    print("🚀 开始抓取 Thrasher Magazine 活动列表，并调用 DeepSeek 打分...")

    try:
        events = fetch_events(limit=5)
        if not events:
            print("😅 未解析到任何活动，页面结构可能已变化。")
            return

        print(f"✅ 抓取到 {len(events)} 条活动，交给 DeepSeek 处理...\n" + "-" * 40)

        client = create_deepseek_client()
        enriched = []

        for idx, event in enumerate(events, start=1):
            title = event["title"]
            link = event["link"]
            desc = event.get("description", "")

            print(f"\n[{idx}] 标题：{title}")
            print(f"    链接：{link}")

            prompt = (
                "请给这条 Thrasher 滑板活动/事件打分（基础 0 分，满分 10 分）。"
                "规则：涉及知名滑手、品牌首映、线下 jam/比赛、街头文化展览等加 2～3 分；"
                "带有嘻哈/街头/亚文化元素再加 1～2 分。其余按“高能程度”在 0～5 分内评估。"
                "只返回一行，格式必须为：【分数】X分 | 【摘要】20字以内的亚文化调性简评。"
                f"\n标题：{title}\n描述：{desc[:150] if desc else '无'}"
            )

            print("    🧠 AI 正在分析并打分...")
            ai_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
            )
            ai_text = (ai_response.choices[0].message.content or "").strip()
            print(f"    原始 AI 输出：{ai_text}")

            score, summary = parse_ai_text(ai_text)
            print(f"    解析结果：分数={score}，摘要={summary}")

            enriched.append({
                "title": title,
                "link": link,
                "score": score,
                "summary": summary,
                "date": event.get("date", ""),
                "description": event.get("description", ""),
            })

            time.sleep(2)

        enriched.sort(key=lambda x: x["score"], reverse=True)

        print("\n📊 按分数从高到低排序：")
        for idx, item in enumerate(enriched, start=1):
            print(f"[{idx}] 分数={item['score']} | {item['title'][:50]}... | {item['summary']}")

        write_events_js(enriched, path="events_data.js")
        print("\n💾 已生成 events_data.js，前端可通过 <script src=\"./events_data.js\"></script> 使用。")

    except Exception as e:
        print(f"\n❌ 运行出错: {e}")


if __name__ == "__main__":
    main()
