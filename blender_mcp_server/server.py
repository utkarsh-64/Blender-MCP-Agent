"""
Main WebSocket server implementation for Blender MCP Server
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, asdict
from queue import Queue, Empty

import bpy

# Try to import websockets, provide fallback if not available
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("⚠️ websockets library not found. Please install it using:")
    print("   In Blender Python Console: subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'websockets'])")

from .utils.validation import validate_command, validate_params
from .utils.error_handling import create_error_response
from .data_models import ServerConfig, CommandMessage, ResponseMessage, BlenderCommand


# Global server instance
_server_instance: Optional['MCPServer'] = None
_server_thread: Optional[threading.Thread] = None

# Command queue for main thread execution
_command_queue: Queue = Queue()
_response_futures: Dict[str, asyncio.Future] = {}
_blender_timer = None


def execute_blender_commands():
    """Execute queued commands on Blender main thread (called by timer)"""
    global _command_queue, _response_futures
    
    try:
        # Process up to 10 commands per timer call to avoid blocking UI
        for _ in range(10):
            try:
                blender_cmd = _command_queue.get_nowait()
                
                # Execute the command
                try:
                    response = execute_blender_command_sync(blender_cmd)
                except Exception as e:
                    response = ResponseMessage(
                        success=False,
                        error=f"EXECUTION_ERROR: {str(e)}"
                    )
                
                # Set the future result
                future = _response_futures.get(blender_cmd.command_id)
                if future and not future.done():
                    # Use call_soon_threadsafe to set result from main thread
                    future.get_loop().call_soon_threadsafe(future.set_result, response)
                
                # Clean up
                _response_futures.pop(blender_cmd.command_id, None)
                
            except Empty:
                break  # No more commands to process
                
    except Exception as e:
        print(f"Error in execute_blender_commands: {e}")
    
    # Return timer interval (0.1 seconds)
    return 0.1


def execute_blender_command_sync(blender_cmd: BlenderCommand) -> ResponseMessage:
    """Execute a single Blender command synchronously on main thread"""
    from .command_router import get_command_router
    
    try:
        # Create command message for router
        command_msg = CommandMessage(
            command=blender_cmd.command,
            params=blender_cmd.params,
            client_id=blender_cmd.client_id
        )
        
        # Route command to appropriate handler
        router = get_command_router()
        response = router.route_command(command_msg)
        
        return response
            
    except Exception as e:
        return ResponseMessage(
            success=False,
            error=f"BLENDER_ERROR: {str(e)}"
        )


class MCPServer:
    """WebSocket MCP server for Blender"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.client_info: Dict[str, Dict[str, Any]] = {}
        self.server = None
        self.running = False
        self.command_queue = asyncio.Queue()
        self.heartbeat_task = None
        
        # Setup logging
        self.logger = logging.getLogger("MCPServer")
        self.logger.setLevel(getattr(logging, config.log_level.upper()))
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    async def start(self):
        """Start the WebSocket server"""
        try:
            self.logger.info(f"Starting MCP server on {self.config.host}:{self.config.port}")
            
            self.server = await websockets.serve(
                self.handle_client,
                self.config.host,
                self.config.port,
                ping_interval=20,  # Send ping every 20 seconds (match client)
                ping_timeout=15,   # Wait 15 seconds for pong
                close_timeout=15   # Wait 15 seconds for close
            )
            
            self.running = True
            
            # Start heartbeat monitoring
            self.heartbeat_task = asyncio.create_task(self.heartbeat_monitor())
            
            self.logger.info("MCP server started successfully")
            
            # Keep the server running
            await self.server.wait_closed()
            
        except OSError as e:
            if e.errno == 10048:  # Port already in use on Windows
                self.logger.error(f"Port {self.config.port} is already in use")
                raise RuntimeError(f"Port {self.config.port} is already in use")
            else:
                self.logger.error(f"Failed to bind to {self.config.host}:{self.config.port}: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            raise
    
    async def stop(self):
        """Stop the WebSocket server"""
        if self.server:
            self.logger.info("Stopping MCP server")
            self.running = False
            
            # Cancel heartbeat monitoring
            if self.heartbeat_task and not self.heartbeat_task.done():
                self.heartbeat_task.cancel()
                try:
                    await asyncio.wait_for(self.heartbeat_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                except Exception as e:
                    self.logger.debug(f"Error cancelling heartbeat task: {e}")
            
            # Close all client connections gracefully
            if self.clients:
                for client_id, websocket in list(self.clients.items()):
                    try:
                        if not websocket.closed:
                            await asyncio.wait_for(
                                websocket.close(code=1001, reason="Server shutting down"),
                                timeout=2.0
                            )
                    except Exception as e:
                        self.logger.debug(f"Error closing client {client_id}: {e}")
                
                # Clear client tracking
                self.clients.clear()
                self.client_info.clear()
            
            # Close server
            try:
                self.server.close()
                await asyncio.wait_for(self.server.wait_closed(), timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("Server close timed out")
            except Exception as e:
                self.logger.debug(f"Error closing server: {e}")
            
            self.logger.info("MCP server stopped")
    
    async def handle_client(self, websocket):
        """Handle new client connection"""
        client_ip = websocket.remote_address[0]
        client_port = websocket.remote_address[1]
        client_id = f"{client_ip}:{client_port}"
        
        # Check if client IP is allowed
        allowed = any(
            client_ip == allowed_ip or 
            allowed_ip == "localhost" and client_ip in ["127.0.0.1", "::1"] or
            allowed_ip == "0.0.0.0"  # Allow all IPs
            for allowed_ip in self.config.allowed_ips
        )
        
        if not allowed:
            self.logger.warning(f"Rejected connection from unauthorized IP: {client_ip}")
            await websocket.close(code=1008, reason="Unauthorized")
            return
        
        # Register client
        self.clients[client_id] = websocket
        self.client_info[client_id] = {
            "ip": client_ip,
            "port": client_port,
            "connected_at": time.time(),
            "last_seen": time.time(),
            "message_count": 0
        }
        
        self.logger.info(f"Client {client_id} connected")
        
        try:
            async for message in websocket:
                # Update last seen timestamp
                self.client_info[client_id]["last_seen"] = time.time()
                self.client_info[client_id]["message_count"] += 1
                
                await self.process_message(websocket, message, client_id)
                
        except websockets.exceptions.ConnectionClosedOK:
            self.logger.info(f"Client {client_id} disconnected normally")
        except websockets.exceptions.ConnectionClosedError as e:
            self.logger.warning(f"Client {client_id} disconnected with error: {e}")
        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Clean up client
            self.clients.pop(client_id, None)
            self.client_info.pop(client_id, None)
            self.logger.debug(f"Cleaned up client {client_id}")
    
    async def process_message(self, websocket, message: str, client_id: str):
        """Process incoming message from client with validation"""
        try:
            # Validate message size (prevent DoS)
            if len(message) > 1024 * 1024:  # 1MB limit
                error_response = create_error_response(
                    "MESSAGE_TOO_LARGE", 
                    "Message exceeds maximum size limit"
                )
                await websocket.send(json.dumps(asdict(error_response)))
                return
            
            # Parse JSON message
            try:
                data = json.loads(message)
            except json.JSONDecodeError as e:
                self.logger.warning(f"Invalid JSON from {client_id}: {e}")
                error_response = create_error_response(
                    "INVALID_JSON", 
                    f"Failed to parse JSON message: {str(e)}"
                )
                await websocket.send(json.dumps(asdict(error_response)))
                return
            
            # Validate message structure
            if not isinstance(data, dict):
                error_response = create_error_response(
                    "INVALID_MESSAGE_FORMAT", 
                    "Message must be a JSON object"
                )
                await websocket.send(json.dumps(asdict(error_response)))
                return
            
            # Extract command and params
            command = data.get("command", "")
            params = data.get("params", {})
            
            # Validate command
            if not command:
                error_response = create_error_response(
                    "MISSING_COMMAND", 
                    "Command field is required"
                )
                await websocket.send(json.dumps(asdict(error_response)))
                return
            
            if not isinstance(command, str):
                error_response = create_error_response(
                    "INVALID_COMMAND_TYPE", 
                    "Command must be a string"
                )
                await websocket.send(json.dumps(asdict(error_response)))
                return
            
            if not validate_command(command):
                error_response = create_error_response(
                    "UNKNOWN_COMMAND", 
                    f"Command '{command}' is not recognized",
                    f"Available commands: ping, get_scene_info, get_server_status, clear_scene, render_scene, create_object, move_object, rotate_object, scale_object, set_material"
                )
                await websocket.send(json.dumps(asdict(error_response)))
                return
            
            # Validate params
            if not isinstance(params, dict):
                error_response = create_error_response(
                    "INVALID_PARAMS_TYPE", 
                    "Params must be a JSON object"
                )
                await websocket.send(json.dumps(asdict(error_response)))
                return
            
            # Validate command-specific parameters
            param_error = validate_params(command, params)
            if param_error:
                error_response = create_error_response(
                    "INVALID_PARAMS", 
                    param_error
                )
                await websocket.send(json.dumps(asdict(error_response)))
                return
            
            # Create validated command message
            command_msg = CommandMessage(
                command=command,
                params=params,
                client_id=client_id
            )
            
            self.logger.debug(f"Received valid command: {command_msg.command} from {client_id}")
            
            # Execute command
            response = await self.execute_command(command_msg)
            
            # Send response
            await websocket.send(json.dumps(asdict(response)))
            
        except Exception as e:
            self.logger.error(f"Error processing message from {client_id}: {e}")
            error_response = create_error_response(
                "PROCESSING_ERROR", 
                f"Internal server error: {str(e)}"
            )
            try:
                await websocket.send(json.dumps(asdict(error_response)))
            except Exception:
                pass  # Client may have disconnected
    
    async def heartbeat_monitor(self):
        """Monitor client connections and clean up stale ones"""
        while self.running:
            try:
                current_time = time.time()
                stale_clients = []
                warning_clients = []
                
                for client_id, info in self.client_info.items():
                    time_since_last_seen = current_time - info["last_seen"]
                    
                    # Consider client stale if no activity for 5 minutes
                    if time_since_last_seen > 300:
                        stale_clients.append(client_id)
                    # Warn about clients inactive for 3 minutes
                    elif time_since_last_seen > 180:
                        warning_clients.append(client_id)
                
                # Log warnings for inactive clients
                for client_id in warning_clients:
                    self.logger.warning(f"Client {client_id} inactive for {int(current_time - self.client_info[client_id]['last_seen'])} seconds")
                
                # Clean up stale clients
                for client_id in stale_clients:
                    await self._cleanup_client(client_id, "Connection timeout")
                
                # Log connection statistics
                if len(self.clients) > 0:
                    self.logger.debug(f"Active connections: {len(self.clients)}, Cleaned up: {len(stale_clients)}")
                
                # Wait 60 seconds before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_client(self, client_id: str, reason: str = "Cleanup"):
        """Clean up a specific client connection"""
        websocket = self.clients.get(client_id)
        if websocket:
            try:
                await websocket.close(code=1001, reason=reason)
            except Exception as e:
                self.logger.debug(f"Error closing client {client_id}: {e}")
        
        # Remove from tracking
        self.clients.pop(client_id, None)
        client_info = self.client_info.pop(client_id, None)
        
        if client_info:
            connection_duration = time.time() - client_info["connected_at"]
            self.logger.info(f"Cleaned up client {client_id} after {connection_duration:.1f}s ({reason})")
    
    async def broadcast_message(self, message: dict, exclude_client: str = None):
        """Broadcast a message to all connected clients"""
        if not self.clients:
            return
        
        message_json = json.dumps(message)
        failed_clients = []
        
        for client_id, websocket in self.clients.items():
            if client_id == exclude_client:
                continue
                
            try:
                await websocket.send(message_json)
            except Exception as e:
                self.logger.warning(f"Failed to send broadcast to {client_id}: {e}")
                failed_clients.append(client_id)
        
        # Clean up failed clients
        for client_id in failed_clients:
            await self._cleanup_client(client_id, "Broadcast failed")
    
    def get_client_stats(self) -> Dict[str, Any]:
        """Get client connection statistics"""
        current_time = time.time()
        stats = {
            "total_clients": len(self.clients),
            "clients": {}
        }
        
        for client_id, info in self.client_info.items():
            stats["clients"][client_id] = {
                "ip": info["ip"],
                "connected_duration": current_time - info["connected_at"],
                "last_activity": current_time - info["last_seen"],
                "message_count": info["message_count"]
            }
        
        return stats
    
    async def execute_command(self, command: CommandMessage) -> ResponseMessage:
        """Execute a command using the main thread queue system"""
        global _command_queue, _response_futures
        
        # Commands that don't need Blender API can be executed directly
        if command.command == "get_server_status":
            return ResponseMessage(
                success=True,
                data={
                    "running": self.running,
                    "server_config": {
                        "host": self.config.host,
                        "port": self.config.port,
                        "allowed_ips": self.config.allowed_ips
                    },
                    "client_stats": self.get_client_stats(),
                    "uptime": time.time() - (min(info["connected_at"] for info in self.client_info.values()) if self.client_info else time.time())
                }
            )
        
        # Commands that need Blender API must be queued for main thread execution
        command_id = str(uuid.uuid4())
        blender_cmd = BlenderCommand(
            command_id=command_id,
            command=command.command,
            params=command.params,
            client_id=command.client_id
        )
        
        # Create future for response
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        _response_futures[command_id] = future
        
        # Queue command for main thread execution
        _command_queue.put(blender_cmd)
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            # Clean up on timeout
            _response_futures.pop(command_id, None)
            return ResponseMessage(
                success=False,
                error="TIMEOUT: Command execution timed out"
            )
        except Exception as e:
            # Clean up on error
            _response_futures.pop(command_id, None)
            return ResponseMessage(
                success=False,
                error=f"EXECUTION_ERROR: {str(e)}"
            )


def start_server(host: str = "localhost", port: int = 8765, 
                allowed_ips: List[str] = None, log_level: str = "INFO"):
    """Start the MCP server in a separate thread"""
    global _server_instance, _server_thread, _blender_timer
    
    if not WEBSOCKETS_AVAILABLE:
        raise RuntimeError("websockets library is not installed. Please install it first.")
    
    # Stop any existing server first
    if _server_instance is not None:
        print("Stopping existing server instance...")
        stop_server()
        import time
        time.sleep(1.0)  # Wait for cleanup
    
    config = ServerConfig(
        host=host,
        port=port,
        allowed_ips=allowed_ips or ["127.0.0.1"],
        log_level=log_level
    )
    
    _server_instance = MCPServer(config)
    
    # Start Blender timer for main thread command execution
    if not _blender_timer:
        _blender_timer = bpy.app.timers.register(execute_blender_commands, persistent=True)
        print("Registered Blender timer for MCP command execution")
    
    def run_server():
        """Run the server in asyncio event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            print(f"MCP Server starting on {config.host}:{config.port}...")
            loop.run_until_complete(_server_instance.start())
        except Exception as e:
            print(f"Server error: {e}")
            # Mark server as not running on error
            if _server_instance:
                _server_instance.running = False
        finally:
            loop.close()
    
    _server_thread = threading.Thread(target=run_server, daemon=True)
    _server_thread.start()
    
    # Give the server a moment to start
    import time
    time.sleep(0.5)
    
    # Verify server started
    max_attempts = 10
    for attempt in range(max_attempts):
        if _server_instance and hasattr(_server_instance, 'running') and _server_instance.running:
            print(f"✓ MCP Server confirmed running on {config.host}:{config.port}")
            break
        time.sleep(0.1)
    else:
        print("⚠️ Server may still be starting up...")


def stop_server():
    """Stop the MCP server"""
    global _server_instance, _server_thread, _blender_timer, _command_queue, _response_futures
    
    if _server_instance:
        # Mark server as not running first
        if hasattr(_server_instance, 'running'):
            _server_instance.running = False
        
        # Try to stop the server gracefully
        try:
            # Check if there's already an event loop running
            try:
                current_loop = asyncio.get_running_loop()
                # If we're in an event loop, we can't use run_until_complete
                # Instead, we'll let the server thread handle the shutdown
                print("Stopping server from within event loop...")
            except RuntimeError:
                # No event loop running, safe to create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_server_instance.stop())
                except Exception as e:
                    print(f"Error stopping server: {e}")
                finally:
                    loop.close()
        except Exception as e:
            print(f"Error during server shutdown: {e}")
        
        # Wait for server thread to finish
        if _server_thread and _server_thread.is_alive():
            _server_thread.join(timeout=3.0)
            if _server_thread.is_alive():
                print("Warning: Server thread did not stop gracefully")
        
        _server_instance = None
        _server_thread = None
    
    # Stop Blender timer
    if _blender_timer:
        try:
            bpy.app.timers.unregister(execute_blender_commands)
            _blender_timer = None
            print("Unregistered Blender timer")
        except Exception as e:
            print(f"Error unregistering timer: {e}")
    
    # Clear command queue and pending futures
    while not _command_queue.empty():
        try:
            _command_queue.get_nowait()
        except Empty:
            break
    
    # Cancel any pending futures
    for future in list(_response_futures.values()):
        if not future.done():
            try:
                future.cancel()
            except Exception:
                pass
    _response_futures.clear()


def is_server_running() -> bool:
    """Check if the server is currently running"""
    global _server_instance, _server_thread
    
    if _server_instance is None:
        return False
    
    # Check if server thread is alive and server instance exists
    if _server_thread and _server_thread.is_alive():
        # Server thread is running, check if server is actually running
        return hasattr(_server_instance, 'running') and _server_instance.running
    
    return False


def get_server_status() -> dict:
    """Get detailed server status information"""
    global _server_instance, _server_thread, _blender_timer
    
    status = {
        "running": False,
        "thread_alive": False,
        "timer_registered": False,
        "instance_exists": False,
        "details": "Server not initialized"
    }
    
    if _server_instance is not None:
        status["instance_exists"] = True
        status["running"] = hasattr(_server_instance, 'running') and _server_instance.running
        
        if hasattr(_server_instance, 'config'):
            status["host"] = _server_instance.config.host
            status["port"] = _server_instance.config.port
    
    if _server_thread is not None:
        status["thread_alive"] = _server_thread.is_alive()
    
    status["timer_registered"] = _blender_timer is not None
    
    # Determine overall status
    if status["running"] and status["thread_alive"]:
        status["details"] = f"Running on {status.get('host', 'unknown')}:{status.get('port', 'unknown')}"
    elif status["thread_alive"]:
        status["details"] = "Starting up..."
    elif status["instance_exists"]:
        status["details"] = "Stopped"
    else:
        status["details"] = "Not initialized"
    
    return status