"""
PageIndex 多知识库管理模块

本模块提供多知识库的管理功能，包括创建、删除、列表等操作。
每个知识库拥有独立的文档存储目录和向量索引。
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class KnowledgeBaseInfo:
    """知识库信息"""
    id: str                          # 知识库唯一标识（英文/拼音）
    name: str                        # 知识库显示名称（中文）
    description: str = ""            # 知识库描述
    created_at: str = ""             # 创建时间
    doc_count: int = 0               # 文档数量
    node_count: int = 0              # 节点数量
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeBaseInfo':
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            doc_count=data.get("doc_count", 0),
            node_count=data.get("node_count", 0)
        )


class KnowledgeBaseManager:
    """
    知识库管理器
    
    管理多个知识库的创建、删除、配置等操作。
    每个知识库拥有独立的目录结构：
    - uploads/: 文档上传目录
    - results/: 结构文件目录
    - chroma_db/: 向量索引目录
    """
    
    _instance: Optional['KnowledgeBaseManager'] = None
    
    def __new__(cls, base_dir: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, base_dir: str = None):
        if self._initialized:
            return
        
        # 知识库根目录
        if base_dir:
            self._base_dir = base_dir
        else:
            # 默认使用 PageIndex/knowledge_bases 目录
            _module_dir = os.path.dirname(os.path.abspath(__file__))
            self._base_dir = os.path.join(os.path.dirname(_module_dir), "knowledge_bases")
        
        # 配置文件路径
        self._config_file = os.path.join(self._base_dir, "kb_config.json")
        
        # 确保目录存在
        os.makedirs(self._base_dir, exist_ok=True)
        
        # 加载配置
        self._config = self._load_config()
        
        self._initialized = True
    
    def _load_config(self) -> Dict[str, Any]:
        """加载知识库配置"""
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载知识库配置失败: {e}")
        return {"knowledge_bases": []}
    
    def _save_config(self):
        """保存知识库配置"""
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存知识库配置失败: {e}")
            raise
    
    def get_kb_dir(self, kb_id: str) -> str:
        """获取知识库目录路径"""
        return os.path.join(self._base_dir, kb_id)
    
    def get_uploads_dir(self, kb_id: str) -> str:
        """获取知识库的文档上传目录"""
        return os.path.join(self.get_kb_dir(kb_id), "uploads")
    
    def get_results_dir(self, kb_id: str) -> str:
        """获取知识库的结构文件目录"""
        return os.path.join(self.get_kb_dir(kb_id), "results")
    
    def get_chroma_dir(self, kb_id: str) -> str:
        """获取知识库的向量索引目录"""
        return os.path.join(self.get_kb_dir(kb_id), "chroma_db")
    
    def exists(self, kb_id: str) -> bool:
        """检查知识库是否存在"""
        for kb in self._config.get("knowledge_bases", []):
            if kb.get("id") == kb_id:
                return True
        return False
    
    def create(self, kb_id: str, name: str, description: str = "") -> KnowledgeBaseInfo:
        """
        创建新知识库
        
        参数:
            kb_id: 知识库唯一标识（英文/拼音，不能与现有重复）
            name: 知识库显示名称（中文）
            description: 知识库描述（可选）
        
        返回:
            创建的知识库信息
        
        异常:
            ValueError: 如果知识库ID已存在
        """
        # 清理输入：去除前后空白和不可见字符
        kb_id = kb_id.strip()
        # 移除零宽字符等不可见字符
        import unicodedata
        kb_id = ''.join(c for c in kb_id if unicodedata.category(c) not in ('Cf', 'Cc'))

        # 检查ID是否已存在
        if self.exists(kb_id):
            raise ValueError(f"知识库ID '{kb_id}' 已存在，请使用其他ID")

        # 验证ID格式（只允许字母、数字、下划线）
        if not kb_id or not kb_id.replace("_", "").isalnum():
            raise ValueError("知识库ID只能包含字母、数字和下划线")
        
        # 创建目录结构
        kb_dir = self.get_kb_dir(kb_id)
        os.makedirs(self.get_uploads_dir(kb_id), exist_ok=True)
        os.makedirs(self.get_results_dir(kb_id), exist_ok=True)
        os.makedirs(self.get_chroma_dir(kb_id), exist_ok=True)
        
        # 创建知识库信息
        kb_info = KnowledgeBaseInfo(
            id=kb_id,
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            doc_count=0,
            node_count=0
        )
        
        # 添加到配置
        self._config["knowledge_bases"].append(kb_info.to_dict())
        self._save_config()
        
        print(f"已创建知识库: {name} ({kb_id})")
        return kb_info
    
    def delete(self, kb_id: str) -> bool:
        """
        删除知识库
        
        参数:
            kb_id: 知识库ID
        
        返回:
            是否删除成功
        """
        if not self.exists(kb_id):
            return False
        
        # 从配置中移除
        self._config["knowledge_bases"] = [
            kb for kb in self._config.get("knowledge_bases", [])
            if kb.get("id") != kb_id
        ]
        self._save_config()
        
        # 删除目录（可选，这里只删除配置，保留文件以防误删）
        # 如果需要删除文件，可以取消下面的注释
        # import shutil
        # kb_dir = self.get_kb_dir(kb_id)
        # if os.path.exists(kb_dir):
        #     shutil.rmtree(kb_dir)
        
        print(f"已删除知识库: {kb_id}")
        return True
    
    def get(self, kb_id: str) -> Optional[KnowledgeBaseInfo]:
        """获取知识库信息"""
        for kb in self._config.get("knowledge_bases", []):
            if kb.get("id") == kb_id:
                return KnowledgeBaseInfo.from_dict(kb)
        return None
    
    def list_all(self) -> List[KnowledgeBaseInfo]:
        """列出所有知识库"""
        return [
            KnowledgeBaseInfo.from_dict(kb)
            for kb in self._config.get("knowledge_bases", [])
        ]
    
    def list_ids(self) -> List[str]:
        """列出所有知识库ID"""
        return [kb.get("id") for kb in self._config.get("knowledge_bases", [])]
    
    def update_stats(self, kb_id: str, doc_count: int = None, node_count: int = None):
        """
        更新知识库统计信息
        
        参数:
            kb_id: 知识库ID
            doc_count: 文档数量（可选）
            node_count: 节点数量（可选）
        """
        for kb in self._config.get("knowledge_bases", []):
            if kb.get("id") == kb_id:
                if doc_count is not None:
                    kb["doc_count"] = doc_count
                if node_count is not None:
                    kb["node_count"] = node_count
                self._save_config()
                return
    
    def get_all_kb_ids(self) -> List[str]:
        """获取所有知识库ID列表"""
        return self.list_ids()


# 全局知识库管理器实例
_kb_manager_instance: Optional[KnowledgeBaseManager] = None


def get_kb_manager() -> KnowledgeBaseManager:
    """
    获取全局知识库管理器实例（单例模式）
    
    返回:
        KnowledgeBaseManager 实例
    """
    global _kb_manager_instance
    if _kb_manager_instance is None:
        _kb_manager_instance = KnowledgeBaseManager()
    return _kb_manager_instance


def reset_kb_manager():
    """重置知识库管理器实例（用于测试）"""
    global _kb_manager_instance
    if _kb_manager_instance is not None:
        _kb_manager_instance._initialized = False
    _kb_manager_instance = None
