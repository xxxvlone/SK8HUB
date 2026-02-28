"""World Skate 滑板资讯页爬虫 + DeepSeek 打分，并导出 worldskate_data.js"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup
from openai import OpenAI


# ==========================================
# DeepSeek API Key（与 spider / thrasher_events 共用）
API_KEY = "sk-4bf1cec59ed641599a3457c7c4481fb6"
# ==========================================


BASE_URL = "https://www.worldskate.org"
SKATEBOARDING_URL = "https://www.worldskate.org/skateboarding.html"


def create_deepseek_client() -> OpenAI:
    """创建并返回已配置 API Key 的 DeepSeek 客户端（OpenAI 兼容接口）"""
    if not API_KEY or API_KEY == "YOUR_DEEPSEEK_API_KEY_HERE":
        raise ValueError("请先在 worldskate_news.py 中配置 DeepSeek API Key 再运行。")
    return OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")


def fetch_news(limit: int = 5):
    """抓取 World Skate 滑板页，返回最新若干条资讯的日期、标题、链接"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(SKATEBOARDING_URL, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    items = []

    # 常见结构：日期 dd.mm.yyyy + h3/h4 标题，或列表项内含链接
    # 先尝试按日期块找：含 "dd.mm.yyyy" 的文本或 data 属性
    date_pattern = re.compile(r"(\d{2}\.\d{2}\.\d{4})")

    # 找所有可能包含“日期+标题”的块：h3/h4 及相邻或父级中的日期
    for tag in soup.find_all(["h3", "h4"]):
        title_text = tag.get_text(strip=True)
        if len(title_text) < 4:
            continue

        # 在父级或前一个兄弟中找日期
        date_str = ""
        parent = tag.find_parent(["div", "article", "li", "section"])
        if parent:
            prev = tag.find_previous_sibling()
            if prev:
                m = date_pattern.search(prev.get_text())
                if m:
                    date_str = m.group(1)
            if not date_str:
                m = date_pattern.search(parent.get_text())
                if m:
                    date_str = m.group(1)

        # 链接：标题所在 a 或父级 a
        link = None
        a = tag.find("a") or tag.find_parent("a")
        if a and a.get("href"):
            href = a.get("href", "").strip()
            if href:
                link = href if href.startswith("http") else (BASE_URL + (href if href.startswith("/") else "/" + href))

        items.append({
            "date": date_str,
            "title": title_text,
            "link": link or SKATEBOARDING_URL,
            "description": "",
        })

    # 若上面没拿到足够条目，再尝试：任意包含日期格式的块 + 其后标题/链接
    if len(items) < limit:
        for block in soup.find_all(["div", "article", "li", "section"]):
            text = block.get_text(strip=True)
            m = date_pattern.search(text)
            if not m:
                continue
            date_str = m.group(1)
            a = block.find("a", href=True)
            title_text = (a.get_text(strip=True) if a else text).strip()
            # 去掉日期部分，只保留标题
            title_text = date_pattern.sub("", title_text).strip()
            if len(title_text) < 4:
                continue
            href = a.get("href", "") if a else ""
            link = href if href.startswith("http") else (BASE_URL + (href if href.startswith("/") else "/" + href)) if href else SKATEBOARDING_URL
            if not any(x["title"] == title_text for x in items):
                items.append({"date": date_str, "title": title_text, "link": link, "description": ""})

    return items[:limit]


def parse_ai_text(ai_text: str):
    """从 DeepSeek 返回文本解析出分数和摘要"""
    if not ai_text:
        return 0, "模型未返回内容"
    m = re.search(r"【分数】\s*(\d+)\s*分.*?【摘要】\s*(.+)", ai_text)
    if not m:
        return 0, ai_text.strip()
    return int(m.group(1)), m.group(2).strip()


def write_js(items, path: str = "worldskate_data.js"):
    """将结果写入 worldskate_data.js"""
    payload = [
        {
            "title": x["title"],
            "link": x["link"],
            "score": x["score"],
            "summary": x["summary"],
            "date": x.get("date", ""),
            "description": x.get("description", ""),
        }
        for x in items
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("const worldskateData = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")


def main():
    print("🚀 开始抓取 World Skate 滑板资讯，并调用 DeepSeek 打分...")

    try:
        news = fetch_news(limit=5)
        if not news:
            print("😅 未解析到任何资讯，页面结构可能已变化。")
            return

        print(f"✅ 抓取到 {len(news)} 条资讯，交给 DeepSeek 处理...\n" + "-" * 40)

        client = create_deepseek_client()
        enriched = []

        for idx, item in enumerate(news, start=1):
            title = item["title"]
            link = item["link"]
            date = item.get("date", "")

            print(f"\n[{idx}] 日期：{date} | 标题：{title}")
            print(f"    链接：{link}")

            prompt = (
                "请给这条 World Skate 滑板/奥运相关资讯打分（基础 0 分，满分 10 分）。"
                "规则：涉及奥运资格、世锦赛/巡回赛、排名、官方日程等加 2～3 分；"
                "涉及青训、奖学金、裁判/教练等体系内容再加 1～2 分。其余按重要性与可读性在 0～5 分内评估。"
                "只返回一行，格式必须为：【分数】X分 | 【摘要】20字以内的简评。"
                f"\n标题：{title}\n日期：{date}"
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
                **item,
                "score": score,
                "summary": summary,
            })

            time.sleep(2)

        enriched.sort(key=lambda x: x["score"], reverse=True)

        print("\n📊 按分数从高到低排序：")
        for idx, x in enumerate(enriched, start=1):
            print(f"[{idx}] 分数={x['score']} | {x['title'][:50]}... | {x['summary']}")

        write_js(enriched, path="worldskate_data.js")
        print("\n💾 已生成 worldskate_data.js，前端可通过 <script src=\"./worldskate_data.js\"></script> 使用。")

    except Exception as e:
        print(f"\n❌ 运行出错: {e}")


if __name__ == "__main__":
    main()
