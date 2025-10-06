import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from mcp.client import BlenderMCPClient, MCPResponse
from PIL import Image
import os

@dataclass
class SceneAnalysis:
    objects: List[Dict[str, Any]]
    scene_description: str
    render_path: Optional[str] = None
    success: bool = True
    error: Optional[str] = None

class VisionAgent:
    """Agent for scene observation and verification"""
    
    def __init__(self, mcp_client: BlenderMCPClient):
        self.mcp_client = mcp_client
    
    async def analyze_scene(self, render_image: bool = False) -> SceneAnalysis:
        """Analyze the current scene state"""
        try:
            # Get scene information from Blender
            scene_response = await self.mcp_client.get_scene_info()
            
            if not scene_response.success:
                return SceneAnalysis(
                    objects=[],
                    scene_description="Failed to get scene information",
                    success=False,
                    error=scene_response.error
                )
            
            scene_data = scene_response.data or {}
            objects = scene_data.get("objects", [])
            
            # Generate scene description
            description = self._generate_scene_description(objects)
            
            render_path = None
            if render_image:
                render_path = await self._capture_scene_render()
            
            return SceneAnalysis(
                objects=objects,
                scene_description=description,
                render_path=render_path,
                success=True
            )
            
        except Exception as e:
            return SceneAnalysis(
                objects=[],
                scene_description="Scene analysis failed",
                success=False,
                error=str(e)
            )
    
    def _generate_scene_description(self, objects: List[Dict[str, Any]]) -> str:
        """Generate a natural language description of the scene"""
        if not objects:
            return "The scene is empty."
        
        descriptions = []
        
        for obj in objects:
            name = obj.get("name", "unnamed object")
            obj_type = obj.get("type", "object")
            location = obj.get("location", [0, 0, 0])
            
            # Format location
            x, y, z = location
            location_desc = f"at position ({x:.1f}, {y:.1f}, {z:.1f})"
            
            # Check for material/color info
            material = obj.get("material")
            color_info = ""
            if material and isinstance(material, dict) and "color" in material:
                color = material["color"]
                if isinstance(color, list) and len(color) >= 3:
                    r, g, b = color[:3]
                    color_name = self._get_color_name(r, g, b)
                    color_info = f" with {color_name} color"
            elif material and isinstance(material, str):
                # Material is just a name string
                color_info = f" with {material} material"
            
            descriptions.append(f"A {obj_type} named '{name}'{color_info} {location_desc}")
        
        if len(descriptions) == 1:
            return f"The scene contains: {descriptions[0]}."
        else:
            return f"The scene contains {len(descriptions)} objects: " + "; ".join(descriptions) + "."
    
    def _get_color_name(self, r: float, g: float, b: float) -> str:
        """Convert RGB values to approximate color name"""
        # Simple color name mapping
        if r > 0.7 and g < 0.3 and b < 0.3:
            return "red"
        elif r < 0.3 and g > 0.7 and b < 0.3:
            return "green"
        elif r < 0.3 and g < 0.3 and b > 0.7:
            return "blue"
        elif r > 0.7 and g > 0.7 and b < 0.3:
            return "yellow"
        elif r > 0.5 and g < 0.5 and b > 0.5:
            return "purple"
        elif r < 0.5 and g > 0.5 and b > 0.5:
            return "cyan"
        elif r > 0.7 and g > 0.4 and b < 0.3:
            return "orange"
        elif r > 0.4 and g > 0.2 and b < 0.2:
            return "brown"
        elif r > 0.7 and g > 0.7 and b > 0.7:
            return "white"
        elif r < 0.3 and g < 0.3 and b < 0.3:
            return "black"
        else:
            return "colored"
    
    async def _capture_scene_render(self) -> Optional[str]:
        """Capture a render of the current scene"""
        try:
            # Create renders directory if it doesn't exist
            os.makedirs("renders", exist_ok=True)
            
            # Generate unique filename
            import time
            timestamp = int(time.time())
            output_path = f"renders/scene_{timestamp}.png"
            
            # Request render from Blender
            render_response = await self.mcp_client.render_scene(output_path)
            
            if render_response.success:
                return output_path
            else:
                print(f"Render failed: {render_response.error}")
                return None
                
        except Exception as e:
            print(f"Failed to capture scene render: {e}")
            return None
    
    async def verify_plan_completion(self, expected_objects: List[str]) -> Dict[str, bool]:
        """Verify that expected objects exist in the scene"""
        analysis = await self.analyze_scene()
        
        if not analysis.success:
            return {obj: False for obj in expected_objects}
        
        existing_objects = {obj.get("name", "") for obj in analysis.objects}
        
        return {
            obj_name: obj_name in existing_objects 
            for obj_name in expected_objects
        }