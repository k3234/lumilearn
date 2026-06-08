# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 学习资源搜索服务
通过搜索API和网页抓取，获取学习相关资源链接

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-01
"""

import re
import json
import time
import hashlib
import logging
import requests
from urllib.parse import quote_plus
from typing import Any, Dict, List, Optional

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

from lumilearn_shared import call_ollama

logger = logging.getLogger("lumilearn.resource_service")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

CATEGORIES = ["math", "english", "physics", "general", "chinese"]

PRESET_RESOURCES = {
    "math": [
        {
            "title": "Khan Academy - 数学课程",
            "url": "https://www.khanacademy.org/math",
            "snippet": "全球最大的免费在线学习平台，涵盖从基础算术到高等数学的完整课程体系，配有视频讲解和交互式练习。"
        },
        {
            "title": "3Blue1Brown - 数学可视化",
            "url": "https://www.3blue1brown.com/",
            "snippet": "以精美的动画可视化讲解线性代数、微积分、概率论等高等数学概念，帮助建立数学直觉。"
        },
        {
            "title": "Desmos - 在线图形计算器",
            "url": "https://www.desmos.com/calculator?lang=zh-CN",
            "snippet": "强大的在线图形计算器，支持函数作图、几何构造、数据分析，适合探索数学概念的可视化工具。"
        },
        {
            "title": "Brilliant - 数学与科学互动学习",
            "url": "https://brilliant.org/courses/#/math",
            "snippet": "通过互动式问题驱动的学习方式，培养数学思维和问题解决能力，覆盖代数、几何、数论等领域。"
        },
        {
            "title": "中国大学MOOC - 数学课程",
            "url": "https://www.icourse163.org/category/math",
            "snippet": "国内顶尖高校（清华、北大等）的数学课程，包括高等数学、线性代数、概率统计等，免费学习。"
        }
    ],
    "english": [
        {
            "title": "BBC Learning English",
            "url": "https://www.bbc.co.uk/learningenglish/",
            "snippet": "BBC出品的免费英语学习平台，提供地道英式英语的新闻、语法、词汇、发音等多媒体课程。"
        },
        {
            "title": "VOA Learning English",
            "url": "https://learningenglish.voanews.com/",
            "snippet": "美国之音慢速英语，用简化的词汇和语速播报新闻，适合英语中级学习者提高听力和阅读能力。"
        },
        {
            "title": "Duolingo - 多语言学习",
            "url": "https://www.duolingo.com/course/en/zh/Learn-English",
            "snippet": "游戏化的语言学习应用，通过每日短时练习积累词汇和语法，适合英语初学者建立学习习惯。"
        },
        {
            "title": "Cambridge Dictionary",
            "url": "https://dictionary.cambridge.org/",
            "snippet": "剑桥在线词典，提供单词的英英释义、例句、发音和学习资源，是英语学习者的必备工具。"
        },
        {
            "title": "TED Talks - 英语演讲",
            "url": "https://www.ted.com/talks?language=en",
            "snippet": "TED演讲平台，提供各类主题的英文演讲视频，配有中英文字幕，适合练习听力和扩展知识面。"
        }
    ],
    "physics": [
        {
            "title": "PhET - 物理交互模拟",
            "url": "https://phet.colorado.edu/zh_CN/simulations/filter?subjects=physics",
            "snippet": "科罗拉多大学开发的免费交互式物理模拟，通过可视化实验理解力学、电磁学、光学等物理概念。"
        },
        {
            "title": "Khan Academy - 物理课程",
            "url": "https://www.khanacademy.org/science/physics",
            "snippet": "涵盖经典力学、电磁学、热力学、量子物理等完整物理课程，配有视频讲解和练习。"
        },
        {
            "title": "费曼物理学讲义在线",
            "url": "https://www.feynmanlectures.caltech.edu/",
            "snippet": "诺贝尔奖得主费曼的经典物理学讲义，以独特的视角和深刻的洞察力讲解物理学基本原理。"
        },
        {
            "title": "中国大学MOOC - 物理课程",
            "url": "https://www.icourse163.org/category/physics",
            "snippet": "国内顶尖高校的大学物理课程，包括力学、电磁学、热学、光学和近代物理等内容。"
        },
        {
            "title": "The Physics Classroom",
            "url": "https://www.physicsclassroom.com/",
            "snippet": "面向中学生的物理学习网站，通过教程、模拟和练习题帮助理解物理概念和解题方法。"
        }
    ],
    "chinese": [
        {
            "title": "B站教育频道",
            "url": "https://www.bilibili.com/v/channel/learn",
            "snippet": "哔哩哔哩学习频道，汇集了大量优质的UP主教育内容，覆盖数学、物理、英语、编程等各学科。"
        },
        {
            "title": "中国大学MOOC",
            "url": "https://www.icourse163.org/",
            "snippet": "国内最大的中文MOOC平台，汇集清华、北大等顶尖高校的免费在线课程，支持证书获取。"
        },
        {
            "title": "学堂在线",
            "url": "https://www.xuetangx.com/",
            "snippet": "清华大学发起的中文MOOC平台，提供大量高质量的大学课程，涵盖理科、工科、文科等多个领域。"
        },
        {
            "title": "网易公开课",
            "url": "https://open.163.com/",
            "snippet": "网易推出的公开课平台，汇集国内外名校公开课和TED演讲的中文翻译版本。"
        },
        {
            "title": "Wikipedia 中文版",
            "url": "https://zh.wikipedia.org/",
            "snippet": "维基百科中文版，作为学习参考资料查询基本概念、定理和历史背景的可靠来源。"
        }
    ],
    "general": [
        {
            "title": "Coursera",
            "url": "https://www.coursera.org/",
            "snippet": "全球最大的在线课程平台，与世界顶尖大学合作提供各类课程，支持免费旁听和付费证书。"
        },
        {
            "title": "edX",
            "url": "https://www.edx.org/",
            "snippet": "哈佛和MIT联合创立的在线课程平台，提供高质量的大学水平课程，涵盖广泛的学科领域。"
        },
        {
            "title": "Wikipedia",
            "url": "https://en.wikipedia.org/",
            "snippet": "全球最大的免费百科全书，作为基础知识查询和学术研究的起点，内容经过社区审核。"
        },
        {
            "title": "GitHub - 开源学习资源",
            "url": "https://github.com/topics/education",
            "snippet": "GitHub上的教育主题仓库，汇集了大量开源的学习资料、课程笔记和编程练习题。"
        },
        {
            "title": "YouTube 教育频道",
            "url": "https://www.youtube.com/education",
            "snippet": "YouTube教育专区，汇集Crash Course、Kurzgesagt等优质教育频道的科普和学习内容。"
        }
    ]
}

CATEGORY_KEYWORDS = {
    "math": ["数学", "代数", "几何", "微积分", "线性代数", "概率",
             "math", "calculus", "algebra", "geometry"],
    "english": ["英语", "英文", "语法", "词汇", "听力", "口语",
                "english", "grammar", "vocabulary", "listening"],
    "physics": ["物理", "力学", "电磁学", "光学", "热力学", "量子",
                "physics", "mechanics", "electromagnetism"],
    "chinese": ["语文", "中文", "写作", "阅读", "古诗词", "文言文", "作文"],
    "general": []
}


class ResourceService:
    """
    学习资源搜索服务

    功能：
    - 多源搜索（DuckDuckGo/Bing）
    - 预设资源降级
    - AI摘要生成
    - 结果缓存
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600

    def _build_query(self, query: str, category: str = "general") -> str:
        """构建分类搜索关键词"""
        keywords = CATEGORY_KEYWORDS.get(category, [])
        if keywords:
            best_kw = keywords[0]
            for kw in keywords[3:]:
                if kw in query.lower():
                    best_kw = kw
                    break
            return f"{best_kw} {query} 学习资源"
        return f"{query} 学习资源 site:edu OR site:org"

    def _get_cached(self, cache_key: str):
        """读取缓存"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() - entry["time"] < self._cache_ttl:
                return entry["data"]
        return None

    def _set_cache(self, cache_key: str, data):
        """写入缓存"""
        self._cache[cache_key] = {"data": data, "time": time.time()}
        if len(self._cache) > 50:
            oldest = min(self._cache.keys(),
                         key=lambda k: self._cache[k]["time"])
            del self._cache[oldest]

    def _search_duckduckgo_html(self, query: str,
                                max_results: int = 5) -> List[Dict]:
        """通过 DuckDuckGo HTML 搜索"""
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query, "kl": "cn-zh"}
        try:
            resp = self._session.post(url, data=params, timeout=10)
            resp.raise_for_status()
        except Exception:
            return []

        if not HAS_BS4:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select(".result")[:max_results]:
            title_el = item.select_one(".result__title a")
            snippet_el = item.select_one(".result__snippet")
            if title_el:
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                if link and title:
                    results.append({
                        "title": title, "url": link, "snippet": snippet
                    })
        return results

    def _search_bing(self, query: str, max_results: int = 5) -> List[Dict]:
        """通过必应搜索"""
        url = "https://www.bing.com/search"
        params = {"q": query, "setlang": "zh-Hans", "count": max_results}
        try:
            resp = self._session.get(url, params=params, timeout=10)
            resp.raise_for_status()
        except Exception:
            return []

        if not HAS_BS4:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select("li.b_algo")[:max_results]:
            title_el = item.select_one("h2 a")
            snippet_el = item.select_one(".b_caption p")
            if title_el:
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                if link and title:
                    results.append({
                        "title": title, "url": link, "snippet": snippet
                    })
        return results

    def _fallback_preset_resources(self, query: str, category: str,
                                   max_results: int) -> List[Dict]:
        """降级方案：返回预设资源"""
        resources = PRESET_RESOURCES.get(category, PRESET_RESOURCES["general"])
        if category not in PRESET_RESOURCES and category != "general":
            general = PRESET_RESOURCES.get("general", [])
            resources = list(resources) + list(general)

        query_lower = query.lower()
        scored = []
        for r in resources:
            score = 0
            title_lower = r["title"].lower()
            snippet_lower = r["snippet"].lower()
            for word in query_lower.split():
                if word in title_lower:
                    score += 3
                if word in snippet_lower:
                    score += 1
            scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:max_results]]

    def search(self, query: str, category: str = "general",
               max_results: int = 5) -> List[Dict]:
        """
        搜索学习资源

        参数：
            query: 搜索关键词
            category: 分类（math/english/physics/chinese/general）
            max_results: 最大结果数

        返回：
            [{"title": "...", "url": "...", "snippet": "..."}, ...]
        """
        cache_key = f"{category}:{query}:{max_results}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        search_query = self._build_query(query, category)
        results = []

        try:
            results = self._search_duckduckgo_html(search_query, max_results)
        except Exception:
            pass

        if not results:
            try:
                results = self._search_bing(search_query, max_results)
            except Exception:
                pass

        if not results:
            results = self._fallback_preset_resources(query, category,
                                                       max_results)
        elif len(results) < max_results:
            preset = self._fallback_preset_resources(
                query, category, max_results - len(results)
            )
            existing_urls = {r["url"] for r in results}
            for p in preset:
                if p["url"] not in existing_urls:
                    results.append(p)
                if len(results) >= max_results:
                    break

        self._set_cache(cache_key, results)
        return results[:max_results]

    def summarize_resources(self, resources: List[Dict],
                            query: str) -> Dict[str, Any]:
        """
        使用本地Ollama模型对搜索结果进行AI摘要

        参数：
            resources: 搜索结果列表
            query: 原始查询关键词

        返回：
            {"summary": "...", "key_points": [...], "suggested_order": [...]}
        """
        if not resources:
            return {
                "summary": "未找到相关学习资源。",
                "key_points": [],
                "suggested_order": []
            }

        resource_text = ""
        for i, r in enumerate(resources, 1):
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            resource_text += f"{i}. {title}\n   摘要: {snippet}\n"

        prompt = f"""你是一位学习资源推荐专家。请分析以下搜索结果，为学习者提供结构化摘要。

【学习者查询】
{query}

【搜索结果】
{resource_text}

请以JSON格式返回分析结果：
```json
{{
  "summary": "一句话概述这些资源对学习'{query}'的价值（不超过50字）",
  "key_points": ["关键知识点1", "关键知识点2", "关键知识点3"],
  "suggested_order": ["建议最先学习的资源标题1", "建议其次学习的资源标题2"]
}}
```

只返回JSON，不要任何额外文字。"""

        try:
            response = call_ollama("qwen2.5:7b", prompt, timeout=60)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                return {
                    "summary": result.get("summary", ""),
                    "key_points": result.get("key_points", []),
                    "suggested_order": result.get("suggested_order", [])
                }
        except Exception as e:
            logger.error(f"AI摘要生成失败: {e}")

        return {
            "summary": f"共找到 {len(resources)} 个与'{query}'相关的学习资源。",
            "key_points": [r["title"][:30] for r in resources[:3]],
            "suggested_order": [r["title"][:30] for r in resources[:2]]
        }

    def search_with_summary(self, query: str, category: str = "general",
                            max_results: int = 5) -> Dict[str, Any]:
        """一站式搜索+摘要"""
        resources = self.search(query, category=category,
                                max_results=max_results)
        summary = self.summarize_resources(resources, query)
        return {
            "resources": resources,
            "summary": summary
        }


_resource_service_instance: Optional[ResourceService] = None


def get_resource_service() -> ResourceService:
    """获取ResourceService单例"""
    global _resource_service_instance
    if _resource_service_instance is None:
        _resource_service_instance = ResourceService()
    return _resource_service_instance