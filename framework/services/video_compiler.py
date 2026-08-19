# -*- coding: utf-8 -*-
"""
FFmpeg 视频编译服务
合并、剪切、添加字幕、音视频合成
"""
import subprocess
import json
from pathlib import Path
from typing import List, Optional


class VideoCompiler:
    """FFmpeg 视频编译服务"""

    @staticmethod
    def merge_clips(clips: List[str], output: str) -> str:
        """合并多个视频片段"""
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 生成文件列表
        list_file = output_path.parent / "concat_list.txt"
        list_file.write_text(
            "\n".join(f"file '{Path(c).absolute()}'" for c in clips)
        )

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"视频合并失败: {result.stderr}")

        # 清理临时文件
        if list_file.exists():
            list_file.unlink()

        return str(output_path)

    @staticmethod
    def add_audio(video: str, audio: str, output: str) -> str:
        """音视频合成（浏览器兼容编码）"""
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-i", audio,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"音视频合成失败: {result.stderr}")

        return str(output_path)

    @staticmethod
    def add_subtitles(video: str, srt_file: str, output: str) -> str:
        """添加字幕"""
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 校验 srt_file 路径：防止路径穿越和 shell 注入
        srt_path = Path(srt_file)
        if ".." in srt_path.parts or srt_path.is_absolute():
            # 相对路径允许，绝对路径需校验是否在允许的目录内
            srt_resolved = srt_path.resolve()
            allowed_dirs = [Path(".").resolve(), Path("/tmp").resolve()]
            if not any(str(srt_resolved).startswith(str(d)) for d in allowed_dirs):
                raise ValueError(f"不允许的字幕文件路径: {srt_file}")
        # ffmpeg subtitles 过滤器对路径中的特殊字符敏感，清理控制字符
        safe_srt = re.sub(r'["\\$`]', r'\\\1', str(srt_path))

        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-vf", f"subtitles={safe_srt}",
            "-c:a", "copy",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(f"添加字幕失败: {result.stderr}")

        return str(output_path)

    @staticmethod
    def get_duration(video: str) -> float:
        """获取视频时长（秒）"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        return 0.0

    @staticmethod
    def extract_frame(video: str, timestamp: float, output: str) -> str:
        """截取单帧"""
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", video,
            "-vframes", "1",
            "-q:v", "2",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"截取帧失败: {result.stderr}")

        return str(output_path)

    @staticmethod
    def compress(video: str, output: str, crf: int = 23) -> str:
        """压缩视频"""
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-i", video,
            "-vcodec", "libx264",
            "-crf", str(crf),
            "-preset", "medium",
            "-acodec", "aac",
            str(output_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"视频压缩失败: {result.stderr}")

        return str(output_path)
