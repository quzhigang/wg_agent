"""
用户认证工具
处理用户登录和会话保持，获取访问令牌
"""

from typing import Dict, Any, List, Optional
import httpx
import time
import json
import base64
import asyncio

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)

# API基础地址常量
API_BASE_URL = "http://10.20.2.153"


class LoginTool(BaseTool):
    """
    用户登录工具
    模拟用户登录过程，获取访问令牌(Token)，用于后续接口调用鉴权
    """
    
    # 类变量存储当前的Token和Session信息，简单实现内存缓存
    _current_token: Optional[str] = None
    _current_user_id: Optional[str] = None
    _token_expiration: Optional[int] = None # Token过期时间戳(秒)
    
    @property
    def name(self) -> str:
        return "login_basin_system"
    
    @property
    def description(self) -> str:
        return "登录卫共流域数字孪生系统，获取访问令牌(Token)。通常在需要鉴权的接口调用前执行。"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO  # 暂时归类为基础信息类
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="account",
                type="string",
                description="登录账号，可选，默认使用系统配置",
                required=False,
                default=settings.basin_auth_account
            ),
            ToolParameter(
                name="password",
                type="string",
                description="登录密码，可选，默认使用系统配置",
                required=False,
                default=settings.basin_auth_password
            ),
             ToolParameter(
                name="force_refresh",
                type="boolean",
                description="是否强制刷新Token",
                required=False,
                default=False
            )
        ]
    
    @classmethod
    def get_token(cls) -> Optional[str]:
        """获取当前有效的Token"""
        # 检查是否过期
        if cls._current_token and cls._token_expiration:
            # 提前5分钟认为过期，确保可用
            if time.time() > (cls._token_expiration - 300):
                logger.info("Token即将过期或已过期")
                return None
        return cls._current_token

    @classmethod
    async def get_auth_headers(cls) -> Dict[str, str]:
        """
        获取认证请求头
        如果Token不存在或过期，会自动尝试登录
        """
        token = cls.get_token()
        if not token:
            logger.info("Token无效或不存在，尝试自动登录...")
            # 创建实例并执行登录
            tool = LoginTool()
            result = await tool.execute()
            if result.success and result.data:
                token = result.data.get("token")
            else:
                logger.error(f"自动登录失败: {result.error}")
                # 登录失败也返回空，由调用方处理
                return {}
        
        if token:
            # 根据Postman测试，服务器期望Authorization头直接使用token值（不带Bearer前缀）
            return {
                "token": token,
                "Authorization": token
            }
        return {}

    @staticmethod
    def _parse_expiration(token: str) -> Optional[int]:
        """尝试从JWT Token中解析过期时间"""
        try:
            # JWT格式: header.payload.signature
            parts = token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                #补全padding
                padding = len(payload) % 4
                if padding > 0:
                    payload += '=' * (4 - padding)
                
                decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
                data = json.loads(decoded)
                
                # 获取exp字段 (Unix时间戳)
                exp = data.get('exp')
                # 或者 expirationDate (提供的示例中有这个字段: 1767056888035 - 毫秒级)
                expiration_date = data.get('expirationDate')
                
                if expiration_date:
                    return int(expiration_date / 1000)
                
                if exp:
                    return int(exp)
            return None
        except Exception as e:
            logger.warning(f"解析Token过期时间失败: {e}")
            return None
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行登录操作"""
        account = kwargs.get('account') or settings.basin_auth_account
        password = kwargs.get('password') or settings.basin_auth_password
        force_refresh = kwargs.get('force_refresh', False)

        # 如果不强制刷新且当前有有效Token，直接返回
        if not force_refresh:
            current = self.get_token()
            if current:
                return ToolResult(
                    success=True,
                    data={
                        "token": current,
                        "userId": self._current_user_id,
                        "message": "使用现有有效Token"
                    }
                )
        
        try:
            url = f"{API_BASE_URL}/api/basin/loginApi"
            
            # 构建请求参数
            params = {
                'account': account,
                'password': password
            }
            
            logger.info(f"正在尝试登录系统，账号: {account}")
            
            async with httpx.AsyncClient(timeout=30) as client:
                # 使用POST请求，Content-Type为application/json
                response = await client.post(url, json=params)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                data = result.get('data', {})
                token = data.get('token')
                user_id = data.get('userId')
                
                if token:
                    # 更新缓存
                    LoginTool._current_token = token
                    LoginTool._current_user_id = user_id
                    
                    # 尝试解析过期时间
                    exp = self._parse_expiration(token)
                    if exp:
                        LoginTool._token_expiration = exp
                        logger.info(f"Token过期时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp))}")
                    else:
                        # 默认30分钟过期 (根据配置或保守估计)
                        LoginTool._token_expiration = int(time.time()) + 1800
                    
                    # 只显示token的前20个字符，保护敏感信息
                    token_preview = token[:20] + "..." if len(token) > 20 else token
                    logger.info(f"登录成功，获取到Token: {token_preview}")
                    
                    # 等待1.5秒让服务器建立会话，避免后续请求因会话未就绪而失败
                    logger.info("等待服务器建立会话...")
                    await asyncio.sleep(1.5)
                    
                    return ToolResult(
                        success=True,
                        data={
                            "token": token,
                            "userId": user_id,
                            "message": "登录成功"
                        },
                        metadata={"code": result.get('code'), "message": result.get('message')}
                    )
                else:
                    return ToolResult(
                        success=False,
                        error="登录响应中未包含Token",
                        metadata={"response": result}
                    )
            else:
                error_msg = result.get('message', '登录失败')
                logger.warning(f"登录失败: {error_msg}")
                return ToolResult(
                    success=False,
                    error=error_msg,
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"登录请求HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"登录执行异常: {e}")
            return ToolResult(success=False, error=str(e))


# 模块加载时自动注册
register_tool(LoginTool())
