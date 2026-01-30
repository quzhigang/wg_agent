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
PAGE_CONFIG_GENERATION_PROMPT = """你是Web前端架构师，根据用户对话和可用数据生成页面配置 (PAGE_CONFIG)。

## 用户对话上下文
用户问题: {user_message}
意图: {intent} (子意图: {sub_intent})
实体: {entities}

## 可用数据路径
{available_data_paths}

## 工具调用结果摘要
{tool_results}

## 工作流数据摘要
{workflow_data_summary}

## 预定义数据路径（优先使用）
- `default_video_url` - 视频流URL（Video组件）
- `camera_list` - 摄像头列表，字段: code, name, stcd, type, status
- `all_images` - 图片URL数组（Carousel/Image）
- `parsed_info_table` - 表格数据，字段: label, value
- `geo_info.center` - 地理坐标 [lng, lat]
- `key_metrics.*` - 关键指标字段（StatCard），如design_flow/bottom_elevation/gate_count/current_state等
- `discharge_curve` - 二维数组[[x,y],...]（Echarts曲线图）

## 硬性规则（必须严格遵守）
1. **占满屏幕**：总高度约980px，StatCard行120px，媒体/图表行400px+
2. **最多3行**：内容多时用Tabs切换，不要超过3行
3. **数据绑定**：使用 `data_source: {{type:"context", path:"xxx"}}`
4. **同组并排**：A组(GISMap/Image/Video/Carousel)、B组(Echarts/SimpleTable/Tabs)、C组(StatCard/InfoCard/HtmlContent)
5. **SimpleTable**：必须设置 maxRows: 10
6. **图片规则**：多张用Carousel，单张用Image
7. **标题通用化**：不含具体对象名
8. **StatCard**：当key_metrics存在且有具体字段时，必须用StatCard展示，每个字段一个卡片，并排放第1行(height:120px)
9. **HtmlContent**：只能绑定字符串路径，如retrieval.documents[0].content
10. **内容过多时用Tabs**：当同类组件超过2个（如多个表格、多个图表）时，必须用Tabs组件切换展示
11. **Echarts的series.data绑定**：必须在series数组元素内使用data_source，格式为 `"series": [{{"data_source": {{"type":"context", "path":"xxx"}}}}]`，xAxis/yAxis的type设为"value"
12. **使用地图组件原则**：当涉及具体对象如水库、闸站、监测站点等实物或需要地图展示的其他情景时，必须使用GISMap组件，且zoom≥10

## 组件类型
- A组：GISMap、Image、Video(autoplay,controls)、Carousel
- B组：Echarts(bindData用series[].data_source)、SimpleTable(columns,maxRows:10)、Tabs(tabs[].content可嵌套组件)
- C组：StatCard(title,data_source绑定value,unit)、InfoCard、HtmlContent、List

**GISMap配置（必须完整）：**
- zoom: 13（不小于10）
- center: 通过data_source绑定geo_info.center，格式[lng,lat]
- markers: 添加标记点，通过data_source绑定geo_info.center
- 示例：`{{"type":"GISMap","zoom":13,"data_source":{{"type":"context","path":"geo_info.center"}},"markers":[{{"data_source":{{"type":"context","path":"geo_info.center"}},"title":"位置"}}]}}`

## 输出JSON格式
{{
  "meta": {{"title": "通用标题", "description": "描述"}},
  "layout": {{"type": "grid", "rows": [{{"height": "xxx", "cols": ["c1", "c2"]}}]}},
  "components": {{"c1": {{"type": "组件类型", "title": "标题", "data_source": {{"type": "context", "path": "xxx"}}, ...}}}},
  "api_config": {{}}
}}

仅返回JSON，不要Markdown代码块。
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

        # 0. 先预处理context，提取key_metrics、discharge_curve等结构化数据
        #    这样LLM才能在available_data_paths中看到这些字段
        preprocessor = DataFileGenerator(Path("."))  # 临时实例，仅用于预处理
        conversation_context = preprocessor._preprocess_context_data(conversation_context)

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
        """准备LLM输入数据（动态生成可用数据路径）"""
        # 提取关键信息
        user_message = context.get('meta', {}).get('user_message', '') or context.get('user_message', '')

        intent_data = context.get('intent') or {}
        intent = intent_data.get('intent_category') or intent_data.get('category', 'unknown')
        sub_intent = intent_data.get('business_sub_intent') or intent_data.get('sub_intent', 'unknown')
        entities = intent_data.get('entities', {})

        # 工具调用结果摘要
        tool_results = []
        tools_executed = context.get('execution', {}).get('tool_calls', [])

        for tool in tools_executed:
            name = tool.get('tool_name')
            result = tool.get('output_result')
            success = tool.get('success')

            # 保存token以便后续注入
            if name == 'login' and success and isinstance(result, dict):
                self.auth_token = result.get('data')

            if success and result:
                extracted_features = self._extract_data_features(name, result)
                tool_results.append(f"- {name}: {extracted_features}")

        # 工作流结果摘要
        workflow_result = context.get('workflow_result', {})
        extracted_result = workflow_result.get('extracted_result')
        forecast_target = workflow_result.get('forecast_target')
        workflow_data_summary = ""
        if extracted_result:
            workflow_data_summary = self._extract_workflow_result_features(extracted_result, forecast_target)

        # 动态生成可用数据路径
        available_paths = self._extract_available_paths(context)

        return {
            "user_message": user_message,
            "intent": intent,
            "sub_intent": sub_intent,
            "entities": str(entities),
            "available_data_paths": available_paths,
            "tool_results": "\n".join(tool_results) if tool_results else "无",
            "workflow_data_summary": workflow_data_summary or "无"
        }

    def _extract_available_paths(self, context: Dict[str, Any]) -> str:
        """
        递归提取context中所有可用的数据路径
        """
        paths = []

        def describe_value(val: Any) -> str:
            """描述值的类型和内容"""
            if val is None:
                return "null"
            if isinstance(val, str):
                if len(val) > 50:
                    return f'"{val[:50]}..."'
                return f'"{val}"'
            if isinstance(val, (int, float)):
                return str(val)
            if isinstance(val, bool):
                return str(val).lower()
            if isinstance(val, list):
                if len(val) == 0:
                    return "[] (空数组)"
                first = val[0]
                if isinstance(first, dict):
                    keys = list(first.keys())[:5]
                    return f"[数组, {len(val)}项, 字段: {', '.join(keys)}]"
                # 检测二维数组（如discharge_curve [[x,y],...]）
                if isinstance(first, list) and len(first) == 2:
                    try:
                        x_vals = [item[0] for item in val]
                        y_vals = [item[1] for item in val]
                        return f"[二维数组, {len(val)}点, X范围:{min(x_vals)}-{max(x_vals)}, Y范围:{min(y_vals)}-{max(y_vals)}]"
                    except (TypeError, IndexError):
                        pass
                return f"[数组, {len(val)}项]"
            if isinstance(val, dict):
                keys = list(val.keys())[:5]
                return f"{{对象, 字段: {', '.join(keys)}}}"
            return str(type(val).__name__)

        # 需要展示的顶层字段
        include_keys = {
            'camera_list', 'default_video_url', 'default_camera_name',
            'all_images', 'parsed_info_table', 'geo_info', 'key_metrics',
            'discharge_curve', 'station_info', 'params_data', 'water_level_data',
            'tool_results', 'retrieval', 'workflow_result'
        }

        for key in include_keys:
            if key in context and context[key]:
                value = context[key]
                desc = describe_value(value)
                paths.append(f"- `{key}`: {desc}")

                # 对于对象数组，展示第一个元素的字段
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    for k in list(value[0].keys())[:5]:
                        paths.append(f"  - `{key}[0].{k}`: {describe_value(value[0][k])}")

                # 对于嵌套对象，展示子字段
                elif isinstance(value, dict):
                    for k, v in list(value.items())[:5]:
                        paths.append(f"  - `{key}.{k}`: {describe_value(v)}")

        if not paths:
            return "无可用数据路径"

        return "\n".join(paths)

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
            
        # 复制 css、js、assets、libs 目录
        for subdir in ["css", "js", "assets", "libs"]:
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
