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

# PAGE_CONFIG 生成提示词
PAGE_CONFIG_GENERATION_PROMPT = """你是优秀的Web前端架构师。
你的任务是根据用户的对话上下文，生成一个完整的、美观的、交互性强的Web页面配置 (PAGE_CONFIG)。

## 用户对话上下文
用户问题: {user_message}
意图: {intent} (子意图: {sub_intent})
实体: {entities}
数据特征: {data_features}

## 工具调用结果 (部分截取)
{tool_results}

## PAGE_CONFIG 生成规则
请生成一个JSON对象，包含以下字段：
1. `meta`: 页面元信息 (title, description, generated_at)
2. `layout`: 布局配置 (type: grid/flex, rows: [...])
3. `components`: 组件详细配置 (key: component_config)
4. `api_config`: API数据源配置 (key: api_config)

## 组件选择指南
- **时序数据** (如水位过程线、流量过程线): 使用 `Echarts` (line/bar)。
- **键值对/摘要信息** (如最高水位、洪峰流量): 使用 `InfoCard` 或 `StatCard`。
- **列表/表格数据**: 使用 `SimpleTable`。
- **地理信息**: 使用 `GISMap`。
- **富文本/Markdown**: 使用 `HtmlContent`。
- **时间线**: 使用 `Timeline`。

## 布局设计指南
- 将关键摘要信息(`InfoCard`, `StatCard`)放在顶部。
- 图表(`Echarts`)和地图(`GISMap`)应占据较大空间。
- 表格(`SimpleTable`)通常放在底部或侧边。
- 使用 `grid` 布局来组织这些组件。

## API配置指南
- 如果数据可以通过API获取，请在 `api_config` 中配置API接口。
- 支持参数占位符 `{{context.path.to.value}}`。
- 如果数据无法通过API获取，请标记为需要放入 `static_data`。

## JSON 输出格式示例
```json
{{
  "meta": {{ "title": "...", "description": "..." }},
  "layout": {{ "type": "grid", "rows": [...] }},
  "components": {{ ... }},
  "api_config": {{ ... }}
}}
```
请仅返回JSON，不要包含Markdown代码块标记。
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
        
        # 6. 返回页面URL
        page_url = f"/pages/{page_id}/index.html"
        logger.info(f"动态页面生成成功: {page_url}")
        
        return page_url
        
    def _prepare_llm_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """准备LLM输入数据"""
        # 提取关键信息
        user_message = context.get('user_message', '')
        intent = context.get('intent', {}).get('category', 'unknown')
        sub_intent = context.get('intent', {}).get('sub_intent', 'unknown')
        entities = context.get('intent', {}).get('entities', {})
        
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
            response = await self.prompt.ainvoke(llm_context)
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
