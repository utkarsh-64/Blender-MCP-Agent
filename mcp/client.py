import json
import asyncio
import websockets
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class MCPResponse:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None

class BlenderMCPClient:
    """Client for communicating with Blender MCP server"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, timeout: int = 60):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.websocket = None
        self.connected = False
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def connect(self) -> bool:
        """Connect to Blender MCP server with improved stability"""
        for attempt in range(self.max_retries):
            try:
                uri = f"ws://{self.host}:{self.port}"
                # Use longer timeouts and better connection settings
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        uri,
                        ping_interval=20,  # Send ping every 20 seconds
                        ping_timeout=10,   # Wait 10 seconds for pong
                        close_timeout=10   # Wait 10 seconds for close
                    ), 
                    timeout=self.timeout
                )
                self.connected = True
                print(f"Connected to Blender MCP server at {uri}")
                return True
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    print(f"Failed to connect after {self.max_retries} attempts")
                    self.connected = False
                    return False
    
    async def disconnect(self):
        """Disconnect from Blender MCP server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
    
    async def send_command(self, command: str, params: Dict[str, Any] = None) -> MCPResponse:
        """Send command to Blender MCP server with retry logic"""
        if not self.connected:
            return MCPResponse(success=False, error="Not connected to MCP server")
        
        for attempt in range(self.max_retries):
            try:
                message = {
                    "command": command,
                    "params": params or {}
                }
                
                await self.websocket.send(json.dumps(message))
                
                # Use longer timeout for complex commands
                command_timeout = self.timeout
                if command in ["render_scene", "create_object", "set_material"]:
                    command_timeout = self.timeout * 2  # Double timeout for complex operations
                
                response_data = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=command_timeout
                )
                
                response = json.loads(response_data)
                
                if response.get("success", False):
                    return MCPResponse(
                        success=True,
                        data=response.get("data"),
                        message=response.get("message")
                    )
                else:
                    return MCPResponse(
                        success=False,
                        error=response.get("error", "Unknown error")
                    )
                    
            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                print(f"Command '{command}' attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    # Try to reconnect
                    self.connected = False
                    if await self.connect():
                        await asyncio.sleep(self.retry_delay)
                        continue
                return MCPResponse(success=False, error=f"Command timeout after {self.max_retries} attempts")
            except Exception as e:
                return MCPResponse(success=False, error=f"Command failed: {str(e)}")
    
    # Blender-specific commands
    async def create_object(self, obj_type: str, name: str, location: List[float] = None) -> MCPResponse:
        """Create a new object in Blender"""
        params = {
            "type": obj_type,
            "name": name,
            "location": location or [0, 0, 0]
        }
        return await self.send_command("create_object", params)
    
    async def move_object(self, name: str, location: List[float]) -> MCPResponse:
        """Move an object to a new location"""
        params = {
            "name": name,
            "location": location
        }
        return await self.send_command("move_object", params)
    
    async def rotate_object(self, name: str, rotation: List[float]) -> MCPResponse:
        """Rotate an object"""
        params = {
            "name": name,
            "rotation": rotation
        }
        return await self.send_command("rotate_object", params)
    
    async def scale_object(self, name: str, scale: List[float]) -> MCPResponse:
        """Scale an object"""
        params = {
            "name": name,
            "scale": scale
        }
        return await self.send_command("scale_object", params)
    
    async def set_material(self, name: str, material_props: Dict[str, Any]) -> MCPResponse:
        """Set material properties for an object"""
        params = {
            "name": name,
            "material": material_props
        }
        return await self.send_command("set_material", params)
    
    async def get_scene_info(self) -> MCPResponse:
        """Get current scene information"""
        return await self.send_command("get_scene_info")
    
    async def render_scene(self, output_path: str = None) -> MCPResponse:
        """Render the current scene"""
        params = {"output_path": output_path} if output_path else {}
        return await self.send_command("render_scene", params)
    
    async def clear_scene(self) -> MCPResponse:
        """Clear all objects from the scene"""
        return await self.send_command("clear_scene")