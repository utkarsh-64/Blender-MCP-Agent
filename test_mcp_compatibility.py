#!/usr/bin/env python3
"""
Test script to verify MCP server compatibility with existing BlenderMCPClient
"""

import asyncio
import sys
import os

# Add the project root to the path so we can import the client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.client import BlenderMCPClient


async def test_basic_connection():
    """Test basic connection and ping"""
    print("🔌 Testing basic connection...")
    
    client = BlenderMCPClient()
    
    try:
        # Connect to server
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to server")
            return False
        
        print("✅ Connected successfully")
        
        # Test ping
        response = await client.send_command("ping", {"echo": "test"})
        if response.success:
            print(f"✅ Ping successful: {response.message}")
            print(f"   Data: {response.data}")
        else:
            print(f"❌ Ping failed: {response.error}")
            return False
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


async def test_scene_operations():
    """Test scene information and manipulation"""
    print("\n🎬 Testing scene operations...")
    
    client = BlenderMCPClient()
    
    try:
        await client.connect()
        
        # Test get_scene_info
        response = await client.get_scene_info()
        if response.success:
            print("✅ Scene info retrieved successfully")
            print(f"   Scene: {response.data.get('scene_name')}")
            print(f"   Objects: {len(response.data.get('objects', []))}")
        else:
            print(f"❌ Scene info failed: {response.error}")
            return False
        
        # Test clear_scene
        response = await client.clear_scene()
        if response.success:
            print("✅ Scene cleared successfully")
            print(f"   {response.message}")
        else:
            print(f"❌ Clear scene failed: {response.error}")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Scene operations test failed: {e}")
        return False


async def test_object_operations():
    """Test object creation and manipulation"""
    print("\n🧊 Testing object operations...")
    
    client = BlenderMCPClient()
    
    try:
        await client.connect()
        
        # Test create_object
        response = await client.create_object("cube", "TestCube", [1, 2, 3])
        if response.success:
            print("✅ Object created successfully")
            print(f"   {response.message}")
        else:
            print(f"❌ Object creation failed: {response.error}")
            return False
        
        # Test move_object
        response = await client.move_object("TestCube", [2, 3, 4])
        if response.success:
            print("✅ Object moved successfully")
            print(f"   {response.message}")
        else:
            print(f"❌ Object move failed: {response.error}")
        
        # Test rotate_object
        response = await client.rotate_object("TestCube", [45, 0, 90])
        if response.success:
            print("✅ Object rotated successfully")
            print(f"   {response.message}")
        else:
            print(f"❌ Object rotation failed: {response.error}")
        
        # Test scale_object
        response = await client.scale_object("TestCube", [1.5, 1.5, 1.5])
        if response.success:
            print("✅ Object scaled successfully")
            print(f"   {response.message}")
        else:
            print(f"❌ Object scaling failed: {response.error}")
        
        # Test set_material
        material_props = {
            "color": [0.8, 0.2, 0.2, 1.0],  # Red color
            "metallic": 0.5,
            "roughness": 0.3
        }
        response = await client.set_material("TestCube", material_props)
        if response.success:
            print("✅ Material set successfully")
            print(f"   {response.message}")
        else:
            print(f"❌ Material setting failed: {response.error}")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Object operations test failed: {e}")
        return False


async def test_render_operations():
    """Test rendering operations"""
    print("\n🎨 Testing render operations...")
    
    client = BlenderMCPClient()
    
    try:
        await client.connect()
        
        # Test render_scene
        response = await client.render_scene("/tmp/test_render.png")
        if response.success:
            print("✅ Scene rendered successfully")
            print(f"   {response.message}")
            print(f"   Output: {response.data.get('output_path')}")
        else:
            print(f"❌ Render failed: {response.error}")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Render operations test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling with invalid commands"""
    print("\n⚠️  Testing error handling...")
    
    client = BlenderMCPClient()
    
    try:
        await client.connect()
        
        # Test invalid command
        response = await client.send_command("invalid_command", {})
        if not response.success:
            print("✅ Invalid command properly rejected")
            print(f"   Error: {response.error}")
        else:
            print("❌ Invalid command was not rejected")
        
        # Test invalid object operation
        response = await client.move_object("NonExistentObject", [0, 0, 0])
        if not response.success:
            print("✅ Invalid object operation properly rejected")
            print(f"   Error: {response.error}")
        else:
            print("❌ Invalid object operation was not rejected")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


async def main():
    """Run all compatibility tests"""
    print("🚀 Starting MCP Server Compatibility Tests")
    print("=" * 50)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Scene Operations", test_scene_operations),
        ("Object Operations", test_object_operations),
        ("Render Operations", test_render_operations),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! MCP server is compatible with BlenderMCPClient")
        return 0
    else:
        print("⚠️  Some tests failed. Check the server implementation.")
        return 1


if __name__ == "__main__":
    print("Note: Make sure the Blender MCP Server addon is installed and running in Blender")
    print("      before running this test script.\n")
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)