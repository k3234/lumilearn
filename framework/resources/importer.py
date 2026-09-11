# -*- coding: utf-8 -*-
"""
LumiLearn 资料入库管线（ResourceImporter）
==========================================
把学校本地教材、教师上传文件（PPT/HTML/md/txt）、网络资源统一解析、去重、
写入 training_data 表，支撑 draft → reviewed → published 评审发布流。

设计约束（离线 / 低依赖优先）：
- HTML：内置正则剥标签提取文本，不引入 bs4。
- PPTX：可选依赖 python-pptx；缺库时返回明确错误并提示先转 md（离线降级）。
- 网络采集：由 config/framework.yaml 的 resources.web_import_enabled 门控（默认 False）。

去重：对正文求哈希（content hash）写入后查同 hash 已存在则拒绝重复导入。
"""
import hashlib
import logging
import re
import urllib.parse

from framework.core.config import get_config
from framework.database import db

logger = logging.getLogger("lumilearn.resources.importer")

# 允许上传的扩展名（小写，去"."）
DEFAULT_UPLOAD_EXTS = ["md", "txt", "html", "htm", "ppt", "pptx"]


def _content_hash(content: str) -> str:
    """对正文内容计算稳定哈希，用于去重。"""
    norm = re.sub(r"\s+", " ", content or "").strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _strip_tags(html: str) -> str:
    """剥离 HTML 标签与脚本/样式，返回可读文本。"""
    if not html:
        return ""
    text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def _extract_html_title(html: str) -> str:
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html or "")
    return (m.group(1).strip() if m else "") or "HTML 导入资料"


def parse_upload(file_stream, filename: str):
    """按扩展名解析上传文件，返回 {'text','ok','error'}。

    支持 md/txt（直读）、html/htm（剥标签）、pptx/ppt（python-pptx 可选）。
    缺库或非支持类型返回 error，不抛异常。
    """
    name = filename or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    try:
        raw = file_stream.read()
    except Exception as e:
        return {"ok": False, "error": f"读取文件失败: {e}"}

    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        text = ""

    if ext in ("md", "txt"):
        return {"ok": True, "text": text.strip(), "title": name.rsplit(".", 1)[0]}
    if ext in ("html", "htm"):
        title = _extract_html_title(text)
        return {"ok": True, "text": _strip_tags(text), "title": title}
    if ext in ("ppt", "pptx"):
        return parse_upload_pptx(raw, filename)
    return {"ok": False,
            "error": f"不支持的文件类型 .{ext}，支持: {', '.join(DEFAULT_UPLOAD_EXTS)}"}


def parse_upload_pptx(raw_bytes: bytes, filename: str):
    """真机运行时的 PPTX 文本抽取（与 parse_upload 分离，避免假 import 误伤）。"""
    try:
        from pptx import Presentation
    except Exception:
        return {"ok": False,
                "error": "解析 PPT/PPTX 需安装可选依赖 python-pptx；请先用 PowerPoint 另存为 .md/.txt 再导入。"}
    try:
        import io
        prs = Presentation(io.BytesIO(raw_bytes))
        parts = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    parts.append(shape.text.strip())
        title = filename.rsplit(".", 1)[0]
        return {"ok": True, "text": "\n\n".join(p for p in parts if p), "title": title}
    except Exception as e:
        return {"ok": False, "error": f"PPT 解析失败: {e}"}


def import_web(url: str, subject: str = "", chapter: str = ""):
    """按 URL 采集网络资源（受 web_import_enabled 门控）。"""
    cfg = get_config()
    resources = cfg.get("resources", {})
    if not resources.get("web_import_enabled", False):
        return {"ok": False, "error": "网络资源采集未开启（resources.web_import_enabled=false）"}
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (LumiLearn)"})
        max_bytes = int(resources.get("max_web_bytes", 500000))
        with urllib.request.urlopen(req, timeout=int(resources.get("timeout", 15))) as resp:
            raw = resp.read(max_bytes)
    except Exception as e:
        return {"ok": False, "error": f"抓取网页失败: {e}"}
    try:
        html = raw.decode(resp.headers.get_content_charset() or "utf-8", errors="ignore")
    except Exception:
        html = raw.decode("utf-8", errors="ignore")
    title = _extract_html_title(html)
    text = _strip_tags(html)
    return {"ok": True, "text": text, "title": title, "source": url, "source_type": "web"}


class ResourceImporter:
    """资料导入单例：提供文本/上传/网络统一入库接口。"""

    def import_text(self, subject="", chapter="", title="", content="",
                    content_type="知识总结", difficulty="中等", grade="高中",
                    keywords="", prerequisites="", learning_objectives="",
                    common_mistakes="", source="manual", source_type="manual",
                    status="draft", quality_score=0.0):
        """校验 + 去重 + 入库 → 返回 {ok, record_id, error}。"""
        content = (content or "").strip()
        if len(content) < 5:
            return {"ok": False, "error": "导入内容过短或为空"}
        title = (title or "").strip() or "未命名资料"

        # 去重：查同 hash 是否已存在（source_type 相同）
        h = _content_hash(content)
        existed = db._query_one(
            "SELECT id FROM training_data WHERE hash = ? LIMIT 1", (h,)) if _has_hash_col() else None
        if existed:
            return {"ok": False, "error": "内容重复，已存在相同资料", "record_id": existed["id"]}

        try:
            rec = db.add_training_data(
                subject=subject or "综合", chapter=chapter, title=title, content=content,
                grade=grade, content_type=content_type, difficulty=difficulty,
                keywords=keywords, prerequisites=prerequisites,
                learning_objectives=learning_objectives, common_mistakes=common_mistakes,
                source=source, source_type=source_type, status=status,
            )
        except Exception as e:
            logger.exception("import_text 入库失败")
            return {"ok": False, "error": f"入库失败: {e}"}

        if _has_hash_col():
            self._store_hash(rec["id"], h)

        if quality_score > 0:
            try:
                db.update_training_data(rec["id"], quality_score=quality_score)
            except Exception:
                pass
        return {"ok": True, "record_id": rec["id"], "hash": h}

    def _store_hash(self, record_id, h):
        # training_data 若存在 hash 列则写入，否则忽略（DB 函数白名单不含 hash）
        try:
            db.conn.execute("UPDATE training_data SET hash = ? WHERE id = ?", (h, record_id))
            db.conn.commit()
        except Exception:
            pass


def _has_hash_col() -> bool:
    """探测 training_data 是否有 hash 列（跨 DB 版本兼容）。"""
    try:
        cols = [r[1] for r in db.conn.execute("PRAGMA table_info(training_data)").fetchall()]
        return "hash" in cols
    except Exception:
        return False