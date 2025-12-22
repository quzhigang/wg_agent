"""
灾损评估和避险转移工具
提供洪涝灾害损失评估、避险安置点查询、转移路线查询等功能

接口基础地址: http://10.20.2.153:8686
注意: 该服务端口号为8686，与其他接口（80端口）不同
"""

from typing import Dict, Any, List, Optional
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)

# 灾损评估服务基础地址（端口8686）
DAMAGE_ASSESS_BASE_URL = "http://10.20.2.153:8686"


# ==========================================
# 一、灾损评估接口（1个）
# ==========================================

class FloodDamageLossCalcTool(BaseTool):
    """
    洪涝灾害损失计算工具
    
    用途: 根据模型编码和业务类型计算洪涝灾害造成的损失，
    包括受灾面积、受灾人口、受灾GDP、受灾企业数等，
    并返回受灾村庄和区县的GeoJSON数据
    """
    
    @property
    def name(self) -> str:
        return "flood_damage_loss_calc"
    
    @property
    def description(self) -> str:
        return "根据模型编码和业务类型计算洪涝灾害造成的损失，包括受灾面积、受灾人口、受灾GDP、受灾企业数等，并返回受灾村庄和区县的GeoJSON数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DAMAGE_ASSESS
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="模型编码，如 model_20240829111000",
                required=True
            ),
            ToolParameter(
                name="businessType",
                type="string",
                description="业务类型：flood_dispatch_route_wg-分洪调度路线、flood_dispatch_wg-分洪调度",
                required=True,
                enum=["flood_dispatch_route_wg", "flood_dispatch_wg"]
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行洪涝灾害损失计算
        
        Args:
            code: 模型编码
            businessType: 业务类型
            
        Returns:
            包含受灾统计数据和GeoJSON的工具结果
        """
        code = kwargs.get('code')
        business_type = kwargs.get('businessType')
        
        try:
            url = f"{DAMAGE_ASSESS_BASE_URL}/wgly-siyu/loss/calc"
            params = {
                "code": code,
                "businessType": business_type
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
            
            # 检查API响应状态
            if result.get("success"):
                return ToolResult(
                    success=True,
                    data=result.get("data"),
                    metadata={
                        "message": result.get("message"),
                        "code": result.get("code")
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("message", "请求失败"),
                    data=result.get("data")
                )
                
        except httpx.TimeoutException:
            logger.error(f"洪涝灾害损失计算接口超时: code={code}")
            return ToolResult(success=False, error="请求超时，请稍后重试")
        except httpx.HTTPStatusError as e:
            logger.error(f"洪涝灾害损失计算接口HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"洪涝灾害损失计算失败: {e}")
            return ToolResult(success=False, error=str(e))


# ==========================================
# 二、避险转移接口（2个）
# ==========================================

class HedgePlacementListTool(BaseTool):
    """
    避险安置点列表查询工具
    
    用途: 根据预案编码查询避险安置点列表，
    包括安置点名称、位置、联系人、容纳人数等信息
    """
    
    @property
    def name(self) -> str:
        return "hedge_placement_list"
    
    @property
    def description(self) -> str:
        return "根据预案编码查询避险安置点列表，包括安置点名称、位置、联系人、容纳人数等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DAMAGE_ASSESS
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="planCode",
                type="string",
                description="预案编码，如 model_20250524100026",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行避险安置点列表查询
        
        Args:
            planCode: 预案编码
            
        Returns:
            避险安置点列表数据
        """
        plan_code = kwargs.get('planCode')
        
        try:
            url = f"{DAMAGE_ASSESS_BASE_URL}/wgly-siyu/hedge/hedgePlacement/list"
            params = {
                "planCode": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
            
            # 检查API响应状态
            if result.get("success"):
                placement_list = result.get("data", [])
                return ToolResult(
                    success=True,
                    data=placement_list,
                    metadata={
                        "message": result.get("message"),
                        "code": result.get("code"),
                        "total_count": len(placement_list) if isinstance(placement_list, list) else 0
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("message", "请求失败"),
                    data=result.get("data")
                )
                
        except httpx.TimeoutException:
            logger.error(f"避险安置点列表查询接口超时: planCode={plan_code}")
            return ToolResult(success=False, error="请求超时，请稍后重试")
        except httpx.HTTPStatusError as e:
            logger.error(f"避险安置点列表查询接口HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"避险安置点列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class HedgeTransferRouteListTool(BaseTool):
    """
    转移路线列表查询工具
    
    用途: 根据预案编码查询转移路线列表，
    包括转移村庄、目标安置点、转移时间、联系人等信息
    """
    
    @property
    def name(self) -> str:
        return "hedge_transfer_route_list"
    
    @property
    def description(self) -> str:
        return "根据预案编码查询转移路线列表，包括转移村庄、目标安置点、转移时间、联系人等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DAMAGE_ASSESS
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="planCode",
                type="string",
                description="预案编码，如 model_20250524100026",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行转移路线列表查询
        
        Args:
            planCode: 预案编码
            
        Returns:
            转移路线列表数据
        """
        plan_code = kwargs.get('planCode')
        
        try:
            url = f"{DAMAGE_ASSESS_BASE_URL}/wgly-siyu/hedge/hedgeTransferRoute/list"
            params = {
                "planCode": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
            
            # 检查API响应状态
            if result.get("success"):
                route_list = result.get("data", [])
                return ToolResult(
                    success=True,
                    data=route_list,
                    metadata={
                        "message": result.get("message"),
                        "code": result.get("code"),
                        "total_count": len(route_list) if isinstance(route_list, list) else 0
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("message", "请求失败"),
                    data=result.get("data")
                )
                
        except httpx.TimeoutException:
            logger.error(f"转移路线列表查询接口超时: planCode={plan_code}")
            return ToolResult(success=False, error="请求超时，请稍后重试")
        except httpx.HTTPStatusError as e:
            logger.error(f"转移路线列表查询接口HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"转移路线列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ==========================================
# 工具注册
# ==========================================

def register_damage_assess_tools():
    """
    注册灾损评估和避险转移工具
    
    包含以下工具:
    1. FloodDamageLossCalcTool - 洪涝灾害损失计算
    2. HedgePlacementListTool - 避险安置点列表查询
    3. HedgeTransferRouteListTool - 转移路线列表查询
    """
    register_tool(FloodDamageLossCalcTool())
    register_tool(HedgePlacementListTool())
    register_tool(HedgeTransferRouteListTool())
    logger.info("灾损评估和避险转移工具注册完成（共3个工具）")


# 模块加载时自动注册
register_damage_assess_tools()
