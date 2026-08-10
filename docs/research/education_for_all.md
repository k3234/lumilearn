# LumiLearn 教育普惠方案

## 让每个孩子都能获得优质教育资源

> 方案日期：2026-06-03
> 核心目标：**落后地区 + 本地运行 + 最低配置 + 最高性能**
> 愿景：让每个孩子，无论身在何处，都能获得优质教育资源

---

## 一、核心理念

### 1.1 使命宣言

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   🌏 让每个孩子，无论身在何处，都能获得优质教育资源                     │
│                                                                     │
│   📱 即使没有网络                                                     │
│   💻 即使只有一部老旧手机或电脑                                        │
│   🧠 也能获得接近发达地区水平的 AI 教育                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 目标用户画像

| 用户类型 | 场景 | 设备条件 | 网络条件 |
|----------|------|----------|----------|
| **山区学生** | 家中学习 | 老旧手机/电脑 | 无网络 |
| **留守儿童** | 爷爷奶奶照看 | 低端手机 | 偶尔有网 |
| **贫困地区学校** | 机房学习 | Windows XP 电脑 | 局域网 |
| **海外华人子女** | 海外学习中文 | 任意设备 | 不稳定 |

### 1.3 核心约束

| 约束 | 说明 | 解决方案 |
|------|------|----------|
| **硬件极低** | 1GB RAM / 低端 CPU | 极致量化 + 高效推理 |
| **无网络** | 离线优先 | 本地模型 + 预置内容 |
| **电费敏感** | 落后地区电价高 | CPU/GPU 优化 + 批处理 |
| **维护困难** | 无技术人员 | 零配置 + 自恢复 |
| **内容适配** | 方言/本地化 | 预置多语言内容 |

---

## 二、硬件分级方案

### 2.1 设备分级标准

| 等级 | 设备类型 | RAM | CPU | 存储 | GPU |
|------|----------|-----|-----|------|-----|
| **Tier 0** | 老年机/树莓派 | 512MB | 1核 | 4GB | ❌ |
| **Tier 1** | 低端安卓机 | 1GB | 2核 | 8GB | ❌ |
| **Tier 2** | 老旧笔记本 | 2GB | 2核 | 32GB | ❌ |
| **Tier 3** | 普通笔记本 | 4GB | 4核 | 64GB | 780M |
| **Tier 4** | 游戏本 | 8GB | 8核 | 256GB | RTX 3060+ |

### 2.2 推荐的模型选择

| 等级 | 推荐模型 | 参数量 | 量化 | 内存需求 | 推理速度 |
|------|----------|--------|------|----------|----------|
| **Tier 0** | Phi-1.5 / Qwen1.8B | 1.8B | Q4 | ~1GB | ⚡⚡⚡ |
| **Tier 1** | Qwen2-2B / Phi-2 | 2B | Q4 | ~1.5GB | ⚡⚡⚡ |
| **Tier 2** | Qwen2.5-3B | 3B | Q4_K_M | ~2GB | ⚡⚡ |
| **Tier 3** | Qwen2.5-7B | 7B | Q4_K_M | ~4GB | ⚡ |
| **Tier 4** | Qwen2.5-14B | 14B | Q4_K_M | ~8GB | ⚡⚡ |

### 2.3 推理框架选择

| 框架 | CPU 优化 | GPU 支持 | 包大小 | Tier 0-2 推荐度 |
|------|----------|----------|--------|-----------------|
| **llama.cpp** | ⭐⭐⭐⭐⭐ | ✅ | 30MB | ⭐⭐⭐⭐⭐ |
| **llamafile** | ⭐⭐⭐⭐⭐ | ✅ | ~200MB | ⭐⭐⭐⭐ |
| **MNN** | ⭐⭐⭐⭐⭐ | ❌ | 10MB | ⭐⭐⭐⭐⭐ |
| **NCNN** | ⭐⭐⭐⭐ | ❌ | 20MB | ⭐⭐⭐⭐ |
| **TensorFlow Lite** | ⭐⭐⭐⭐ | ✅ | 5MB | ⭐⭐⭐ |

---

## 三、教育内容分级

### 3.1 内容分层

```
教育内容分层架构
┌─────────────────────────────────────────────────────────────────────┐
│                        L5: AI 个性化辅导                             │
│                    (需要 Tier 3-4 设备，复杂推理)                   │
├─────────────────────────────────────────────────────────────────────┤
│                        L4: 互动练习+反馈                            │
│                    (需要 Tier 2+ 设备，实时反馈)                    │
├─────────────────────────────────────────────────────────────────────┤
│                        L3: 课程+测验                                │
│                    (Tier 1+ 设备，基础 AI)                         │
├─────────────────────────────────────────────────────────────────────┤
│                        L2: 预置课程内容                             │
│                    (Tier 0+ 设备，纯本地内容)                        │
├─────────────────────────────────────────────────────────────────────┤
│                        L1: 文本+图片                                │
│                    (任何设备，静态内容)                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 内容包设计

| 内容包 | 大小 | 内容 | 适用等级 |
|--------|------|------|----------|
| **核心包** | 100MB | 语文/数学基础 + AI 引擎 | Tier 0+ |
| **扩展包** | 200MB | 英语/科学 + 练习题 | Tier 1+ |
| **高级包** | 500MB | 物理/化学 + 实验模拟 | Tier 2+ |
| **AI 增强** | 2GB | 本地大模型 (Q4) | Tier 3+ |
| **完整包** | 4GB | 所有内容 + 本地 AI | Tier 4 |

---

## 四、性能优化技术

### 4.1 模型优化

```python
# llama.cpp 量化命令示例
# 将 FP16 模型转为 Q4_K_M 量化

llama-quantize.exe ^
  models/qwen2.5-7b-fp16.gguf ^
  models/qwen2.5-7b-q4_k_m.gguf ^
  q4_k_m

# 参数说明：
# q4_k_m: 4位量化，平衡质量和大小
# q5_k_m: 5位量化，更高质量但更大
# q8_0:   8位量化，最高质量
```

### 4.2 推理优化

| 技术 | 效果 | 适用场景 |
|------|------|----------|
| **KV Cache** | 加速 3-5x | 多轮对话 |
| **批量处理** | 吞吐提升 10x | 多用户 |
| **Flash Attention** | 内存减半 | 长上下文 |
| **Speculative Decoding** | 加速 2x | 生成任务 |
| **Pruning** | 模型压缩 30% | 所有场景 |

### 4.3 分层降级策略

```python
class TieredInference:
    """分层降级推理策略"""

    def __init__(self, device_tier):
        self.tier = device_tier

    def get_response(self, query):
        if self.tier >= 3:
            # Tier 3-4: 使用本地大模型
            return self.local_llm(query)
        elif self.tier >= 2:
            # Tier 2: 使用本地小模型
            return self.local_small(query)
        elif self.tier >= 1:
            # Tier 1: 使用预置规则 + 小模型
            return self.hybrid(query)
        else:
            # Tier 0: 纯预置内容
            return self.predefined(query)

    def get_tier_from_device(self):
        """自动检测设备等级"""
        import psutil
        ram = psutil.virtual_memory().total / (1024**3)  # GB

        if ram < 1:
            return 0
        elif ram < 2:
            return 1
        elif ram < 4:
            return 2
        elif ram < 8:
            return 3
        else:
            return 4
```

---

## 五、离线优先架构

### 5.1 分层网络策略

```
┌─────────────────────────────────────────────────────────────────────┐
│                         网络优先级                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Level 0: 完全离线                                                │
│  ├── 预置教育内容（100% 覆盖核心知识点）                            │
│  ├── 本地小模型（1-3B）                                           │
│  └── 基础练习题库                                                  │
│                                                                     │
│  Level 1: 偶尔联网                                                  │
│  ├── 同步学习进度到云端                                             │
│  ├── 下载新内容包                                                  │
│  └── 匿名使用统计                                                   │
│                                                                     │
│  Level 2: 持续联网                                                 │
│  ├── 使用云端大模型（复杂推理）                                      │
│  ├── 获取最新内容                                                   │
│  └── 在线社区讨论                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 内容预置策略

```python
class OfflineContentManager:
    """离线内容管理器"""

    def __init__(self):
        self.local_content = {}
        self.update_queue = []

    def preload_essential(self):
        """预置核心内容（无网络时使用）"""
        self.local_content = {
            # 语文
            "chinese_grade1": load_from_bundle("chinese_g1.zip"),
            "chinese_grade2": load_from_bundle("chinese_g2.zip"),
            # 数学
            "math_grade1": load_from_bundle("math_g1.zip"),
            "math_grade2": load_from_bundle("math_g2.zip"),
            # 英语
            "english_basic": load_from_bundle("english_basic.zip"),
        }

    def get_response(self, query, network_available=False):
        """智能选择内容来源"""
        if network_available:
            # 优先使用云端大模型
            return self.cloud_inference(query)
        else:
            # 使用本地内容 + 小模型
            return self.local_inference(query)
```

### 5.3 同步机制

```python
class SyncManager:
    """学习进度同步"""

    def sync_when_possible(self):
        """尽可能同步"""
        if not self.is_network_available():
            return

        # 1. 上传本地进度
        self.upload_progress()

        # 2. 下载新内容
        self.download_updates()

        # 3. 更新模型（如果有更好的）
        self.update_models()

    def offline_fallback(self):
        """离线降级"""
        return {
            "mode": "offline",
            "model": "local_small",
            "content": "preloaded",
            "sync_needed": True
        }
```

---

## 六、设备适配实现

### 6.1 自动设备检测

```python
def detect_device_capability():
    """检测设备能力"""
    import platform
    import psutil

    info = {
        "platform": platform.system(),
        "ram_gb": psutil.virtual_memory().total / (1024**3),
        "cpu_count": psutil.cpu_count(),
        "has_gpu": check_gpu(),
    }

    # 计算设备等级
    if info["ram_gb"] < 1:
        tier = 0
    elif info["ram_gb"] < 2:
        tier = 1
    elif info["ram_gb"] < 4:
        tier = 2
    elif info["ram_gb"] < 8:
        tier = 3
    else:
        tier = 4

    return {"tier": tier, **info}
```

### 6.2 自适应 UI

```python
class AdaptiveUI:
    """自适应界面"""

    def render(self, tier):
        if tier >= 3:
            return self.render_full()
        elif tier >= 2:
            return self.render_light()
        elif tier >= 1:
            return self.render_minimal()
        else:
            return self.render_text_only()

    def render_text_only(self):
        """文本模式（最低配置）"""
        return {
            "theme": "text",
            "images": False,
            "animations": False,
            "font_size": 16,
        }
```

---

## 七、部署方案

### 7.1 多平台部署

| 平台 | 包大小 | 安装难度 | 推荐场景 |
|------|--------|----------|----------|
| **Android APK** | 50MB | ⭐ | 手机 |
| **Windows EXE** | 100MB | ⭐ | 老旧电脑 |
| **Linux AppImage** | 80MB | ⭐⭐ | 学校机房 |
| **iOS IPA** | 100MB | ⭐ | iPhone |
| **Web APK** | 20MB | ⭐⭐⭐ | 浏览器 |

### 7.2 安装包设计

```bash
# Android APK 结构
LumiLearn_Edu.apk
├── assets/
│   ├── content_core.zip      # 核心内容（100MB）
│   ├── model_qwen2b_q4.gguf  # 本地模型（1.5GB）
│   └── lessons.json          # 课程数据
├── lib/
│   └── llama.cpp.so          # 本地推理引擎
└── res/
    └── launcher_icon.png
```

### 7.3 安装流程（零配置）

```
安装步骤：
1. 下载 APK（约 50MB）
2. 点击安装（无需 Root）
3. 首次运行，自动下载内容包
4. 选择离线模式
5. 开始学习！

全程无需登录、无需配置、插电即用
```

---

## 八、社会价值

### 8.1 影响力估算

| 指标 | 目标 |
|------|------|
| **覆盖地区** | 农村、山区、贫困地区 |
| **潜在用户** | 2亿+ 学生 |
| **教育公平** | 让每个孩子都能获得 AI 教育 |
| **SDG 贡献** | SDG 4（优质教育）、SDG 10（减少不平等） |

### 8.2 商业模式（可持续）

| 模式 | 说明 | 可行性 |
|------|------|--------|
| **公益免费** | 基础版完全免费 | ⭐⭐⭐⭐⭐ |
| **政府购买** | 政府教育部门采购 | ⭐⭐⭐⭐ |
| **企业赞助** | 企业 CSR 赞助 | ⭐⭐⭐ |
| **增值服务** | 高级功能付费 | ⭐⭐ |

### 8.3 合作机会

| 合作方 | 合作方式 |
|--------|----------|
| **教育部** | 纳入教育信息化工程 |
| **慈善基金会** | 资金支持 + 设备捐赠 |
| **运营商** | 定向流量优惠 |
| **设备厂商** | 预装合作 |
| **内容提供商** | 免费授权教材 |

---

## 九、里程碑

| 阶段 | 时间 | 目标 | 验证指标 |
|------|------|------|----------|
| **M1: MVP** | 2026.6 | 基础版上线 | 10个用户完成学习 |
| **M2: 优化** | 2026.9 | 性能优化 + 内容扩展 | 100个用户 |
| **M3: 试点** | 2026.12 | 1所农村学校试点 | 学生成绩提升 10% |
| **M4: 推广** | 2027.6 | 10所学校 | 1000个用户 |
| **M5: 规模化** | 2027.12 | 100所学校 | 10000个用户 |

---

## 十、行动路线

### 10.1 第一阶段：技术准备（本周）

```bash
# 1. 测试 llama.cpp 在极低配置下的运行
# 目标：512MB RAM 流畅运行

# 2. 下载最小模型
# Phi-1.5 (1.3B, Q4 量化，约 800MB)

# 3. 制作 Android 演示版
```

### 10.2 第二阶段：内容准备（本月）

```bash
# 1. 准备核心教育内容
# 语文：部编版 1-6 年级核心课文
# 数学：人教版 1-6 年级核心知识点
# 英语：基础词汇 1000 词

# 2. 制作离线内容包
```

### 10.3 第三阶段：试点验证（下月）

```bash
# 1. 联系 1 所农村学校
# 2. 安装试用
# 3. 收集反馈
# 4. 迭代优化
```

---

## 十一、总结

### 11.1 核心理念

```
让 AI 教育像水电一样普及
├── 任何人
├── 任何设备
├── 任何地方
└── 都能获得
```

### 11.2 技术路线

```
最低配置：512MB RAM + 4GB 存储
├── Tier 0: Phi-1.5-Q4 (800MB) + 预置内容
├── 推理速度：3-5 tokens/s
└── 功能：文本问答 + 基础练习

目标配置：2GB RAM + 16GB 存储
├── Tier 2: Qwen2.5-3B-Q4 (2GB) + 增强内容
├── 推理速度：5-10 tokens/s
└── 功能：AI 问答 + 课程讲解 + 练习反馈
```

### 11.3 愿景

> **不是让落后地区追赶上发达地区，而是让每个人都能够获得最适合自己的教育资源**

---

## 参考资料

- llama.cpp: https://github.com/ggerganov/llama.cpp
- llamafile: https://github.com/Mozilla-Ocho/llamafile
- Phi 模型: https://huggingface.co/microsoft/phi-1_5
- Qwen 模型: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
- LumiLearn: <project-root>\lumilearn