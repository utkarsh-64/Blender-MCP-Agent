"""
Blender MCP Server Addon
A WebSocket-based MCP server for remote Blender control
"""

bl_info = {
    "name": "Blender MCP Server",
    "author": "Autonomous 3D Scene Generator",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "Edit > Preferences > Add-ons",
    "description": "WebSocket-based MCP server for remote Blender control",
    "category": "System",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
}

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.types import AddonPreferences, Operator, Panel

from . import server
from . import ui


class MCPServerPreferences(AddonPreferences):
    """Addon preferences for MCP server configuration"""
    bl_idname = __name__

    # Server configuration
    host: StringProperty(
        name="Host",
        description="Server host address",
        default="localhost",
    )
    
    port: IntProperty(
        name="Port",
        description="Server port number",
        default=8765,
        min=1024,
        max=65535,
    )
    
    auto_start: BoolProperty(
        name="Auto Start",
        description="Automatically start server when addon is enabled",
        default=True,
    )
    
    allowed_ips: StringProperty(
        name="Allowed IPs",
        description="Comma-separated list of allowed client IP addresses",
        default="127.0.0.1,localhost",
    )
    
    log_level: StringProperty(
        name="Log Level",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
        default="INFO",
    )

    def draw(self, context):
        """Draw the preferences panel"""
        layout = self.layout
        
        # Server status section
        box = layout.box()
        box.label(text="Server Status", icon='NETWORK_DRIVE')
        
        # Get detailed server status
        try:
            status = server.get_server_status()
            is_running = status["running"]
            details = status["details"]
        except:
            is_running = server.is_server_running()
            details = "Running" if is_running else "Stopped"
        
        row = box.row()
        if is_running:
            row.label(text=details, icon='CHECKMARK')
            
            # Control buttons
            control_row = box.row()
            control_row.operator("mcp_server.stop", text="Stop", icon='PAUSE')
            control_row.operator("mcp_server.restart", text="Restart", icon='FILE_REFRESH')
            
            # Show server statistics if running
            try:
                box.label(text="Server is active and accepting connections")
            except:
                pass
        else:
            row.label(text=details, icon='X' if details == "Stopped" else 'TIME')
            row.operator("mcp_server.start", text="Start Server", icon='PLAY')
        
        # Server configuration section
        box = layout.box()
        box.label(text="Network Configuration", icon='PREFERENCES')
        
        col = box.column()
        row = col.row()
        row.prop(self, "host", text="Host Address")
        row.prop(self, "port", text="Port")
        
        col.prop(self, "allowed_ips", text="Allowed IPs (comma-separated)")
        
        # Advanced settings
        box = layout.box()
        box.label(text="Advanced Settings", icon='SETTINGS')
        
        col = box.column()
        col.prop(self, "auto_start", text="Auto-start server when addon is enabled")
        col.prop(self, "log_level", text="Log Level")
        
        # Help section
        box = layout.box()
        box.label(text="Help & Information", icon='INFO')
        
        col = box.column()
        col.label(text="• Use 'localhost' or '127.0.0.1' for local connections only")
        col.label(text="• Use '0.0.0.0' in allowed IPs to accept connections from any IP")
        col.label(text="• Default port 8765 should work for most setups")
        col.label(text="• Check Blender console for detailed server logs")
        
        # Connection test section
        if server.is_server_running():
            box = layout.box()
            box.label(text="Connection Test", icon='LINKED')
            
            col = box.column()
            col.label(text=f"Test connection: ws://{self.host}:{self.port}")
            col.label(text="Send JSON: {\"command\": \"ping\", \"params\": {}}")
            
            row = col.row()
            row.operator("mcp_server.test_connection", text="Test Connection", icon='PLAY')


class MCP_OT_StartServer(Operator):
    """Start the MCP server"""
    bl_idname = "mcp_server.start"
    bl_label = "Start MCP Server"
    bl_description = "Start the WebSocket MCP server"
    
    def execute(self, context):
        preferences = context.preferences.addons[__name__].preferences
        
        try:
            server.start_server(
                host=preferences.host,
                port=preferences.port,
                allowed_ips=preferences.allowed_ips.split(','),
                log_level=preferences.log_level
            )
            self.report({'INFO'}, f"MCP Server started on {preferences.host}:{preferences.port}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to start server: {str(e)}")
            
        return {'FINISHED'}


class MCP_OT_StopServer(Operator):
    """Stop the MCP server"""
    bl_idname = "mcp_server.stop"
    bl_label = "Stop MCP Server"
    bl_description = "Stop the WebSocket MCP server"
    
    def execute(self, context):
        try:
            server.stop_server()
            self.report({'INFO'}, "MCP Server stopped")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to stop server: {str(e)}")
            
        return {'FINISHED'}


class MCP_OT_TestConnection(Operator):
    """Test MCP server connection"""
    bl_idname = "mcp_server.test_connection"
    bl_label = "Test MCP Connection"
    bl_description = "Test connection to the MCP server"
    
    def execute(self, context):
        preferences = context.preferences.addons[__name__].preferences
        
        if not server.is_server_running():
            self.report({'ERROR'}, "Server is not running")
            return {'CANCELLED'}
        
        try:
            # This is a simple test - in a real implementation you might
            # want to actually test the WebSocket connection
            self.report({'INFO'}, f"Server appears to be running on {preferences.host}:{preferences.port}")
            self.report({'INFO'}, "Use external WebSocket client to test full functionality")
        except Exception as e:
            self.report({'ERROR'}, f"Connection test failed: {str(e)}")
            
        return {'FINISHED'}


class MCP_OT_RestartServer(Operator):
    """Restart the MCP server with current settings"""
    bl_idname = "mcp_server.restart"
    bl_label = "Restart MCP Server"
    bl_description = "Restart the server with current configuration"
    
    def execute(self, context):
        preferences = context.preferences.addons[__name__].preferences
        
        try:
            # Stop server if running
            if server.is_server_running():
                self.report({'INFO'}, "Stopping existing server...")
                server.stop_server()
                
                # Wait a moment for cleanup
                import time
                time.sleep(1.0)
            
            # Start server with new settings
            allowed_ips = [ip.strip() for ip in preferences.allowed_ips.split(',') if ip.strip()]
            
            self.report({'INFO'}, "Starting server with new settings...")
            server.start_server(
                host=preferences.host,
                port=preferences.port,
                allowed_ips=allowed_ips,
                log_level=preferences.log_level
            )
            
            # Wait a moment for startup
            import time
            time.sleep(0.5)
            
            if server.is_server_running():
                self.report({'INFO'}, f"Server restarted successfully on {preferences.host}:{preferences.port}")
            else:
                self.report({'WARNING'}, "Server restart initiated, check console for status")
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to restart server: {str(e)}")
            print(f"Restart error details: {e}")
            
        return {'FINISHED'}


# Registration
classes = [
    MCPServerPreferences,
    MCP_OT_StartServer,
    MCP_OT_StopServer,
    MCP_OT_TestConnection,
    MCP_OT_RestartServer,
]


def register():
    """Register addon classes and start server if auto-start is enabled"""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register UI components
    ui.register()
    
    # Auto-start server if enabled
    try:
        preferences = bpy.context.preferences.addons[__name__].preferences
        if preferences.auto_start:
            try:
                allowed_ips = [ip.strip() for ip in preferences.allowed_ips.split(',') if ip.strip()]
                server.start_server(
                    host=preferences.host,
                    port=preferences.port,
                    allowed_ips=allowed_ips,
                    log_level=preferences.log_level
                )
                print(f"✓ MCP Server auto-started on {preferences.host}:{preferences.port}")
                print(f"  Allowed IPs: {', '.join(allowed_ips)}")
                print(f"  Log level: {preferences.log_level}")
            except Exception as e:
                print(f"✗ Failed to auto-start MCP server: {e}")
                print("  You can manually start the server from the addon preferences")
    except Exception as e:
        print(f"✗ Error accessing addon preferences during registration: {e}")


def unregister():
    """Unregister addon classes and stop server"""
    # Stop server gracefully
    try:
        if server.is_server_running():
            print("Stopping MCP Server...")
            server.stop_server()
            print("✓ MCP Server stopped successfully")
    except Exception as e:
        print(f"✗ Error stopping server during unregister: {e}")
    
    # Unregister UI components
    try:
        ui.unregister()
    except Exception as e:
        print(f"Error unregistering UI components: {e}")
    
    # Unregister classes
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering class {cls.__name__}: {e}")


if __name__ == "__main__":
    register()