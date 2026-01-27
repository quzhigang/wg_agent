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

## 用户对话上下文
用户问题: {user_message}
意图: {intent} (子意图: {sub_intent})
实体: {entities}
数据特征: {data_features}

## 工具调用结果
{tool_results}

## 组件类型 (共17种)

**数据展示类：**
| 组件类型 | 适用场景 | 关键配置 |
|---------|---------|---------|
| `Echarts` | 时序曲线、柱状图、饼图 | chartType: line/bar/pie, options: {{...}} |
| `StatCard` | 单个关键指标 | value, unit, status |
| `InfoCard` | 多个键值对信息 | 直接传入对象 |
| `SimpleTable` | 列表/表格数据 | columns, dataSource |
| `GISMap` | 地图展示 | 使用固定Portal地图 |
| `HtmlContent` | 富文本/Markdown | content |
| `List` | 简单列表 | items: ["item1"] 或 [{{text, link}}], ordered |
| `Divider` | 分割线 | text (可选标题), color |

**媒体类：**
| 组件类型 | 适用场景 | 关键配置 |
|---------|---------|---------|
| `Image` | 单张图片 | src, alt, fit: cover/contain, caption |
| `Video` | 视频播放 | src, poster, autoplay, controls |
| `Gallery` | 图片画廊 | images: [{{src, caption}}], columns: 3 |

**表单类：**
| 组件类型 | 适用场景 | 关键配置 |
|---------|---------|---------|
| `Radio` | 单选按钮 | options: [{{value, label}}], defaultValue |
| `Checkbox` | 多选勾选 | options: [{{value, label}}], defaultValues |
| `Select` | 下拉选择 | options: [{{value, label}}], placeholder |
| `Switch` | 开关切换 | checked, label, onText, offText |

**导航/交互类：**
| 组件类型 | 适用场景 | 关键配置 |
|---------|---------|---------|
| `Tabs` | 标签页切换 | tabs: [{{key, label, content}}], defaultTab |
| `ActionBar` | 操作按钮 | buttons: [{{label, action, type, url}}], align |

## 布局原则
1. 关键指标(StatCard) → 顶部
2. 图表(Echarts)/地图(GISMap) → 中部，占大空间
3. 表格(SimpleTable) → 底部或侧边
4. 使用 grid 布局，rows 数组定义行，cols 定义列

## 输出格式 (JSON)
```json
{{
  "meta": {{ "title": "根据数据内容确定", "description": "页面描述" }},
  "layout": {{
    "type": "grid",
    "rows": [
      {{ "cols": ["组件key1", "组件key2", ...], "height": "可选高度" }},
      {{ "cols": ["组件key3"] }}
    ]
  }},
  "components": {{
    "组件key": {{
      "type": "组件类型",
      "title": "标题",
      "其他配置": "根据组件类型填写"
    }}
  }},
  "api_config": {{}}
}}
```

**注意：**
1. 深色主题样式已内置，无需配置颜色
2. Echarts 图表会自动应用深色主题
3. GISMap 使用河南省水利厅 Portal WebMap (固定地图服务)
4. 根据工具调用结果中的实际数据类型选择合适的组件
5. 仅返回JSON，不要包含Markdown代码块标记
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
        """准备LLM输入数据"""
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
        
        # 工具调用结果摘要 (避免token过长)
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
                    
                # 截断Result用于Prompt
                result_str = str(result)
                if len(result_str) > 500:
                    result_str = result_str[:500] + "...(truncated)"
                
                tool_results.append(f"- Tool: {name}\n  Result: {result_str}")
        
        return {
            "user_message": user_message,
            "intent": intent,
            "sub_intent": sub_intent,
            "entities": str(entities),
            "tool_results": "\n".join(tool_results) or "无工具调用结果",
            "data_features": ", ".join(data_features)
        }

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
