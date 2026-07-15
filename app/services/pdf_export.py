"""
PDF 导出服务：使用 reportlab 生成对话记录的 PDF 文档

支持中文（微软雅黑），A4 竖版，每条消息带角色标注和时间戳
"""
import os
import json
import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
# 字体注册（模块加载时执行一次）
# ============================================================
_FONT_PATHS = [
    ("YaHei", "C:/Windows/Fonts/msyh.ttc"),
    ("YaHei", "C:/Windows/Fonts/msyh.ttf"),
    ("SimSun", "C:/Windows/Fonts/simsun.ttc"),
    ("SimSun", "C:/Windows/Fonts/simsun.ttf"),
    ("SimHei", "C:/Windows/Fonts/simhei.ttf"),
]

_FONT_NAME = None  # 实际注册成功的中文字体名
_FONT_BOLD = None

for _name, _path in _FONT_PATHS:
    if os.path.exists(_path):
        try:
            pdfmetrics.registerFont(TTFont(_name, _path))
            if _FONT_NAME is None:
                _FONT_NAME = _name
            if _name == "YaHei" and os.path.exists("C:/Windows/Fonts/msyhbd.ttc"):
                try:
                    pdfmetrics.registerFont(TTFont("YaHeiBold", "C:/Windows/Fonts/msyhbd.ttc"))
                    _FONT_BOLD = "YaHeiBold"
                except Exception:
                    _FONT_BOLD = _name  # 回退到常规体
            elif _FONT_BOLD is None:
                _FONT_BOLD = _name
        except Exception:
            continue

if _FONT_NAME is None:
    _FONT_NAME = "Helvetica"
    _FONT_BOLD = "Helvetica-Bold"


# ============================================================
# 样式定义
# ============================================================
_PRIMARY_COLOR = HexColor("#2b5fd9")
_LIGHT_GRAY = HexColor("#f0f2f5")
_BORDER_COLOR = HexColor("#e8ecf1")
_TEXT_PRIMARY = HexColor("#1a2332")
_TEXT_SECONDARY = HexColor("#5a6a7e")

_STYLES = getSampleStyleSheet()

# 封面标题
COVER_TITLE = ParagraphStyle(
    "CoverTitle", _STYLES["Title"],
    fontName=_FONT_BOLD or _FONT_NAME,
    fontSize=22, leading=30, spaceAfter=12,
    textColor=_PRIMARY_COLOR,
    alignment=TA_CENTER,
)
# 封面副标题
COVER_SUBTITLE = ParagraphStyle(
    "CoverSubtitle", _STYLES["Normal"],
    fontName=_FONT_NAME,
    fontSize=12, leading=18, spaceAfter=6,
    textColor=_TEXT_SECONDARY,
    alignment=TA_CENTER,
)
# 章节标题（对话标题）
SECTION_TITLE = ParagraphStyle(
    "SectionTitle", _STYLES["Heading2"],
    fontName=_FONT_BOLD or _FONT_NAME,
    fontSize=15, leading=22, spaceBefore=16, spaceAfter=4,
    textColor=_TEXT_PRIMARY,
)
# 对话元信息
CONV_META = ParagraphStyle(
    "ConvMeta", _STYLES["Normal"],
    fontName=_FONT_NAME,
    fontSize=9, leading=14, spaceBefore=2, spaceAfter=8,
    textColor=_TEXT_SECONDARY,
)
# 消息角色标签
ROLE_LABEL_USER = ParagraphStyle(
    "RoleLabelUser", _STYLES["Normal"],
    fontName=_FONT_BOLD or _FONT_NAME,
    fontSize=10, leading=16, spaceBefore=8, spaceAfter=2,
    textColor=_PRIMARY_COLOR,
)
ROLE_LABEL_AI = ParagraphStyle(
    "RoleLabelAI", _STYLES["Normal"],
    fontName=_FONT_BOLD or _FONT_NAME,
    fontSize=10, leading=16, spaceBefore=8, spaceAfter=2,
    textColor=HexColor("#10b981"),
)
# 消息正文
MSG_BODY = ParagraphStyle(
    "MsgBody", _STYLES["Normal"],
    fontName=_FONT_NAME,
    fontSize=10, leading=16, spaceBefore=2, spaceAfter=4,
    textColor=_TEXT_PRIMARY,
    leftIndent=8,
)
# 消息元数据（token/时间）
MSG_META = ParagraphStyle(
    "MsgMeta", _STYLES["Normal"],
    fontName=_FONT_NAME,
    fontSize=8, leading=12, spaceBefore=1, spaceAfter=6,
    textColor=_TEXT_SECONDARY,
    leftIndent=8,
)
# 页脚
FOOTER_STYLE = ParagraphStyle(
    "Footer", _STYLES["Normal"],
    fontName=_FONT_NAME,
    fontSize=8, leading=12,
    textColor=_TEXT_SECONDARY,
    alignment=TA_CENTER,
)


def _page_template(canvas, doc):
    """PDF 页眉页脚模板"""
    canvas.saveState()
    # 页眉
    canvas.setFont(_FONT_NAME, 8)
    canvas.setFillColor(_TEXT_SECONDARY)
    canvas.drawString(2 * cm, A4[1] - 1.5 * cm, "智能瞭望与问数系统 · 对话记录导出")
    canvas.setStrokeColor(_BORDER_COLOR)
    canvas.line(2 * cm, A4[1] - 1.7 * cm, A4[0] - 2 * cm, A4[1] - 1.7 * cm)
    # 页脚
    canvas.drawString(2 * cm, 1.2 * cm, datetime.datetime.now().strftime("导出时间: %Y-%m-%d %H:%M"))
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"第 {canvas.getPageNumber()} 页")
    canvas.restoreState()


def _strip_markdown(text):
    """简单去除 markdown 标记，保留纯文本"""
    import re
    if not text:
        return ""
    # 去除代码块
    text = re.sub(r'```[\s\S]*?```', '[代码块]', text)
    # 去除行内代码
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 去除标题标记
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # 去除加粗/斜体
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # 去除链接保留文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 去除图片
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'[图片: \1]', text)
    # 去除多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def generate_conversations_pdf(conversations, username):
    """
    生成对话记录 PDF

    Args:
        conversations: list[dict] — 对话记录列表，每条含 title, messages(JSON字符串), created_at, updated_at
        username: str — 导出用户名

    Returns:
        bytes — PDF 文件的二进制内容
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2.2 * cm, bottomMargin=2 * cm,
        title="智能瞭望与问数 — 对话记录导出",
        author=username,
    )

    story = []

    # ======== 封面 ========
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("智能瞭望与问数", COVER_TITLE))
    story.append(Paragraph("对话记录导出", COVER_SUBTITLE))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        f"导出用户: {username}<br/>"
        f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
        f"对话数量: {len(conversations)}<br/>"
        f"系统名称: DataFinderAgentOS",
        COVER_SUBTITLE
    ))
    story.append(PageBreak())

    # ======== 每个对话 ========
    for i, conv in enumerate(conversations):
        title = conv.get("title", "新对话")
        created_at = conv.get("created_at", "")
        updated_at = conv.get("updated_at", "")

        # --- 对话标题 ---
        story.append(Paragraph(f"对话 {i+1}: {title}", SECTION_TITLE))

        # --- 对话元信息 ---
        meta_parts = []
        if created_at:
            meta_parts.append(f"创建: {created_at}")
        if updated_at:
            meta_parts.append(f"更新: {updated_at}")
        story.append(Paragraph(" | ".join(meta_parts), CONV_META))

        # 分割线
        story.append(HRFlowable(
            width="100%", thickness=0.5,
            color=_BORDER_COLOR, spaceBefore=4, spaceAfter=8
        ))

        # --- 消息列表 ---
        messages = conv.get("messages", [])
        if isinstance(messages, str):
            try:
                messages = json.loads(messages)
            except (json.JSONDecodeError, TypeError):
                messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            employee_name = msg.get("employee_name", "")
            tokens = msg.get("tokens", 0)
            time_ms = msg.get("time_ms", 0)

            # 角色标签
            if role == "user":
                story.append(Paragraph("👤 用户", ROLE_LABEL_USER))
            else:
                label = "🤖 AI"
                if employee_name:
                    label += f" · {employee_name}"
                story.append(Paragraph(label, ROLE_LABEL_AI))

            # 消息正文（清理 Markdown）
            clean_content = _strip_markdown(content)
            if clean_content:
                story.append(Paragraph(clean_content.replace("\n", "<br/>"), MSG_BODY))
            else:
                story.append(Paragraph("[非文本内容]", MSG_BODY))

            # 元数据
            meta_items = []
            if time_ms and int(time_ms) > 0:
                meta_items.append(f"响应时间: {int(time_ms)}ms")
            if tokens and int(tokens) > 0:
                meta_items.append(f"Token: {int(tokens)}")
            if meta_items:
                story.append(Paragraph(" · ".join(meta_items), MSG_META))

        # 对话间分页（最后一个不加）
        if i < len(conversations) - 1:
            story.append(PageBreak())

    # ======== 构建 PDF ========
    doc.build(story, onFirstPage=_page_template, onLaterPages=_page_template)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
