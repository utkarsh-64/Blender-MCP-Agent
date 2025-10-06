"""
UI components for Blender MCP Server addon
"""

import bpy
from bpy.types import Panel
from . import server


class MCP_PT_ServerPanel(Panel):
    """Main panel for MCP server control"""
    bl_label = "MCP Server"
    bl_idname = "MCP_PT_server_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP Server"
    
    def draw(self, context):
        layout = self.layout
        preferences = context.preferences.addons[__package__].preferences
        
        # Server status
        box = layout.box()
        box.label(text="Server Status", icon='NETWORK_DRIVE')
        
        # Get detailed server status
        try:
            status = server.get_server_status()
            is_running = status["running"]
            details = status["details"]
        except:
            is_running = server.is_server_running()
            details = f"Running on {preferences.host}:{preferences.port}" if is_running else "Stopped"
        
        if is_running:
            box.label(text=details, icon='CHECKMARK')
            box.operator("mcp_server.stop", text="Stop Server", icon='PAUSE')
        else:
            box.label(text=details, icon='X' if details == "Stopped" else 'TIME')
            box.operator("mcp_server.start", text="Start Server", icon='PLAY')
        
        # Quick settings
        box = layout.box()
        box.label(text="Quick Settings", icon='PREFERENCES')
        box.prop(preferences, "host")
        box.prop(preferences, "port")
        box.prop(preferences, "auto_start")
        
        # Info
        box = layout.box()
        box.label(text="Info", icon='INFO')
        box.label(text="Configure server in Add-ons preferences")
        box.operator("preferences.addon_show", text="Open Preferences").module = __package__


class MCP_PT_ServerInfo(Panel):
    """Information panel for MCP server"""
    bl_label = "Server Info"
    bl_idname = "MCP_PT_server_info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MCP Server"
    bl_parent_id = "MCP_PT_server_panel"
    
    def draw(self, context):
        layout = self.layout
        preferences = context.preferences.addons[__package__].preferences
        
        # Connection info
        box = layout.box()
        box.label(text="Connection Details")
        box.label(text=f"Host: {preferences.host}")
        box.label(text=f"Port: {preferences.port}")
        box.label(text=f"Allowed IPs: {preferences.allowed_ips}")
        
        # Available commands
        box = layout.box()
        box.label(text="Available Commands")
        
        # Object commands
        sub_box = box.box()
        sub_box.label(text="Object Commands:", icon='OBJECT_DATA')
        object_commands = [
            "create_object - Create new object (cube, sphere, cylinder, etc.)",
            "move_object - Move object to new location",
            "rotate_object - Rotate object by degrees",
            "scale_object - Scale object by factors",
            "set_material - Set object material properties"
        ]
        for cmd in object_commands:
            sub_box.label(text=f"• {cmd}")
        
        # Scene commands
        sub_box = box.box()
        sub_box.label(text="Scene Commands:", icon='SCENE_DATA')
        scene_commands = [
            "get_scene_info - Get current scene information",
            "clear_scene - Remove all user-created objects"
        ]
        for cmd in scene_commands:
            sub_box.label(text=f"• {cmd}")
        
        # Render commands
        sub_box = box.box()
        sub_box.label(text="Render Commands:", icon='RENDER_STILL')
        render_commands = [
            "render_scene - Render current scene to image",
            "set_render_settings - Configure render parameters",
            "get_render_settings - Get current render settings"
        ]
        for cmd in render_commands:
            sub_box.label(text=f"• {cmd}")
        
        # System commands
        sub_box = box.box()
        sub_box.label(text="System Commands:", icon='SYSTEM')
        system_commands = [
            "ping - Test connection",
            "get_server_status - Get server status and statistics",
            "get_error_stats - Get error statistics"
        ]
        for cmd in system_commands:
            sub_box.label(text=f"• {cmd}")


# Registration
classes = [
    MCP_PT_ServerPanel,
    MCP_PT_ServerInfo,
]


def register():
    """Register UI classes"""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Unregister UI classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)