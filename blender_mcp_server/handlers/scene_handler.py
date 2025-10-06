"""
Scene management command handlers
"""

from typing import Dict, Any, List
import math

import bpy
from ..data_models import ResponseMessage
from ..utils.error_handling import handle_blender_error


class SceneHandler:
    """Handler for scene management commands"""
    
    @staticmethod
    def get_scene_info(params: Dict[str, Any]) -> ResponseMessage:
        """Get scene information"""
        try:
            scene = bpy.context.scene
            objects = []
            
            for obj in scene.objects:
                obj_info = {
                    "name": obj.name,
                    "type": obj.type,
                    "location": list(obj.location),
                    "rotation": [math.degrees(angle) for angle in obj.rotation_euler],
                    "scale": list(obj.scale),
                    "visible": obj.visible_get(),
                    "material": obj.active_material.name if obj.active_material else None
                }
                objects.append(obj_info)
            
            # Get camera info
            camera = scene.camera
            camera_info = None
            if camera:
                camera_info = {
                    "name": camera.name,
                    "location": list(camera.location),
                    "rotation": [math.degrees(angle) for angle in camera.rotation_euler]
                }
            
            # Get render settings
            render_settings = {
                "resolution_x": scene.render.resolution_x,
                "resolution_y": scene.render.resolution_y,
                "engine": scene.render.engine,
                "filepath": scene.render.filepath
            }
            
            return ResponseMessage(
                success=True,
                data={
                    "scene_name": scene.name,
                    "objects": objects,
                    "object_count": len(objects),
                    "camera": camera_info,
                    "render_settings": render_settings,
                    "active_object": bpy.context.active_object.name if bpy.context.active_object else None
                }
            )
            
        except Exception as e:
            return handle_blender_error(e, "get_scene_info")
    
    @staticmethod
    def clear_scene(params: Dict[str, Any]) -> ResponseMessage:
        """Clear scene of user-created objects"""
        try:
            scene = bpy.context.scene
            objects_to_delete = []
            preserved_objects = []
            
            # Identify objects to delete (preserve default camera and light)
            for obj in scene.objects:
                if obj.type in ['CAMERA', 'LIGHT'] and obj.name in ['Camera', 'Light']:
                    preserved_objects.append(obj.name)
                else:
                    objects_to_delete.append(obj.name)
            
            # Delete objects
            bpy.ops.object.select_all(action='DESELECT')
            deleted_count = 0
            
            for obj_name in objects_to_delete:
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    obj.select_set(True)
                    deleted_count += 1
            
            if deleted_count > 0:
                bpy.ops.object.delete()
            
            return ResponseMessage(
                success=True,
                message=f"Cleared scene: deleted {deleted_count} objects, preserved {len(preserved_objects)} default objects",
                data={
                    "deleted_count": deleted_count,
                    "preserved_objects": preserved_objects,
                    "deleted_objects": objects_to_delete
                }
            )
            
        except Exception as e:
            return handle_blender_error(e, "clear_scene")