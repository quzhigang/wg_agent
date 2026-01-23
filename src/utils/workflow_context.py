"""
工作流执行上下文管理器

管理工作流执行过程中的数据传递，支持：
1. 用户输入数据
2. 各步骤执行结果
3. 全局状态
4. 点号路径数据访问
"""

from typing import Dict, Any, Optional, List
from copy import deepcopy

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowContext:
    """
    工作流执行上下文

    数据结构：
    {
        "inputs": {
            "user_message": "盘石头水库洪水预报",
            "entities": {"object": "盘石头水库", "object_type": "水库"}
        },
        "steps": {
            "login": {"token": "xxx", "success": true},
            "query_stcd": {"stcd": "31005650", "stnm": "盘石头水库"},
            "forecast": {"planCode": "model_auto", "data": {...}}
        },
        "state": {
            "current_step": 3,
            "workflow_name": "get_auto_forecast_result"
        }
    }
    """

    def __init__(self):
        self._data = {
            "inputs": {},
            "steps": {},
            "state": {}
        }

    @property
    def inputs(self) -> Dict[str, Any]:
        """获取用户输入数据"""
        return self._data["inputs"]

    @property
    def steps(self) -> Dict[str, Any]:
        """获取各步骤执行结果"""
        return self._data["steps"]

    @property
    def state(self) -> Dict[str, Any]:
        """获取全局状态"""
        return self._data["state"]

    def set_input(self, key: str, value: Any):
        """
        设置用户输入数据

        Args:
            key: 输入键名
            value: 输入值
        """
        self._data["inputs"][key] = value
        logger.debug(f"Context.inputs.{key} = {str(value)[:100]}")

    def set_inputs(self, inputs: Dict[str, Any]):
        """
        批量设置用户输入数据

        Args:
            inputs: 输入数据字典
        """
        self._data["inputs"].update(inputs)
        logger.debug(f"Context.inputs updated with {len(inputs)} keys")

    def set_step_result(self, step_name: str, result: Dict[str, Any]):
        """
        设置步骤执行结果

        Args:
            step_name: 步骤名称（如 "login", "query_stcd"）
            result: 步骤执行结果
        """
        self._data["steps"][step_name] = result
        logger.debug(f"Context.steps.{step_name} = {str(result)[:200]}")

    def set_state(self, key: str, value: Any):
        """
        设置全局状态

        Args:
            key: 状态键名
            value: 状态值
        """
        self._data["state"][key] = value

    def get(self, path: str, default: Any = None) -> Any:
        """
        通过点号路径获取值

        支持的路径格式：
        - "inputs.user_message"
        - "inputs.entities.object"
        - "steps.login.token"
        - "steps.forecast.data.planCode"
        - "state.current_step"

        Args:
            path: 点号分隔的路径
            default: 默认值（路径不存在时返回）

        Returns:
            路径对应的值，或默认值
        """
        if not path:
            return default

        parts = path.split(".")
        current = self._data

        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    return default
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return default
            else:
                return default

        return current

    def get_step(self, step_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定步骤的执行结果

        Args:
            step_name: 步骤名称

        Returns:
            步骤执行结果，不存在则返回 None
        """
        return self._data["steps"].get(step_name)

    def has(self, path: str) -> bool:
        """
        检查路径是否存在

        Args:
            path: 点号分隔的路径

        Returns:
            路径是否存在
        """
        return self.get(path, _MISSING) is not _MISSING

    def to_dict(self) -> Dict[str, Any]:
        """
        导出为字典（深拷贝）

        Returns:
            上下文数据的深拷贝
        """
        return deepcopy(self._data)

    def from_dict(self, data: Dict[str, Any]):
        """
        从字典导入数据

        Args:
            data: 上下文数据字典
        """
        if "inputs" in data:
            self._data["inputs"] = data["inputs"]
        if "steps" in data:
            self._data["steps"] = data["steps"]
        if "state" in data:
            self._data["state"] = data["state"]

    def extract_for_template(self, required_keys: List[str]) -> Dict[str, Any]:
        """
        提取模板所需的数据

        Args:
            required_keys: 需要提取的路径列表

        Returns:
            提取的数据字典，键为路径，值为对应数据
        """
        result = {}
        missing = []

        for key in required_keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
            else:
                missing.append(key)

        if missing:
            logger.warning(f"Context 中缺少以下键: {missing}")

        return result

    def __repr__(self) -> str:
        return f"WorkflowContext(inputs={len(self.inputs)}, steps={list(self.steps.keys())}, state={list(self.state.keys())})"


# 用于检测路径不存在的哨兵值
class _MissingSentinel:
    pass

_MISSING = _MissingSentinel()


def create_context_from_state(state: Dict[str, Any]) -> WorkflowContext:
    """
    从智能体状态创建工作流上下文

    Args:
        state: 智能体状态字典

    Returns:
        初始化的 WorkflowContext 实例
    """
    ctx = WorkflowContext()

    # 设置用户输入
    ctx.set_input("user_message", state.get("user_message", ""))
    ctx.set_input("entities", state.get("entities", {}))
    ctx.set_input("intent_category", state.get("intent_category", ""))
    ctx.set_input("business_sub_intent", state.get("business_sub_intent", ""))

    # 如果已有工作流上下文，恢复它
    if "workflow_context" in state and isinstance(state["workflow_context"], dict):
        existing = state["workflow_context"]
        if "steps" in existing:
            for step_name, step_result in existing["steps"].items():
                ctx.set_step_result(step_name, step_result)
        if "state" in existing:
            for key, value in existing["state"].items():
                ctx.set_state(key, value)

    return ctx
