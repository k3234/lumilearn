# 动画生成教学模块实施计划

> **制定日期:** 2026-06-06
> **目标:** 为 LumiLearn 框架添加 AI 驱动的动画生成教学功能

---

## 一、技术方案

### 两条路线对比

| 方案 | 优势 | 劣势 | 推荐场景 |
|------|------|------|----------|
| **A: Manim** | 数学/物理公式动画，3Blue1Brown 风格，可编程控制 | 需要渲染，动画效果有限 | ✅ **首选**，精确控制 |
| **B: AI 视频生成** | 效果酷炫，生成快 | 不可控，中文支持差 | 辅助，通用场景 |

### 最终架构：混合方案

```
┌──────────────────────────────────────────────────────────────┐
│                   动画生成教学管线                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  用户提问                                                    │
│  "讲解勾股定理"                                             │
│       ↓                                                      │
│  ┌─────────────┐                                            │
│  │ AI 分析模块 │  → 拆解知识点、确定动画类型                  │
│  └─────────────┘                                            │
│       ↓                                                      │
│  ┌─────────────────────────────────────────┐                │
│  │ 动画代码生成                              │                │
│  │  ├─ Manim 代码（数学公式/几何图形）       │                │
│  │  └─ 旁白文案（配音用）                   │                │
│  └─────────────────────────────────────────┘                │
│       ↓                                                      │
│  ┌─────────────┐                                            │
│  │ 渲染引擎    │  → manim 渲染 PNG/MP4                       │
│  └─────────────┘                                            │
│       ↓                                                      │
│  ┌─────────────────────────────────────────┐                │
│  │ 音频合成                              │                │
│  │  ├─ TTS 配音（已有 voicebox_service）│                │
│  │  └─ 背景音乐（可选）                  │                │
│  └─────────────────────────────────────────┘                │
│       ↓                                                      │
│  ┌─────────────┐                                            │
│  │ FFmpeg 合成 │  → 音视频合并 + 字幕                       │
│  └─────────────┘                                            │
│       ↓                                                      │
│  输出: MP4 教学动画视频                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 二、文件结构设计

```
lumilearn/
├── framework/services/
│   ├── manim_service.py           ← 核心：Manim 动画服务
│   └── video_compiler.py          ← 视频编译服务
├── framework/api/routes/
│   └── animation.py               ← REST API 端点
├── animation/
│   ├── templates/                  ← 动画模板库
│   │   ├── geometry.py           # 几何图形动画
│   │   ├── algebra.py            # 代数/公式动画
│   │   ├── physics.py            # 物理过程动画
│   │   └── functions.py           # 函数/图像动画
│   ├── generators/               ← 代码生成器
│   │   ├── base.py               # 基类
│   │   ├── geometry_gen.py        # 几何生成器
│   │   ├── formula_gen.py        # 公式生成器
│   │   └── process_gen.py        # 过程动画生成器
│   ├── renderer.py               ← Manim 渲染器
│   └── pipeline.py               ← 完整管线
└── scripts/
    └── install_manim.sh          ← Manim 安装脚本
```

---

## 三、实施步骤

### Task 1: 环境准备与基础服务

**Files:**
- Create: `framework/services/manim_service.py`
- Create: `animation/renderer.py`
- Create: `scripts/install_manim.sh`

- [ ] **Step 1: 创建 Manim 安装脚本**

```bash
# scripts/install_manim.sh
#!/bin/bash
# Manim 依赖安装（Linux/服务器）

# 系统依赖
sudo apt-get update
sudo apt-get install -y ffmpeg texlive-full imagemagick libcairo2-dev pkg-config python3-dev

# Python 依赖
pip install manim pillow scipy

# 验证安装
python -c "import manim; print(manim.__version__)"
```

- [ ] **Step 2: 创建 Manim 服务类**

```python
# framework/services/manim_service.py
"""
Manim 动画生成服务
AI 生成动画代码 -> 渲染 -> 输出视频
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

class ManimService:
    """Manim 动画生成服务"""

    def __init__(
        self,
        output_dir: str = "output/animations",
        quality: str = "medium",  # low, medium, high, production
        fps: int = 30
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality
        self.fps = fps

    def render(self, manim_code: str, scene_name: str = "GeneratedScene") -> str:
        """
        渲染 Manim 动画

        Args:
            manim_code: Manim Python 代码
            scene_name: 场景类名

        Returns:
            输出视频文件路径
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入临时文件
            script_path = Path(tmpdir) / "scene.py"
            script_path.write_text(self._wrap_code(manim_code, scene_name))

            # 执行 manim 渲染
            cmd = [
                "manim",
                "-qm",  # medium quality
                "--fps", str(self.fps),
                "-o", scene_name,
                str(script_path),
                scene_name
            ]

            result = subprocess.run(
                cmd,
                cwd=tmpdir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                raise RuntimeError(f"Manim 渲染失败: {result.stderr}")

            # 移动输出
            output_file = Path(tmpdir) / "media" / "videos" / "scene" / "720p30fps" / f"{scene_name}.mp4"
            if output_file.exists():
                dest = self.output_dir / f"{scene_name}.mp4"
                shutil.copy(output_file, dest)
                return str(dest)

        raise RuntimeError("Manim 渲染未生成输出文件")
```

- [ ] **Step 3: 验证安装**

```bash
# 在服务器上执行
ssh kai@192.168.2.63 'bash /home/kai/lumilearn/scripts/install_manim.sh'
```

---

### Task 2: 动画代码生成器

**Files:**
- Create: `animation/generators/base.py`
- Create: `animation/generators/geometry_gen.py`
- Create: `animation/generators/formula_gen.py`

- [ ] **Step 1: 创建生成器基类**

```python
# animation/generators/base.py
"""动画代码生成器基类"""
from abc import ABC, abstractmethod
from typing import List, Dict

class AnimationGenerator(ABC):
    """动画生成器基类"""

    def __init__(self, model_client=None):
        self.model_client = model_client

    @abstractmethod
    def generate(self, topic: str, **kwargs) -> Dict[str, str]:
        """
        生成动画

        Returns:
            {
                "manim_code": "from manim import *\nclass...",
                "narration": "首先，画一个直角三角形...",
                "scene_type": "geometry"
            }
        """
        pass

    def build_prompt(self, topic: str, scene_type: str) -> str:
        """构建生成提示"""
        return f"""你是一位专业的数学动画制作师，擅长用 Manim 制作 3Blue1Brown 风格的动画。

任务：为"{topic}"生成一个 Manim 动画代码。

要求：
1. 代码必须是完整可运行的 Python 代码
2. 使用英文变量名，注释用中文
3. 动画时长控制在 30-60 秒
4. 包含完整的 construct 方法
5. 使用 LaTeX 显示数学公式

动画类型：{scene_type}

请生成以下内容：
1. Manim Python 代码
2. 旁白文案（用于配音）
"""
```

- [ ] **Step 2: 创建几何动画生成器**

```python
# animation/generators/geometry_gen.py
"""几何动画生成器"""
from .base import AnimationGenerator
from typing import Dict

class GeometryAnimationGenerator(AnimationGenerator):
    """几何动画生成器"""

    PROMPT_TEMPLATE = """为"{topic}"生成几何动画代码。

示例场景：
- 三角形相关：勾股定理、余弦定理
- 圆相关：圆的面积推导
- 多边形：正多边形的性质

动画结构：
1. 展示基本图形
2. 标注关键元素
3. 动态变换/推导
4. 得出结论

请生成完整代码：
```python
from manim import *

class {scene_name}(Scene):
    def construct(self):
        # 你的代码
```
"""

    def generate(self, topic: str, **kwargs) -> Dict[str, str]:
        """生成几何动画"""
        prompt = self.PROMPT_TEMPLATE.format(
            topic=topic,
            scene_name=kwargs.get("scene_name", "GeometryScene")
        )

        if self.model_client:
            response = self.model_client.generate(prompt)
            return self._parse_response(response)
        else:
            # 使用模板
            return self._default_geometric_animation(topic)

    def _default_geometric_animation(self, topic: str) -> Dict[str, str]:
        """默认几何动画（勾股定理示例）"""
        code = '''from manim import *
import numpy as np

class PythagoreanTheorem(Scene):
    """勾股定理动画"""

    def construct(self):
        # 标题
        title = Text("勾股定理", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))

        # 创建直角三角形
        triangle = Polygon(
            LEFT * 2 + DOWN * 2,
            RIGHT * 2 + DOWN * 2,
            LEFT * 2 + UP * 2,
            color=BLUE
        )
        self.play(Create(triangle))

        # 标注顶点
        labels = [
            Text("A", font_size=24).next_to(triangle.get_vertices()[0], DOWN + LEFT),
            Text("B", font_size=24).next_to(triangle.get_vertices()[1], DOWN),
            Text("C", font_size=24).next_to(triangle.get_vertices()[2], LEFT),
        ]
        for label in labels:
            self.play(Write(label))

        # 标注直角
        right_angle = RightAngle(
            Line(LEFT * 2 + DOWN * 2, RIGHT * 2 + DOWN * 2),
            Line(LEFT * 2 + DOWN * 2, LEFT * 2 + UP * 2),
            length=0.3
        )
        self.play(Create(right_angle))

        # 显示边长
        a_sq = MathTex("a^2", font_size=36).shift(LEFT * 3)
        b_sq = MathTex("b^2", font_size=36).shift(DOWN * 3)
        c_sq = MathTex("c^2", font_size=36).shift(RIGHT * 2 + UP * 2)

        self.play(Write(a_sq))
        self.play(Write(b_sq))
        self.play(Write(c_sq))

        # 公式
        formula = MathTex("a^2 + b^2 = c^2", font_size=60)
        formula.to_edge(DOWN)
        self.play(Write(formula))

        # 保持
        self.wait(2)
'''

        narration = """首先，我们画出一个直角三角形，标注三个顶点 A、B、C。
直角位于点 A。接下来，我们标注三条边的长度。
根据勾股定理，直角三角形的两条直角边平方和等于斜边平方。
这就是著名的勾股定理：a² + b² = c²。"""

        return {
            "manim_code": code,
            "narration": narration,
            "scene_type": "geometry"
        }
```

- [ ] **Step 3: 创建公式动画生成器**

```python
# animation/generators/formula_gen.py
"""公式动画生成器"""
from .base import AnimationGenerator
from typing import Dict

class FormulaAnimationGenerator(AnimationGenerator):
    """数学公式动画生成器"""

    def generate(self, topic: str, **kwargs) -> Dict[str, str]:
        """生成公式推导动画"""
        code = f'''from manim import *

class FormulaAnimation(Scene):
    """公式推导动画"""

    def construct(self):
        # 标题
        title = Text("{topic}", font_size=48)
        self.play(Write(title))
        self.wait()

        # 公式
        formula = MathTex("{self._topic_to_latex(topic)}", font_size=60)
        self.play(Write(formula))
        self.wait()

        # 推导步骤（根据 topic 动态生成）
        # ...
'''
        return {"manim_code": code, "narration": "", "scene_type": "formula"}

    def _topic_to_latex(self, topic: str) -> str:
        """将 topic 转换为 LaTeX"""
        mapping = {
            "求根公式": "x = \\frac{{-b \\pm \\sqrt{{b^2-4ac}}}}{{2a}}",
            "欧拉公式": "e^{{i\\pi}} + 1 = 0",
        }
        return mapping.get(topic, topic)
```

---

### Task 3: 完整动画管线

**Files:**
- Create: `animation/pipeline.py`
- Create: `framework/services/video_compiler.py`

- [ ] **Step 1: 创建完整管线**

```python
# animation/pipeline.py
"""
动画生成完整管线
AI 理解 -> 代码生成 -> 渲染 -> 配音 -> 合成
"""
import asyncio
from pathlib import Path
from typing import Optional
from .generators.geometry_gen import GeometryAnimationGenerator
from .generators.formula_gen import FormulaAnimationGenerator
from ..framework.services.manim_service import ManimService

class AnimationPipeline:
    """动画生成管线"""

    def __init__(
        self,
        manim_service: Optional[ManimService] = None,
        tts_service=None,  # 复用已有的 voicebox_service
    ):
        self.manim_service = manim_service or ManimService()
        self.tts_service = tts_service
        self.generators = {
            "geometry": GeometryAnimationGenerator(),
            "formula": FormulaAnimationGenerator(),
        }

    async def generate(self, topic: str, scene_type: str = "auto") -> Dict:
        """
        生成完整动画

        Args:
            topic: 教学主题，如"勾股定理"
            scene_type: 动画类型，"auto"时由 AI 判断

        Returns:
            {
                "video_path": "output/animations/pythagorean.mp4",
                "audio_path": "output/animations/pythagorean.mp3",
                "duration": 45.0,
                "scenes": [{"type": "geometry", "narration": "..."}]
            }
        """
        # Step 1: 选择生成器
        if scene_type == "auto":
            scene_type = self._detect_scene_type(topic)

        generator = self.generators.get(scene_type, GeometryAnimationGenerator())

        # Step 2: 生成动画代码和旁白
        result = generator.generate(topic)

        # Step 3: 渲染动画（后台）
        loop = asyncio.get_event_loop()
        video_path = await loop.run_in_executor(
            None,
            self.manim_service.render,
            result["manim_code"],
            topic
        )

        # Step 4: TTS 配音
        audio_path = None
        if self.tts_service and result["narration"]:
            audio_path = await self.tts_service.synthesize(
                text=result["narration"],
                voice="ai_teacher"
            )

        # Step 5: 音视频合成
        if audio_path:
            final_path = await self._compile(video_path, audio_path)
        else:
            final_path = video_path

        return {
            "video_path": str(final_path),
            "audio_path": audio_path,
            "narration": result["narration"],
            "scene_type": result["scene_type"],
        }

    def _detect_scene_type(self, topic: str) -> str:
        """根据 topic 自动判断动画类型"""
        geometry_keywords = ["三角形", "圆", "四边形", "勾股", "几何", "面积", "角度"]
        formula_keywords = ["公式", "方程", "求根", "推导", "证明"]

        for kw in geometry_keywords:
            if kw in topic:
                return "geometry"
        for kw in formula_keywords:
            if kw in topic:
                return "formula"
        return "geometry"  # 默认几何

    async def _compile(self, video_path: str, audio_path: str) -> str:
        """FFmpeg 合成音视频"""
        output_path = video_path.replace(".mp4", "_with_audio.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

        return output_path
```

- [ ] **Step 2: 创建视频编译服务**

```python
# framework/services/video_compiler.py
"""视频编译服务"""
import subprocess
from pathlib import Path
from typing import List

class VideoCompiler:
    """FFmpeg 视频编译服务"""

    @staticmethod
    def merge_clips(clips: List[str], output: str) -> str:
        """合并多个视频片段"""
        # 生成文件列表
        list_file = Path(output).parent / "concat_list.txt"
        list_file.write_text("\n".join(f"file '{c}'" for c in clips))

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            output
        ]
        subprocess.run(cmd, check=True)
        return output

    @staticmethod
    def add_subtitles(video: str, srt_file: str, output: str) -> str:
        """添加字幕"""
        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-vf", f"subtitles={srt_file}",
            output
        ]
        subprocess.run(cmd, check=True)
        return output
```

---

### Task 4: API 端点

**Files:**
- Create: `framework/api/routes/animation.py`
- Modify: `framework/api/server.py` (注册路由)

- [ ] **Step 1: 创建 API 端点**

```python
# framework/api/routes/animation.py
"""动画生成 API 路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from ...services.manim_service import ManimService
from ...services.video_compiler import VideoCompiler

router = APIRouter(prefix="/api/animation", tags=["animation"])

class AnimationRequest(BaseModel):
    topic: str                    # 教学主题
    scene_type: str = "auto"      # 动画类型
    duration: Optional[int] = 60  # 时长（秒）
    include_audio: bool = True    # 是否配音

class AnimationResponse(BaseModel):
    video_url: str
    audio_url: Optional[str]
    duration: float
    narration_text: str

@router.post("/generate", response_model=AnimationResponse)
async def generate_animation(request: AnimationRequest):
    """生成教学动画"""
    try:
        # TODO: 调用 AnimationPipeline
        # pipeline = AnimationPipeline()
        # result = await pipeline.generate(request.topic, request.scene_type)

        return AnimationResponse(
            video_url=f"/output/animations/{request.topic}.mp4",
            audio_url=f"/output/animations/{request.topic}.mp3",
            duration=45.0,
            narration_text="旁白文案..."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
async def list_templates():
    """列出可用的动画模板"""
    return {
        "templates": [
            {"id": "geometry", "name": "几何图形", "description": "三角形、圆、多边形"},
            {"id": "formula", "name": "公式推导", "description": "数学公式动态展示"},
            {"id": "physics", "name": "物理过程", "description": "物理过程动画"},
            {"id": "functions", "name": "函数图像", "description": "函数图像绘制与变换"},
        ]
    }
```

- [ ] **Step 2: 注册路由**

```python
# framework/api/server.py (添加)
from .routes.animation import router as animation_router

app.include_router(animation_router)
```

---

## 四、Manim 安装指南

### 服务器端安装（192.168.2.63）

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y ffmpeg texlive-full imagemagick libcairo2-dev pkg-config python3-dev

# 安装 Manim
pip install manim pillow scipy

# 验证
python -c "import manim; print(manim.__version__)"
```

### Windows 本地开发

```powershell
# 使用 WSL2 或 Docker
# 推荐 WSL2
wsl --install

# 在 WSL2 中安装
sudo apt-get install ffmpeg texlive-full
pip install manim
```

---

## 五、使用示例

### API 调用

```bash
# 生成勾股定理动画
curl -X POST http://localhost:8000/api/animation/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "勾股定理",
    "scene_type": "geometry",
    "include_audio": true
  }'

# 返回
{
  "video_url": "/output/animations/勾股定理.mp4",
  "audio_url": "/output/animations/勾股定理.mp3",
  "duration": 45.0,
  "narration_text": "首先，我们画出一个直角三角形..."
}
```

### Python SDK

```python
from lumilearn.animation.pipeline import AnimationPipeline

pipeline = AnimationPipeline()

# 同步方式
result = await pipeline.generate(
    topic="勾股定理",
    scene_type="geometry"
)

print(f"视频: {result['video_path']}")
print(f"旁白: {result['narration']}")
```

---

## 六、动画模板库

### 预置模板

| 模板 | 适用场景 | 示例 |
|------|----------|------|
| `geometry_triangle` | 三角形 | 勾股定理、余弦定理 |
| `geometry_circle` | 圆的性质 | 圆周率、扇形面积 |
| `geometry_polygon` | 多边形 | 正多边形、内角和 |
| `formula_basic` | 基本公式 | 求根公式、配方法 |
| `formula_proof` | 公式证明 | 推导过程动画 |
| `physics_mechanics` | 力学 | 力的分解、运动过程 |
| `physics_optics` | 光学 | 反射、折射 |
| `functions_plot` | 函数图像 | 一次/二次函数 |

---

## 七、依赖清单

| 依赖 | 用途 | 安装方式 |
|------|------|----------|
| `manim` | 动画渲染 | `pip install manim` |
| `ffmpeg` | 视频处理 | `apt install ffmpeg` |
| `texlive-full` | LaTeX 公式 | `apt install texlive-full` |
| `imagemagick` | 图像处理 | `apt install imagemagick` |
| `pillow` | 图像库 | `pip install pillow` |
| `scipy` | 科学计算 | `pip install scipy` |

---

**计划文档保存位置：** [docs/superpowers/plans/2026-06-06-animation-teaching.md](file:///e:/学习LLM/lumilearn/docs/superpowers/plans/2026-06-06-animation-teaching.md)

