"""
Object manipulation command handlers
"""

import time
import math
from typing import Dict, Any

import bpy
from ..data_models import ResponseMessage
from ..utils.error_handling import handle_blender_error, create_error_response


class ObjectHandler:
    """Handler for object manipulation commands"""
    
    @staticmethod
    def create_object(params: Dict[str, Any]) -> ResponseMessage:
        """Create a new object"""
        try:
            obj_type = params["type"].lower()
            name = params["name"]
            location = params.get("location", [0, 0, 0])
            
            # Create object based on type
            if obj_type == "cube":
                bpy.ops.mesh.primitive_cube_add(location=location)
            elif obj_type == "sphere":
                bpy.ops.mesh.primitive_uv_sphere_add(location=location)
            elif obj_type == "cylinder":
                bpy.ops.mesh.primitive_cylinder_add(location=location)
            elif obj_type == "plane":
                bpy.ops.mesh.primitive_plane_add(location=location)
            elif obj_type == "cone":
                bpy.ops.mesh.primitive_cone_add(location=location)
            elif obj_type == "torus":
                bpy.ops.mesh.primitive_torus_add(location=location)
            else:
                return create_error_response(
                    "UNSUPPORTED_TYPE",
                    f"Object type '{obj_type}' not supported"
                )
            
            # Rename the object
            if bpy.context.active_object:
                bpy.context.active_object.name = name
                actual_name = bpy.context.active_object.name  # Blender may modify the name
                
                return ResponseMessage(
                    success=True,
                    message=f"Created {obj_type} '{actual_name}' at {location}",
                    data={
                        "name": actual_name,
                        "type": obj_type,
                        "location": location
                    }
                )
            else:
                return create_error_response(
                    "CREATION_FAILED",
                    "Object was created but is not active"
                )
                
        except Exception as e:
            return handle_blender_error(e, "create_object")
    
    @staticmethod
    def move_object(params: Dict[str, Any]) -> ResponseMessage:
        """Move an object"""
        try:
            name = params["name"]
            location = params["location"]
            
            # Find object
            obj = bpy.data.objects.get(name)
            if not obj:
                return create_error_response(
                    "OBJECT_NOT_FOUND",
                    f"Object '{name}' not found in scene"
                )
            
            # Move object
            obj.location = location
            
            return ResponseMessage(
                success=True,
                message=f"Moved object '{name}' to {location}",
                data={
                    "name": name,
                    "location": list(obj.location)
                }
            )
            
        except Exception as e:
            return handle_blender_error(e, "move_object")
    
    @staticmethod
    def rotate_object(params: Dict[str, Any]) -> ResponseMessage:
        """Rotate an object"""
        try:
            name = params["name"]
            rotation = params["rotation"]
            
            # Find object
            obj = bpy.data.objects.get(name)
            if not obj:
                return create_error_response(
                    "OBJECT_NOT_FOUND",
                    f"Object '{name}' not found in scene"
                )
            
            # Convert degrees to radians
            rotation_rad = [math.radians(angle) for angle in rotation]
            obj.rotation_euler = rotation_rad
            
            return ResponseMessage(
                success=True,
                message=f"Rotated object '{name}' to {rotation} degrees",
                data={
                    "name": name,
                    "rotation_degrees": rotation,
                    "rotation_radians": rotation_rad
                }
            )
            
        except Exception as e:
            return handle_blender_error(e, "rotate_object")
    
    @staticmethod
    def scale_object(params: Dict[str, Any]) -> ResponseMessage:
        """Scale an object"""
        try:
            name = params["name"]
            scale = params["scale"]
            
            # Find object
            obj = bpy.data.objects.get(name)
            if not obj:
                return create_error_response(
                    "OBJECT_NOT_FOUND",
                    f"Object '{name}' not found in scene"
                )
            
            # Scale object
            obj.scale = scale
            
            return ResponseMessage(
                success=True,
                message=f"Scaled object '{name}' to {scale}",
                data={
                    "name": name,
                    "scale": list(obj.scale)
                }
            )
            
        except Exception as e:
            return handle_blender_error(e, "scale_object")
    
    @staticmethod
    def set_material(params: Dict[str, Any]) -> ResponseMessage:
        """Set object material"""
        try:
            name = params["name"]
            material_props = params["material"]
            
            # Find object
            obj = bpy.data.objects.get(name)
            if not obj:
                return create_error_response(
                    "OBJECT_NOT_FOUND",
                    f"Object '{name}' not found in scene"
                )
            
            # Create or get material
            material_name = f"{name}_material"
            material = bpy.data.materials.get(material_name)
            if not material:
                material = bpy.data.materials.new(name=material_name)
                material.use_nodes = True
            
            # Get the principled BSDF node
            nodes = material.node_tree.nodes
            principled = nodes.get("Principled BSDF")
            if not principled:
                principled = nodes.new(type="ShaderNodeBsdfPrincipled")
            
            # Set material properties
            if "color" in material_props:
                color = material_props["color"]
                if isinstance(color, str):
                    # Convert hex to RGB
                    hex_color = color.lstrip('#')
                    rgb = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
                    principled.inputs["Base Color"].default_value = (*rgb, 1.0)
                elif isinstance(color, list):
                    if len(color) == 3:
                        principled.inputs["Base Color"].default_value = (*color, 1.0)
                    else:
                        principled.inputs["Base Color"].default_value = color
            
            if "metallic" in material_props:
                principled.inputs["Metallic"].default_value = material_props["metallic"]
            
            if "roughness" in material_props:
                principled.inputs["Roughness"].default_value = material_props["roughness"]
            
            # Assign material to object
            if obj.data.materials:
                obj.data.materials[0] = material
            else:
                obj.data.materials.append(material)
            
            return ResponseMessage(
                success=True,
                message=f"Applied material to object '{name}'",
                data={
                    "name": name,
                    "material_name": material_name,
                    "properties": material_props
                }
            )
            
        except Exception as e:
            return handle_blender_error(e, "set_material")