import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass
from agents.planner import Plan, PlanStep
from mcp.client import BlenderMCPClient, MCPResponse

@dataclass
class ExecutionResult:
    success: bool
    completed_steps: int
    failed_steps: int
    errors: List[str]
    results: List[MCPResponse]

class ExecutionAgent:
    """Agent responsible for executing plans via Blender MCP"""
    
    def __init__(self, mcp_client: BlenderMCPClient, max_retries: int = 3):
        self.mcp_client = mcp_client
        self.max_retries = max_retries
    
    async def execute_plan(self, plan: Plan) -> ExecutionResult:
        """Execute a complete plan step by step"""
        print(f"Executing plan: {plan.description}")
        
        completed_steps = 0
        failed_steps = 0
        errors = []
        results = []
        
        for step in plan.steps:
            print(f"Step {step.order}: {step.description}")
            
            success = False
            for attempt in range(self.max_retries):
                try:
                    result = await self._execute_step(step)
                    results.append(result)
                    
                    if result.success:
                        print(f"  ✓ Completed: {step.description}")
                        completed_steps += 1
                        success = True
                        break
                    else:
                        print(f"  ✗ Failed (attempt {attempt + 1}): {result.error}")
                        if attempt == self.max_retries - 1:
                            errors.append(f"Step {step.order}: {result.error}")
                
                except Exception as e:
                    error_msg = f"Step {step.order} exception: {str(e)}"
                    print(f"  ✗ Exception (attempt {attempt + 1}): {error_msg}")
                    if attempt == self.max_retries - 1:
                        errors.append(error_msg)
            
            if not success:
                failed_steps += 1
        
        return ExecutionResult(
            success=failed_steps == 0,
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            errors=errors,
            results=results
        )
    
    async def _execute_step(self, step: PlanStep) -> MCPResponse:
        """Execute a single plan step"""
        action = step.action
        params = step.parameters
        
        # Map plan actions to MCP client methods
        if action == "create_object":
            return await self.mcp_client.create_object(
                obj_type=params.get("type", "cube"),
                name=params.get("name", "object"),
                location=params.get("location", [0, 0, 0])
            )
        
        elif action == "move_object":
            return await self.mcp_client.move_object(
                name=params.get("name"),
                location=params.get("location", [0, 0, 0])
            )
        
        elif action == "rotate_object":
            return await self.mcp_client.rotate_object(
                name=params.get("name"),
                rotation=params.get("rotation", [0, 0, 0])
            )
        
        elif action == "scale_object":
            return await self.mcp_client.scale_object(
                name=params.get("name"),
                scale=params.get("scale", [1, 1, 1])
            )
        
        elif action == "set_material":
            return await self.mcp_client.set_material(
                name=params.get("name"),
                material_props=params.get("material", {})
            )
        
        elif action == "clear_scene":
            return await self.mcp_client.clear_scene()
        
        elif action == "render_scene":
            return await self.mcp_client.render_scene(
                output_path=params.get("output_path")
            )
        
        else:
            return MCPResponse(
                success=False,
                error=f"Unknown action: {action}"
            )