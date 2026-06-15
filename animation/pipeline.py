# -*- coding: utf-8 -*-
"""
动画生成完整管线
AI 理解 -> 代码生成 -> 渲染 -> 配音 -> 合成
"""
import asyncio
import re
from pathlib import Path
from typing import Optional, Dict

from framework.services.manim_service import ManimService
from framework.services.video_compiler import VideoCompiler
from .generators import (
    GeometryAnimationGenerator,
    FormulaAnimationGenerator,
)


class AnimationPipeline:
    """动画生成管线"""

    def __init__(
        self,
        manim_service: Optional[ManimService] = None,
        tts_service=None,  # 复用 voicebox_service
        output_dir: str = "output/animations"
    ):
        self.manim_service = manim_service or ManimService(output_dir=output_dir)
        self.tts_service = tts_service
        self.video_compiler = VideoCompiler()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 注册生成器
        self.generators = {
            "geometry": GeometryAnimationGenerator(),
            "formula": FormulaAnimationGenerator(),
            "auto": GeometryAnimationGenerator(),  # 默认用几何
        }

    async def generate(self, topic: str, scene_type: str = "auto", **kwargs) -> Dict:
        """
        生成完整动画

        Args:
            topic: 教学主题，如"勾股定理"
            scene_type: 动画类型，"auto"时自动判断

        Returns:
            {
                "video_path": "output/animations/pythagorean.mp4",
                "audio_path": "output/animations/pythagorean.mp3",
                "duration": 45.0,
                "narration": "...",
                "scene_type": "geometry"
            }
        """
        # Step 1: 选择/检测生成器
        if scene_type == "auto":
            # 使用默认生成器检测
            generator = GeometryAnimationGenerator()
            scene_type = generator.detect_scene_type(topic)
        else:
            generator = self.generators.get(scene_type, GeometryAnimationGenerator())

        # Step 2: 生成动画代码和旁白
        result = generator.generate(topic, scene_type=scene_type)
        manim_code = result["manim_code"]
        narration = result.get("narration", "")
        detected_type = result.get("scene_type", scene_type)

        # 生成场景名
        scene_name = self._topic_to_scene_name(topic)

        # Step 3: 渲染动画（后台）
        loop = asyncio.get_event_loop()
        try:
            video_path = await loop.run_in_executor(
                None,
                self._render_animation,
                manim_code,
                scene_name
            )
        except Exception as e:
            # Manim 渲染失败，返回代码供手动渲染
            return {
                "video_path": None,
                "audio_path": None,
                "duration": 0,
                "narration": narration,
                "scene_type": detected_type,
                "manim_code": manim_code,
                "error": str(e)
            }

        # Step 4: TTS 配音
        audio_path = None
        if self.tts_service and narration:
            try:
                audio_path = await self.tts_service.synthesize(
                    text=narration,
                    voice="ai_teacher"
                )
            except Exception:
                pass  # TTS 失败不影响主流程

        # Step 5: 音视频合成
        final_path = video_path
        if audio_path and video_path:
            try:
                final_path = await self._compile(video_path, audio_path, scene_name)
            except Exception:
                final_path = video_path  # 合成失败，返回纯视频

        # Step 6: 获取时长
        duration = 0
        if final_path:
            try:
                duration = self.video_compiler.get_duration(final_path)
            except Exception:
                pass

        return {
            "video_path": final_path,
            "audio_path": audio_path,
            "duration": duration,
            "narration": narration,
            "scene_type": detected_type,
            "manim_code": manim_code,
        }

    def _render_animation(self, code: str, scene_name: str) -> str:
        """渲染动画"""
        return self.manim_service.render(code, scene_name)

    async def _compile(self, video_path: str, audio_path: str, scene_name: str) -> str:
        """音视频合成"""
        output_path = str(self.output_dir / f"{scene_name}_with_audio.mp4")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.video_compiler.add_audio,
            video_path,
            audio_path,
            output_path
        )

    def _topic_to_scene_name(self, topic: str) -> str:
        """将 topic 转换为安全的场景名"""
        # 移除非字母数字字符
        safe_name = re.sub(r'[^\w]', '_', topic)
        safe_name = safe_name[:30]  # 限制长度
        return safe_name

    def list_templates(self) -> list:
        """列出可用的动画模板"""
        return [
            {
                "id": "geometry",
                "name": "几何图形",
                "description": "三角形、圆、多边形等几何图形动画",
                "examples": ["勾股定理", "余弦定理", "圆面积", "三角形内角和"]
            },
            {
                "id": "formula",
                "name": "公式推导",
                "description": "数学公式动态推导展示",
                "examples": ["求根公式", "配方法", "平方差公式"]
            },
            {
                "id": "physics",
                "name": "物理过程",
                "description": "物理过程动画（开发中）",
                "examples": ["自由落体", "光的折射"]
            },
            {
                "id": "functions",
                "name": "函数图像",
                "description": "函数图像绘制与变换（开发中）",
                "examples": ["一次函数", "二次函数图像"]
            }
        ]

    def list_outputs(self) -> list:
        """列出已生成的动画"""
        outputs = []
        for f in self.output_dir.glob("*"):
            outputs.append({
                "name": f.stem,
                "path": str(f),
                "size": f.stat().st_size if f.is_file() else 0,
                "type": f.suffix[1:]
            })
        return outputs
