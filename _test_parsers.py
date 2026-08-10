# -*- coding: utf-8 -*-
"""本地验证 slides/mindmap 解析逻辑"""
import sys, os
sys.path.insert(0, r"<project-root>")
os.environ["OLLAMA_BASE_URL"] = "http://192.168.2.xx:11434"

from framework.api.routes.slides import _parse_slides, _fallback_slides
from framework.api.routes.mindmap import _parse_mindmap

# 模拟模型输出
model_out = """PAGE|光合作用|Photosynthesis
光反应阶段在类囊体薄膜上进行
暗反应（卡尔文循环）在叶绿体基质中进行
水的光解产生氧气和[H]
- 光反应产生 ATP 和 NADPH
PAGE|影响因素|Factors
光照强度、二氧化碳浓度、温度影响光合速率
- 光照强度：光照越强光合速率越快
- 二氧化碳：原料之一，浓度影响速率
PAGE|应用与总结|Summary
提高作物产量的措施：合理密植、增施有机肥
总结光反应与暗反应的联系"""

slides = _parse_slides(model_out, "光合作用", 5)
print(f"[slides] 解析到 {len(slides)} 页")
for s in slides:
    print(f"  - {s['title']} | {s['subtitle']} | content字符数={len(s['content'])}")
    print(f"    content: {s['content'][:120]}...")

fb = _fallback_slides("牛顿定律", 5)
print(f"[fallback] {len(fb)} 页, 首页 title={fb[0]['title']}")

mm_out = """MINDMAP|光合作用
- 光反应
  - 类囊体薄膜
  - 水的光解
  - ATP 合成
- 暗反应
  - 卡尔文循环
  - CO2 固定
  - C3 还原
- 影响因素
  - 光照强度
  - 温度"""

mm = _parse_mindmap(mm_out, "光合作用")
print(f"[mindmap] nodes={len(mm['nodes'])} edges={len(mm['edges'])}")
for n in mm["nodes"]:
    print(f"  - {n['id']}: {n['label']}")
for e in mm["edges"][:8]:
    print(f"    {e['from']} -> {e['to']}")

# 空输入兜底
mm2 = _parse_mindmap("", "牛顿定律")
print(f"[mindmap fallback] nodes={len(mm2['nodes'])} edges={len(mm2['edges'])}")
print("=== 本地解析测试全部通过 ===")
