"""简单测试：生成一些样本数据用于测试前端"""

import json
import random

# 生成样本数据
sample_data = [
    {
        "title": "FISE Battle of the Champions 2026",
        "link": "https://www.kickerclub.com/2026/02/fise-battle-2026/",
        "score": 18,
        "summary": "冠军之战来袭"
    },
    {
        "title": "Nyjah Huston 发布全新滑板视频",
        "link": "https://www.thrashermagazine.com/videos/nyjah-2026/",
        "score": 17,
        "summary": "传奇滑手新作"
    },
    {
        "title": "中国滑板队奥运资格赛",
        "link": "https://www.worldskate.org/olympics-qualifiers/",
        "score": 16,
        "summary": "奥运资格争夺"
    },
    {
        "title": "Avenue & Son 上海滑板活动",
        "link": "https://www.kickerclub.com/2026/02/avenue-son-shanghai/",
        "score": 15,
        "summary": "中国滑板活动"
    },
    {
        "title": "Thrasher 滑板大电影首映",
        "link": "https://www.thrashermagazine.com/premiere/",
        "score": 14,
        "summary": "滑板大片首映"
    },
    {
        "title": "街头滑板赛在北京举行",
        "link": "https://www.kickerclub.com/2026/02/beijing-street-contest/",
        "score": 13,
        "summary": "北京滑板赛事"
    },
    {
        "title": "Paul Rodriguez 签名款滑板发布",
        "link": "https://www.kickerclub.com/2026/02/prod-signature-deck/",
        "score": 12,
        "summary": "签名款发布"
    },
    {
        "title": "世界滑板锦标赛赛程公布",
        "link": "https://www.worldskate.org/world-championship-schedule/",
        "score": 11,
        "summary": "世锦赛赛程"
    },
    {
        "title": "滑板与嘻哈文化融合活动",
        "link": "https://www.kickerclub.com/2026/02/skate-hip-hop-event/",
        "score": 10,
        "summary": "街头文化盛事"
    },
    {
        "title": "女子滑板公开赛在深圳举办",
        "link": "https://www.kickerclub.com/2026/02/shenzhen-womens-open/",
        "score": 9,
        "summary": "女子滑板赛"
    }
]

# 写入 data.js
js_content = "const newsData = " + json.dumps(sample_data, ensure_ascii=False, indent=2) + ";\n"

with open("data.js", "w", encoding="utf-8") as f:
    f.write(js_content)

print("✅ 已生成测试用 data.js 文件！")
print(f"共 {len(sample_data)} 条滑板资讯")
print("\n现在可以打开 index.html 查看效果了！")
