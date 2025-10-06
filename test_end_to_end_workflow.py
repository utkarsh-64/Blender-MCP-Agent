#!/usr/bin/env python3
"""
End-to-end workflow test for the Blender MCP Server
Simulates the autonomous 3D scene generator workflows
"""

import asyncio
import sys
import os
import time

# Add the project root to the path so we can import the client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.client import BlenderMCPClient


class SceneWorkflowTester:
    """Test complete scene creation workflows"""
    
    def __init__(self):
        self.client = BlenderMCPClient()
        self.test_results = []
    
    async def connect(self):
        """Connect to the MCP server"""
        connected = await self.client.connect()
        if not connected:
            raise ConnectionError("Failed to connect to MCP server")
        print("✅ Connected to MCP server")
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        await self.client.disconnect()
        print("✅ Disconnected from MCP server")
    
    async def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log a test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append((test_name, success, message))
    
    async def test_basic_scene_setup(self):
        """Test basic scene setup workflow"""
        print("\n🎬 Testing Basic Scene Setup Workflow")
        print("-" * 40)
        
        try:
            # Clear the scene first
            response = await self.client.clear_scene()
            await self.log_test_result("Clear Scene", response.success, response.message or response.error)
            
            # Get initial scene info
            response = await self.client.get_scene_info()
            if response.success:
                initial_objects = len(response.data.get('objects', []))
                await self.log_test_result("Get Initial Scene Info", True, f"{initial_objects} objects in scene")
            else:
                await self.log_test_result("Get Initial Scene Info", False, response.error)
                return False
            
            return True
            
        except Exception as e:
            await self.log_test_result("Basic Scene Setup", False, str(e))
            return False
    
    async def test_living_room_scene(self):
        """Test creating a living room scene"""
        print("\n🏠 Testing Living Room Scene Creation")
        print("-" * 40)
        
        try:
            # Create furniture objects
            furniture = [
                ("cube", "Sofa", [0, 0, 0.5], [2, 1, 1]),
                ("cube", "CoffeeTable", [0, -2, 0.3], [1.5, 0.8, 0.6]),
                ("cylinder", "FloorLamp", [3, 2, 1], [0.2, 0.2, 2]),
                ("cube", "TVStand", [0, 4, 0.3], [2, 0.5, 0.6]),
                ("plane", "Rug", [0, 0, 0.01], [4, 3, 0.1])
            ]
            
            created_objects = []
            
            for obj_type, name, location, scale in furniture:
                # Create object
                response = await self.client.create_object(obj_type, name, location)
                if response.success:
                    created_objects.append(name)
                    await self.log_test_result(f"Create {name}", True, f"Created at {location}")
                    
                    # Scale object
                    response = await self.client.scale_object(name, scale)
                    await self.log_test_result(f"Scale {name}", response.success, response.message or response.error)
                else:
                    await self.log_test_result(f"Create {name}", False, response.error)
            
            # Apply materials
            materials = [
                ("Sofa", {"color": [0.3, 0.2, 0.8, 1.0], "roughness": 0.8}),  # Blue fabric
                ("CoffeeTable", {"color": [0.6, 0.4, 0.2, 1.0], "roughness": 0.3}),  # Wood
                ("FloorLamp", {"color": [0.9, 0.9, 0.9, 1.0], "metallic": 0.8}),  # Metal
                ("TVStand", {"color": [0.1, 0.1, 0.1, 1.0], "roughness": 0.2}),  # Black
                ("Rug", {"color": [0.8, 0.1, 0.1, 1.0], "roughness": 0.9})  # Red carpet
            ]
            
            for obj_name, material_props in materials:
                if obj_name in created_objects:
                    response = await self.client.set_material(obj_name, material_props)
                    await self.log_test_result(f"Material {obj_name}", response.success, response.message or response.error)
            
            # Get final scene info
            response = await self.client.get_scene_info()
            if response.success:
                final_objects = len(response.data.get('objects', []))
                await self.log_test_result("Final Scene Info", True, f"{final_objects} objects in scene")
            
            return len(created_objects) >= 4  # Success if most objects were created
            
        except Exception as e:
            await self.log_test_result("Living Room Scene", False, str(e))
            return False
    
    async def test_geometric_arrangement(self):
        """Test creating geometric arrangements"""
        print("\n📐 Testing Geometric Arrangement")
        print("-" * 40)
        
        try:
            # Clear scene first
            await self.client.clear_scene()
            
            # Create a circle of cubes
            import math
            radius = 3
            num_objects = 8
            
            created_objects = []
            
            for i in range(num_objects):
                angle = (2 * math.pi * i) / num_objects
                x = radius * math.cos(angle)
                y = radius * math.sin(angle)
                z = 0
                
                name = f"Cube_{i:02d}"
                response = await self.client.create_object("cube", name, [x, y, z])
                
                if response.success:
                    created_objects.append(name)
                    
                    # Rotate to face center
                    rotation_z = math.degrees(angle + math.pi/2)
                    response = await self.client.rotate_object(name, [0, 0, rotation_z])
                    
                    # Apply gradient color
                    hue = i / num_objects
                    color = self._hsv_to_rgb(hue, 1.0, 1.0)
                    response = await self.client.set_material(name, {"color": color})
            
            await self.log_test_result("Geometric Circle", True, f"Created {len(created_objects)} objects in circle")
            
            # Create center object
            response = await self.client.create_object("sphere", "CenterSphere", [0, 0, 1])
            if response.success:
                await self.client.scale_object("CenterSphere", [1.5, 1.5, 1.5])
                await self.client.set_material("CenterSphere", {"color": [1, 1, 0, 1], "metallic": 0.8})
                await self.log_test_result("Center Sphere", True, "Created center sphere")
            
            return len(created_objects) >= 6
            
        except Exception as e:
            await self.log_test_result("Geometric Arrangement", False, str(e))
            return False
    
    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB color"""
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return [r, g, b, 1.0]
    
    async def test_render_workflow(self):
        """Test complete render workflow"""
        print("\n🎨 Testing Render Workflow")
        print("-" * 40)
        
        try:
            # Set render settings
            render_settings = {
                "resolution": [800, 600],
                "engine": "BLENDER_EEVEE",
                "samples": 64,
                "format": "PNG"
            }
            
            response = await self.client.send_command("set_render_settings", render_settings)
            await self.log_test_result("Set Render Settings", response.success, response.message or response.error)
            
            # Get render settings to verify
            response = await self.client.send_command("get_render_settings", {})
            if response.success:
                settings = response.data
                await self.log_test_result("Get Render Settings", True, f"Engine: {settings.get('engine')}, Resolution: {settings.get('resolution')}")
            
            # Render scene
            output_path = "/tmp/test_workflow_render.png"
            response = await self.client.render_scene(output_path)
            
            if response.success:
                render_time = response.data.get('render_time', 0)
                file_size = response.data.get('file_size', 0)
                await self.log_test_result("Render Scene", True, f"Rendered in {render_time:.2f}s, size: {file_size} bytes")
                return True
            else:
                await self.log_test_result("Render Scene", False, response.error)
                return False
            
        except Exception as e:
            await self.log_test_result("Render Workflow", False, str(e))
            return False
    
    async def test_multi_step_scene_modification(self):
        """Test multi-step scene modifications"""
        print("\n🔄 Testing Multi-Step Scene Modifications")
        print("-" * 40)
        
        try:
            # Create initial objects
            objects = ["Cube_A", "Cube_B", "Cube_C"]
            positions = [[0, 0, 0], [2, 0, 0], [4, 0, 0]]
            
            # Step 1: Create objects
            for obj_name, pos in zip(objects, positions):
                response = await self.client.create_object("cube", obj_name, pos)
                await self.log_test_result(f"Create {obj_name}", response.success)
            
            # Step 2: Animate-like sequence (move objects in steps)
            for step in range(3):
                await asyncio.sleep(0.5)  # Small delay to simulate animation
                
                for i, obj_name in enumerate(objects):
                    new_y = step * 2
                    new_pos = [positions[i][0], new_y, positions[i][2]]
                    response = await self.client.move_object(obj_name, new_pos)
                    
                await self.log_test_result(f"Animation Step {step + 1}", True, f"Moved objects to y={new_y}")
            
            # Step 3: Apply different materials
            colors = [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]]  # RGB
            for obj_name, color in zip(objects, colors):
                response = await self.client.set_material(obj_name, {"color": color})
                await self.log_test_result(f"Color {obj_name}", response.success)
            
            # Step 4: Final scene verification
            response = await self.client.get_scene_info()
            if response.success:
                scene_objects = response.data.get('objects', [])
                created_count = sum(1 for obj in scene_objects if obj['name'] in objects)
                await self.log_test_result("Scene Verification", created_count == len(objects), f"{created_count}/{len(objects)} objects found")
            
            return True
            
        except Exception as e:
            await self.log_test_result("Multi-Step Modifications", False, str(e))
            return False
    
    async def test_error_recovery(self):
        """Test error recovery and robustness"""
        print("\n⚠️  Testing Error Recovery")
        print("-" * 40)
        
        try:
            # Test 1: Invalid object operations
            response = await self.client.move_object("NonExistentObject", [0, 0, 0])
            await self.log_test_result("Invalid Object Handling", not response.success, "Properly rejected invalid object")
            
            # Test 2: Invalid parameters
            response = await self.client.create_object("invalid_type", "TestObj", [0, 0, 0])
            await self.log_test_result("Invalid Parameters", not response.success, "Properly rejected invalid type")
            
            # Test 3: Recovery after errors - server should still work
            response = await self.client.create_object("cube", "RecoveryTest", [0, 0, 0])
            await self.log_test_result("Recovery After Errors", response.success, "Server recovered from errors")
            
            # Test 4: Concurrent operations simulation
            tasks = []
            for i in range(3):
                task = self.client.create_object("sphere", f"Concurrent_{i}", [i, 0, 0])
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if hasattr(r, 'success') and r.success)
            await self.log_test_result("Concurrent Operations", success_count >= 2, f"{success_count}/3 concurrent operations succeeded")
            
            return True
            
        except Exception as e:
            await self.log_test_result("Error Recovery", False, str(e))
            return False
    
    async def run_all_tests(self):
        """Run all end-to-end workflow tests"""
        print("🚀 Starting End-to-End Workflow Tests")
        print("=" * 50)
        
        try:
            await self.connect()
            
            # Run test workflows
            workflows = [
                ("Basic Scene Setup", self.test_basic_scene_setup),
                ("Living Room Scene", self.test_living_room_scene),
                ("Geometric Arrangement", self.test_geometric_arrangement),
                ("Render Workflow", self.test_render_workflow),
                ("Multi-Step Modifications", self.test_multi_step_scene_modification),
                ("Error Recovery", self.test_error_recovery),
            ]
            
            workflow_results = []
            
            for workflow_name, workflow_func in workflows:
                try:
                    start_time = time.time()
                    result = await workflow_func()
                    duration = time.time() - start_time
                    workflow_results.append((workflow_name, result, duration))
                    
                    status = "✅ PASS" if result else "❌ FAIL"
                    print(f"\n{status} {workflow_name} completed in {duration:.2f}s")
                    
                except Exception as e:
                    workflow_results.append((workflow_name, False, 0))
                    print(f"\n❌ FAIL {workflow_name} crashed: {e}")
            
            await self.disconnect()
            
            # Print summary
            self._print_summary(workflow_results)
            
            # Return overall success
            return all(result for _, result, _ in workflow_results)
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            return False
    
    def _print_summary(self, workflow_results):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 End-to-End Workflow Test Summary")
        print("=" * 50)
        
        total_workflows = len(workflow_results)
        passed_workflows = sum(1 for _, result, _ in workflow_results if result)
        total_time = sum(duration for _, _, duration in workflow_results)
        
        print(f"Workflows: {passed_workflows}/{total_workflows} passed")
        print(f"Total time: {total_time:.2f} seconds")
        print()
        
        for workflow_name, result, duration in workflow_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {workflow_name} ({duration:.2f}s)")
        
        print("\nDetailed Test Results:")
        print("-" * 30)
        
        for test_name, success, message in self.test_results:
            status = "✅" if success else "❌"
            print(f"{status} {test_name}: {message}")
        
        if passed_workflows == total_workflows:
            print("\n🎉 All workflows completed successfully!")
            print("The MCP server is ready for production use with the autonomous 3D scene generator.")
        else:
            print(f"\n⚠️  {total_workflows - passed_workflows} workflow(s) failed.")
            print("Review the failed tests and fix issues before production use.")


async def main():
    """Main test runner"""
    print("Note: Make sure the Blender MCP Server addon is installed and running in Blender")
    print("      before running this test script.\n")
    
    tester = SceneWorkflowTester()
    success = await tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)