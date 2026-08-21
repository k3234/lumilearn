# -*- coding: utf-8 -*-
"""
LumiLearn API 输入校验工具
==========================
可复用的请求参数校验函数，供各 API 路由调用：

- validate_text_field: 必填文本字段校验（非空 + 长度上限）
- validate_document_import: 文档导入文件名/文件类型白名单校验

所有函数返回 (ok, error_msg)：
- ok=True 表示通过，error_msg 为空字符串
- ok=False 表示校验失败，error_msg 为可直接返回给客户端的友好提示
"""

import os

# 文档导入允许的文件类型白名单（扩展名或 format 值）
ALLOWED_DOC_EXTENSIONS = {
    "md", "markdown", "txt", "text", "pdf", "docx", "obsidian",
}

# 对外展示的允许类型文案
ALLOWED_DOC_HINT = "md/txt/pdf/docx/obsidian"


def validate_text_field(value, field_name: str, max_len: int):
    """校验必填文本字段：非空且长度 ≤ max_len。

    参数：
        value:      字段原始值（可能为 None / 非字符串）
        field_name: 字段中文名，用于错误提示（如 "topic"）
        max_len:    最大允许字符数

    返回：
        (True, "") 或 (False, "错误提示")
    """
    text = (value or "").strip() if isinstance(value, str) else ""
    if not text:
        return False, f"{field_name}不能为空"
    if len(text) > max_len:
        return False, f"{field_name}长度不能超过 {max_len} 个字符"
    return True, ""


def validate_document_import(filename, fmt: str = ""):
    """校验文档导入的文件名/文件类型白名单（md/txt/pdf/docx/obsidian）。

    - filename 缺失/为空 → 失败
    - 优先用 format 字段（未传时按文件名扩展名推断），
      不在白名单内 → 失败

    返回：
        (True, "") 或 (False, "错误提示")
    """
    name = (filename or "").strip()
    if not name:
        return False, "缺少 filename 字段"
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    fmt = (fmt or "").strip().lower()
    candidate = fmt or ext
    if candidate not in ALLOWED_DOC_EXTENSIONS:
        return False, f"不支持的文件类型「{candidate or name}」，仅支持 {ALLOWED_DOC_HINT}"
    return True, ""
