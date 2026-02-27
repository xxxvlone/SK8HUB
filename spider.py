"""KickerClub 新闻爬虫 + Gemini 打分，并导出 data.js 给前端使用"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup
from google import genai


# ==========================================
# ⚠️ 这里请替换成你自己的真实 GEMINI API KEY
API_KEY = "AIzaSyDPgZsuARebRprOD85Hm1b0DgOfic9EW6k"
# ==========================================


def create_gemini_client() -> genai.Client:
    """创建并返回一个已经配置好 API Key 的 Gemini 客户端"""
    if API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError("请先在 spider.py 中把 API_KEY 替换为你自己的 GEMINI API Key 再运行。")
    return genai.Client(api_key=API_KEY)


def fetch_latest_articles(limit: int = 5):
    """抓取 KickerClub 新闻页面，返回最新若干条文章的标题和链接"""
    url = "https://www.kickerclub.com/category/news/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # 直接抓取页面中的 h2 / h3 里的 a 标签作为候选文章
    title_tags = soup.find_all(["h2", "h3"])
    articles = []
    for tag in title_tags:
        a_tag = tag.find("a")
        if a_tag and len(a_tag.text.strip()) > 2:
            articles.append({"title": a_tag.text.strip(), "link": a_tag.get("href")})

    return articles[:limit]


def parse_ai_text(ai_text: str):
    """从 Gemini 返回的文本里解析出分数和摘要"""
    if not ai_text:
        return 0, "模型未返回内容"

    # 期望格式：【分数】X分 | 【摘要】一句 20 字以内的亚文化调性简评
    m = re.search(r"【分数】\s*(\d+)\s*分.*?【摘要】\s*(.+)", ai_text)
    if not m:
        # 如果解析失败，就把整段文本当作摘要，分数给 0
        return 0, ai_text.strip()

    score = int(m.group(1))
    summary = m.group(2).strip()
    return score, summary


def write_data_js(items, path: str = "data.js"):
    """把最终结果写入 data.js，供前端页面通过 <script src> 使用"""
    payload = []
    for item in items:
        payload.append(
            {
                "title": item["title"],
                "link": item["link"],
                "score": item["score"],
                "summary": item["summary"],
            }
        )

    js_content = "const newsData = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(js_content)


def main():
    print("🚀 开始抓取 KickerClub 最新资讯，并调用 Gemini 打分...")

    try:
        # 1. 抓取最新文章
        articles = fetch_latest_articles(limit=5)
        if not articles:
            print("😅 没有抓到任何新闻标题，可能是页面结构发生了变化。")
            return

        print(f"✅ 抓取到 {len(articles)} 条新闻，准备交给 Gemini 处理...\n" + "-" * 40)

        # 2. 创建 Gemini 客户端
        client = create_gemini_client()

        # 3. 逐条调用 Gemini 打分与摘要
        enriched = []
        for idx, article in enumerate(articles, start=1):
            title = article["title"]
            link = article["link"]

            print(f"\n[{idx}] 标题：{title}")
            print(f"    链接：{link}")

            prompt = (
                "请给这个滑板新闻标题打分（基础 0 分，满分 10 分）。"
                "规则：含“奥运 / 历史记录 / 冠军 / 首发”等竞技与突破性词汇，加 2 分；"
                "涉及国内外知名滑手，或带有嘻哈 / 街头亚文化元素，再加 3 分。"
                "其余部分在 0～5 分范围内自由评估整体高能程度。"
                "只返回一行，格式必须为：【分数】X分 | 【摘要】20字以内的亚文化调性简评。"
                f"\n标题：{title}"
            )

            print("    🧠 AI 正在分析并打分...")
            ai_response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            ai_text = (ai_response.text or "").strip()
            print(f"    原始 AI 输出：{ai_text}")

            score, summary = parse_ai_text(ai_text)
            print(f"    解析结果：分数={score}，摘要={summary}")

            enriched.append(
                {
                    "title": title,
                    "link": link,
                    "score": score,
                    "summary": summary,
                }
            )

            # 每次请求后暂停 2 秒，避免触发频率限制
            time.sleep(2)

        # 4. 按分数从高到低排序
        enriched.sort(key=lambda item: item["score"], reverse=True)

        print("\n📊 按分数从高到低排序后的结果：")
        for idx, item in enumerate(enriched, start=1):
            print(
                f"[{idx}] 分数={item['score']} | 标题={item['title']} | 摘要={item['summary']}"
            )

        # 5. 写入 data.js 文件
        write_data_js(enriched, path="data.js")
        print("\n💾 已生成 data.js 文件，前端可通过 <script src=\"./data.js\"></script> 直接使用。")

    except Exception as e:
        print(f"\n❌ 运行出错: {e}")


if __name__ == "__main__":
    main()