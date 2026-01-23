"""
模板配置器

负责将工作流执行上下文中的数据注入到Web模板中。

支持两种注入模式：
1. regex_replace: 正则替换模式，用于预定义模板（直接修改 main.js 等文件）
2. json_injection: JSON注入模式，用于动态模板（生成 data.js 文件）

核心原则：
- 轻量化传递：只传递"钥匙"（Token, ID, Path），不传递"货物"（海量数据）
- 配置驱动：使用 JSON 配置定义数据提取规则
- 前端自治：Web 模板利用"钥匙"自行获取重型数据
"""

import re
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..config.logging_config import get_logger
from ..config.settings import settings
from .workflow_context import WorkflowContext

logger = get_logger(__name__)


class TemplateConfigurator:
    """
    模板配置器

    根据 replacement_config 配置，将 Context 中的数据注入到模板文件中。
    """

    def __init__(self):
        self._templates_dir = Path(settings.web_templates_dir)
        logger.info(f"TemplateConfigurator 初始化，模板目录: {self._templates_dir}")

    def configure(
        self,
        template_path: str,
        context: WorkflowContext,
        replacement_config: Dict[str, Any]
    ) -> str:
        """
        配置模板，注入数据

        Args:
            template_path: 模板相对路径（相对于 web_templates 目录）
            context: 工作流执行上下文
            replacement_config: 数据替换配置

        Returns:
            配置后的模板访问路径
        """
        mode = replacement_config.get("mode", "regex_replace")

        if mode == "regex_replace":
            return self._configure_regex_replace(template_path, context, replacement_config)
        elif mode == "json_injection":
            return self._configure_json_injection(template_path, context, replacement_config)
        else:
            logger.warning(f"未知的配置模式: {mode}，使用默认 regex_replace")
            return self._configure_regex_replace(template_path, context, replacement_config)

    def _configure_regex_replace(
        self,
        template_path: str,
        context: WorkflowContext,
        config: Dict[str, Any]
    ) -> str:
        """
        正则替换模式：直接修改模板文件中的配置值

        适用于预定义模板，如水库预报结果展示模板。
        直接修改 main.js 中的 DEFAULT_PARAMS 等配置。
        """
        target_file = config.get("target_file", "js/main.js")
        mappings = config.get("mappings", [])

        if not mappings:
            logger.warning("replacement_config 中没有定义 mappings")
            return self._get_template_url(template_path)

        # 构建目标文件的完整路径
        template_dir = self._templates_dir / Path(template_path).parent
        target_file_path = template_dir / target_file

        if not target_file_path.exists():
            logger.error(f"目标文件不存在: {target_file_path}")
            return self._get_template_url(template_path)

        # 读取目标文件内容
        try:
            with open(target_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"读取目标文件失败: {e}")
            return self._get_template_url(template_path)

        # 执行替换
        modified = False
        for mapping in mappings:
            context_path = mapping.get("context_path")
            pattern = mapping.get("pattern")
            replacement_template = mapping.get("replacement_template")

            if not all([context_path, pattern, replacement_template]):
                logger.warning(f"mapping 配置不完整: {mapping}")
                continue

            # 从 Context 中获取值
            value = context.get(context_path)
            if value is None:
                logger.warning(f"Context 中未找到路径: {context_path}")
                continue

            # 构建替换字符串
            replacement = replacement_template.format(value=value)

            # 执行正则替换
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                modified = True
                logger.info(f"替换成功: {context_path} -> {mapping.get('target_key')} (替换 {count} 处)")
            else:
                logger.warning(f"未匹配到模式: {pattern}")

        # 写回文件
        if modified:
            try:
                with open(target_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"模板配置完成: {target_file_path}")
            except Exception as e:
                logger.error(f"写入目标文件失败: {e}")

        return self._get_template_url(template_path)

    def _configure_json_injection(
        self,
        template_path: str,
        context: WorkflowContext,
        config: Dict[str, Any]
    ) -> str:
        """
        JSON注入模式：生成 data.js 文件供前端读取

        适用于动态生成的模板，将数据以 window.PAGE_DATA 形式注入。
        """
        target_file = config.get("target_file", "data.js")
        export_keys = config.get("export_keys", [])
        api_config = config.get("api_config", {})

        # 构建目标文件路径
        template_dir = self._templates_dir / Path(template_path).parent
        target_file_path = template_dir / target_file

        # 提取需要导出的数据
        page_data = {}

        # 导出指定的键
        for key_config in export_keys:
            if isinstance(key_config, str):
                # 简单字符串格式: "inputs.entities.object"
                context_path = key_config
                export_name = key_config.split(".")[-1]
            elif isinstance(key_config, dict):
                # 字典格式: {"context_path": "xxx", "export_name": "yyy"}
                context_path = key_config.get("context_path")
                export_name = key_config.get("export_name", context_path.split(".")[-1])
            else:
                continue

            value = context.get(context_path)
            if value is not None:
                page_data[export_name] = value

        # 添加 API 配置（用于前端调用接口）
        if api_config:
            processed_api_config = self._process_api_config(api_config, context)
            page_data["api_config"] = processed_api_config

        # 生成 data.js 内容
        js_content = self._generate_data_js(page_data)

        # 写入文件
        try:
            target_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(js_content)
            logger.info(f"生成数据文件: {target_file_path}")
        except Exception as e:
            logger.error(f"生成数据文件失败: {e}")

        return self._get_template_url(template_path)

    def _process_api_config(
        self,
        api_config: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """
        处理 API 配置，替换其中的 Context 引用

        支持在 API 配置中使用 {context:path} 格式引用 Context 数据
        """
        result = {}

        for api_name, api_def in api_config.items():
            processed_def = {}
            for key, value in api_def.items():
                if isinstance(value, str) and value.startswith("{context:") and value.endswith("}"):
                    # 提取 Context 路径
                    context_path = value[9:-1]  # 去掉 "{context:" 和 "}"
                    processed_def[key] = context.get(context_path, value)
                elif isinstance(value, dict):
                    # 递归处理嵌套字典
                    processed_def[key] = self._process_dict_values(value, context)
                else:
                    processed_def[key] = value
            result[api_name] = processed_def

        return result

    def _process_dict_values(
        self,
        data: Dict[str, Any],
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """递归处理字典中的 Context 引用"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("{context:") and value.endswith("}"):
                context_path = value[9:-1]
                result[key] = context.get(context_path, value)
            elif isinstance(value, dict):
                result[key] = self._process_dict_values(value, context)
            else:
                result[key] = value
        return result

    def _generate_data_js(self, page_data: Dict[str, Any]) -> str:
        """
        生成 data.js 文件内容

        格式：
        (function() {
            window.PAGE_DATA = { ... };
        })();
        """
        json_str = json.dumps(page_data, ensure_ascii=False, indent=2)

        return f"""/**
 * 页面数据文件（自动生成）
 * 由 TemplateConfigurator 根据工作流执行结果生成
 */
(function() {{
    window.PAGE_DATA = {json_str};
}})();
"""

    def _get_template_url(self, template_path: str) -> str:
        """
        获取模板的访问 URL

        Args:
            template_path: 模板相对路径

        Returns:
            模板访问 URL
        """
        # 提取模板目录名
        template_dir = Path(template_path).parent.name
        return f"/static/web_templates/{template_dir}/index.html"

    def reset_template(
        self,
        template_path: str,
        replacement_config: Dict[str, Any]
    ) -> bool:
        """
        重置模板到默认状态

        将模板文件中的配置值恢复为占位符，以便下次使用时重新注入。

        Args:
            template_path: 模板相对路径
            replacement_config: 数据替换配置

        Returns:
            是否重置成功
        """
        mode = replacement_config.get("mode", "regex_replace")

        if mode != "regex_replace":
            # JSON 注入模式不需要重置
            return True

        target_file = replacement_config.get("target_file", "js/main.js")
        mappings = replacement_config.get("mappings", [])
        default_values = replacement_config.get("default_values", {})

        if not mappings or not default_values:
            logger.warning("无法重置模板：缺少 mappings 或 default_values 配置")
            return False

        # 构建目标文件路径
        template_dir = self._templates_dir / Path(template_path).parent
        target_file_path = template_dir / target_file

        if not target_file_path.exists():
            logger.error(f"目标文件不存在: {target_file_path}")
            return False

        try:
            with open(target_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for mapping in mappings:
                target_key = mapping.get("target_key")
                pattern = mapping.get("pattern")
                replacement_template = mapping.get("replacement_template")

                if target_key in default_values:
                    default_value = default_values[target_key]
                    replacement = replacement_template.format(value=default_value)
                    content = re.sub(pattern, replacement, content)

            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"模板已重置: {target_file_path}")
            return True

        except Exception as e:
            logger.error(f"重置模板失败: {e}")
            return False


# 全局模板配置器实例
_template_configurator: Optional[TemplateConfigurator] = None


def get_template_configurator() -> TemplateConfigurator:
    """获取模板配置器单例"""
    global _template_configurator
    if _template_configurator is None:
        _template_configurator = TemplateConfigurator()
    return _template_configurator
