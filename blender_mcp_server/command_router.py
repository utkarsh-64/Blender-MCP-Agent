"""
Command router for handling and dispatching MCP commands
"""

import logging
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass

from .data_models import ResponseMessage, CommandMessage
from .handlers.object_handler import ObjectHandler
from .handlers.scene_handler import SceneHandler
from .handlers.render_handler import RenderHandler
from .utils.error_handling import create_error_response, get_error_handler, ErrorCategory


class CommandRouter:
    """Routes commands to appropriate handlers"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable[[Dict[str, Any]], ResponseMessage]] = {}
        self.logger = logging.getLogger("CommandRouter")
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default command handlers"""
        # Object manipulation commands
        self.register_handler("create_object", ObjectHandler.create_object)
        self.register_handler("move_object", ObjectHandler.move_object)
        self.register_handler("rotate_object", ObjectHandler.rotate_object)
        self.register_handler("scale_object", ObjectHandler.scale_object)
        self.register_handler("set_material", ObjectHandler.set_material)
        
        # Scene management commands
        self.register_handler("get_scene_info", SceneHandler.get_scene_info)
        self.register_handler("clear_scene", SceneHandler.clear_scene)
        
        # Rendering commands
        self.register_handler("render_scene", RenderHandler.render_scene)
        self.register_handler("set_render_settings", RenderHandler.set_render_settings)
        self.register_handler("get_render_settings", RenderHandler.get_render_settings)
        
        # Built-in commands
        self.register_handler("ping", self._handle_ping)
        self.register_handler("get_server_status", self._handle_server_status)
        self.register_handler("get_error_stats", self._handle_error_stats)
        self.register_handler("disconnect_client", self._handle_disconnect_client)
        
        self.logger.info(f"Registered {len(self.handlers)} command handlers")
    
    def register_handler(self, command: str, handler: Callable[[Dict[str, Any]], ResponseMessage]):
        """Register a command handler"""
        self.handlers[command] = handler
        self.logger.debug(f"Registered handler for command: {command}")
    
    def unregister_handler(self, command: str):
        """Unregister a command handler"""
        if command in self.handlers:
            del self.handlers[command]
            self.logger.debug(f"Unregistered handler for command: {command}")
    
    def get_available_commands(self) -> list:
        """Get list of available commands"""
        return list(self.handlers.keys())
    
    def route_command(self, command_msg: CommandMessage) -> ResponseMessage:
        """Route command to appropriate handler"""
        command = command_msg.command
        
        if command not in self.handlers:
            return create_error_response(
                "UNKNOWN_COMMAND",
                f"Command '{command}' not found",
                f"Available commands: {', '.join(self.get_available_commands())}",
                ErrorCategory.COMMAND
            )
        
        try:
            handler = self.handlers[command]
            self.logger.debug(f"Routing command '{command}' to handler")
            
            # Execute handler
            response = handler(command_msg.params)
            
            # Ensure response is valid
            if not isinstance(response, ResponseMessage):
                error_handler = get_error_handler()
                return error_handler.handle_error(
                    ValueError("Handler returned invalid response type"),
                    f"route_command_{command}",
                    ErrorCategory.COMMAND,
                    {"command": command, "response_type": type(response).__name__}
                )
            
            return response
            
        except Exception as e:
            error_handler = get_error_handler()
            return error_handler.handle_error(
                e, 
                f"route_command_{command}",
                ErrorCategory.COMMAND,
                {"command": command, "client_id": command_msg.client_id}
            )
    
    def _handle_ping(self, params: Dict[str, Any]) -> ResponseMessage:
        """Handle ping command"""
        import time
        return ResponseMessage(
            success=True,
            message="pong",
            data={
                "timestamp": time.time(),
                "echo": params.get("echo", "")
            }
        )
    
    def _handle_server_status(self, params: Dict[str, Any]) -> ResponseMessage:
        """Handle server status command (placeholder - will be filled by server)"""
        return ResponseMessage(
            success=True,
            message="Server status command should be handled by server directly"
        )
    
    def _handle_error_stats(self, params: Dict[str, Any]) -> ResponseMessage:
        """Handle error statistics command"""
        error_handler = get_error_handler()
        return ResponseMessage(
            success=True,
            data=error_handler.get_error_stats()
        )
    
    def _handle_disconnect_client(self, params: Dict[str, Any]) -> ResponseMessage:
        """Handle client disconnection command (placeholder - handled by server)"""
        return ResponseMessage(
            success=True,
            message="Disconnect client command should be handled by server directly"
        )


# Global command router instance
_command_router: Optional[CommandRouter] = None


def get_command_router() -> CommandRouter:
    """Get the global command router instance"""
    global _command_router
    if _command_router is None:
        _command_router = CommandRouter()
    return _command_router


def reset_command_router():
    """Reset the global command router (useful for testing)"""
    global _command_router
    _command_router = None