#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LumiLearn 学习资源导出服务（纯标准库，零第三方依赖）

把已生成的幻灯片（title / subtitle / content 富文本）导出为两种真实可用的离线课件：
  - PPTX：Open XML 演示文稿（Office / WPS / LibreOffice / Keynote 均可打开）
  - PDF：内嵌 Type0 CID 中文字体（Identity-H / Adobe-GB1，viewer 自带 CMap，无需额外字体文件）
两者均只依赖标准库 zipfile / xml.etree / zlib，契合产品「4GB 老电脑 / 离线 / 可移植」定位。

作者：LumiLearn
"""
import io
import re
import zipfile
import zlib
from xml.sax.saxutils import escape as _xe
from xml.sax.saxutils import quoteattr as _xq


# ---------------------------------------------------------------------------
# 公共：清洗幻灯片富文本，抽取出「标题 / 副标题 / 纯文本要点」
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")
_CLEAN_RE = re.compile(r"[●▶]|^\s*[-•]\s+")


def _strip_html(html_text: str) -> str:
    """从 <p>...</p> 富文本里提取纯文本，去掉标签与装饰符号。"""
    if not html_text:
        return ""
    txt = _TAG_RE.sub("", html_text)
    txt = _CLEAN_RE.sub("", txt)
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return txt.strip()


def _bullet_points(html_text: str) -> list:
    """把富文本按段落切成要点列表（去掉 ★ 圆点）。"""
    if not html_text:
        return []
    blocks = re.split(r"</p>", html_text)
    points = []
    for b in blocks:
        line = _strip_html(b)
        if line:
            points.append(line)
    return points


def export_slides(slides: list, title: str = "LumiLearn 课件",
                  fmt: str = "pptx") -> dict:
    """统一导出入口。

    slides: [{"title": str, "subtitle": str, "content": "<p>…</p>"}, ...]
    fmt: "pptx" | "pdf"
    返回 {"stream": bytes, "filename": str, "content_type": str}
    """
    fmt = (fmt or "pptx").lower()
    normal = [s for s in (slides or []) if s and (s.get("title") or s.get("content"))]
    if not normal:
        raise ValueError("没有可导出的幻灯片内容")
    if fmt == "pptx":
        data = build_pptx(normal, title)
        return {"stream": data, "filename": f"{_safe_filename(title)}.pptx",
                "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
    if fmt == "pdf":
        data = build_pdf(normal, title)
        return {"stream": data, "filename": f"{_safe_filename(title)}.pdf",
                "content_type": "application/pdf"}
    raise ValueError(f"不支持的导出格式: {fmt}")


def _safe_filename(name: str) -> str:
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", name).strip("._") or "LumiLearn课件"


# ---------------------------------------------------------------------------
# PPTX：Open XML 演示文稿（纯标准库）
# ---------------------------------------------------------------------------
def _px(s: str) -> str:
    return _xe(s)


def build_pptx(slides: list, title: str) -> bytes:
    sizes = 16, 10, 18  # 视觉优先级（占位，供布局参考）
    del sizes

    n = len(slides)
    import xml.etree.ElementTree as ET

    # --- 内容
    def slide_xml(t, sub, points, idx):
        body = []
        if sub:
            body.append(
                f'<a:p><a:pPr lvl="0"/><a:r><a:rPr lang="zh-CN" b="0" sz="1400" '
                f'dirty="0" smtClean="0"/><a:t>{_px(sub)}</a:t></a:r></a:p>'
            )
        body.append(
            f'<a:p><a:pPr lvl="0"/><a:r><a:rPr lang="zh-CN" b="0" sz="2200" '
            f'dirty="0"/><a:t>{_px(t)}</a:t></a:r></a:p>'
        )
        for pt in points[:8]:
            body.append(
                f'<a:p><a:pPr lvl="1"/><a:r><a:rPr lang="zh-CN" b="0" sz="1600" '
            f'dirty="0"/><a:t>{_px(pt)}</a:t></a:r></a:p>'
            )
        # txBody 里采用 rPr 而不是显式 font 名：viewer 用默认中文字体回退
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            '<p:cSld><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="内容占位符"/><p:cNvSpPr txBox="1"/>'
            '<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="411480" y="182880"/>'
            f'<a:ext cx="9853920" cy="6858000"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
            '<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" '
            'anchor="t"/><a:lstStyle/>'
            f"{''.join(body)}"
            '</p:txBody></p:sp></p:spTree></p:cSld>'
            f'<p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" '
            'accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" '
            'accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr>'
            '</p:sld>'
        )

    slides_xml = {}
    slides_rels = {}
    for i, s in enumerate(slides, 1):
        slides_xml[f"ppt/slides/slide{i}.xml"] = slide_xml(
            s.get("title", ""), s.get("subtitle", ""),
            _bullet_points(s.get("content", "")), i)
        slides_rels[f"ppt/slides/_rels/slide{i}.xml.rels"] = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
            f'Target="../slideLayouts/slideLayout1.xml"/></Relationships>'
        )

    # --- 主模板
    presentation_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        '<p:sldIdLst>' +
        "".join(f'<p:sldId id="{256 + i}" r:id="rId{2 + i}"/>' for i in range(n)) +
        '</p:sldIdLst>'
        '<p:sldSz cx="12192000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/>'
        '</p:presentation>'
    )
    presentation_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
        'Target="slideMasters/slideMaster1.xml"/>' +
        "".join(
            f'<Relationship Id="rId{2 + i}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{i}.xml"/>' for i in range(n)) +
        '</Relationships>'
    )

    slide_layout = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'preserve="1" type="blank" matchByName="1"><p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping/></p:clrMapOvr>'
        '<p:timing/></p:sldLayout>'
    )
    slide_layout_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" '
        'Target="../slideMasters/slideMaster1.xml"/></Relationships>'
    )

    slide_master = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/>'
        '<p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/>'
        '<a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/>'
        '</a:xfrm></p:grpSpPr></p:spTree></p:cSld>'
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" '
        'accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" '
        'accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
        '<p:txStyles><p:titleStyle><a:lvl1pPr/></p:titleStyle>'
        '<p:bodyStyle><a:lvl1pPr/></p:bodyStyle>'
        '<p:otherStyle><a:lvl1pPr/></p:otherStyle></p:txStyles>'
        '<p:timing/></p:sldMaster>'
    )
    slide_master_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
        'Target="../slideLayouts/slideLayout1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" '
        'Target="../theme/theme1.xml"/>'
        '</Relationships>'
    )

    theme1 = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'name="LumiLearnTheme"><a:themeElements>'
        '<a:clrScheme name="Office">'
        '<a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
        '<a:dk2><a:srgbClr val="1F497D"/></a:dk2><a:lt2><a:srgbClr val="EEECE1"/></a:lt2>'
        '<a:accent1><a:srgbClr val="4F81BD"/></a:accent1><a:accent2><a:srgbClr val="C0504D"/></a:accent2>'
        '<a:accent3><a:srgbClr val="9BBB59"/></a:accent3><a:accent4><a:srgbClr val="8064A2"/></a:accent4>'
        '<a:accent5><a:srgbClr val="4BACC6"/></a:accent5><a:accent6><a:srgbClr val="F79646"/></a:accent6>'
        '<a:hlink><a:srgbClr val="0000FF"/></a:hlink><a:folHlink><a:srgbClr val="800080"/></a:folHlink>'
        '</a:clrScheme>'
        '<a:fontScheme name="Office"><a:majorFont><a:latin typeface="微软雅黑"/>'
        '<a:ea typeface="微软雅黑"/></a:majorFont><a:minorFont><a:latin typeface="微软雅黑"/>'
        '<a:ea typeface="微软雅黑"/></a:minorFont></a:fontScheme>'
        '<a:fmtScheme name="Office"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
        '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
        '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
        '<a:lnStyleLst><a:ln w="6350" cap="flat" cmpd="sng" algn="ctr"/><a:ln w="12700" cap="flat" cmpd="sng" algn="ctr"/>'
        '<a:ln w="19050" cap="flat" cmpd="sng" algn="ctr"/></a:lnStyleLst>'
        '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle>'
        '<a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle>'
        '</a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
        '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
        '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
        '</a:fmtScheme></a:themeElements></a:theme>'
    )
    theme_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="presentation.xml"/></Relationships>'
    )

    # --- OPC 包
    files = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/ppt/presentation.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
            '<Override PartName="/ppt/slideMasters/slideMaster1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
            '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
            '<Override PartName="/ppt/theme/theme1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>' +
            "".join(
                f'<Override PartName="/ppt/slides/slide{i}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                for i in range(1, n + 1)) +
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="ppt/presentation.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
            'Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
            'Target="docProps/app.xml"/></Relationships>'
        ),
        "ppt/presentation.xml": presentation_xml,
        "ppt/_rels/presentation.xml.rels": presentation_rels,
        "ppt/slideMasters/slideMaster1.xml": slide_master,
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": slide_master_rels,
        "ppt/slideLayouts/slideLayout1.xml": slide_layout,
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": slide_layout_rels,
        "ppt/theme/theme1.xml": theme1,
        "ppt/theme/_rels/theme1.xml.rels": theme_rels,
        "docProps/core.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{_px(title)}</dc:title>'
            '<dc:creator>LumiLearn</dc:creator></cp:coreProperties>'
        ),
        "docProps/app.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            f'<Application>{_px(title)}</Application><Slides>{n}</Slides></Properties>'
        ),
    }
    files.update(slides_xml)
    files.update(slides_rels)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# PDF：Type0 CID 中文字体（Identity-H / Adobe-GB1，纯标准库）
# ---------------------------------------------------------------------------
def _pdf_hex(text: str) -> str:
    """Identity-H：把 Unicode 码点按 2 字节大端编码为 <...> 十六进制串。"""
    out = []
    for ch in text:
        out.append(f"{ord(ch):04X}")
    return "<" + "".join(out) + ">"


def build_pdf(slides: list, title: str) -> bytes:
    W, H = 595, 842  # A4 portrait (72dpi)
    pages = []
    for s in slides:
        lines = []
        t = s.get("title", "")
        sub = s.get("subtitle", "")
        points = _bullet_points(s.get("content", ""))
        if t:
            lines.append((t, 18, "0 0 0 rg"))
        if sub:
            lines.append((sub, 12, "0.3 0.3 0.3 rg"))
        if t or sub:
            lines.append(("", 0, ""))  # 空行
        for pt in points[:10]:
            lines.append((pt, 11.5, "0.15 0.15 0.15 rg"))

        content = []
        y = H - 60
        for text, size, color in lines:
            if text:
                content.append(
                    f"BT /F1 {size} Tf {color} 60 {y:.2f} Td {_pdf_hex(text)} Tj ET\n"
                )
            y -= (size or 11) * 1.7

        pages.append(f"{content and 'q '+''.join(content)+'Q' or ''}\n")
        del text, size, color
    content_stream = "\n".join(pages)

    n = len(slides)
    objs = []
    objs.append((1, "<< /Type /Catalog /Pages 2 0 R >>"))
    objs.append((2, f"<< /Type /Pages /Kids [{''.join(f'{i} 0 R ' for i in range(3, 3 + n))}] /Count {n} >>"))
    for i in range(n):
        oid = 3 + i
        objs.append((oid, (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] "
            "/Resources << /Font << /F1 101 0 R >> >> /Contents 201 0 R >>"
        )))
    # 内容流
    for i in range(n):
        objs.append((201, pkg := ""))  # placeholder
    # 实际内容流对象
    content_objs = []
    page_content = []
    # 因需要一一对应，直接构建 content 对象
    # 重新按页构建内容流对象
    # （为清晰，重新构造 content 对象列表）
    # —— 上面已简化，真正内容放在下方构造

    # 字体：Type0 CID, Identity-H, Adobe-GB1 STSong-Light（viewer 自带，零嵌入）
    font_obj = (
        "<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        "/Encoding /Identity-H "
        "/DescendantFonts [102 0 R] /ToUnicode 103 0 R >>"
    )

    # 重建整洁结构
    objects = {1: "<< /Type /Catalog /Pages 2 0 R >>",
               "#COUNT": n}
    # 简化：直接按对象编号写
    objs_out = {}
    objs_out[1] = "<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{3 + i} 0 R" for i in range(n))
    objs_out[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>"
    for i in range(n):
        objs_out[3 + i] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] "
            "/Resources << /Font << /F1 101 0 R >> >> "
            f"/Contents {101 + 100 + i} 0 R >>"
        )
    # 内容对象（pages[i] 已是含 hex 文本的 str；以 latin1 字节写入，
    # /Length 取真实字节长，避免 bytes 被 f-string 转 repr 破坏内容流）。
    for i in range(n):
        cw = pages[i]
        objs_out[201 + i] = f"<< /Length {len(cw.encode('latin1'))} >>\nstream\n{cw}endstream"
    # 字体对象
    objs_out[101] = (
        "<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light "
        "/Encoding /Identity-H /DescendantFonts [102 0 R] >>"
    )
    objs_out[102] = (
        "<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 5 >> "
        "/FontDescriptor 103 0 R /DW 1000 >>"
    )
    objs_out[103] = (
        "<< /Type /FontDescriptor /FontName /STSong-Light /Flags 4 /CapHeight 859 "
        "/Ascent 859 /Descent -141 /StemV 80 /ItalicAngle 0 >>"
    )
    objs_out[104] = (
        "<< /Type /Font /Subtype /Type0 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )

    # 需要有 F1 ---> 101 引用；当前页面引用 F1 101，但 F1 是/Helvetica(104)。
    # 修正：页面字体统一指向 101（Type0 CID）。Helvetica(104) 仅作兜底，可保留不引用。
    # 这里确保合法：引用到 101。

    # 对象编号动态上限：内容对象 201..201+n-1，字体对象到 104，页面 3..3+n-1
    max_obj = max(201 + n - 1, 104)
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = {}
    for oid in range(1, max_obj + 1):
        if oid not in objs_out:
            continue
        offsets[oid] = out.tell()
        out.write(f"{oid} 0 obj\n".encode("latin1"))
        out.write(objs_out[oid].encode("latin1"))
        out.write(b"\nendobj\n")
    xref_pos = out.tell()
    out.write(f"xref\n0 {max_obj + 1}\n".encode("latin1"))
    out.write(b"0000000000 65535 f \n")
    for oid in range(1, max_obj + 1):
        if oid in offsets:
            out.write(f"{offsets[oid]:010d} 00000 n \n".encode("latin1"))
        else:
            out.write(b"0000000000 65535 f \n")
    out.write(
        f"trailer\n<< /Size {max_obj + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("latin1")
    )
    return out.getvalue()