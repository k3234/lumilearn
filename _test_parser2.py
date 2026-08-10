# -*- coding: utf-8 -*-
"""用真实模型输出测试宽松解析器"""
import sys, os
sys.path.insert(0, r"<project-root>")

from framework.api.routes.slides import _parse_slides

# 真实模型输出（markdown 风格，无 PAGE| 格式）
real_output = """### 牛顿第二定律：探究与应用
#### 力的独立作用原理
1. **概念讲解**：
   - 一个物体受到多个力的作用，如果这些力产生的效果相等，则称它们是作用在同一个物体上的同一相互作用力。
2. **例题分析**：
   - 题目：质量为 m 的小车在水平面上受三个共点力 F1、F2 和 F3 作用而保持匀速直线运动。
   - 解答：合力为零，F3 = -(F1 + F2)。
#### 运动学与力学结合
3. **公式推导**：
   - 根据牛顿第二定律和运动学基本公式推导匀变速直线运动公式：v = v0 + at。
4. **例题分析**：
   - 汽车以 15 m/s 刹车后 6 s 停止，求加速度和刹车距离。
### 课堂小结与思考
1. 牛顿第二定律的瞬时性与恒定性。
2. 应用关键点：正确受力分析、选择适当公式。
3. 总结：揭示力与运动的本质联系。"""

slides = _parse_slides(real_output, "牛顿第二定律", 5)
print(f"[markdown 解析] {len(slides)} 页")
for s in slides:
    print(f"  - {s['title']} | content={len(s['content'])}字符")
    print(f"    {s['content'][:100]}")

# 无标题纯文本
plain = "牛顿第二定律：F=ma。力是改变物体运动状态的原因。质量是惯性的量度。应用：汽车刹车、火箭发射。练习：求合力。"
slides2 = _parse_slides(plain, "牛顿第二定律", 5)
print(f"\n[纯文本均分] {len(slides2)} 页")
for s in slides2:
    print(f"  - {s['title']} | {s['content'][:60]}")

print("\n=== 测试完成 ===")
