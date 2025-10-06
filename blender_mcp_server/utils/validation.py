"""
Input validation utilities
"""

import re
from typing import Dict, Any, List, Optional, Union


def validate_command(command: str) -> bool:
    """Validate command name"""
    valid_commands = {
        'ping', 'get_scene_info', 'get_server_status', 'clear_scene', 'render_scene',
        'set_render_settings', 'get_render_settings',
        'create_object', 'move_object', 'rotate_object', 'scale_object', 'set_material'
    }
    return command in valid_commands


def validate_object_name(name: str) -> bool:
    """Validate object name (alphanumeric, underscore, dash, dot allowed)"""
    if not isinstance(name, str) or not name:
        return False
    # Allow alphanumeric, underscore, dash, dot, and space
    return re.match(r'^[a-zA-Z0-9_\-\.\s]+$', name) is not None


def validate_coordinates(coords: Any, name: str = "coordinates") -> Optional[str]:
    """Validate 3D coordinates"""
    if not isinstance(coords, list):
        return f"{name} must be a list"
    if len(coords) != 3:
        return f"{name} must have exactly 3 elements"
    for i, coord in enumerate(coords):
        if not isinstance(coord, (int, float)):
            return f"{name}[{i}] must be a number"
        if abs(coord) > 1000000:  # Reasonable limit
            return f"{name}[{i}] value too large (max ±1,000,000)"
    return None


def validate_color(color: Any) -> Optional[str]:
    """Validate color value (RGB or RGBA)"""
    if isinstance(color, str):
        # Hex color validation
        if re.match(r'^#[0-9a-fA-F]{6}$', color):
            return None
        return "Color string must be hex format (#RRGGBB)"
    
    if isinstance(color, list):
        if len(color) not in [3, 4]:
            return "Color list must have 3 (RGB) or 4 (RGBA) elements"
        for i, val in enumerate(color):
            if not isinstance(val, (int, float)):
                return f"Color[{i}] must be a number"
            if not 0 <= val <= 1:
                return f"Color[{i}] must be between 0 and 1"
        return None
    
    return "Color must be hex string (#RRGGBB) or RGB/RGBA list"


def validate_params(command: str, params: Dict[str, Any]) -> Optional[str]:
    """Validate command parameters, return error message if invalid"""
    
    if command == "create_object":
        # Required parameters
        if "type" not in params:
            return "Missing required parameter: type"
        if "name" not in params:
            return "Missing required parameter: name"
        
        # Validate object type
        valid_types = {"cube", "sphere", "cylinder", "plane", "cone", "torus"}
        obj_type = params["type"].lower() if isinstance(params["type"], str) else ""
        if obj_type not in valid_types:
            return f"Invalid object type '{params['type']}'. Valid types: {', '.join(valid_types)}"
        
        # Validate object name
        if not validate_object_name(params["name"]):
            return "Invalid object name. Use alphanumeric characters, underscore, dash, dot, or space"
        
        # Validate optional location
        if "location" in params:
            error = validate_coordinates(params["location"], "location")
            if error:
                return error
    
    elif command == "move_object":
        if "name" not in params:
            return "Missing required parameter: name"
        if "location" not in params:
            return "Missing required parameter: location"
        
        if not validate_object_name(params["name"]):
            return "Invalid object name"
        
        error = validate_coordinates(params["location"], "location")
        if error:
            return error
    
    elif command == "rotate_object":
        if "name" not in params:
            return "Missing required parameter: name"
        if "rotation" not in params:
            return "Missing required parameter: rotation"
        
        if not validate_object_name(params["name"]):
            return "Invalid object name"
        
        error = validate_coordinates(params["rotation"], "rotation")
        if error:
            return error
    
    elif command == "scale_object":
        if "name" not in params:
            return "Missing required parameter: name"
        if "scale" not in params:
            return "Missing required parameter: scale"
        
        if not validate_object_name(params["name"]):
            return "Invalid object name"
        
        error = validate_coordinates(params["scale"], "scale")
        if error:
            return error
        
        # Additional validation for scale (must be positive)
        for i, val in enumerate(params["scale"]):
            if val <= 0:
                return f"scale[{i}] must be positive (got {val})"
    
    elif command == "set_material":
        if "name" not in params:
            return "Missing required parameter: name"
        if "material" not in params:
            return "Missing required parameter: material"
        
        if not validate_object_name(params["name"]):
            return "Invalid object name"
        
        material = params["material"]
        if not isinstance(material, dict):
            return "Parameter 'material' must be an object"
        
        # Validate material properties
        if "color" in material:
            error = validate_color(material["color"])
            if error:
                return f"Invalid material color: {error}"
        
        if "metallic" in material:
            metallic = material["metallic"]
            if not isinstance(metallic, (int, float)) or not 0 <= metallic <= 1:
                return "Material 'metallic' must be a number between 0 and 1"
        
        if "roughness" in material:
            roughness = material["roughness"]
            if not isinstance(roughness, (int, float)) or not 0 <= roughness <= 1:
                return "Material 'roughness' must be a number between 0 and 1"
    
    elif command == "render_scene":
        if "output_path" in params:
            if not isinstance(params["output_path"], str):
                return "Parameter 'output_path' must be a string"
            if not params["output_path"].strip():
                return "Parameter 'output_path' cannot be empty"
        
        if "resolution" in params:
            resolution = params["resolution"]
            if not isinstance(resolution, list) or len(resolution) != 2:
                return "Parameter 'resolution' must be a list with 2 elements [width, height]"
            for i, val in enumerate(resolution):
                if not isinstance(val, int) or val <= 0:
                    return f"resolution[{i}] must be a positive integer"
                if val > 8192:  # Reasonable limit
                    return f"resolution[{i}] too large (max 8192)"
    
    elif command == "set_render_settings":
        if "resolution" in params:
            resolution = params["resolution"]
            if not isinstance(resolution, list) or len(resolution) != 2:
                return "Parameter 'resolution' must be a list with 2 elements [width, height]"
            for i, val in enumerate(resolution):
                if not isinstance(val, int) or val <= 0:
                    return f"resolution[{i}] must be a positive integer"
                if val > 8192:
                    return f"resolution[{i}] too large (max 8192)"
        
        if "engine" in params:
            engine = params["engine"].upper()
            valid_engines = ["CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"]
            if engine not in valid_engines:
                return f"Invalid render engine. Valid engines: {', '.join(valid_engines)}"
        
        if "samples" in params:
            samples = params["samples"]
            if not isinstance(samples, int) or samples <= 0:
                return "Parameter 'samples' must be a positive integer"
            if samples > 10000:
                return "Parameter 'samples' too large (max 10000)"
        
        if "format" in params:
            format_type = params["format"].upper()
            valid_formats = ["PNG", "JPEG", "TIFF", "OPEN_EXR", "HDR"]
            if format_type not in valid_formats:
                return f"Invalid format. Valid formats: {', '.join(valid_formats)}"
        
        if "quality" in params:
            quality = params["quality"]
            if not isinstance(quality, int) or not 0 <= quality <= 100:
                return "Parameter 'quality' must be an integer between 0 and 100"
    
    return None  # No validation errors