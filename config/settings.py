import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class BlenderMCPConfig:
    host: str = "localhost"
    port: int = 8765
    timeout: int = 30

@dataclass
class LLMConfig:
    provider: str = "openai"  # "openai" or "google"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

@dataclass
class SystemConfig:
    blender_mcp: BlenderMCPConfig = BlenderMCPConfig()
    llm: LLMConfig = LLMConfig()
    max_retries: int = 3
    debug: bool = False

def load_config() -> SystemConfig:
    """Load configuration from environment variables"""
    config = SystemConfig()
    
    # Load from environment
    config.llm.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    config.llm.provider = os.getenv("LLM_PROVIDER", "openai")
    config.llm.model = os.getenv("LLM_MODEL", "gpt-4")
    
    config.blender_mcp.host = os.getenv("BLENDER_MCP_HOST", "localhost")
    config.blender_mcp.port = int(os.getenv("BLENDER_MCP_PORT", "8765"))
    
    config.debug = os.getenv("DEBUG", "false").lower() == "true"
    
    return config