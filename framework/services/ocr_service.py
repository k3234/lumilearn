# -*- coding: utf-8 -*-
"""
灵学 lumilearn - OCR文字识别服务
使用 PaddleOCR 进行图片文字识别，支持懒加载

作者：lumilearn AI自动化专家
版本：1.0.0
日期：2026-06-01
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("lumilearn.ocr_service")

PADDLEOCR_LANG = os.environ.get("PADDLEOCR_LANG", "ch")
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

_paddleocr_instance = None


class OCRService:
    """
    OCR文字识别服务

    功能：
    - PaddleOCR 图片文字识别
    - 懒加载模型（首次调用时加载）
    - 支持多种图片格式（png/jpg/jpeg/webp）
    - CPU模式运行
    """

    def __init__(self, lang: str = None):
        self._lang = lang or PADDLEOCR_LANG
        self._ocr = None

    def _load_model(self):
        """懒加载 PaddleOCR 模型"""
        global _paddleocr_instance
        if _paddleocr_instance is None:
            from paddleocr import PaddleOCR
            logger.info(f"[PaddleOCR] 正在加载模型: lang={self._lang}（CPU模式）...")
            print(f"[PaddleOCR] 正在加载模型: lang={self._lang}（CPU模式）...")
            _paddleocr_instance = PaddleOCR(
                use_angle_cls=True,
                lang=self._lang,
                use_gpu=False,
                show_log=False
            )
            print(f"[PaddleOCR] 模型 lang={self._lang} 加载完成")
        self._ocr = _paddleocr_instance

    @staticmethod
    def is_allowed_extension(filename: str) -> bool:
        """检查图片文件扩展名是否在白名单中"""
        if not filename:
            return False
        return Path(filename).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS

    @staticmethod
    def get_allowed_extensions() -> str:
        """获取支持的图片格式列表"""
        return ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))

    def recognize(self, file_path: str) -> Dict:
        """
        识别图片中的文字

        参数：
            file_path: 图片文件路径

        返回：
            {
                "text": "完整识别文字",
                "confidence": 平均置信度,
                "details": [
                    {"text": "...", "confidence": 0.99, "box": [[x1,y1],...]},
                    ...
                ]
            }
        """
        if self._ocr is None:
            self._load_model()

        raw_result = self._ocr.ocr(file_path, cls=True)

        all_text_parts = []
        details = []
        overall_confidences = []

        if raw_result and raw_result[0]:
            for detection in raw_result[0]:
                # detection: [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ('text', confidence)]
                box = detection[0]
                text_info = detection[1]
                text = text_info[0]
                confidence = float(text_info[1])

                all_text_parts.append(text)
                overall_confidences.append(confidence)
                details.append({
                    "text": text,
                    "confidence": round(confidence, 4),
                    "box": [[int(p[0]), int(p[1])] for p in box]
                })

        full_text = "".join(all_text_parts) if all_text_parts else ""
        avg_confidence = (
            round(sum(overall_confidences) / len(overall_confidences), 4)
            if overall_confidences else 0.0
        )

        return {
            "text": full_text,
            "confidence": avg_confidence,
            "details": details
        }

    def recognize_file(self, file_storage) -> Dict:
        """
        接收上传的文件对象并识别

        参数：
            file_storage: Flask FileStorage 对象

        返回：
            {
                "text": "完整识别文字",
                "confidence": 平均置信度,
                "details": [...]
            }
        """
        suffix = Path(file_storage.filename).suffix.lower()
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                file_storage.save(tmp.name)
                tmp_path = tmp.name

            return self.recognize(tmp_path)

        finally:
            if tmp_path and Path(tmp_path).exists():
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    @property
    def lang(self) -> str:
        return self._lang

    @property
    def is_loaded(self) -> bool:
        return self._ocr is not None


_ocr_service_instance: Optional[OCRService] = None


def get_ocr_service(lang: str = None) -> OCRService:
    """获取OCRService单例"""
    global _ocr_service_instance
    if _ocr_service_instance is None:
        _ocr_service_instance = OCRService(lang)
    return _ocr_service_instance