#!/usr/bin/env python3
"""
灵学 lumilearn - 语音 API 路由
语音合成和识别端点
"""
import base64
import io
import logging
from flask import Blueprint, request, jsonify
from werkzeug.datastructures import FileStorage

from framework.security.uploads import validate_upload_file, ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_BYTES

logger = logging.getLogger("lumilearn.routes.speech")

speech_bp = Blueprint("speech", __name__)


def _decode_audio_from_form(file_storage) -> bytes:
    """从 FileStorage 中解码音频并做前置校验"""
    validate_upload_file(file_storage, ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_BYTES)
    return file_storage.read()


def _decode_audio_from_base64(b64_data: str, filename: str) -> bytes:
    """从 base64 解码并做前置校验"""
    try:
        raw = base64.b64decode(b64_data)
    except Exception:
        raise ValueError("音频数据 base64 解码失败")
    # 用虚拟 FileStorage 做文件名和扩展名校验
    fs = FileStorage(stream=io.BytesIO(raw), filename=filename, content_type="audio/wav")
    validate_upload_file(fs, ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_BYTES)
    return raw


@speech_bp.route("/api/speech/synthesize", methods=["POST", "OPTIONS"])
def synthesize_speech():
    """
    语音合成端点

    请求体（JSON）:
        {
            "text": "要合成的文本",
            "voice": "voice_name",
            "speed": 1.0
        }
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    text = data.get("text", "")
    if not text:
        return jsonify({"error": "缺少 text 字段"}), 400

    # TODO: 实现语音合成逻辑
    return jsonify({
        "status": "success",
        "message": "语音合成功能开发中",
        "text": text
    })


@speech_bp.route("/api/speech/recognize", methods=["POST", "OPTIONS"])
def recognize_speech():
    """
    语音识别端点

    支持两种请求方式：
    1. multipart/form-data: 上传 audio 文件
    2. application/json: {"audio": "base64数据", "filename": "audio.wav"}
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"})

    # 方式1：文件上传
    if "audio" in request.files:
        file_storage = request.files["audio"]
        try:
            raw_data = _decode_audio_from_form(file_storage)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        # TODO: 调用 SpeechService.transcribe() 并传入 raw_data

    # 方式2：base64 JSON
    data = request.get_json(force=True)
    if data:
        b64 = data.get("audio", "")
        filename = data.get("filename", "audio.wav")
        if b64:
            try:
                raw_data = _decode_audio_from_base64(b64, filename)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            # TODO: 调用 SpeechService.transcribe() 并传入 raw_data
        else:
            return jsonify({"error": "缺少 audio 字段"}), 400
    else:
        return jsonify({"error": "请求体为空"}), 400

    return jsonify({
        "status": "success",
        "message": "语音识别功能开发中",
        "text": ""
    })
