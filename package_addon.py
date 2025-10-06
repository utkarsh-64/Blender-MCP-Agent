#!/usr/bin/env python3
"""
Package the Blender MCP Server addon for distribution
"""

import os
import shutil
import zipfile
from pathlib import Path


def create_addon_package():
    """Create a distributable addon package"""
    
    # Define paths
    addon_dir = Path("blender_mcp_server")
    dist_dir = Path("dist")
    package_name = "blender_mcp_server_v1.0.0"
    
    # Create distribution directory
    dist_dir.mkdir(exist_ok=True)
    
    # Files to include in the addon package
    addon_files = [
        "__init__.py",
        "server.py", 
        "command_router.py",
        "data_models.py",
        "ui.py",
        "handlers/__init__.py",
        "handlers/object_handler.py",
        "handlers/scene_handler.py", 
        "handlers/render_handler.py",
        "utils/__init__.py",
        "utils/validation.py",
        "utils/error_handling.py"
    ]
    
    # Create ZIP package
    zip_path = dist_dir / f"{package_name}.zip"
    
    print(f"Creating addon package: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in addon_files:
            full_path = addon_dir / file_path
            if full_path.exists():
                # Add file to ZIP with proper directory structure
                arcname = f"blender_mcp_server/{file_path}"
                zipf.write(full_path, arcname)
                print(f"  Added: {file_path}")
            else:
                print(f"  Warning: Missing file {file_path}")
    
    print(f"✅ Addon package created: {zip_path}")
    print(f"   Size: {zip_path.stat().st_size / 1024:.1f} KB")
    
    return zip_path


def create_full_distribution():
    """Create a complete distribution package with documentation"""
    
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    package_name = "blender_mcp_server_complete_v1.0.0"
    
    # Files to include in complete distribution
    files_to_include = [
        # Addon files
        ("blender_mcp_server/", "blender_mcp_server/"),
        
        # Documentation
        ("README.md", "README.md"),
        ("INSTALLATION.md", "INSTALLATION.md"), 
        ("API_REFERENCE.md", "API_REFERENCE.md"),
        
        # Test files
        ("test_mcp_compatibility.py", "tests/test_mcp_compatibility.py"),
        ("test_end_to_end_workflow.py", "tests/test_end_to_end_workflow.py"),
        
        # Example client (if exists)
        ("mcp/client.py", "examples/mcp_client.py"),
    ]
    
    zip_path = dist_dir / f"{package_name}.zip"
    
    print(f"Creating complete distribution: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for src_path, arc_path in files_to_include:
            src = Path(src_path)
            
            if src.is_file():
                zipf.write(src, arc_path)
                print(f"  Added file: {src_path}")
            elif src.is_dir():
                # Add directory recursively
                for file_path in src.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        rel_path = file_path.relative_to(src.parent)
                        zipf.write(file_path, str(rel_path))
                        print(f"  Added: {rel_path}")
            else:
                print(f"  Warning: Missing {src_path}")
    
    print(f"✅ Complete distribution created: {zip_path}")
    print(f"   Size: {zip_path.stat().st_size / 1024:.1f} KB")
    
    return zip_path


def create_installation_script():
    """Create an installation script for easy setup"""
    
    script_content = '''#!/usr/bin/env python3
"""
Blender MCP Server Installation Script
Automatically installs the addon to the correct Blender directory
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
import platform


def find_blender_addons_dir():
    """Find the Blender addons directory"""
    system = platform.system()
    
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            blender_dir = Path(appdata) / "Blender Foundation" / "Blender"
    elif system == "Darwin":  # macOS
        home = Path.home()
        blender_dir = home / "Library" / "Application Support" / "Blender"
    else:  # Linux
        home = Path.home()
        blender_dir = home / ".config" / "blender"
    
    if not blender_dir.exists():
        return None
    
    # Find the latest version directory
    version_dirs = [d for d in blender_dir.iterdir() if d.is_dir() and d.name.replace(".", "").isdigit()]
    if not version_dirs:
        return None
    
    latest_version = max(version_dirs, key=lambda x: tuple(map(int, x.name.split("."))))
    addons_dir = latest_version / "scripts" / "addons"
    
    return addons_dir


def install_addon():
    """Install the Blender MCP Server addon"""
    print("🚀 Blender MCP Server Installation")
    print("=" * 40)
    
    # Find addon ZIP file
    addon_zip = None
    for file in Path(".").glob("blender_mcp_server*.zip"):
        addon_zip = file
        break
    
    if not addon_zip:
        print("❌ Error: No addon ZIP file found")
        print("   Please ensure blender_mcp_server_v*.zip is in the current directory")
        return False
    
    print(f"📦 Found addon package: {addon_zip}")
    
    # Find Blender addons directory
    addons_dir = find_blender_addons_dir()
    if not addons_dir:
        print("❌ Error: Could not find Blender addons directory")
        print("   Please install manually by copying to your Blender addons folder")
        return False
    
    print(f"📁 Blender addons directory: {addons_dir}")
    
    # Create addons directory if it doesn't exist
    addons_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract addon
    addon_target = addons_dir / "blender_mcp_server"
    
    # Remove existing installation
    if addon_target.exists():
        print("🗑️  Removing existing installation...")
        shutil.rmtree(addon_target)
    
    print("📂 Extracting addon...")
    with zipfile.ZipFile(addon_zip, 'r') as zipf:
        zipf.extractall(addons_dir)
    
    if addon_target.exists():
        print("✅ Addon installed successfully!")
        print()
        print("Next steps:")
        print("1. Start Blender")
        print("2. Go to Edit > Preferences > Add-ons")
        print("3. Search for 'Blender MCP Server'")
        print("4. Enable the addon")
        print("5. Configure server settings in addon preferences")
        return True
    else:
        print("❌ Error: Installation failed")
        return False


if __name__ == "__main__":
    success = install_addon()
    if not success:
        sys.exit(1)
'''
    
    script_path = Path("dist") / "install_addon.py"
    script_path.write_text(script_content)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod(script_path, 0o755)
    
    print(f"✅ Installation script created: {script_path}")
    
    return script_path


def create_version_info():
    """Create version information file"""
    
    version_info = {
        "name": "Blender MCP Server",
        "version": "1.0.0",
        "blender_version": "3.0.0",
        "description": "WebSocket-based MCP server for remote Blender control",
        "author": "Autonomous 3D Scene Generator Team",
        "category": "System",
        "support": "COMMUNITY",
        "files": [
            "blender_mcp_server/__init__.py",
            "blender_mcp_server/server.py",
            "blender_mcp_server/command_router.py",
            "blender_mcp_server/ui.py",
            "blender_mcp_server/handlers/",
            "blender_mcp_server/utils/"
        ],
        "dependencies": [
            "websockets (included with Blender)",
            "asyncio (included with Python)"
        ],
        "features": [
            "WebSocket server for remote control",
            "Object creation and manipulation",
            "Scene management",
            "Render control",
            "Material assignment",
            "Error handling and logging",
            "Security with IP filtering"
        ]
    }
    
    import json
    version_file = Path("dist") / "version_info.json"
    version_file.write_text(json.dumps(version_info, indent=2))
    
    print(f"✅ Version info created: {version_file}")
    
    return version_file


def main():
    """Main packaging function"""
    print("📦 Blender MCP Server Packaging")
    print("=" * 40)
    
    # Create addon package
    addon_zip = create_addon_package()
    
    # Create complete distribution
    complete_zip = create_full_distribution()
    
    # Create installation script
    install_script = create_installation_script()
    
    # Create version info
    version_info = create_version_info()
    
    print("\n" + "=" * 40)
    print("📋 Packaging Summary")
    print("=" * 40)
    print(f"✅ Addon package: {addon_zip}")
    print(f"✅ Complete distribution: {complete_zip}")
    print(f"✅ Installation script: {install_script}")
    print(f"✅ Version info: {version_info}")
    
    print("\n🎉 Packaging complete!")
    print("\nDistribution files:")
    print("- Use the addon ZIP for manual Blender installation")
    print("- Use the complete ZIP for full documentation and tests")
    print("- Run the installation script for automatic setup")


if __name__ == "__main__":
    main()