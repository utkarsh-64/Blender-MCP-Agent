"""
Rendering command handlers
"""

import os
import time
from typing import Dict, Any

import bpy
from ..data_models import ResponseMessage
from ..utils.error_handling import handle_blender_error, create_error_response


class RenderHandler:
    """Handler for rendering commands"""
    
    @staticmethod
    def set_render_settings(params: Dict[str, Any]) -> ResponseMessage:
        """Set render settings"""
        try:
            scene = bpy.context.scene
            settings_applied = {}
            
            # Set resolution
            if "resolution" in params:
                resolution = params["resolution"]
                scene.render.resolution_x = resolution[0]
                scene.render.resolution_y = resolution[1]
                settings_applied["resolution"] = resolution
            
            # Set render engine
            if "engine" in params:
                engine = params["engine"].upper()
                if engine in ["CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"]:
                    scene.render.engine = engine
                    settings_applied["engine"] = engine
                else:
                    return create_error_response(
                        "INVALID_ENGINE",
                        f"Render engine '{params['engine']}' not supported"
                    )
            
            # Set samples (for Cycles and Eevee)
            if "samples" in params:
                samples = params["samples"]
                if scene.render.engine == "CYCLES":
                    scene.cycles.samples = samples
                    settings_applied["samples"] = samples
                elif scene.render.engine == "BLENDER_EEVEE":
                    scene.eevee.taa_render_samples = samples
                    settings_applied["samples"] = samples
            
            # Set output format
            if "format" in params:
                format_type = params["format"].upper()
                valid_formats = ["PNG", "JPEG", "TIFF", "OPEN_EXR", "HDR"]
                if format_type in valid_formats:
                    scene.render.image_settings.file_format = format_type
                    settings_applied["format"] = format_type
                else:
                    return create_error_response(
                        "INVALID_FORMAT",
                        f"Format '{params['format']}' not supported. Use: {', '.join(valid_formats)}"
                    )
            
            # Set quality (for JPEG)
            if "quality" in params and scene.render.image_settings.file_format == "JPEG":
                quality = max(0, min(100, params["quality"]))
                scene.render.image_settings.quality = quality
                settings_applied["quality"] = quality
            
            return ResponseMessage(
                success=True,
                message="Render settings updated",
                data={
                    "settings_applied": settings_applied,
                    "current_settings": RenderHandler._get_current_settings()
                }
            )
            
        except Exception as e:
            return handle_blender_error(e, "set_render_settings")
    
    @staticmethod
    def get_render_settings(params: Dict[str, Any]) -> ResponseMessage:
        """Get current render settings"""
        try:
            return ResponseMessage(
                success=True,
                data=RenderHandler._get_current_settings()
            )
        except Exception as e:
            return handle_blender_error(e, "get_render_settings")
    
    @staticmethod
    def _get_current_settings() -> Dict[str, Any]:
        """Get current render settings as dictionary"""
        scene = bpy.context.scene
        settings = {
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "engine": scene.render.engine,
            "format": scene.render.image_settings.file_format,
            "filepath": scene.render.filepath
        }
        
        # Add engine-specific settings
        if scene.render.engine == "CYCLES":
            settings["samples"] = scene.cycles.samples
            settings["device"] = scene.cycles.device
        elif scene.render.engine == "BLENDER_EEVEE":
            settings["samples"] = scene.eevee.taa_render_samples
            settings["bloom"] = scene.eevee.use_bloom
            settings["ssr"] = scene.eevee.use_ssr
        
        # Add format-specific settings
        if scene.render.image_settings.file_format == "JPEG":
            settings["quality"] = scene.render.image_settings.quality
        
        return settings
    
    @staticmethod
    def render_scene(params: Dict[str, Any]) -> ResponseMessage:
        """Render scene"""
        try:
            scene = bpy.context.scene
            
            # Set output path
            output_path = params.get("output_path")
            if output_path:
                # Ensure directory exists
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                    except Exception as e:
                        return create_error_response(
                            "PATH_ERROR",
                            f"Cannot create output directory: {str(e)}"
                        )
                scene.render.filepath = output_path
            else:
                # Use default path with timestamp
                timestamp = int(time.time())
                default_path = f"/tmp/blender_render_{timestamp}.png"
                scene.render.filepath = default_path
                output_path = default_path
            
            # Set resolution if provided
            if "resolution" in params:
                resolution = params["resolution"]
                scene.render.resolution_x = resolution[0]
                scene.render.resolution_y = resolution[1]
            
            # Set render engine if provided
            if "engine" in params:
                engine = params["engine"].upper()
                if engine in ["CYCLES", "BLENDER_EEVEE", "BLENDER_WORKBENCH"]:
                    scene.render.engine = engine
                else:
                    return create_error_response(
                        "INVALID_ENGINE",
                        f"Render engine '{params['engine']}' not supported. Use: CYCLES, BLENDER_EEVEE, or BLENDER_WORKBENCH"
                    )
            
            # Set image format
            scene.render.image_settings.file_format = 'PNG'
            
            # Perform render
            start_time = time.time()
            bpy.ops.render.render(write_still=True)
            render_time = time.time() - start_time
            
            # Check if file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                return ResponseMessage(
                    success=True,
                    message=f"Scene rendered successfully in {render_time:.2f} seconds",
                    data={
                        "output_path": output_path,
                        "render_time": render_time,
                        "file_size": file_size,
                        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
                        "engine": scene.render.engine
                    }
                )
            else:
                return create_error_response(
                    "RENDER_FAILED",
                    "Render completed but output file was not created"
                )
            
        except Exception as e:
            return handle_blender_error(e, "render_scene")