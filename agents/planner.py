import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import openai
import google.generativeai as genai
from config.settings import LLMConfig

@dataclass
class PlanStep:
    action: str
    parameters: Dict[str, Any]
    description: str
    order: int

@dataclass
class Plan:
    steps: List[PlanStep]
    description: str
    estimated_duration: Optional[int] = None

class LLMPlanner:
    """LLM-based planning agent for 3D scene manipulation"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
        self._setup_client()
    
    def _setup_client(self):
        """Setup LLM client based on provider"""
        if self.config.provider == "openai":
            openai.api_key = self.config.api_key
            self.client = openai
        elif self.config.provider == "google":
            genai.configure(api_key="AIzaSyCuCRBCL9Ix_eMlEOB1v9UgSRR6rBLOBoI")
            self.client = genai.GenerativeModel("gemini-2.5-flash")
    
    def create_plan(self, user_input: str) -> Plan:
        """Create a step-by-step plan from natural language input"""
        
        system_prompt = """You are a 3D scene planning agent. Convert natural language descriptions into structured plans for 3D scene manipulation.

Available actions:
- create_object: Create new objects (cube, sphere, cylinder, plane, etc.)
- move_object: Move objects to specific locations
- rotate_object: Rotate objects (angles in degrees)
- scale_object: Scale objects
- set_material: Set material properties (color, texture, etc.)
- clear_scene: Clear all objects

Return a JSON plan with this structure:
{
    "description": "Brief description of the plan",
    "steps": [
        {
            "action": "action_name",
            "parameters": {"param1": "value1", "param2": "value2"},
            "description": "What this step does",
            "order": 1
        }
    ]
}

Guidelines:
- Use realistic 3D coordinates (x, y, z)
- Rotations in degrees [x_rot, y_rot, z_rot]
- Colors as {"color": [r, g, b, a]} where values are 0-1
- Object names should be descriptive
- Break complex tasks into simple steps
- Consider object relationships (next to, above, etc.)

Example input: "Place a red chair next to a wooden table"
Example output:
{
    "description": "Create a red chair positioned next to a wooden table",
    "steps": [
        {
            "action": "create_object",
            "parameters": {"type": "cube", "name": "table", "location": [0, 0, 0]},
            "description": "Create the wooden table",
            "order": 1
        },
        {
            "action": "scale_object",
            "parameters": {"name": "table", "scale": [2, 1, 0.1]},
            "description": "Scale table to appropriate size",
            "order": 2
        },
        {
            "action": "set_material",
            "parameters": {"name": "table", "material": {"color": [0.6, 0.4, 0.2, 1.0]}},
            "description": "Set wooden brown color for table",
            "order": 3
        },
        {
            "action": "create_object",
            "parameters": {"type": "cube", "name": "chair", "location": [3, 0, 0]},
            "description": "Create chair next to table",
            "order": 4
        },
        {
            "action": "set_material",
            "parameters": {"name": "chair", "material": {"color": [0.8, 0.2, 0.2, 1.0]}},
            "description": "Set red color for chair",
            "order": 5
        }
    ]
}"""

        try:
            if self.config.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Create a plan for: {user_input}"}
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
                plan_json = response.choices[0].message.content
                
            elif self.config.provider == "google":
                prompt = f"{system_prompt}\n\nUser request: {user_input}"
                response = self.client.generate_content(prompt)
                plan_json = response.text
            
            # Parse JSON response
            plan_data = json.loads(plan_json.strip().replace('```json', '').replace('```', ''))
            
            steps = []
            for step_data in plan_data.get("steps", []):
                step = PlanStep(
                    action=step_data["action"],
                    parameters=step_data["parameters"],
                    description=step_data["description"],
                    order=step_data["order"]
                )
                steps.append(step)
            
            return Plan(
                steps=sorted(steps, key=lambda x: x.order),
                description=plan_data.get("description", "Generated plan")
            )
            
        except Exception as e:
            print(f"Planning failed: {e}")
            # Return a simple fallback plan
            return Plan(
                steps=[],
                description=f"Failed to create plan for: {user_input}"
            )