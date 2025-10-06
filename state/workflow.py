import asyncio
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass
from agents.planner import LLMPlanner, Plan
from agents.executor import ExecutionAgent, ExecutionResult
from agents.vision import VisionAgent, SceneAnalysis
from mcp.client import BlenderMCPClient
from config.settings import SystemConfig

class WorkflowState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class WorkflowResult:
    success: bool
    final_state: WorkflowState
    user_input: str
    plan: Optional[Plan] = None
    execution_result: Optional[ExecutionResult] = None
    scene_analysis: Optional[SceneAnalysis] = None
    error_message: Optional[str] = None
    render_path: Optional[str] = None

class SceneWorkflow:
    """State machine for managing the complete workflow"""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.state = WorkflowState.IDLE
        
        # Initialize components
        self.mcp_client = BlenderMCPClient(
            host=config.blender_mcp.host,
            port=config.blender_mcp.port,
            timeout=config.blender_mcp.timeout
        )
        
        self.planner = LLMPlanner(config.llm)
        self.executor = ExecutionAgent(self.mcp_client, config.max_retries)
        self.vision_agent = VisionAgent(self.mcp_client)
        
        # Workflow data
        self.current_plan: Optional[Plan] = None
        self.current_execution: Optional[ExecutionResult] = None
        self.current_analysis: Optional[SceneAnalysis] = None
    
    async def process_request(self, user_input: str, capture_render: bool = True) -> WorkflowResult:
        """Process a complete user request through the workflow"""
        print(f"\n🚀 Starting workflow for: '{user_input}'")
        
        try:
            # Step 1: Connect to Blender MCP
            if not await self._ensure_connection():
                return WorkflowResult(
                    success=False,
                    final_state=WorkflowState.ERROR,
                    user_input=user_input,
                    error_message="Failed to connect to Blender MCP server"
                )
            
            # Step 2: Planning
            await self._transition_to(WorkflowState.PLANNING)
            plan = await self._create_plan(user_input)
            if not plan or not plan.steps:
                return WorkflowResult(
                    success=False,
                    final_state=WorkflowState.ERROR,
                    user_input=user_input,
                    error_message="Failed to create execution plan"
                )
            
            # Step 3: Execution
            await self._transition_to(WorkflowState.EXECUTING)
            execution_result = await self._execute_plan(plan)
            
            # Step 4: Observation
            await self._transition_to(WorkflowState.OBSERVING)
            scene_analysis = await self._analyze_scene(capture_render)
            
            # Step 5: Completion
            await self._transition_to(WorkflowState.COMPLETED)
            
            success = execution_result.success and scene_analysis.success
            
            return WorkflowResult(
                success=success,
                final_state=self.state,
                user_input=user_input,
                plan=plan,
                execution_result=execution_result,
                scene_analysis=scene_analysis,
                render_path=scene_analysis.render_path if scene_analysis else None
            )
            
        except Exception as e:
            await self._transition_to(WorkflowState.ERROR)
            return WorkflowResult(
                success=False,
                final_state=WorkflowState.ERROR,
                user_input=user_input,
                error_message=f"Workflow error: {str(e)}"
            )
        
        finally:
            # Always disconnect when done
            await self.mcp_client.disconnect()
    
    async def _ensure_connection(self) -> bool:
        """Ensure connection to Blender MCP server"""
        if not self.mcp_client.connected:
            return await self.mcp_client.connect()
        return True
    
    async def _transition_to(self, new_state: WorkflowState):
        """Transition to a new workflow state"""
        print(f"🔄 {self.state.value} → {new_state.value}")
        self.state = new_state
    
    async def _create_plan(self, user_input: str) -> Optional[Plan]:
        """Create execution plan from user input"""
        print("🧠 Creating plan...")
        try:
            plan = self.planner.create_plan(user_input)
            self.current_plan = plan
            
            print(f"📋 Plan created: {plan.description}")
            print(f"   Steps: {len(plan.steps)}")
            for step in plan.steps:
                print(f"   {step.order}. {step.description}")
            
            return plan
        except Exception as e:
            print(f"❌ Planning failed: {e}")
            return None
    
    async def _execute_plan(self, plan: Plan) -> ExecutionResult:
        """Execute the plan via MCP"""
        print("⚡ Executing plan...")
        try:
            result = await self.executor.execute_plan(plan)
            self.current_execution = result
            
            print(f"📊 Execution completed:")
            print(f"   Success: {result.success}")
            print(f"   Completed steps: {result.completed_steps}")
            print(f"   Failed steps: {result.failed_steps}")
            
            if result.errors:
                print("   Errors:")
                for error in result.errors:
                    print(f"     - {error}")
            
            return result
        except Exception as e:
            print(f"❌ Execution failed: {e}")
            return ExecutionResult(
                success=False,
                completed_steps=0,
                failed_steps=len(plan.steps),
                errors=[str(e)],
                results=[]
            )
    
    async def _analyze_scene(self, capture_render: bool = True) -> SceneAnalysis:
        """Analyze the current scene state"""
        print("👁️ Analyzing scene...")
        try:
            analysis = await self.vision_agent.analyze_scene(capture_render)
            self.current_analysis = analysis
            
            print(f"🔍 Scene analysis:")
            print(f"   Success: {analysis.success}")
            print(f"   Objects: {len(analysis.objects)}")
            print(f"   Description: {analysis.scene_description}")
            
            if analysis.render_path:
                print(f"   Render saved: {analysis.render_path}")
            
            return analysis
        except Exception as e:
            print(f"❌ Scene analysis failed: {e}")
            return SceneAnalysis(
                objects=[],
                scene_description="Analysis failed",
                success=False,
                error=str(e)
            )