# Blender MCP Server

A WebSocket-based Model Context Protocol (MCP) server for Blender that enables remote control of 3D scene creation, manipulation, and rendering. This addon allows external applications to programmatically control Blender through a standardized JSON-based API.

## Features

- 🌐 **WebSocket Server**: Real-time communication with external applications
- 🎯 **Object Manipulation**: Create, move, rotate, scale, and apply materials to 3D objects
- 🎬 **Scene Management**: Query scene information and manage scene state
- 🎨 **Rendering Control**: Configure render settings and generate images
- 🔒 **Security**: IP-based access control and input validation
- 📊 **Monitoring**: Built-in error tracking and connection statistics
- 🔧 **Easy Setup**: Simple Blender addon installation with GUI configuration

## Quick Start

### 1. Installation

1. Download or clone this repository
2. Copy the `blender_mcp_server` folder to your Blender addons directory
3. Enable the addon in Blender preferences (Edit > Preferences > Add-ons)
4. Configure server settings in the addon preferences

### 2. Start the Server

The server can start automatically when the addon is enabled, or manually:

- **Automatic**: Enable "Auto Start" in addon preferences
- **Manual**: Click "Start Server" in preferences or the 3D viewport sidebar

### 3. Connect Your Application

```python
from mcp.client import BlenderMCPClient

async def example():
    client = BlenderMCPClient()
    await client.connect()
    
    # Create a cube
    response = await client.create_object("cube", "MyCube", [0, 0, 0])
    print(response.message)
    
    # Get scene info
    response = await client.get_scene_info()
    print(f"Scene has {len(response.data['objects'])} objects")
    
    await client.disconnect()
```

## Architecture

```
External Application
        ↓ WebSocket
Blender MCP Server Addon
        ↓
Command Router → Object Handler
               → Scene Handler  
               → Render Handler
        ↓
Blender Python API
        ↓
Blender Scene
```

## API Reference

### Connection

Connect to the server using WebSocket:
- **URL**: `ws://localhost:8765` (default)
- **Protocol**: JSON messages over WebSocket
- **Authentication**: IP-based access control

### Message Format

**Request:**
```json
{
    "command": "command_name",
    "params": {
        "param1": "value1",
        "param2": "value2"
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {...},
    "message": "Optional message",
    "error": "Error description if success=false"
}
```

### Available Commands

#### Object Commands

**create_object**
```json
{
    "command": "create_object",
    "params": {
        "type": "cube|sphere|cylinder|plane|cone|torus",
        "name": "ObjectName",
        "location": [x, y, z]
    }
}
```

**move_object**
```json
{
    "command": "move_object",
    "params": {
        "name": "ObjectName",
        "location": [x, y, z]
    }
}
```

**rotate_object**
```json
{
    "command": "rotate_object",
    "params": {
        "name": "ObjectName",
        "rotation": [x_degrees, y_degrees, z_degrees]
    }
}
```

**scale_object**
```json
{
    "command": "scale_object",
    "params": {
        "name": "ObjectName",
        "scale": [x_scale, y_scale, z_scale]
    }
}
```

**set_material**
```json
{
    "command": "set_material",
    "params": {
        "name": "ObjectName",
        "material": {
            "color": [r, g, b, a] | "#RRGGBB",
            "metallic": 0.0-1.0,
            "roughness": 0.0-1.0
        }
    }
}
```

#### Scene Commands

**get_scene_info**
```json
{
    "command": "get_scene_info",
    "params": {}
}
```

**clear_scene**
```json
{
    "command": "clear_scene",
    "params": {}
}
```

#### Render Commands

**render_scene**
```json
{
    "command": "render_scene",
    "params": {
        "output_path": "/path/to/output.png",
        "resolution": [width, height],
        "engine": "CYCLES|BLENDER_EEVEE|BLENDER_WORKBENCH"
    }
}
```

**set_render_settings**
```json
{
    "command": "set_render_settings",
    "params": {
        "resolution": [width, height],
        "engine": "CYCLES|BLENDER_EEVEE|BLENDER_WORKBENCH",
        "samples": 64,
        "format": "PNG|JPEG|TIFF"
    }
}
```

**get_render_settings**
```json
{
    "command": "get_render_settings",
    "params": {}
}
```

#### System Commands

**ping**
```json
{
    "command": "ping",
    "params": {
        "echo": "optional_message"
    }
}
```

**get_server_status**
```json
{
    "command": "get_server_status",
    "params": {}
}
```

## Configuration

### Network Settings

- **Host**: Server bind address
  - `localhost`: Local connections only
  - `0.0.0.0`: Accept from any IP
- **Port**: Server port (default: 8765)
- **Allowed IPs**: Comma-separated list of allowed client IPs

### Security Settings

- **IP Filtering**: Only specified IPs can connect
- **Input Validation**: All commands and parameters are validated
- **Error Isolation**: Client errors don't affect other clients

## Testing

### Compatibility Test
```bash
python test_mcp_compatibility.py
```

### End-to-End Workflow Test
```bash
python test_end_to_end_workflow.py
```

### Manual Testing
1. Start the server in Blender
2. Use any WebSocket client to connect
3. Send JSON commands and verify responses

## Use Cases

### Autonomous 3D Scene Generation
- Natural language to 3D scene conversion
- Automated scene composition
- Batch rendering workflows

### External Tool Integration
- CAD software integration
- Game engine asset pipeline
- Automated testing of 3D content

### Remote Blender Control
- Headless Blender operations
- Cloud-based 3D processing
- Multi-user collaborative workflows

## Troubleshooting

### Common Issues

**Server won't start**
- Check if port is available
- Verify Blender addon is enabled
- Check console for error messages

**Connection refused**
- Verify server is running
- Check host/port settings
- Review allowed IPs configuration

**Commands not working**
- Validate JSON format
- Check command spelling
- Review parameter requirements

### Debug Information

Enable debug logging in addon preferences and check:
- Blender console (Window > Toggle System Console)
- Addon preferences for server status
- Error statistics via `get_error_stats` command

## Development

### Project Structure
```
blender_mcp_server/
├── __init__.py              # Addon registration
├── server.py                # WebSocket server
├── command_router.py        # Command routing
├── handlers/                # Command handlers
│   ├── object_handler.py
│   ├── scene_handler.py
│   └── render_handler.py
├── utils/                   # Utilities
│   ├── validation.py
│   └── error_handling.py
└── ui.py                    # User interface
```

### Adding New Commands

1. Add handler method to appropriate handler class
2. Register command in `command_router.py`
3. Add validation rules in `utils/validation.py`
4. Update documentation

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## Requirements

- Blender 3.0 or later
- Python websockets library (included with Blender)
- Network access for remote connections

## License

This project is open source. See LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Blender console output
3. Run the provided test scripts
4. Create an issue with detailed information

## Changelog

### Version 1.0.0
- Initial release
- Full MCP server implementation
- Object manipulation commands
- Scene management commands
- Render control commands
- WebSocket server with security
- Blender addon with GUI
- Comprehensive testing suite