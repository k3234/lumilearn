#!/usr/bin/env python3
"""
灵学 lumilearn - OCR API 路由
光学字符识别端点
"""
import base64
import io
import logging
from flask import Blueprint, request, jsonify
from werkzeug.datastructures import FileStorage

from framework.security.uploads import validate_upload_file, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES

logger = logging.getLogger("lumilearn.routes.ocr")

ocr_bp = Blueprint("ocr", __name__)


def _decode_image_from_form(file_storage) -> bytes:
    """从 FileStorage 中解码图片并做前置校验"""
    validate_upload_file(file_storage, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
    return file_storage.read()


def _decode_image_from_base64(b64_data: str, filename: str) -> bytes:
    """从 base64 解码并做前置校验"""
    try:
        raw = base64.b64decode(b64_data)
    except Exception:
        raise ValueError("图片数据 base64 解码失败")
    # 用虚拟 FileStorage 做文件名和扩展名校验
    fs = FileStorage(stream=io.BytesIO(raw), filename=filename, content_type="image/png")
    validate_upload_file(fs, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
    return raw


@ocr_bp.route("/api/ocr/recognize", methods=["POST", "OPTIONS"])
def recognize_text():
    """
    OCR 文字识别端点

    支持两种请求方式：
    1. multipart/form-data: 上传 image 文件
    2. application/json: {"image": "base64数据", "filename": "name.png"}
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    # 方式1：文件上传
    if "image" in request.files:
        file_storage = request.files["image"]
        try:
            raw_data = _decode_image_from_form(file_storage)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        # TODO: 调用 OCRService.recognize() 并传入 raw_data

    # 方式2：base64 JSON
    data = request.get_json(force=True)
    if data:
        b64 = data.get("image", "")
        filename = data.get("filename", "image.png")
        if b64:
            try:
                raw_data = _decode_image_from_base64(b64, filename)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            # TODO: 调用 OCRService.recognize() 并传入 raw_data
        else:
            return jsonify({"error": "缺少 image 字段"}), 400
    else:
        return jsonify({"error": "请求体为空"}), 400

    return jsonify({
        "status": "success",
        "message": "OCR 功能开发中",
        "text": ""
    })


@ocr_bp.route("/api/ocr/batch", methods=["POST", "OPTIONS"])
def batch_recognize():
    """
    批量 OCR 识别端点
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    images = data.get("images", [])
    if not images:
        return jsonify({"error": "缺少 images 字段"}), 400

    # TODO: 对每张图做 validate_upload_file 后调用 OCRService
    return jsonify({
        "status": "success",
        "message": "批量 OCR 功能开发中",
        "results": []
    })
