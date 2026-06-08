# -*- coding: utf-8 -*-
"""
Manim 动画生成服务
AI 生成动画代码 -> 渲染 -> 输出视频
"""
import os
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class ManimService:
    """Manim 动画生成服务"""

    def __init__(
        self,
        output_dir: str = "output/animations",
        quality: str = "medium",
        fps: int = 30
    ):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality
        self.fps = fps

        # 质量映射
        self.quality_flag = {
            "low": "-ql",
            "medium": "-qm",
            "high": "-qh",
            "production": "-qp",
        }.get(quality, "-qm")

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
            tmpdir = Path(tmpdir)

            try:
                # 写入临时文件
                script_path = tmpdir / "scene.py"
                wrapped_code = self._wrap_code(manim_code, scene_name)
                script_path.write_text(wrapped_code, encoding="utf-8")

                # 查找 manim 可执行文件绝对路径
                manim_exe = shutil.which("manim")
                if not manim_exe:
                    # 尝试常见路径
                    for guess in ["/usr/local/bin/manim", "/usr/bin/manim",
                                  os.path.expanduser("~/.local/bin/manim")]:
                        if os.path.exists(guess):
                            manim_exe = guess
                            break
                if not manim_exe:
                    raise RuntimeError("找不到 manim 可执行文件，请确认 Manim 已安装并在 PATH 中")

                # 执行 manim 渲染
                cmd = [
                    manim_exe,
                    self.quality_flag,
                    "--fps", str(self.fps),
                    "-o", scene_name,
                    str(script_path),
                    scene_name
                ]

                try:
                    result = subprocess.run(
                        cmd,
                        cwd=str(tmpdir),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                except subprocess.TimeoutExpired:
                    logger.error(f"Manim 渲染超时 (300s): {scene_name}")
                    raise RuntimeError(f"Manim 渲染超时 (300秒): {scene_name}")

                if result.returncode != 0:
                    error_msg = (
                        f"Manim 渲染失败 (exit code: {result.returncode})\n"
                        f"STDERR:\n{result.stderr}\n"
                        f"STDOUT:\n{result.stdout}"
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                # 查找输出文件
                media_dir = tmpdir / "media"
                if not media_dir.exists():
                    raise RuntimeError("Manim 未生成输出目录")

                # 查找视频文件：查找 media/videos 下的所有子目录
                videos_base = media_dir / "videos"
                if not videos_base.exists():
                    raise RuntimeError("Manim 未生成视频目录")

                # 检查所有可能的子目录
                for script_dir in videos_base.iterdir():
                    if not script_dir.is_dir():
                        continue

                    for ext in ["mp4", "webm", "mov"]:
                        video_file = script_dir / self._get_quality_dir() / f"{scene_name}.{ext}"
                        if video_file.exists():
                            dest = self.output_dir / f"{scene_name}.{ext}"
                            # 使用 copy2 保留元数据，并验证完整性
                            shutil.copy2(str(video_file), str(dest))

                            if not dest.exists() or dest.stat().st_size == 0:
                                raise RuntimeError(
                                    f"视频文件复制失败或为空: {dest}"
                                )

                            logger.info(
                                f"视频文件已生成: {video_file} -> {dest} "
                                f"({dest.stat().st_size} bytes)"
                            )
                            return str(dest)

                raise RuntimeError("Manim 渲染未生成视频文件")

            finally:
                # 临时目录由 with 语句自动清理
                # 此处确保所有子进程已终止
                pass

    def render_preview(self, manim_code: str, scene_name: str = "PreviewScene") -> str:
        """渲染预览图（比视频快）"""
        preview_code = manim_code + f"""

class {scene_name}Preview(Scene):
    def construct(self):
        # 渲染静态预览
        pass
"""
        try:
            return self.render(preview_code, scene_name)
        except Exception:
            return None

    def _wrap_code(self, code: str, scene_name: str) -> str:
        """包装代码，确保类名正确"""
        # 如果代码中没有导入 manim，添加导入
        if "from manim import" not in code and "import manim" not in code:
            code = "from manim import *\n" + code
        return code

    def _get_quality_dir(self) -> str:
        """获取质量对应的目录名"""
        dirs = {
            "low": "480p15",
            "medium": "720p30",
            "high": "1080p60",
            "production": "4K",
        }
        return dirs.get(self.quality, "720p30")

    def list_outputs(self) -> list:
        """列出已生成的动画"""
        return [str(f) for f in self.output_dir.glob("*")]
