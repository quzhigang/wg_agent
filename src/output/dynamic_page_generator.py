"""
DynamicPageGenerator - 动态页面生成器
负责使用单一LLM调用完成布局选择和配置生成，并组装页面。
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import uuid
import shutil
import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import settings
from ..config.logging_config import get_logger
from ..config.llm_prompt_logger import log_llm_call
from .data_file_generator import DataFileGenerator

logger = get_logger(__name__)

# PAGE_CONFIG 生成提示词 (精简版)
PAGE_CONFIG_GENERATION_PROMPT = """你是Web前端架构师，根据用户对话生成页面配置 (PAGE_CONFIG)。
**风格要求：深色科技风格 (深蓝背景 #0a1628，青色强调 #00d4ff，发光效果)**

## ⚠️ 最重要的硬性规则（违反则配置无效）
**一屏完整展示：页面尽量在一屏内完整显示，尽量不要生成需要滚动的长页面！**
- 屏幕可用高度约 980px，
- **最多3行布局**，绝对不能超过3行
- 内容多时要精简合并，必要时采用切换标签

## ⚠️ 数据绑定规则（核心规则，必须遵守）
**所有动态数据必须通过 data_source 绑定，禁止硬编码具体数据值！**

模板需要支持复用，因此：
- ✅ 正确：使用 `data_source: {{ type: "context", path: "retrieval.documents[0].metadata.images" }}`
- ❌ 错误：直接写 `src: "/knowledge/kb-doc/xxx.jpg"`
- ✅ 正确：使用 `data_source: {{ type: "context", path: "retrieval.documents" }}` 绑定表格数据
- ❌ 错误：直接写 `dataSource: [{{ "label": "xxx", "value": "yyy" }}]`

## 用户对话上下文
用户问题: {user_message}
意图: {intent} (子意图: {sub_intent})
实体: {entities}
数据特征: {data_features}

## 工具调用结果
{tool_results}

## 工作流业务数据摘要
{workflow_data_summary}

## 组件类型及分组

**A组 - 媒体可视化类（同组可并排）：**
| 组件类型 | 适用场景 | 关键配置 |
|---------|---------|---------|
| `GISMap` | 地图展示 | zoom: 10 (不小于10级), center: [lng, lat] 或 data_source 绑定 |
| `Image` | **仅用于单张图片** | data_source 绑定 src，或静态 src |
| `Video` | 视频播放 | src, poster, autoplay, controls |
| `Carousel` | **多张图片必须使用轮播**（≥2张图片时强制使用） | data_source 绑定 images 数组 |

**B组 - 数据分析类（同组可并排）：**
| 组件类型 | 适用场景 | 关键配置 |
|---------|---------|---------|
| `Echarts` | 时序曲线、柱状图、饼图 | chartType: line/bar/pie, options 或 data_source |
| `SimpleTable` | 列表/表格数据（**优先使用**） | columns 定义列，data_source 绑定数据，**maxRows: 10**（最多显示10行，超出滚动） |

**SimpleTable 配置规范（重要）：**
- **必须设置 maxRows: 10**，表格最多显示10行，超出部分滚动显示
- 示例：`{{ "type": "SimpleTable", "title": "参数列表", "maxRows": 10, "columns": [...], "data_source": {{...}} }}`

**Echarts 配置规范（重要）：**
- 对于散点图或XY数值曲线，使用 `series.data: [[x1,y1], [x2,y2], ...]` 格式
- **坐标轴范围**：必须根据数据实际范围设置 `min` 和 `max`，避免从0开始导致图形压缩
- 示例：数据X范围0-900，Y范围56-60，则设置 `xAxis: {{type:"value", min:0, max:900}}, yAxis: {{type:"value", min:55, max:61}}`

**C组 - 紧凑信息类（同组可并排）：**
| 组件类型 | 适用场景 | 关键配置 |
|---------|---------|---------|
| `StatCard` | 单个关键指标（**最多2-5个**） | data_source 绑定 value，或静态 value, unit, status |
| `InfoCard` | 多个键值对信息 | data_source 绑定对象 |
| `HtmlContent` | 富文本/Markdown | data_source 绑定 content |
| `List` | 简单列表 | data_source 绑定 items |

**表单类（按需使用）：**
| 组件类型 | 适用场景 | 关键配置 |
|---------|---------|---------|
| `Radio` | 单选按钮 | options: [{{value, label}}], defaultValue |
| `Checkbox` | 多选勾选 | options: [{{value, label}}], defaultValues |
| `Select` | 下拉选择 | options: [{{value, label}}], placeholder |
| `Switch` | 开关切换 | checked, label, onText, offText |
| `Tabs` | 标签页切换 | tabs: [{{key, label, content}}], defaultTab |

## 布局规则

### 行数限制（硬性规则）
**最多3行，绝对不能超过3行！**
- 1行布局：简单内容
- 2行布局：内容较多时的上限
- 3行布局：少数情况，必须精简合并内容

### 组件分组并排原则
**只有同组的组件才能放在同一行：**
- ✅ A组并排：GISMap + Image、Image + Carousel
- ✅ B组并排：SimpleTable + Echarts
- ✅ C组并排：StatCard + StatCard、InfoCard + HtmlContent
- ❌ 跨组禁止：GISMap + Echarts、Image + SimpleTable

### 行高度规则
- StatCard 行：height: "120px"
- 其他行：不设置或 height: "auto"

### 布局示例（都是1-2行）
**示例1 - 简单回答（1行）：**
```
第1行: [HtmlContent, Image]  // 文字+配图
```

**示例2 - 数据展示（2行）：**
```
第1行: [StatCard, StatCard, StatCard]  // 关键指标，height: "120px"
第2行: [SimpleTable, Echarts]          // 数据详情
```

**示例3 - 媒体展示（2行）：**
```
第1行: [GISMap, Carousel]  // 地图+图片轮播
第2行: [HtmlContent]       // 说明文字
```

## 实时数据展示规则
**只有当意图为 business 且子意图为 realtime_query 时，才展示实时数据。**

## data_source 路径说明
context 数据结构如下，使用点号访问嵌套属性（支持数组索引如 [0]）：

**预处理后的便捷路径（强烈推荐使用，已从原始数据中提取整理）：**
- `all_images` - 所有图片URL数组（已从所有文档中提取）
- `all_images[0]` - 第一张图片URL
- `parsed_info_table` - 解析后的表格数据数组，格式: [{{label, value}}, ...]，用于 SimpleTable
- `geo_info.center` - 地理坐标 [lng, lat]（如果有）
- `discharge_curve` - 泄流曲线数据 [[流量, 水位], ...]，用于 Echarts 图表
- `key_metrics.design_flow` - 设计流量（用于 StatCard）
- `key_metrics.bottom_elevation` - 闸底高程（用于 StatCard）
- `key_metrics.gate_count` - 闸孔数量（用于 StatCard）
- `key_metrics.current_state` - 当前状态（用于 StatCard）
- `key_metrics.gate_width` - 单孔净宽
- `key_metrics.gate_height` - 闸门高度
- `key_metrics.capacity` - 库容
- `key_metrics.normal_level` - 正常蓄水位

**StatCard 组件必须使用 key_metrics 路径：**
- ✅ 正确：`data_source: {{ type: "context", path: "key_metrics.design_flow" }}`
- ❌ 错误：`data_source: {{ type: "context", path: "retrieval.documents[1].metadata.design_flow" }}`

**Echarts 泄流曲线必须使用 discharge_curve 路径：**
- ✅ 正确：在 series.data 中使用 `data_source: {{ type: "context", path: "discharge_curve" }}`
- ❌ 错误：使用 `retrieval.documents[2].metadata.curve_points`

**原始数据路径（仅在预处理路径不满足需求时使用）：**
- `meta.user_message` - 用户问题
- `intent.entities` - 提取的实体
- `retrieval.documents` - 检索到的文档数组
- `retrieval.documents[0].content` - 第一个文档内容
- `retrieval.documents[0].metadata.images` - 第一个文档的图片数组
- `workflow_result.extracted_result` - 工作流结果

## 输出格式 (JSON)
```json
{{
  "meta": {{ "title": "通用标题（不含具体对象名）", "description": "描述" }},
  "layout": {{
    "type": "grid",
    "rows": [
      {{ "cols": ["comp1", "comp2"] }},
      {{ "cols": ["comp3"] }}
    ]
  }},
  "components": {{
    "site_image": {{
      "type": "Image",
      "title": "现场实景",
      "data_source": {{ "type": "context", "path": "all_images[0]" }},
      "alt": "现场照片",
      "fit": "cover"
    }},
    "gallery": {{
      "type": "Carousel",
      "title": "图片展示",
      "data_source": {{ "type": "context", "path": "all_images" }},
      "autoplay": true,
      "interval": 3000
    }},
    "gis_map": {{
      "type": "GISMap",
      "title": "地理位置",
      "zoom": 13,
      "data_source": {{ "type": "context", "path": "geo_info.center" }}
    }},
    "info_table": {{
      "type": "SimpleTable",
      "title": "基本信息",
      "columns": [
        {{ "title": "参数项", "dataIndex": "label" }},
        {{ "title": "内容", "dataIndex": "value" }}
      ],
      "data_source": {{ "type": "context", "path": "parsed_info_table" }}
    }}
  }},
  "api_config": {{}}
}}
```

## 重要约束
1. **最多3行**：绝对不能超过3行，这是最重要的硬性规则
2. **数据绑定**：所有动态数据必须使用 data_source 绑定，禁止硬编码
3. **同组并排**：只有同组（A/B/C）的组件才能放在同一行
4. **StatCard紧凑**：行高120px，最多2-5个
5. **列表优先**：用 SimpleTable 整合多个属性
6. **图表合并**：同一对象的多条曲线放在一个 Echarts 中
7. **图片规则（严格执行）**：
   - 单张图片：使用 Image 组件，data_source 绑定图片路径
   - **多张图片（≥2张）：必须使用 Carousel 轮播组件，data_source 绑定图片数组**
   - **禁止**：使用多个 Image 组件垂直排列展示多张图片
8. **StatCard置顶**：若有 StatCard，放在第1行
9. **标题通用化**：meta.title 不要包含具体对象名称，使用通用描述如"闸站详情"、"水库信息"
10. 仅返回JSON，不要包含Markdown代码块标记
"""

class DynamicPageGenerator:
    """
    动态页面生成器
    
    整合了布局选择、组件配置和文件生成。
    """
    
    def __init__(self):
        """初始化"""
        # LLM配置
        page_gen_cfg = settings.get_page_gen_config()
        self.llm = ChatOpenAI(
            api_key=page_gen_cfg["api_key"],
            base_url=page_gen_cfg["api_base"],
            model=page_gen_cfg["model"],
            temperature=page_gen_cfg["temperature"]
        )
        
        self.output_dir = Path(settings.generated_pages_dir)
        self.template_dir = Path(settings.web_templates_dir) / "dynamic_shell"
        
        # 提示词模板
        self.prompt = ChatPromptTemplate.from_template(PAGE_CONFIG_GENERATION_PROMPT)
        self.auth_token = None # 用于传递认证token
        
    async def generate(self, conversation_context: Dict[str, Any]) -> str:
        """
        生成动态页面
        
        Args:
            conversation_context: 对话上下文数据
            
        Returns:
            生成的页面相对URL (例如: /pages/dynamic_xxx/)
        """
        logger.info("开始生成动态页面Config...")
        
        # 1. 准备LLM输入上下文
        llm_context = self._prepare_llm_context(conversation_context)
        
        # 2. 调用LLM生成PAGE_CONFIG
        page_config = await self._generate_page_config(llm_context)
        
        # 3. 创建页面目录结构
        page_id = f"dynamic_{datetime.datetime.now().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}"
        page_dir = self.output_dir / page_id
        page_dir.mkdir(parents=True, exist_ok=True)
        
        # 4. 复制模板文件 (dynamic_shell)
        self._copy_template_files(page_dir)
        
        # 5. 生成 config.js 和 data.js
        self._generate_data_files(page_dir, page_config, conversation_context)
        
        # 6. 返回页面URL（使用 /static/pages 路径，与 FastAPI 静态文件挂载一致）
        page_url = f"/static/pages/{page_id}/index.html"
        logger.info(f"动态页面生成成功: {page_url}")
        
        return page_url
        
    def _prepare_llm_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """准备LLM输入数据（智能提取关键特征，而非简单截断）"""
        # 提取关键信息
        # 优先从 meta 中获取 user_message（to_frontend_format 格式）
        user_message = context.get('meta', {}).get('user_message', '') or context.get('user_message', '')

        # 兼容两种数据格式：
        # 1. to_frontend_format 格式: intent.intent_category, intent.business_sub_intent
        # 2. 旧格式: intent.category, intent.sub_intent
        intent_data = context.get('intent') or {}
        intent = intent_data.get('intent_category') or intent_data.get('category', 'unknown')
        sub_intent = intent_data.get('business_sub_intent') or intent_data.get('sub_intent', 'unknown')
        entities = intent_data.get('entities', {})

        # 工具调用结果摘要
        tool_results = []
        tools_executed = context.get('execution', {}).get('tool_calls', [])

        data_features = set()

        for tool in tools_executed:
            name = tool.get('tool_name')
            result = tool.get('output_result')
            success = tool.get('success')

            # 保存token以便后续注入
            if name == 'login' and success and isinstance(result, dict):
                self.auth_token = result.get('data')

            if success and result:
                # 分析数据特征
                if self._has_timeseries(result):
                    data_features.add("has_timeseries")
                if self._has_list_data(result):
                    data_features.add("has_list_data")

                # 智能提取数据特征（而非简单截断）
                extracted_features = self._extract_data_features(name, result)
                tool_results.append(f"- Tool: {name}\n  Result: {extracted_features}")

        # 提取工作流结果的关键数据（核心业务数据）
        workflow_result = context.get('workflow_result', {})
        extracted_result = workflow_result.get('extracted_result')
        forecast_target = workflow_result.get('forecast_target')

        workflow_data_summary = ""
        if extracted_result:
            # 提取工作流结果的关键特征
            workflow_data_summary = self._extract_workflow_result_features(extracted_result, forecast_target)
            data_features.add("has_workflow_result")

        # 提取检索到的文档（知识库查询结果）
        retrieved_docs_summary = ""
        retrieved_images = []
        retrieved_documents = context.get('retrieval', {}).get('documents', [])
        if retrieved_documents:
            data_features.add("has_retrieved_documents")
            docs_info = []
            for doc in retrieved_documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                title = metadata.get('title', '')
                doc_name = metadata.get('doc_name', '')

                # 提取图片URL
                images = metadata.get('images', [])
                if images:
                    retrieved_images.extend(images)
                    data_features.add("has_images")

                # 摘要文档内容（限制长度）
                content_preview = content[:500] + "..." if len(content) > 500 else content
                docs_info.append(f"- 文档: {doc_name}, 章节: {title}\n  内容: {content_preview}")

            retrieved_docs_summary = "\n".join(docs_info)

        # 构建工具结果（合并工具调用和检索文档）
        final_tool_results = "\n".join(tool_results) if tool_results else ""
        if retrieved_docs_summary:
            if final_tool_results:
                final_tool_results += "\n\n## 知识库检索结果\n" + retrieved_docs_summary
            else:
                final_tool_results = "## 知识库检索结果\n" + retrieved_docs_summary

        # 如果有图片，添加图片信息
        if retrieved_images:
            final_tool_results += f"\n\n## 检索到的图片URL\n" + "\n".join([f"- {img}" for img in retrieved_images])

        return {
            "user_message": user_message,
            "intent": intent,
            "sub_intent": sub_intent,
            "entities": str(entities),
            "tool_results": final_tool_results or "无工具调用结果",
            "data_features": ", ".join(data_features),
            "workflow_data_summary": workflow_data_summary
        }

    def _extract_data_features(self, tool_name: str, result: Any) -> str:
        """
        智能提取数据特征供LLM使用（而非简单截断）

        Args:
            tool_name: 工具名称
            result: 工具返回结果

        Returns:
            提取的特征描述字符串
        """
        if not isinstance(result, dict):
            # 非字典类型，简单截断
            result_str = str(result)
            if len(result_str) > 300:
                return result_str[:300] + "...(truncated)"
            return result_str

        features = {"keys": list(result.keys())}

        # 提取关键数值字段（洪水预报相关）
        key_fields = [
            'Max_Level', 'Max_Qischarge', 'MaxQ_AtTime', 'SectionName',
            'Total_Flood', 'Stcd', 'warning_level', 'guarantee_level',
            'name', 'type', 'summary'
        ]
        for key in key_fields:
            if key in result:
                features[key] = result[key]

        # 处理时序数据字典（只提取范围和采样点数）
        for key in ['Level_Dic', 'Discharge_Dic', 'level_data', 'flow_data']:
            if key in result and isinstance(result[key], dict):
                data_dict = result[key]
                if data_dict:
                    times = list(data_dict.keys())
                    values = list(data_dict.values())
                    features[f'{key}_info'] = {
                        'time_range': f"{times[0]} ~ {times[-1]}",
                        'value_range': f"{min(values):.2f} ~ {max(values):.2f}",
                        'data_points': len(values)
                    }

        # 处理嵌套的 data 字段
        if 'data' in result and isinstance(result['data'], dict):
            nested_features = self._extract_data_features(tool_name, result['data'])
            features['nested_data'] = nested_features

        return json.dumps(features, ensure_ascii=False, default=str)

    def _extract_workflow_result_features(self, extracted_result: Dict[str, Any], forecast_target: Dict[str, Any] = None) -> str:
        """
        提取工作流结果的关键特征

        Args:
            extracted_result: 工作流提取的结果数据
            forecast_target: 预报目标信息

        Returns:
            工作流数据摘要字符串
        """
        summary_parts = []

        # 目标信息
        if forecast_target:
            target_name = forecast_target.get('name', '')
            target_type = forecast_target.get('type', '')
            summary_parts.append(f"预报目标: {target_name} ({target_type})")

        # 提取结果摘要
        if extracted_result:
            result_summary = extracted_result.get('summary', '')
            if result_summary:
                summary_parts.append(f"结果摘要: {result_summary}")

            # 提取核心数据
            data = extracted_result.get('data', {})
            if data:
                # 关键指标
                key_metrics = []
                if 'SectionName' in data:
                    key_metrics.append(f"断面: {data['SectionName']}")
                if 'Stcd' in data:
                    key_metrics.append(f"站码: {data['Stcd']}")
                if 'Max_Level' in data:
                    key_metrics.append(f"最大水位: {data['Max_Level']}m")
                if 'Max_Qischarge' in data:
                    key_metrics.append(f"最大流量: {data['Max_Qischarge']}m³/s")
                if 'MaxQ_AtTime' in data:
                    key_metrics.append(f"峰值时间: {data['MaxQ_AtTime']}")
                if 'Total_Flood' in data:
                    key_metrics.append(f"总洪量: {data['Total_Flood']}万m³")

                if key_metrics:
                    summary_parts.append("关键指标: " + ", ".join(key_metrics))

                # 时序数据信息
                if 'Level_Dic' in data:
                    level_dic = data['Level_Dic']
                    times = list(level_dic.keys())
                    values = list(level_dic.values())
                    summary_parts.append(f"水位预报: {len(values)}个时间点, 范围 {min(values):.2f}~{max(values):.2f}m, 时段 {times[0]}~{times[-1]}")

                if 'Discharge_Dic' in data:
                    discharge_dic = data['Discharge_Dic']
                    times = list(discharge_dic.keys())
                    values = list(discharge_dic.values())
                    summary_parts.append(f"流量预报: {len(values)}个时间点, 范围 {min(values):.2f}~{max(values):.2f}m³/s")

        return "\n".join(summary_parts) if summary_parts else "无工作流数据"

    async def _generate_page_config(self, llm_context: Dict[str, Any]) -> Dict[str, Any]:
        """调用LLM生成配置"""
        import time
        start_time = time.time()

        try:
            # 先格式化提示词，再调用LLM
            formatted_prompt = await self.prompt.ainvoke(llm_context)
            response = await self.llm.ainvoke(formatted_prompt)
            content = response.content
            
            # 清理 Markdown 代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            config = json.loads(content)
            
            # 记录日志
            log_llm_call(
                step_name="PageConfig生成",
                module_name="DynamicPageGenerator",
                prompt_template_name="PAGE_CONFIG_GENERATION_PROMPT",
                context_variables=llm_context,
                full_prompt=str(self.prompt.format(**llm_context)),
                response=content,
                elapsed_time=time.time() - start_time
            )
            
            return config
            
        except Exception as e:
            logger.error(f"生成PAGE_CONFIG失败: {e}")
            # 返回默认配置作为回退
            return self._get_fallback_config(llm_context)

    def _copy_template_files(self, target_dir: Path):
        """复制模板文件"""
        if not self.template_dir.exists():
            logger.warning(f"模板目录不存在: {self.template_dir}")
            # 创建最小化 index.html
            with open(target_dir / "index.html", "w", encoding="utf-8") as f:
                f.write("<html><body><h1>Template Not Found</h1></body></html>")
            return

        # 复制 index.html
        if (self.template_dir / "index.html").exists():
            shutil.copy(self.template_dir / "index.html", target_dir / "index.html")
            
        # 复制 css 和 js 目录
        for subdir in ["css", "js", "assets"]:
             src_sub = self.template_dir / subdir
             if src_sub.exists():
                 if (target_dir / subdir).exists():
                     shutil.rmtree(target_dir / subdir)
                 shutil.copytree(src_sub, target_dir / subdir)

    def _generate_data_files(self, output_dir: Path, page_config: Dict[str, Any], context: Dict[str, Any]):
        """生成 config.js 和 data.js"""
        generator = DataFileGenerator(output_dir)
        
        # 注入全局 API 配置 (如 Token)
        if self.auth_token:
            if "api_config" not in page_config:
                page_config["api_config"] = {}
            # 为所有API请求添加认证头
            for api_name, api_cfg in page_config["api_config"].items():
                if "headers" not in api_cfg:
                    api_cfg["headers"] = {}
                api_cfg["headers"]["Authorization"] = f"Bearer {self.auth_token}"
        
        # 提取静态数据
        static_data = page_config.pop("static_data", {})
        
        # 生成文件
        generator.generate_all(
            page_config=page_config,
            static_data=static_data,
            context_data=context # 将完整上下文数据放入 data.js 供前端使用
        )

    def _has_timeseries(self, data: Any) -> bool:
        """简单的时序数据检测"""
        # (简化逻辑)
        s_data = str(data)
        return "time" in s_data or "date" in s_data
        
    def _has_list_data(self, data: Any) -> bool:
        """简单的列表数据检测"""
        return isinstance(data, list) and len(data) > 0

    def _get_fallback_config(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成失败时的回退配置"""
        return {
            "meta": {
                "title": "查询结果(自动生成)",
                "description": "由于自动生成配置失败，显示默认视图",
                "generated_at": datetime.datetime.now().isoformat()
            },
            "layout": {
                "type": "grid",
                "rows": [{"cols": ["main_content"]}]
            },
            "components": {
                "main_content": {
                    "type": "HtmlContent",
                    "title": "原始数据",
                    "data_source": {
                        "type": "static",
                        "value": "<pre>{}</pre>".format(context.get("tool_results", ""))
                    }
                }
            }
        }

# 全局实例
_dynamic_page_generator = None

def get_dynamic_page_generator() -> DynamicPageGenerator:
    global _dynamic_page_generator
    if _dynamic_page_generator is None:
        _dynamic_page_generator = DynamicPageGenerator()
    return _dynamic_page_generator
