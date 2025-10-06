"""
Data models for Blender MCP Server
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Server configuration data class"""
    host: str = "localhost"
    port: int = 8765
    auto_start: bool = True
    allowed_ips: List[str] = None
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.allowed_ips is None:
            self.allowed_ips = ["127.0.0.1"]


@dataclass
class CommandMessage:
    """Command message data class"""
    command: str
    params: Dict[str, Any]
    client_id: Optional[str] = None


@dataclass
class ResponseMessage:
    """Response message data class"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BlenderCommand:
    """Command to be executed on Blender main thread"""
    command_id: str
    command: str
    params: Dict[str, Any]
    client_id: str