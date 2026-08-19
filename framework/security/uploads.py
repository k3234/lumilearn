# -*- coding: utf-8 -*-
"""
文件上传安全校验工具（M-7）

为未来接线的文件上传路由提供统一防护：
- secure_filename 文件名清洗（阻断路径穿越 / 非法字符）
- 扩展名白名单
- 文件大小上限
- 文件头（魔数）真实性校验（防伪造扩展名，如 PHP 伪装成 png）

用法（未来路由接线时）：
    from framework.security.uploads import (
        validate_upload_file, check_file_magic,
        ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES,
    )
    ok, err = validate_upload_file(request.files["file"], ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
    if not ok:
        return jsonify({"error": err}), 400
"""
import os
from pathlib import Path
from typing import Optional, Tuple

from werkzeug.utils import secure_filename

# 各类型白名单与大小上限
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024    # 5MB
MAX_AUDIO_BYTES = 10 * 1024 * 1024   # 10MB

# 文件头魔数（bytes 前缀 → 扩展名集合）；RIFF/WAVE、RIFF/WEBP 单独细分
_MAGIC_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": {".png"},
    b"\xff\xd8\xff": {".jpg", ".jpeg"},
    b"GIF87a": {".gif"},
    b"GIF89a": {".gif"},
    b"ID3": {".mp3"},
    b"\xff\xfb": {".mp3"},
    b"\xff\xf3": {".mp3"},
    b"\xff\xf2": {".mp3"},
    b"fLaC": {".flac"},
    b"OggS": {".ogg"},
}


def validate_upload_file(file_storage, allowed_extensions: set, max_bytes: int) -> Tuple[bool, str]:
    """校验上传文件（Flask FileStorage），返回 (ok, error)。

    检查项：
    1. 文件名非空；
    2. secure_filename 清洗后与原名一致（原名含 `../`、`\\`、路径分隔符等即拒绝）；
    3. 扩展名在白名单内；
    4. 文件大小不超过上限（content_length 或流式长度）。
    """
    if file_storage is None:
        return False, "未收到文件"
    filename = getattr(file_storage, "filename", "") or ""
    if not filename or not filename.strip():
        return False, "文件名不能为空"
    safe = secure_filename(filename)
    if not safe or safe != filename:
        return False, "非法文件名（仅允许字母数字 _-.，且不得包含路径分隔符）"
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        return False, f"不支持的文件类型 {ext or '(无扩展名)'}，允许: {', '.join(sorted(allowed_extensions))}"
    size = _file_size(file_storage)
    if size is not None and size > max_bytes:
        return False, f"文件过大（{size} 字节），上限 {max_bytes} 字节"
    return True, ""


def check_file_magic(path: str, ext: str) -> bool:
    """校验文件头魔数与扩展名是否一致（防伪造扩展名）。

    - `.m4a` 无固定魔数（MPEG-4 容器），跳过校验返回 True；
    - `.wav` / `.webp` 均为 RIFF 容器，通过第 8-11 字节（WAVE/WEBP）细分；
    - 其余类型比对文件头魔数。
    """
    ext = (ext or "").lower()
    if ext in (".m4a",):
        return True
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except Exception:
        return False
    if ext == ".wav":
        return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
    if ext == ".webp":
        return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
    for magic, exts in _MAGIC_SIGNATURES.items():
        if head.startswith(magic):
            return ext in exts
    return False


def _file_size(file_storage) -> Optional[int]:
    """获取上传文件大小。

    优先使用 content_length（真实请求头 / Werkzeug LimitedStream 时准确）；
    其为 0/None（普通内存流无法获知长度）时回退流式测量（seek 到末尾）。
    """
    try:
        cl = getattr(file_storage, "content_length", None)
        if cl and cl > 0:
            return int(cl)
    except Exception:
        pass
    try:
        stream = file_storage.stream
        pos = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(pos)
        return int(size)
    except Exception:
        return None
