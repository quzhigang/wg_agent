"""
水利专业模型-获取专业模型参数及边界条件相关工具
提供产汇流模型类型、河堤溃口设置、故障闸门信息、调度信息、初始水情、边界条件、优化调度目标等参数信息的获取功能
所有接口基于 Model_Ser.ashx.cs 处理，接口地址统一为：http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx
"""

from typing import Dict, Any, List, Optional
import json
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)

# 模型服务基础URL
MODEL_SERVER_URL = "http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx"


class GetRfmodelTool(BaseTool):
    """获取方案的产汇流模型类型工具"""
    
    @property
    def name(self) -> str:
        return "get_rfmodel"
    
    @property
    def description(self) -> str:
        return "获取方案的产汇流模型类型，返回各子流域采用的产汇流模型编码（共3种：nam、swmm5、xaj）"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取产汇流模型类型"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_rfmodel",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_rfmodel"}
            )
            
        except Exception as e:
            logger.error(f"获取产汇流模型类型失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_rfmodel"}
            )


class GetReachBreakTool(BaseTool):
    """获取方案河堤溃口设置信息工具"""
    
    @property
    def name(self) -> str:
        return "get_reach_break"
    
    @property
    def description(self) -> str:
        return "获取方案河堤溃口设置信息，包括溃口编码、名称、位置、溃口宽度、溃堤时长、溃决水位、溃口底高程、开始溃口时间等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取河堤溃口设置信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_reach_break",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_reach_break"}
            )
            
        except Exception as e:
            logger.error(f"获取河堤溃口设置信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_reach_break"}
            )


class GetFaultgateBaseinfoTool(BaseTool):
    """获取故障水闸的闸门基本信息工具"""
    
    @property
    def name(self) -> str:
        return "get_faultgate_baseinfo"
    
    @property
    def description(self) -> str:
        return "获取故障水闸的闸门基本信息，根据业务编码获取，一个业务编码对应一个故障水闸。返回建筑物编码、名称及各闸门的编码、名称、闸底高程、闸门高度、经纬度坐标等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="business_code",
                type="string",
                description="业务编码字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取故障水闸的闸门基本信息"""
        business_code = kwargs.get('business_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_faultgate_baseinfo",
                "request_pars": business_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"business_code": business_code, "request_type": "get_faultgate_baseinfo"}
            )
            
        except Exception as e:
            logger.error(f"获取故障水闸的闸门基本信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"business_code": business_code, "request_type": "get_faultgate_baseinfo"}
            )


class GetFaultGateTool(BaseTool):
    """获取方案的故障闸门信息工具"""
    
    @property
    def name(self) -> str:
        return "get_fault_gate"
    
    @property
    def description(self) -> str:
        return "获取方案的故障闸门信息，包括故障水闸名称、故障描述、各闸门最大开度和当前开度、故障闸门名称及经纬度"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取方案的故障闸门信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_fault_gate",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_fault_gate"}
            )
            
        except Exception as e:
            logger.error(f"获取方案的故障闸门信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_fault_gate"}
            )


class GetDdinfoTool(BaseTool):
    """获取模型方案所有可控建筑物的调度信息工具"""
    
    @property
    def name(self) -> str:
        return "get_ddinfo"
    
    @property
    def description(self) -> str:
        return "获取模型方案所有可控建筑物的调度信息，包括建筑物编码、序号、名称、类型、所在河道及闸门调度过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取可控建筑物调度信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_ddinfo",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_ddinfo"}
            )
            
        except Exception as e:
            logger.error(f"获取可控建筑物调度信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_ddinfo"}
            )


class GetInitialWaterlevelTool(BaseTool):
    """获取模型方案的初始水情信息工具"""
    
    @property
    def name(self) -> str:
        return "get_initial_waterlevel"
    
    @property
    def description(self) -> str:
        return "获取模型方案的初始水情信息，包括各水库和河道站点的序号、名称、初始水位、水位来源、stcd编码等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取初始水情信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_initial_waterlevel",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_initial_waterlevel"}
            )
            
        except Exception as e:
            logger.error(f"获取初始水情信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_initial_waterlevel"}
            )


class GetBndinfoTool(BaseTool):
    """获取模型方案的边界条件信息工具"""
    
    @property
    def name(self) -> str:
        return "get_bndinfo"
    
    @property
    def description(self) -> str:
        return "获取模型方案的边界条件信息，包括边界条件类型描述（如'降雨计算洪水'）和边界条件值（各子流域的流量过程）"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取边界条件信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_bndinfo",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_bndinfo"}
            )
            
        except Exception as e:
            logger.error(f"获取边界条件信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_bndinfo"}
            )


class GetDispatchTargetTool(BaseTool):
    """获取方案的优化调度目标设置信息工具"""
    
    @property
    def name(self) -> str:
        return "get_dispatch_target"
    
    @property
    def description(self) -> str:
        return "获取方案的优化调度目标设置信息，包括方案ID、调度目标（站点名称、stcd、最大流量）、各水库约束水位及其他约束条件"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取优化调度目标设置信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_dispatch_target",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_dispatch_target"}
            )
            
        except Exception as e:
            logger.error(f"获取优化调度目标设置信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_dispatch_target"}
            )


# 注册所有工具
def register_hydromodel_parget_tools():
    """注册水利专业模型-获取专业模型参数及边界条件相关工具"""
    register_tool(GetRfmodelTool())                 # 1. get_rfmodel - 获取产汇流模型类型
    register_tool(GetReachBreakTool())              # 2. get_reach_break - 获取河堤溃口设置信息
    register_tool(GetFaultgateBaseinfoTool())       # 3. get_faultgate_baseinfo - 获取故障水闸的闸门基本信息
    register_tool(GetFaultGateTool())               # 4. get_fault_gate - 获取方案的故障闸门信息
    register_tool(GetDdinfoTool())                  # 5. get_ddinfo - 获取可控建筑物调度信息
    register_tool(GetInitialWaterlevelTool())       # 6. get_initial_waterlevel - 获取初始水情信息
    register_tool(GetBndinfoTool())                 # 7. get_bndinfo - 获取边界条件信息
    register_tool(GetDispatchTargetTool())          # 8. get_dispatch_target - 获取优化调度目标设置信息
    logger.info("水利专业模型-获取专业模型参数及边界条件相关工具注册完成，共8个接口")


# 模块加载时自动注册
register_hydromodel_parget_tools()
