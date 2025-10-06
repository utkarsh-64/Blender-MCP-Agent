#!/usr/bin/env python3
"""
Autonomous 3D Scene Generator
Main entry point for the system
"""

import asyncio
import os
from dotenv import load_dotenv
from config.settings import load_config
from state.workflow import SceneWorkflow, WorkflowResult

def print_banner():
    """Print system banner"""
    print("=" * 60)
    print("🎨 Autonomous 3D Scene Generator")
    print("   LLM + Vision + Blender MCP Integration")
    print("=" * 60)

def print_result(result: WorkflowResult):
    """Print workflow result summary"""
    print("\n" + "=" * 50)
    print("📋 WORKFLOW SUMMARY")
    print("=" * 50)
    
    print(f"Input: {result.user_input}")
    print(f"Success: {'✅' if result.success else '❌'}")
    print(f"Final State: {result.final_state.value}")
    
    if result.plan:
        print(f"\nPlan: {result.plan.description}")
        print(f"Steps: {len(result.plan.steps)}")
    
    if result.execution_result:
        exec_result = result.execution_result
        print(f"\nExecution:")
        print(f"  Completed: {exec_result.completed_steps}")
        print(f"  Failed: {exec_result.failed_steps}")
        
        if exec_result.errors:
            print("  Errors:")
            for error in exec_result.errors:
                print(f"    - {error}")
    
    if result.scene_analysis:
        analysis = result.scene_analysis
        print(f"\nScene Analysis:")
        print(f"  Objects: {len(analysis.objects)}")
        print(f"  Description: {analysis.scene_description}")
        
        if analysis.render_path and os.path.exists(analysis.render_path):
            print(f"  Render: {analysis.render_path}")
    
    if result.error_message:
        print(f"\nError: {result.error_message}")
    
    print("=" * 50)

async def interactive_mode():
    """Run in interactive mode"""
    print("\n🎮 Interactive Mode")
    print("Enter natural language commands to manipulate 3D scenes.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    # Load configuration
    config = load_config()
    workflow = SceneWorkflow(config)
    
    example_commands = [
        "Place a red chair next to the wooden table and rotate the lamp 45 degrees",
        "Create a living room with a sofa, coffee table, and floor lamp",
        "Add a blue sphere above a green cube",
        "Clear the scene and create a simple bedroom setup"
    ]
    
    print("💡 Example commands:")
    for i, cmd in enumerate(example_commands, 1):
        print(f"   {i}. {cmd}")
    print()
    
    while True:
        try:
            user_input = input("🎨 Enter command: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Process the request
            result = await workflow.process_request(user_input)
            print_result(result)
            
            # Ask if user wants to continue
            print("\n" + "-" * 30)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

async def batch_mode(commands_file: str):
    """Run in batch mode from file"""
    print(f"\n📁 Batch Mode: {commands_file}")
    
    if not os.path.exists(commands_file):
        print(f"❌ File not found: {commands_file}")
        return
    
    config = load_config()
    workflow = SceneWorkflow(config)
    
    with open(commands_file, 'r') as f:
        commands = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"📋 Processing {len(commands)} commands...")
    
    for i, command in enumerate(commands, 1):
        print(f"\n🔄 Command {i}/{len(commands)}: {command}")
        
        result = await workflow.process_request(command)
        print_result(result)
        
        if not result.success:
            print(f"⚠️ Command {i} failed, continuing...")

def main():
    """Main entry point"""
    load_dotenv()  # Load environment variables
    
    print_banner()
    
    # Check for batch mode
    import sys
    if len(sys.argv) > 1:
        commands_file = sys.argv[1]
        asyncio.run(batch_mode(commands_file))
    else:
        asyncio.run(interactive_mode())

if __name__ == "__main__":
    main()