# Web模板匹配和管理系统实施计划

## 一、项目概述

### 1.1 目标
为卫共流域数字孪生智能体系统实现Web模板的智能匹配和管理功能，采用与工作流匹配相同的两阶段匹配策略（向量检索 + LLM精选）。

### 1.2 核心功能
1. **模板元数据管理** - 数据库存储模板信息
2. **模板向量化存储** - ChromaDB向量检索
3. **两阶段模板匹配** - 向量粗筛 + LLM精选
4. **模板管理页面** - 类似工作流管理的Web界面
5. **模板管理API** - RESTful接口

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Web 前端层                                │
├─────────────────────────────────────────────────────────────┤
│  web_templates.html (模板管理页面)                           │
│  web/web_templates/res_module/ (预定义模板文件)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    API 层                                    │
├─────────────────────────────────────────────────────────────┤
│  src/api/web_templates.py (模板管理 API)                     │
│  - CRUD 操作                                                 │
│  - 向量索引管理                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  业务逻辑层                                  │
├─────────────────────────────────────────────────────────────┤
│  src/output/template_vector_index.py (向量索引)              │
│  src/output/template_match_service.py (匹配服务)             │
│  src/output/page_generator.py (页面生成 - 修改)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  数据存储层                                  │
├─────────────────────────────────────────────────────────────┤
│  MySQL (web_templates 表)                                    │
│  ChromaDB (template_vectors/)                                │
│  文件系统 (web/web_templates/)                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、实施步骤

### 步骤1: 数据库模型 (WebTemplate)

**文件**: `src/models/database.py`

**新增内容**:
```python
class WebTemplate(Base):
    """Web模板元数据表"""
    __tablename__ = "web_templates"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(100), nullable=False, unique=True)  # 英文标识
    display_name = Column(String(100), nullable=False)  # 中文名称
    description = Column(Text, nullable=True)  # 详细描述
    template_path = Column(String(255), nullable=False)  # 模板路径
    supported_sub_intents = Column(Text, nullable=False)  # 支持的子意图(JSON数组)
    template_type = Column(String(50), default="full_page")  # 模板类型
    data_schema = Column(Text, nullable=True)  # 数据要求(JSON)
    trigger_pattern = Column(Text, nullable=True)  # 触发模式
    features = Column(Text, nullable=True)  # 特性标签(JSON数组)
    priority = Column(Integer, default=0)  # 优先级
    use_count = Column(Integer, default=0)  # 使用次数
    success_count = Column(Integer, default=0)  # 成功次数
    is_active = Column(Boolean, default=True)  # 是否激活
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

### 步骤2: 向量索引类 (WebTemplateVectorIndex)

**新建文件**: `src/output/template_vector_index.py`

**核心功能**:
- 复用 PageIndex 的 OllamaEmbedding
- ChromaDB 持久化存储 (`template_vectors/`)
- 支持按子意图过滤检索
- L2距离转相似度分数

**关键方法**:
| 方法 | 功能 |
|------|------|
| `index_template()` | 索引单个模板 |
| `delete_template()` | 删除模板索引 |
| `search()` | 向量检索模板 |
| `get_stats()` | 获取统计信息 |
| `rebuild_index_from_db()` | 从数据库重建索引 |

---

### 步骤3: 模板匹配服务 (TemplateMatchService)

**新建文件**: `src/output/template_match_service.py`

**两阶段匹配流程**:
```
用户问题 + 执行结果摘要
        ↓
第一阶段: 向量检索 Top-5 候选
        ↓
第二阶段: LLM精选最佳模板
        ↓
返回匹配的模板信息
```

**关键方法**:
| 方法 | 功能 |
|------|------|
| `match_template()` | 两阶段模板匹配 |
| `_llm_select_template()` | LLM精选 |
| `get_template_by_id()` | 根据ID获取模板 |
| `get_default_template()` | 获取默认模板 |

---

### 步骤4: 模板管理API

**新建文件**: `src/api/web_templates.py`

**API端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/web-templates` | 获取模板列表(分页) |
| GET | `/web-templates/{id}` | 获取模板详情 |
| POST | `/web-templates` | 创建模板 |
| PUT | `/web-templates/{id}` | 编辑模板 |
| DELETE | `/web-templates/{id}` | 删除模板 |
| PATCH | `/web-templates/{id}/toggle` | 启用/禁用模板 |
| POST | `/web-templates/vector-index/rebuild` | 重建向量索引 |
| GET | `/web-templates/vector-index/stats` | 获取索引统计 |
| POST | `/web-templates/vector-index/search` | 向量检索模板 |
| POST | `/web-templates/{id}/index` | 索引单个模板 |

---

### 步骤5: 模板管理页面

**新建文件**: `web/main/web_templates.html`

**功能设计** (参考 saved_workflows.html):
- 模板列表表格 (分页)
- 按子意图过滤
- 查看模板详情 (模态框)
- 编辑模板信息 (模态框)
- 删除模板 (确认)
- 向量索引管理 (重建/统计)

**表格列**:
- 序号
- 模板名称 (display_name)
- 模板ID (name)
- 模板路径
- 支持的子意图 (彩色徽章)
- 特性标签
- 优先级
- 使用次数
- 操作按钮

---

### 步骤6: 集成到页面生成器

**修改文件**: `src/output/page_generator.py`

**修改内容**:
1. 新增 `generate_page_with_template()` 方法
2. 支持使用预定义模板生成页面
3. 模板数据注入机制

```python
async def generate_page_with_template(
    self,
    template_info: Dict[str, Any],
    data: Dict[str, Any],
    title: str = ""
) -> str:
    """
    使用预定义模板生成页面

    Args:
        template_info: 模板信息 (包含 template_path)
        data: 要注入的数据
        title: 页面标题

    Returns:
        生成的页面URL
    """
    # 1. 读取模板文件
    # 2. 注入数据 (替换占位符或通过JS变量)
    # 3. 保存到 generated_pages
    # 4. 返回访问URL
```

---

### 步骤7: 集成到Controller

**修改文件**: `src/agents/controller.py`

**修改 `_generate_web_page_response()` 方法**:

```python
async def _generate_web_page_response(self, state: AgentState) -> Dict[str, Any]:
    # 1. 获取执行结果和子意图
    sub_intent = state.get('business_sub_intent', '')
    execution_results = state.get('execution_results', [])

    # 2. 调用模板匹配服务
    template_match_service = get_template_match_service()
    matched_template = await template_match_service.match_template(
        user_message=state.get('user_message', ''),
        sub_intent=sub_intent,
        execution_results=execution_results,
        execution_summary=self._summarize_results(execution_results)
    )

    # 3. 如果匹配到模板，使用模板生成页面
    if matched_template and matched_template.get('confidence', 0) >= 0.7:
        page_url = await self.page_generator.generate_page_with_template(
            template_info=matched_template,
            data=self._prepare_template_data(execution_results),
            title=self._generate_title(state)
        )
        return {
            "output_type": "web_page",
            "generated_page_url": page_url,
            "template_used": matched_template.get('display_name')
        }

    # 4. 否则使用原有的动态生成逻辑
    return await self._generate_dynamic_page(state)
```

---

### 步骤8: 注册路由

**修改文件**: `src/main.py`

**新增内容**:
```python
from .api import web_templates_router

# 在 create_app() 中添加
app.include_router(web_templates_router)
```

**修改文件**: `src/api/__init__.py`

**新增导出**:
```python
from .web_templates import router as web_templates_router
```

---

### 步骤9: 初始化预定义模板数据

**新建文件**: `scripts/init_web_templates.py`

**功能**: 将现有的 `res_module` 模板注册到数据库

```python
# 初始模板数据
INITIAL_TEMPLATES = [
    {
        "name": "res_flood_forecast",
        "display_name": "水库洪水预报结果展示",
        "description": "用于展示水库洪水预报结果，包含地图定位、入库/出库流量曲线、水位变化图表、关键指标卡片",
        "template_path": "res_module/index.html",
        "supported_sub_intents": ["flood_forecast", "manual_forecast", "auto_forecast"],
        "template_type": "full_page",
        "trigger_pattern": "水库预报结果 洪水预报 入库流量 出库流量 水位变化 预报方案结果 水库水情",
        "features": ["map", "chart", "realtime", "reservoir"],
        "priority": 10
    }
]
```

---

## 四、文件清单

### 新建文件
| 文件路径 | 用途 |
|----------|------|
| `src/output/template_vector_index.py` | 模板向量索引类 |
| `src/output/template_match_service.py` | 模板匹配服务 |
| `src/api/web_templates.py` | 模板管理API |
| `web/main/web_templates.html` | 模板管理页面 |
| `scripts/init_web_templates.py` | 初始化模板数据脚本 |

### 修改文件
| 文件路径 | 修改内容 |
|----------|----------|
| `src/models/database.py` | 新增 WebTemplate 模型 |
| `src/output/page_generator.py` | 新增模板生成方法 |
| `src/agents/controller.py` | 集成模板匹配逻辑 |
| `src/main.py` | 注册新路由 |
| `src/api/__init__.py` | 导出新路由 |

### 新建目录
| 目录路径 | 用途 |
|----------|------|
| `template_vectors/` | ChromaDB向量存储 |

---

## 五、数据流程

### 5.1 模板匹配流程

```
用户问题: "查询盘石头水库的洪水预报结果"
                    ↓
Controller._generate_web_page_response()
                    ↓
TemplateMatchService.match_template()
    ├─ 第一阶段: 向量检索
    │   query = "查询盘石头水库的洪水预报结果 水库预报结果..."
    │   sub_intent = "flood_forecast"
    │   → 返回 Top-5 候选模板
    │
    └─ 第二阶段: LLM精选
        → 选择 "水库洪水预报结果展示" 模板
                    ↓
PageGenerator.generate_page_with_template()
    ├─ 读取 res_module/index.html
    ├─ 注入预报数据
    └─ 保存到 generated_pages/
                    ↓
返回页面URL: /pages/res_flood_forecast_xxx.html
```

### 5.2 模板管理流程

```
管理员访问 /ui/web_templates.html
                    ↓
前端调用 GET /web-templates
                    ↓
显示模板列表
                    ↓
编辑模板 → PUT /web-templates/{id}
    └─ 自动更新向量索引
                    ↓
重建索引 → POST /web-templates/vector-index/rebuild
```

---

## 六、验证方案

### 6.1 单元测试
1. 测试 WebTemplate 数据库模型 CRUD
2. 测试 WebTemplateVectorIndex 索引和检索
3. 测试 TemplateMatchService 两阶段匹配

### 6.2 集成测试
1. 启动服务: `python -m src.main`
2. 运行初始化脚本: `python scripts/init_web_templates.py`
3. 访问管理页面: http://localhost:8000/ui/web_templates.html
4. 验证模板列表显示
5. 测试编辑、删除功能
6. 测试向量索引重建

### 6.3 端到端测试
1. 发送洪水预报查询请求
2. 验证是否匹配到 `res_flood_forecast` 模板
3. 验证生成的页面是否使用了预定义模板
4. 检查页面数据注入是否正确

---

## 七、后续扩展

### 7.1 新增模板
1. 在 `web/web_templates/` 下创建新模板目录
2. 通过管理页面或脚本注册模板元数据
3. 系统自动向量化并支持匹配

### 7.2 模板类型扩展
- `full_page`: 完整页面模板
- `component`: 可嵌入的组件模板
- `chart`: 纯图表模板
- `report`: 报告文档模板

### 7.3 数据注入方式
- **方式1**: HTML占位符替换 (`{{variable}}`)
- **方式2**: JavaScript全局变量注入 (`window.PAGE_DATA = {...}`)
- **方式3**: API数据加载 (模板通过AJAX获取数据)

---

## 八、模板改造方案

### 8.1 数据注入方式: JavaScript全局变量

**原理**: 在生成的页面中注入 `window.PAGE_DATA` 全局变量，模板JS读取该变量渲染数据。

**生成的页面结构**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>水库洪水预报结果</title>
    <!-- 原模板的CSS -->
</head>
<body>
    <!-- 原模板的HTML结构 -->

    <!-- 数据注入脚本 (在模板JS之前) -->
    <script>
        window.PAGE_DATA = {
            "reservoir_name": "盘石头水库",
            "plan_code": "model_20250715112532",
            "reservoir_result": {
                "InQ_Dic": {...},
                "OutQ_Dic": {...},
                "Level_Dic": {...},
                "Max_Level": 185.5,
                "Max_InQ": 1200
            },
            "rain_data": [...],
            "result_desc": "预报结论文本..."
        };
    </script>

    <!-- 原模板的JS -->
    <script src="js/main.js"></script>
</body>
</html>
```

### 8.2 res_module/js/main.js 改造

**修改文件**: `web/web_templates/res_module/js/main.js`

**改造要点**:
1. 检测 `window.PAGE_DATA` 是否存在
2. 如果存在，直接使用注入的数据
3. 如果不存在，保持原有的API获取逻辑（兼容独立访问）

**改造后的 init() 函数**:
```javascript
async function init() {
    updateTime();
    setInterval(updateTime, 1000);

    const conclusionTextDom = document.getElementById('conclusionText');

    try {
        let floodData, rainData;

        // 检查是否有注入的数据
        if (window.PAGE_DATA) {
            console.log("Using injected PAGE_DATA");
            floodData = {
                reservoir_result: {
                    [window.PAGE_DATA.reservoir_name || "盘石头水库"]: window.PAGE_DATA.reservoir_result
                },
                result_desc: window.PAGE_DATA.result_desc || ""
            };
            rainData = window.PAGE_DATA.rain_data || [];
        } else {
            // 原有的API获取逻辑
            if (conclusionTextDom) {
                conclusionTextDom.innerText = "正在获取实时预报数据...";
            }
            [floodData, rainData] = await Promise.all([
                fetchFloodResult(),
                fetchRainProcess()
            ]);
        }

        if (floodData) {
            // 动态获取水库名称
            const reservoirName = window.PAGE_DATA?.reservoir_name || "盘石头水库";
            processAllDataDynamic(floodData, rainData, reservoirName);
        } else {
            throw new Error("未能获取洪水结果数据");
        }
    } catch (error) {
        console.error("Data loading error:", error);
        if (conclusionTextDom) {
            conclusionTextDom.innerText = "数据获取失败，请检查网络或 API 服务。";
        }
    }

    initMap();
}

// 新增: 支持动态水库名称的数据处理
function processAllDataDynamic(floodRaw, rainData, reservoirName) {
    if (!floodRaw.reservoir_result || !floodRaw.reservoir_result[reservoirName]) {
        console.error(`Data for ${reservoirName} not found.`);
        return;
    }
    const reservoirData = floodRaw.reservoir_result[reservoirName];
    const description = floodRaw.result_desc || "";

    renderChart(reservoirData, rainData);
    renderConclusion(reservoirData, description);
}
```

### 8.3 PageGenerator 生成逻辑

**文件**: `src/output/page_generator.py`

**新增方法**:
```python
async def generate_page_with_template(
    self,
    template_info: Dict[str, Any],
    data: Dict[str, Any],
    title: str = ""
) -> str:
    """使用预定义模板生成页面"""
    import json
    import shutil
    from pathlib import Path

    template_path = template_info.get('template_path', '')
    template_dir = Path(settings.web_templates_dir) / Path(template_path).parent

    # 1. 读取模板HTML
    template_html_path = Path(settings.web_templates_dir) / template_path
    with open(template_html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 2. 生成唯一文件名
    page_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = Path(settings.generated_pages_dir) / f"{template_info['name']}_{timestamp}_{page_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 3. 复制模板资源文件 (css, js)
    for subdir in ['css', 'js']:
        src_dir = template_dir / subdir
        if src_dir.exists():
            shutil.copytree(src_dir, output_dir / subdir, dirs_exist_ok=True)

    # 4. 注入数据脚本
    data_script = f"""
    <script>
        window.PAGE_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};
    </script>
    """

    # 在 </head> 或第一个 <script> 之前注入
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', f'{data_script}\n</head>')
    else:
        html_content = data_script + html_content

    # 5. 修改标题
    if title:
        html_content = re.sub(
            r'<title>.*?</title>',
            f'<title>{title}</title>',
            html_content
        )

    # 6. 保存生成的页面
    output_html = output_dir / 'index.html'
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 7. 返回访问URL
    relative_path = output_dir.relative_to(Path(settings.generated_pages_dir))
    return f"/static/pages/{relative_path}/index.html"
```

---

## 九、模板预览功能

### 9.1 预览API

**文件**: `src/api/web_templates.py`

**新增端点**:
```python
@router.get("/web-templates/{template_id}/preview")
async def preview_template(template_id: str):
    """
    预览模板

    使用模拟数据渲染模板，返回预览页面URL
    """
    # 1. 获取模板信息
    # 2. 生成模拟数据
    # 3. 调用 generate_page_with_template
    # 4. 返回预览URL
```

### 9.2 模拟数据生成

**文件**: `src/output/template_mock_data.py`

```python
"""模板预览用的模拟数据"""

MOCK_DATA = {
    "res_flood_forecast": {
        "reservoir_name": "示例水库",
        "plan_code": "preview_demo",
        "reservoir_result": {
            "InQ_Dic": {
                "2025-07-15 00:00": 100,
                "2025-07-15 01:00": 150,
                "2025-07-15 02:00": 200,
                # ... 更多时间点
            },
            "OutQ_Dic": {...},
            "Level_Dic": {...},
            "Max_Level": 185.5,
            "Max_InQ": 1200,
            "Max_OutQ": 800
        },
        "rain_data": [
            {"time": "2025-07-15 00:00", "value": 5.2},
            {"time": "2025-07-15 01:00", "value": 8.5},
            # ... 更多数据
        ],
        "result_desc": "这是模板预览的示例结论文本。"
    }
}
```

### 9.3 管理页面预览按钮

**文件**: `web/main/web_templates.html`

在操作列添加预览按钮:
```html
<button class="btn btn-sm btn-info" onclick="previewTemplate('${tpl.id}')">
    <i class="bi bi-eye"></i> 预览
</button>
```

```javascript
async function previewTemplate(templateId) {
    const response = await fetch(`/web-templates/${templateId}/preview`);
    const result = await response.json();
    if (result.preview_url) {
        window.open(result.preview_url, '_blank');
    }
}
```

---

## 十、实施顺序

### 第一阶段: 基础设施 (数据库 + 向量索引)
1. 修改 `src/models/database.py` - 新增 WebTemplate 模型
2. 新建 `src/output/template_vector_index.py` - 向量索引类
3. 创建 `template_vectors/` 目录

### 第二阶段: 模板匹配服务
1. 新建 `src/output/template_match_service.py` - 匹配服务
2. 新建 `src/output/template_mock_data.py` - 模拟数据

### 第三阶段: API接口
1. 新建 `src/api/web_templates.py` - 模板管理API
2. 修改 `src/api/__init__.py` - 导出路由
3. 修改 `src/main.py` - 注册路由

### 第四阶段: 模板改造
1. 修改 `web/web_templates/res_module/js/main.js` - 支持数据注入
2. 修改 `src/output/page_generator.py` - 新增模板生成方法

### 第五阶段: 管理页面
1. 新建 `web/main/web_templates.html` - 管理界面
2. 实现列表、编辑、删除、预览功能

### 第六阶段: 集成到Controller
1. 修改 `src/agents/controller.py` - 集成模板匹配逻辑

### 第七阶段: 初始化和测试
1. 新建 `scripts/init_web_templates.py` - 初始化脚本
2. 运行测试验证
