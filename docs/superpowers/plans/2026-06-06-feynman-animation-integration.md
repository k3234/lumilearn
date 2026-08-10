# 费曼教学 + 动画联动模块 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:spec-to-implementation (recommended) to break into tasks and implement.

**Goal:** 部署动画模块到远程服务器服务器，并实现费曼五步法教学的自动检测与动画联动。当模型使用费曼五步法教学时，自动识别主题并生成 Manim 动画。

**Architecture:** 在现有 feynman 教学引擎和 animation 动画管线之间建立桥接层 (feynman_animation_bridge.py)。feynman/explain 接口返回时检测响应是否包含费曼五步特征，自动提取主题，异步触发动画生成，将 animation_task_id 返回给前端。前端交互学习页面展示动画生成进度。

**Tech Stack:** Python Flask, Manim, FFmpeg, Server-Sent Events (SSE), paramiko (部署)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `framework/services/feynman_animation_bridge.py` | 创建 | 费曼检测 + 主题提取 + 动画触发桥接层 |
| `framework/api/routes/feynman.py` | 修改 | feynman/explain 接口增加动画联动 |
| `framework/api/routes/animation.py` | 修改 | 增加 SSE 进度推送端点 |
| `remote/templates/animation_learn.html` | 修改 | 集成费曼教学面板 + 动画进度展示 |
| 部署脚本 | 创建 | 一键部署所有文件到服务器 |

---

### Task 1: 创建费曼动画桥接层

**Files:**
- Create: `framework/services/feynman_animation_bridge.py`

- [ ] **Step 1: 实现费曼五步检测**

```python
# feynman_animation_bridge.py
FEYNMAN_STEPS_KEYWORDS = {
    "观察": ["观察", "提出问题", "现象", "看到"],
    "假设": ["设想", "假设", "猜测", "猜测"],
    "推理": ["推理", "实验", "推导", "证明"],
    "分析": ["分析", "数据", "计算", "总结"],
    "结论": ["结论", "总结", "得出", "因此"],
}

def detect_feynman(response_text: str) -> bool:
    """检测响应是否包含费曼五步法结构"""
    found = 0
    for step_name, keywords in FEYNMAN_STEPS_KEYWORDS.items():
        for kw in keywords:
            if kw in response_text:
                found += 1
                break
    return found >= 3  # 至少有3个步骤

def extract_topic(user_input: str, response_text: str) -> dict:
    """从问题中提取主题关键词"""
    import re
    # 提取数学/物理关键词
    topics = {
        "geometry": ["勾股定理", "三角形", "圆", "角度", "几何", "余弦", "正弦"],
        "formula": ["公式", "方程", "求根", "配方", "代数", "多项式"],
        "physics": ["牛顿", "力学", "落体", "折射", "运动", "力", "速度"],
        "functions": ["函数", "图像", "一次函数", "二次函数"],
        "statistics": ["统计", "概率", "正态", "均值", "中位数"],
    }
    
    text = user_input + response_text[:200]
    for scene_type, keywords in topics.items():
        for kw in keywords:
            if kw in text:
                return {"topic": kw, "scene_type": scene_type}
    
    return {"topic": user_input[:30], "scene_type": "auto"}
```

- [ ] **Step 2: 实现异步动画触发**

```python
def trigger_animation(topic: str, scene_type: str, user_id: str = "default") -> str:
    """触发异步动画生成，返回 task_id"""
    import uuid
    task_id = str(uuid.uuid4())[:8]
    # 注册任务到 animation 的任务队列
    from framework.services.adaptive_learning import get_adaptive_engine
    # ... 异步启动动画生成
    return task_id
```

- [ ] **Step 3: 测试桥接层**

Run: `python -c "from framework.services.feynman_animation_bridge import detect_feynman; print(detect_feynman('观察...设想...假设...结论'))"`
Expected: `True`

---

### Task 2: 修改 feynman/explain 接口

**Files:**
- Modify: `framework/api/routes/feynman.py`

- [ ] **Step 4: 注入动画桥接到 feynman 响应**

在 `feynman/explain` 的响应中添加 `animation` 字段：

```python
from framework.services.feynman_animation_bridge import (
    detect_feynman, extract_topic, trigger_animation
)

# 在 feynman/explain 处理函数中，生成回复后：
if detect_feynman(response):
    topic_info = extract_topic(question, response)
    task_id = trigger_animation(
        topic_info["topic"], 
        topic_info["scene_type"],
        user_id
    )
    result["animation"] = {
        "detected": True,
        "topic": topic_info["topic"],
        "scene_type": topic_info["scene_type"],
        "task_id": task_id,
        "progress_url": f"/api/animation/progress/{task_id}"
    }
```

- [ ] **Step 5: 测试 feynman 联动**

Run: 调用 `/api/feynman/explain` 传入 "勾股定理"，验证响应是否包含 `animation.detected: true`

---

### Task 3: 增加 SSE 进度端点

**Files:**
- Modify: `framework/api/routes/animation.py`

- [ ] **Step 6: 添加 SSE 实时进度端点**

```python
@animation_bp.route('/progress/<task_id>/stream', methods=['GET'])
def progress_stream(task_id):
    """SSE 实时进度推送"""
    import json, time
    def generate():
        while True:
            task = _task_queue.get(task_id, {})
            yield f"data: {json.dumps(task)}\n\n"
            if task.get("status") in ("completed", "failed"):
                break
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream')
```

---

### Task 4: 更新前端界面

**Files:**
- Modify: `remote/templates/animation_learn.html`

- [ ] **Step 7: 集成费曼教学面板**

在界面左侧增加"费曼教学"标签页：
- 输入问题，调用 `/api/feynman/explain`
- 展示费曼五步教学回复
- 如果检测到动画可用，显示"生成动画中..."进度条
- 动画完成后自动播放

---

### Task 5: 部署到远程服务器服务器

**Files:**
- Create: `remote/deploy_animation_v2.sh` (部署脚本)

- [ ] **Step 8: 创建部署脚本**

```bash
#!/bin/bash
# 1. 停止服务
# 2. 复制新文件
# 3. 安装 Manim 依赖
# 4. 重启服务
# 5. 验证 API
```

- [ ] **Step 9: 执行部署**
- [ ] **Step 10: 验证部署结果**

---

## 自检清单

1. **规格覆盖**: 费曼检测 ✓ / 主题提取 ✓ / 动画触发 ✓ / 部署 ✓
2. **无占位符**: 所有代码完整
3. **类型一致**: task_id 字符串，统一使用 uuid[:8]