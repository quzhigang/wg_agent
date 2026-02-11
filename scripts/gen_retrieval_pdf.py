"""生成检索逻辑PDF文档"""
import os
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 注册中文字体
FONT_PATHS = [
    "C:/Windows/Fonts/msyh.ttc",   # 微软雅黑
    "C:/Windows/Fonts/simsun.ttc",  # 宋体
    "C:/Windows/Fonts/simhei.ttf",  # 黑体
]

CN_FONT = None
CN_FONT_BOLD = None

for fp in FONT_PATHS:
    if os.path.exists(fp):
        name = os.path.splitext(os.path.basename(fp))[0]
        try:
            pdfmetrics.registerFont(TTFont(name, fp))
            if CN_FONT is None:
                CN_FONT = name
                CN_FONT_BOLD = name
            break
        except Exception:
            continue

if CN_FONT is None:
    print("警告: 未找到中文字体，PDF中文可能无法正常显示")
    CN_FONT = "Helvetica"
    CN_FONT_BOLD = "Helvetica-Bold"

# 颜色
PRIMARY = HexColor("#1a5276")
ACCENT = HexColor("#2980b9")
LIGHT_BG = HexColor("#eaf2f8")
DARK_TEXT = HexColor("#2c3e50")
GRAY = HexColor("#7f8c8d")


def build_styles():
    """构建段落样式"""
    styles = {}
    styles["title"] = ParagraphStyle(
        "Title", fontName=CN_FONT, fontSize=22, leading=30,
        alignment=TA_CENTER, textColor=PRIMARY, spaceAfter=6,
    )
    styles["subtitle"] = ParagraphStyle(
        "Subtitle", fontName=CN_FONT, fontSize=11, leading=16,
        alignment=TA_CENTER, textColor=GRAY, spaceAfter=20,
    )
    styles["h1"] = ParagraphStyle(
        "H1", fontName=CN_FONT, fontSize=16, leading=24,
        textColor=PRIMARY, spaceBefore=18, spaceAfter=8,
    )
    styles["h2"] = ParagraphStyle(
        "H2", fontName=CN_FONT, fontSize=13, leading=20,
        textColor=ACCENT, spaceBefore=12, spaceAfter=6,
    )
    styles["body"] = ParagraphStyle(
        "Body", fontName=CN_FONT, fontSize=10.5, leading=18,
        textColor=DARK_TEXT, spaceAfter=4,
    )
    styles["bullet"] = ParagraphStyle(
        "Bullet", fontName=CN_FONT, fontSize=10.5, leading=18,
        textColor=DARK_TEXT, leftIndent=20, spaceAfter=2,
        bulletIndent=8, bulletFontSize=10,
    )
    styles["code"] = ParagraphStyle(
        "Code", fontName=CN_FONT, fontSize=9, leading=14,
        textColor=HexColor("#c0392b"), leftIndent=20, spaceAfter=2,
    )
    styles["note"] = ParagraphStyle(
        "Note", fontName=CN_FONT, fontSize=9.5, leading=15,
        textColor=GRAY, leftIndent=16, spaceAfter=4,
    )
    return styles


def build_content(styles):
    """构建文档内容"""
    story = []
    s = styles

    # 标题
    story.append(Spacer(1, 30))
    story.append(Paragraph("卫共流域数字孪生智能体", s["title"]))
    story.append(Paragraph("知识检索逻辑梳理文档", s["title"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("wg_agent / PageIndex 检索系统", s["subtitle"]))
    story.append(HRFlowable(
        width="80%", thickness=1, color=ACCENT,
        spaceAfter=20, spaceBefore=10
    ))

    # ===== 一、两种检索方式 =====
    story.append(Paragraph("一、两种检索方式", s["h1"]))

    story.append(Paragraph("1. 向量检索（Vector）", s["h2"]))
    for line in [
        "- 使用 ChromaDB 向量数据库存储文档节点的 embedding",
        "- Embedding 模型: bge-m3 (通过 Ollama 部署在 10.20.2.135:11434)",
        "- 检索流程: 用户查询 -> embedding -> ChromaDB 相似度搜索 -> 返回 top_k 个最相关节点",
        "- 每个节点包含: doc_name, node_id, title, summary, score",
        "- 支持多知识库并行检索 (search_multi_kb)",
    ]:
        story.append(Paragraph(line, s["bullet"]))

    story.append(Paragraph("2. LLM 层进式检索（LLM Hierarchical）", s["h2"]))
    for line in [
        "- 参考 PageIndex (VectifyAI) 的 Reasoning-based RAG 理念",
        "- 让 LLM 阅读文档的树形目录结构，通过推理定位相关节点",
        "- 检索流程:",
    ]:
        story.append(Paragraph(line, s["bullet"]))

    steps = [
        "a) 加载文档的 _structure.json 树结构文件",
        "b) 去掉 text 字段（减少 token 消耗），保留 node_id / title / summary",
        "c) 将树结构 + 用户问题发送给 LLM（qwen3-4b）",
        "d) LLM 推理返回最相关的 node_id 列表",
        "e) 根据 node_id 从原始结构中提取完整内容",
    ]
    for step in steps:
        story.append(Paragraph(
            f"&nbsp;&nbsp;&nbsp;&nbsp;{step}", s["bullet"]
        ))

    for line in [
        "- LLM 配置: qwen3-4b, DashScope API (阿里云通义千问)",
        "- 评分机制: 按排名赋分（第1个=1.0, 第2个=0.9, 递减, 最低0.1）",
        "- 支持并发处理多个文档 (asyncio.gather)",
    ]:
        story.append(Paragraph(line, s["bullet"]))

    # ===== 二、三层架构 =====
    story.append(Paragraph("二、三层架构", s["h1"]))

    story.append(Paragraph("第一层: PageIndex 检索引擎", s["h2"]))
    for line in [
        "- vector_index.py: 向量检索核心，封装 ChromaDB 操作",
        "- llm_retriever.py: LLM 层进式检索核心，封装 LLM 调用和树结构解析",
        "- kb_manager.py: 知识库管理，维护 9 个知识库的路径和配置",
    ]:
        story.append(Paragraph(line, s["bullet"]))

    story.append(Paragraph("第二层: API 服务 (PageIndex/api.py)", s["h2"]))
    story.append(Paragraph(
        "运行在端口 8502，提供 RESTful 接口:", s["body"]
    ))

    # API 表格
    api_data = [
        ["接口", "方式", "说明"],
        ["POST /query/raw", "向量检索", "纯向量检索，返回原始结果"],
        ["POST /query/llm", "LLM检索", "纯 LLM 层进式检索"],
        ["POST /query/compare", "对比检索", "同时执行两种检索并返回对比结果"],
        ["POST /query", "RAG问答", "检索 + LLM 生成回答"],
    ]
    api_table = Table(api_data, colWidths=[120, 70, 220])
    api_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, -1), CN_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(Spacer(1, 6))
    story.append(api_table)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "请求体格式: {q: 查询文本, top_k: 返回数量, kb_ids: 知识库ID列表}",
        s["note"]
    ))

    story.append(Paragraph(
        "第三层: RAG 检索器 (src/rag/retriever.py)", s["h2"]
    ))
    for line in [
        "- 智能体主项目的检索入口，封装 PageIndex 的两种检索方式",
        "- retrieve(): 向量检索",
        "- retrieve_llm(): LLM 层进式检索",
        "- retrieve_compare(): 对比检索（并发执行两种方式）",
        "- get_relevant_context(): 统一入口，根据 retrieval_mode 参数选择检索方式",
    ]:
        story.append(Paragraph(line, s["bullet"]))

    # ===== 三、前端交互 =====
    story.append(Paragraph("三、前端交互", s["h1"]))
    for line in [
        "- PageIndex 前端 (Streamlit, app.py) 提供两个使用检索的 Tab:",
        "&nbsp;&nbsp;&nbsp;&nbsp;- Tab1 智能对话: 支持选择 向量检索 / LLM检索 / 检索对比",
        "&nbsp;&nbsp;&nbsp;&nbsp;- Tab5 知识检索: 支持选择 向量检索 / LLM检索 / 检索对比",
        "- 检索对比模式使用双栏布局 (st.columns(2)) 并排展示两种结果",
        "- 智能体主项目通过 RAGRetriever 调用，默认使用 .env 中 DEFAULT_RETRIEVAL_MODE 配置",
    ]:
        story.append(Paragraph(line, s["bullet"]))

    # ===== 四、配置项 =====
    story.append(Paragraph("四、配置项", s["h1"]))

    config_data = [
        ["配置项", "位置", "说明"],
        ["OPENAI_API_KEY", "PageIndex/.env", "LLM API 密钥（通义千问）"],
        ["OPENAI_API_BASE", "PageIndex/.env", "LLM API 地址"],
        ["OPENAI_MODEL_NAME", "PageIndex/.env", "LLM 模型名 (qwen3-32b)"],
        ["EMBEDDING_MODEL_NAME", "PageIndex/.env", "Embedding 模型 (bge-m3)"],
        ["EMBEDDING_MODEL_API_URL", "PageIndex/.env", "Ollama 服务地址"],
        ["LLM_RETRIEVAL_API_KEY", "PageIndex/.env", "LLM检索专用密钥"],
        ["LLM_RETRIEVAL_API_BASE", "PageIndex/.env", "LLM检索专用API地址"],
        ["LLM_RETRIEVAL_MODEL_NAME", "PageIndex/.env", "LLM检索模型 (qwen3-4b)"],
        ["DEFAULT_RETRIEVAL_MODE", ".env (项目根)", "默认检索方式 (vector/llm)"],
    ]
    cfg_table = Table(config_data, colWidths=[150, 100, 180])
    cfg_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, -1), CN_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(Spacer(1, 6))
    story.append(cfg_table)

    # ===== 五、数据流向 =====
    story.append(Paragraph("五、数据流向", s["h1"]))

    story.append(Paragraph("向量检索数据流:", s["h2"]))
    story.append(Paragraph(
        "用户查询 -> RAGRetriever.retrieve() -> MultiKBVectorIndex.search_multi_kb()"
        " -> ChromaDB 相似度搜索 -> 加载 _structure.json 获取完整文本 -> 返回结果",
        s["body"]
    ))

    story.append(Paragraph("LLM 检索数据流:", s["h2"]))
    story.append(Paragraph(
        "用户查询 -> RAGRetriever.retrieve_llm() -> LLMRetriever.search()"
        " -> 加载 _structure.json 树结构 -> 去掉 text 字段 -> 发送给 LLM 推理"
        " -> 返回 node_id 列表 -> 从原始结构提取内容 -> 返回结果",
        s["body"]
    ))

    story.append(Paragraph("对比检索数据流:", s["h2"]))
    story.append(Paragraph(
        "用户查询 -> RAGRetriever.retrieve_compare()"
        " -> asyncio.gather(向量检索, LLM检索) -> 并行执行 -> 返回两组结果",
        s["body"]
    ))

    # ===== 六、知识库列表 =====
    story.append(Paragraph("六、知识库列表", s["h1"]))

    kb_data = [
        ["知识库ID", "名称"],
        ["catchment_basin", "流域概况"],
        ["water_project", "水利工程"],
        ["monitor_site", "监测站点"],
        ["history_flood", "历史洪水"],
        ["flood_preplan", "防洪预案"],
        ["system_function", "系统功能"],
        ["hydro_model", "水文模型"],
        ["catchment_planning", "流域规划"],
        ["project_designplan", "工程设计"],
    ]
    kb_table = Table(kb_data, colWidths=[160, 160])
    kb_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, -1), CN_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(Spacer(1, 6))
    story.append(kb_table)

    return story


def main():
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "检索逻辑.pdf"
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="检索逻辑",
        author="wg_agent",
    )

    styles = build_styles()
    story = build_content(styles)
    doc.build(story)
    print(f"PDF 已生成: {output_path}")


if __name__ == "__main__":
    main()
