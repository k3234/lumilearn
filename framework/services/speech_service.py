# -*- coding: utf-8 -*-
"""
灵学 lumilearn - 语音识别服务
使用 OpenAI Whisper 模型进行语音转文字，支持懒加载

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-01
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional

from framework.security.uploads import validate_upload_file, check_file_magic, ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_BYTES

logger = logging.getLogger("lumilearn.speech_service")

WHISPER_MODEL_NAME = os.environ.get("WHISPER_MODEL", "tiny")
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}

_whisper_model = None


class SpeechService:
    """
    语音识别服务

    功能：
    - OpenAI Whisper 语音转文字
    - 懒加载模型（首次调用时加载）
    - 支持多种音频格式（wav/mp3/m4a/ogg/flac）
    - CPU模式运行
    """

    def __init__(self, model_name: str = None):
        self._model_name = model_name or WHISPER_MODEL_NAME
        self._model = None

    def _load_model(self):
        """懒加载 Whisper 模型"""
        global _whisper_model
        if _whisper_model is None:
            import whisper
            logger.info(f"[Whisper] 正在加载模型: {self._model_name}（CPU模式）...")
            print(f"[Whisper] 正在加载模型: {self._model_name}（CPU模式）...")
            _whisper_model = whisper.load_model(self._model_name, device="cpu")
            print(f"[Whisper] 模型 {self._model_name} 加载完成")
        self._model = _whisper_model

    @staticmethod
    def is_allowed_extension(filename: str) -> bool:
        """检查音频文件扩展名是否在白名单中"""
        if not filename:
            return False
        return Path(filename).suffix.lower() in ALLOWED_AUDIO_EXTENSIONS

    @staticmethod
    def get_allowed_extensions() -> str:
        """获取支持的音频格式列表"""
        return ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))

    def transcribe(self, file_path: str) -> Dict:
        """
        语音转文字

        参数：
            file_path: 音频文件路径

        返回：
            {
                "text": "识别出的文字",
                "language": "检测到的语言代码"
            }
        """
        if self._model is None:
            self._load_model()

        result = self._model.transcribe(file_path)

        return {
            "text": result.get("text", "").strip(),
            "language": result.get("language", "zh")
        }

    def transcribe_file(self, file_storage) -> Dict:
        """
        接收上传的文件对象并转写

        参数：
            file_storage: Flask FileStorage 对象

        返回：
            {
                "text": "识别出的文字",
                "language": "检测到的语言代码"
            }
        """
        # 前置校验：文件名、扩展名、大小、魔数，在模型加载前拒绝恶意文件
        ok, err = validate_upload_file(file_storage, ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_BYTES)
        if not ok:
            raise ValueError(err)

        suffix = Path(file_storage.filename).suffix.lower()
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                file_storage.save(tmp.name)
                tmp_path = tmp.name

            check_file_magic(tmp_path, suffix) or (_ for _ in ()).throw(ValueError("文件魔数校验失败"))
            return self.transcribe(tmp_path)

        finally:
            if tmp_path and Path(tmp_path).exists():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_loaded(self) -> bool:
        return self._model is not None


_speech_service_instance: Optional[SpeechService] = None


def get_speech_service(model_name: str = None) -> SpeechService:
    """获取SpeechService单例"""
    global _speech_service_instance
    if _speech_service_instance is None:
        _speech_service_instance = SpeechService(model_name)
    return _speech_service_instance