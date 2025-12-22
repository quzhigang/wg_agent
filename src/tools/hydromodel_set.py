"""
水利专业模型-方案新建计算及参数设置相关工具
提供模型方案的创建、计算、参数设置等功能
所有接口基于 Model_Ser.ashx.cs 处理，使用GET/POST请求
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


class AutoForcastTool(BaseTool):
    """自动预报模型方案创建并计算工具"""
    
    @property
    def name(self) -> str:
        return "auto_forcast"
    
    @property
    def description(self) -> str:
        return "创建洪水自动预报模型方案并进行计算"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """无需输入参数"""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行自动预报模型方案创建并计算"""
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "auto_forcast",
                "request_pars": ""
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"request_type": "auto_forcast"}
            )
            
        except Exception as e:
            logger.error(f"自动预报模型创建失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"request_type": "auto_forcast"}
            )


class CreateModelTool(BaseTool):
    """手工创建模型方案工具"""
    
    @property
    def name(self) -> str:
        return "create_model"
    
    @property
    def description(self) -> str:
        return "手工创建模型方案，仅创建方案不设置边界条件，也不计算"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID，如'model_20230513101926'",
                required=True
            ),
            ToolParameter(
                name="fangan_name",
                type="string",
                description="方案名称",
                required=True
            ),
            ToolParameter(
                name="start_timestr",
                type="string",
                description="开始时间，格式如'2021/07/20 00:00:00'",
                required=True
            ),
            ToolParameter(
                name="end_timestr",
                type="string",
                description="结束时间，格式如'2021/07/21 00:00:00'",
                required=True
            ),
            ToolParameter(
                name="fangan_desc",
                type="string",
                description="方案描述，如'1日模拟'",
                required=True
            ),
            ToolParameter(
                name="step_saveminutes",
                type="integer",
                description="结果保存步长(分钟)",
                required=True
            ),
            ToolParameter(
                name="base_plan_code",
                type="string",
                description="基础方案ID，默认采用空字符串",
                required=False,
                default=""
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行手工创建模型方案"""
        plan_code = kwargs.get('plan_code')
        fangan_name = kwargs.get('fangan_name')
        start_timestr = kwargs.get('start_timestr')
        end_timestr = kwargs.get('end_timestr')
        fangan_desc = kwargs.get('fangan_desc')
        step_saveminutes = kwargs.get('step_saveminutes')
        base_plan_code = kwargs.get('base_plan_code', '')
        
        try:
            url = MODEL_SERVER_URL
            # 构建request_pars参数数组
            request_pars = json.dumps([
                plan_code, 
                fangan_name, 
                start_timestr, 
                end_timestr, 
                fangan_desc, 
                step_saveminutes, 
                base_plan_code
            ])
            params = {
                "request_type": "create_model",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "create_model"}
            )
            
        except Exception as e:
            logger.error(f"手工创建模型方案失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "create_model"}
            )


class ChangeModelBaseinfoTool(BaseTool):
    """修改模型方案基本信息工具"""
    
    @property
    def name(self) -> str:
        return "change_model_baseinfo"
    
    @property
    def description(self) -> str:
        return "修改模型方案名称、描述和保存时间步长"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="fangan_name",
                type="string",
                description="新的模型名称",
                required=True
            ),
            ToolParameter(
                name="model_desc",
                type="string",
                description="新的模型描述",
                required=True
            ),
            ToolParameter(
                name="step_save_minutes",
                type="integer",
                description="保存时间步长(分钟)",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行修改模型方案基本信息"""
        plan_code = kwargs.get('plan_code')
        fangan_name = kwargs.get('fangan_name')
        model_desc = kwargs.get('model_desc')
        step_save_minutes = kwargs.get('step_save_minutes')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, fangan_name, model_desc, step_save_minutes])
            params = {
                "request_type": "change_model_baseinfo",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "change_model_baseinfo"}
            )
            
        except Exception as e:
            logger.error(f"修改模型方案基本信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "change_model_baseinfo"}
            )


class DelModelTool(BaseTool):
    """删除模型方案工具"""
    
    @property
    def name(self) -> str:
        return "del_model"
    
    @property
    def description(self) -> str:
        return "删除模型方案，返回剩下的模型方案基础信息集合"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="要删除的方案ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行删除模型方案"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "del_model",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "del_model"}
            )
            
        except Exception as e:
            logger.error(f"删除模型方案失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "del_model"}
            )


class RunModelTool(BaseTool):
    """计算模型工具"""
    
    @property
    def name(self) -> str:
        return "run_model"
    
    @property
    def description(self) -> str:
        return "计算模型，返回所需的计算时间(秒)"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def timeout_seconds(self) -> int:
        return 600  # 10分钟超时
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行模型计算"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "run_model",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=600) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                # 返回值为计算所需时间(秒)的字符串
                data = response.text
            
            return ToolResult(
                success=True,
                data={"expect_seconds": data},
                metadata={"plan_code": plan_code, "request_type": "run_model"}
            )
            
        except Exception as e:
            logger.error(f"模型计算失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "run_model"}
            )


class RunModelQuickTool(BaseTool):
    """一维快速计算模型工具"""
    
    @property
    def name(self) -> str:
        return "run_model_quick"
    
    @property
    def description(self) -> str:
        return "一维快速计算模型(不进行GIS结果后处理)，返回所需的计算时间(秒)"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def timeout_seconds(self) -> int:
        return 300  # 5分钟超时
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行一维快速模型计算"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "run_model_quick",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                # 返回值为计算所需时间(秒)的字符串
                data = response.text
            
            return ToolResult(
                success=True,
                data={"expect_seconds": data},
                metadata={"plan_code": plan_code, "request_type": "run_model_quick"}
            )
            
        except Exception as e:
            logger.error(f"一维快速模型计算失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "run_model_quick"}
            )


class StopModelTool(BaseTool):
    """停止模型计算工具"""
    
    @property
    def name(self) -> str:
        return "stop_model"
    
    @property
    def description(self) -> str:
        return "停止模型计算，返回成功信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行停止模型计算"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "stop_model",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "stop_model"}
            )
            
        except Exception as e:
            logger.error(f"停止模型计算失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "stop_model"}
            )


class ModifyInitialTool(BaseTool):
    """修改初始水位条件工具"""
    
    @property
    def name(self) -> str:
        return "modify_initial"
    
    @property
    def description(self) -> str:
        return "修改方案的水库河道初始水位条件"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="initial_level",
                type="string",
                description="初始水位设置。可输入'monitor'(采用监测水位)，或水位字典JSON格式如'{\"站点ID1\": 水位值1, \"站点ID2\": 水位值2}'",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行修改初始水位条件"""
        plan_code = kwargs.get('plan_code')
        initial_level = kwargs.get('initial_level')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, initial_level])
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    data={
                        "request_type": "modify_initial",
                        "request_pars": request_pars
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "modify_initial"}
            )
            
        except Exception as e:
            logger.error(f"修改初始水位条件失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "modify_initial"}
            )


class ChangeRfmodelTool(BaseTool):
    """修改产汇流模型类型工具"""
    
    @property
    def name(self) -> str:
        return "change_rfmodel"
    
    @property
    def description(self) -> str:
        return "修改方案的各个子流域产汇流模型类型"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="rf_model",
                type="string",
                description="产汇流模型参数JSON，格式为'{\"子流域编码1\": \"模型编码1\", \"子流域编码2\": \"模型编码2\"}'。模型编码共3种: 'nam'、'swmm5'、'xaj'。可为空对象或空字符串",
                required=False,
                default=""
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行修改产汇流模型类型"""
        plan_code = kwargs.get('plan_code')
        rf_model = kwargs.get('rf_model', '')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, rf_model])
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    data={
                        "request_type": "change_rfmodel",
                        "request_pars": request_pars
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "change_rfmodel"}
            )
            
        except Exception as e:
            logger.error(f"修改产汇流模型类型失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "change_rfmodel"}
            )


class ChangeBoundryTool(BaseTool):
    """修改洪水入流边界条件工具"""
    
    @property
    def name(self) -> str:
        return "change_boundry"
    
    @property
    def description(self) -> str:
        return "修改方案的洪水入流边界条件，可指定为利用降雨计算洪水、直接指定子流域洪水过程、指定河道洪水过程或无洪水入流"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="bnd_type",
                type="string",
                description="边界类型: 'rf_model'(降雨计算洪水), 'reach_inflow'(指定河道洪水), 'no_inflow'(无洪水入流), 'catchment_inflow'(指定子流域洪水)",
                required=True,
                enum=["rf_model", "reach_inflow", "no_inflow", "catchment_inflow"]
            ),
            ToolParameter(
                name="bnd_value",
                type="string",
                description="边界值JSON。当bnd_type为'reach_inflow'时，格式为'{\"边界条件编码1\": {\"时间1\": 流量1, \"时间2\": 流量2}}'；当bnd_type为'catchment_inflow'时，格式为'{\"子流域编码1\": {\"时间1\": 流量1}}'。其他类型不需要此参数",
                required=False,
                default=""
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行修改洪水入流边界条件"""
        plan_code = kwargs.get('plan_code')
        bnd_type = kwargs.get('bnd_type')
        bnd_value = kwargs.get('bnd_value', '')
        
        try:
            url = MODEL_SERVER_URL
            # 根据是否有边界值构建参数数组
            if bnd_value:
                request_pars = json.dumps([plan_code, bnd_type, bnd_value])
            else:
                request_pars = json.dumps([plan_code, bnd_type])
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    data={
                        "request_type": "change_boundry",
                        "request_pars": request_pars
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "bnd_type": bnd_type, "request_type": "change_boundry"}
            )
            
        except Exception as e:
            logger.error(f"修改洪水入流边界条件失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "change_boundry"}
            )


class ModifyGatestateTool(BaseTool):
    """修改闸站调度设置工具"""
    
    @property
    def name(self) -> str:
        return "modify_gatestate"
    
    @property
    def description(self) -> str:
        return "修改方案闸站调度设置"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="gate_dispatch",
                type="string",
                description="调度方式。可为'monitor'(采用当前监测的闸站状态工情)、'gaterule'(采用各闸站设计调度规则)、或调度指令数组JSON格式'[[\"建筑物编码1\",[\"时间1\",\"操作类型1\",\"闸孔数\",\"值\"]],...]'",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行修改闸站调度设置"""
        plan_code = kwargs.get('plan_code')
        gate_dispatch = kwargs.get('gate_dispatch')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, gate_dispatch])
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    data={
                        "request_type": "modify_gatestate",
                        "request_pars": request_pars
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "modify_gatestate"}
            )
            
        except Exception as e:
            logger.error(f"修改闸站调度设置失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "modify_gatestate"}
            )


class ChangeReachBreakTool(BaseTool):
    """修改河堤溃口设置工具"""
    
    @property
    def name(self) -> str:
        return "change_reach_break"
    
    @property
    def description(self) -> str:
        return "修改方案河堤溃口设置"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="break_name",
                type="string",
                description="溃口名称",
                required=True
            ),
            ToolParameter(
                name="location",
                type="array",
                description="溃口位置坐标 [经度, 纬度]",
                required=True
            ),
            ToolParameter(
                name="fh_width",
                type="float",
                description="溃口宽度(米)",
                required=True
            ),
            ToolParameter(
                name="fh_minutes",
                type="integer",
                description="溃堤时长(分钟)",
                required=True
            ),
            ToolParameter(
                name="break_condition",
                type="string",
                description="溃决时机描述: 'max_level'(河道水位达到最高水位) 或 'set_level'(指定河道水位)",
                required=True,
                enum=["max_level", "set_level"]
            ),
            ToolParameter(
                name="break_level",
                type="float",
                description="溃决水位。当break_condition为'max_level'时可填任意值(如0)，否则填指定值",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行修改河堤溃口设置"""
        plan_code = kwargs.get('plan_code')
        break_name = kwargs.get('break_name')
        location = kwargs.get('location')
        fh_width = kwargs.get('fh_width')
        fh_minutes = kwargs.get('fh_minutes')
        break_condition = kwargs.get('break_condition')
        break_level = kwargs.get('break_level')
        
        try:
            url = MODEL_SERVER_URL
            # 构建溃口基本信息JSON对象
            break_info = {
                "name": break_name,
                "location": location,
                "fh_width": fh_width,
                "fh_minutes": fh_minutes,
                "break_condition": break_condition,
                "break_level": break_level
            }
            request_pars = json.dumps([plan_code, break_info])
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    data={
                        "request_type": "change_reach_break",
                        "request_pars": request_pars
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "break_name": break_name, "request_type": "change_reach_break"}
            )
            
        except Exception as e:
            logger.error(f"修改河堤溃口设置失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "change_reach_break"}
            )


class SetDispatchTargetTool(BaseTool):
    """设置优化调度目标参数工具"""
    
    @property
    def name(self) -> str:
        return "set_dispatch_target"
    
    @property
    def description(self) -> str:
        return "设置方案的优化调度目标参数"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="dd_target",
                type="object",
                description="调度目标对象，格式为'{\"name\": \"元村\", \"stcd\": \"31004300\", \"max_discharge\": 2500}'，包含水文站名称、水文站ID、最大允许洪峰流量",
                required=True
            ),
            ToolParameter(
                name="res_level_constraint",
                type="array",
                description="水库调洪水位约束数组，格式为'[{\"name\": \"双泉水库\", \"stcd\": \"31006950\", \"level_name\": \"防洪高水位\", \"level_value\": 142.3}]'",
                required=True
            ),
            ToolParameter(
                name="other_constraint",
                type="object",
                description="其他约束对象，格式为'{\"gate\": true, \"reach\": true, \"xzhq_level\": true}'，分别为闸门过流能力约束、河道过流能力约束、滞洪区滞洪水位约束",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行设置优化调度目标参数"""
        plan_code = kwargs.get('plan_code')
        dd_target = kwargs.get('dd_target')
        res_level_constraint = kwargs.get('res_level_constraint')
        other_constraint = kwargs.get('other_constraint')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, dd_target, res_level_constraint, other_constraint])
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    data={
                        "request_type": "set_dispatch_target",
                        "request_pars": request_pars
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "set_dispatch_target"}
            )
            
        except Exception as e:
            logger.error(f"设置优化调度目标参数失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "set_dispatch_target"}
            )


class IterCalTool(BaseTool):
    """优化迭代计算工具"""
    
    @property
    def name(self) -> str:
        return "iter_cal"
    
    @property
    def description(self) -> str:
        return "开始方案的优化迭代计算"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def timeout_seconds(self) -> int:
        return 600  # 10分钟超时
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行优化迭代计算"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "iter_cal",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=600) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                # 返回值为计算所需时间(秒)的字符串
                data = response.text
            
            return ToolResult(
                success=True,
                data={"expect_seconds": data},
                metadata={"plan_code": plan_code, "request_type": "iter_cal"}
            )
            
        except Exception as e:
            logger.error(f"优化迭代计算失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "iter_cal"}
            )


class BackcalResddTool(BaseTool):
    """反向推演水库调度方案工具"""
    
    @property
    def name(self) -> str:
        return "backcal_resdd"
    
    @property
    def description(self) -> str:
        return "反向推演水库的调度方案和该调度方案下的调蓄结果。需要设置水库允许达到的最高水位，并且只针对已经完成的预报预演方案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def timeout_seconds(self) -> int:
        return 300  # 5分钟超时
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="res_name",
                type="string",
                description="水库名称",
                required=True
            ),
            ToolParameter(
                name="max_level",
                type="float",
                description="允许最高水位",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行反向推演水库调度方案"""
        plan_code = kwargs.get('plan_code')
        res_name = kwargs.get('res_name')
        max_level = kwargs.get('max_level')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, res_name, max_level])
            params = {
                "request_type": "backcal_resdd",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "res_name": res_name, "request_type": "backcal_resdd"}
            )
            
        except Exception as e:
            logger.error(f"反向推演水库调度方案失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "res_name": res_name, "request_type": "backcal_resdd"}
            )


class SetFaultGateTool(BaseTool):
    """设置故障闸门工具"""
    
    @property
    def name(self) -> str:
        return "set_fault_gate"
    
    @property
    def description(self) -> str:
        return "设置方案的故障闸门"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="sluice_code",
                type="string",
                description="故障水闸编码，如'QHNZ_XHKJZZ'",
                required=True
            ),
            ToolParameter(
                name="fault_desc",
                type="string",
                description="故障信息描述，如'部分闸门无法完全关闭'",
                required=True
            ),
            ToolParameter(
                name="fault_gate_codes",
                type="array",
                description="故障闸门编码数组，如['XHK_JZZ2', 'XHK_JZZ4']",
                required=True
            ),
            ToolParameter(
                name="gate_openings",
                type="array",
                description="水闸各闸门开度数组，如[0, 0.5, 0, 0.2, 0]",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行设置故障闸门"""
        plan_code = kwargs.get('plan_code')
        sluice_code = kwargs.get('sluice_code')
        fault_desc = kwargs.get('fault_desc')
        fault_gate_codes = kwargs.get('fault_gate_codes')
        gate_openings = kwargs.get('gate_openings')
        
        try:
            url = MODEL_SERVER_URL
            # 构建故障闸门信息数组
            fault_dinfo = [sluice_code, fault_desc, fault_gate_codes, gate_openings]
            request_pars = json.dumps([plan_code, fault_dinfo])
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    data={
                        "request_type": "set_fault_gate",
                        "request_pars": request_pars
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "sluice_code": sluice_code, "request_type": "set_fault_gate"}
            )
            
        except Exception as e:
            logger.error(f"设置故障闸门失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "set_fault_gate"}
            )


# 注册所有工具
def register_hydromodel_set_tools():
    """注册水利专业模型-方案新建计算及参数设置相关工具"""
    register_tool(AutoForcastTool())           # 1. auto_forcast - 自动预报
    register_tool(CreateModelTool())           # 2. create_model - 手工创建模型方案
    register_tool(ChangeModelBaseinfoTool())   # 3. change_model_baseinfo - 修改方案基本信息
    register_tool(DelModelTool())              # 4. del_model - 删除模型方案
    register_tool(RunModelTool())              # 5. run_model - 计算模型
    register_tool(RunModelQuickTool())         # 6. run_model_quick - 一维快速计算
    register_tool(StopModelTool())             # 7. stop_model - 停止模型计算
    register_tool(ModifyInitialTool())         # 8. modify_initial - 修改初始水位条件
    register_tool(ChangeRfmodelTool())         # 9. change_rfmodel - 修改产汇流模型类型
    register_tool(ChangeBoundryTool())         # 10. change_boundry - 修改洪水入流边界条件
    register_tool(ModifyGatestateTool())       # 11. modify_gatestate - 修改闸站调度设置
    register_tool(ChangeReachBreakTool())      # 12. change_reach_break - 修改河堤溃口设置
    register_tool(SetDispatchTargetTool())     # 13. set_dispatch_target - 设置优化调度目标参数
    register_tool(IterCalTool())               # 14. iter_cal - 优化迭代计算
    register_tool(BackcalResddTool())          # 15. backcal_resdd - 反向推演水库调度方案
    register_tool(SetFaultGateTool())          # 16. set_fault_gate - 设置故障闸门
    logger.info("水利专业模型-方案新建计算及参数设置相关工具注册完成，共16个接口")


# 模块加载时自动注册
register_hydromodel_set_tools()
